#!/usr/bin/env bash
# deploy.sh —— 浪报生产部署流水线（deployment-and-ops D9）
#
# 子命令：
#   ./deploy.sh test       仅跑 pytest（部署前门禁，D9.2）
#   ./deploy.sh validate   terraform fmt + validate
#   ./deploy.sh apply       terraform apply（创建/更新 AWS 资源；审批由调用者把关）
#   ./deploy.sh build       临时 ARM64 t4g EC2 构建镜像推 ECR（偏好云端构建，自终止）
#   ./deploy.sh redeploy    强制 ECS 拉新镜像滚动部署
#   ./deploy.sh frontend    发布 web/浪报MVP.html → S3 web 桶/index.html + CloudFront 失效
#   ./deploy.sh smoke       ALB/CloudFront 冒烟（health + 未登录 401）
#   ./deploy.sh all         test→validate→apply→build→redeploy→frontend→smoke
#
# 踩坑备忘（已固化）：
#   * Fargate 任务定义须设 AWS_REGION，否则容器 boto3 无 region → DynamoDB/S3 调用失败。
#   * 同名 DynamoDB 表 replace 与异步删除竞态 → ResourceInUseException，删尽后重 apply 即可。
#   * 内网 HTTP 验证 cookie_secure=0；接 CloudFront/HTTPS 后置 1。
set -euo pipefail

# —— 可配置（env 覆盖）——
: "${AWS_PROFILE:=oversea1}"
: "${AWS_REGION:=ap-northeast-1}"
: "${ACCOUNT_ID:=153705321444}"
: "${NAME_PREFIX:=surf-forecast-dev}"
: "${TFVARS:=dev.tfvars.example}"
: "${BUILDER_PROFILE:=surf-forecast-builder}"
export AWS_PROFILE AWS_REGION

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TF_DIR="$ROOT/iac/terraform"
ECR="$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"
REPO="$ECR/$NAME_PREFIX-backend"
CACHE_BUCKET="$NAME_PREFIX-cache-$ACCOUNT_ID-apne1"
WEB_BUCKET="$NAME_PREFIX-web-$ACCOUNT_ID-apne1"
AMI="${AMI:-ami-05bfa8036543cdeb3}"  # AL2023 ARM64 @ ap-northeast-1（按区域调整）

log(){ printf '\033[36m[deploy]\033[0m %s\n' "$*"; }
die(){ printf '\033[31m[deploy] ERROR:\033[0m %s\n' "$*" >&2; exit 1; }

cmd_test(){
  log "pytest 门禁…"
  ( cd "$ROOT" && . .venv/bin/activate 2>/dev/null || true; python -m pytest -q ) \
    || die "测试失败，阻断部署"
}

cmd_validate(){
  log "terraform fmt + validate…"
  ( cd "$TF_DIR" && terraform fmt -recursive && terraform init -backend=false -no-color >/dev/null && terraform validate )
}

cmd_apply(){
  log "terraform apply（$TFVARS）…"
  ( cd "$TF_DIR" && terraform init -no-color >/dev/null && terraform apply -var-file="$TFVARS" -auto-approve )
}

cmd_build(){
  log "打包代码 → S3 → 临时 t4g EC2 构建推镜像…"
  local tgz=/tmp/$NAME_PREFIX-build.tgz
  ( cd "$ROOT" && tar --exclude='./.venv' --exclude='./.git' --exclude='./iac/terraform/.terraform' \
      --exclude='*.tfstate*' --exclude='__pycache__' -czf "$tgz" pyproject.toml src config templates web Dockerfile )
  aws s3api put-object --bucket "$CACHE_BUCKET" --key build/build.tgz --body "$tgz" >/dev/null
  local stamp; stamp=$(date +%s)
  local subnet; subnet=$(aws ec2 describe-subnets --filters Name=default-for-az,Values=true \
      --query 'Subnets[0].SubnetId' --output text)
  local ud; ud=$(cat <<EOF | base64
#!/bin/bash
set -xe
dnf install -y docker; systemctl start docker
for i in \$(seq 1 12); do aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR && break || sleep 5; done
cd /root && aws s3 cp s3://$CACHE_BUCKET/build/build.tgz . --region $AWS_REGION
mkdir -p b && tar -xzf build.tgz -C b && cd b
docker build -t $REPO:latest . && docker push $REPO:latest && echo done | aws s3 cp - s3://$CACHE_BUCKET/build/done-$stamp.txt --region $AWS_REGION
sleep 5; shutdown -h now
EOF
)
  local iid; iid=$(aws ec2 run-instances --image-id "$AMI" --instance-type t4g.medium \
      --subnet-id "$subnet" --associate-public-ip-address \
      --iam-instance-profile Name="$BUILDER_PROFILE" \
      --instance-initiated-shutdown-behavior terminate --user-data "$ud" \
      --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$NAME_PREFIX-builder}]" \
      --query 'Instances[0].InstanceId' --output text)
  log "构建机 $iid 启动，等待构建成功标记 done-$stamp…"
  for i in $(seq 1 40); do
    sleep 15
    if aws s3api head-object --bucket "$CACHE_BUCKET" --key build/done-$stamp.txt >/dev/null 2>&1; then
      log "镜像已推送 ✅"; return 0
    fi
  done
  die "构建超时（10min）—— 构建可能失败，检查 EC2 /var/log/sf-build.log"
}

cmd_redeploy(){
  log "强制 ECS 滚动部署…"
  aws ecs update-service --cluster "$NAME_PREFIX-cluster" --service "$NAME_PREFIX-svc" \
    --force-new-deployment --query 'service.serviceName' --output text
}

cmd_frontend(){
  log "前端已内置后端镜像（ALB 直供 /）→ 重建镜像 + 滚动部署…"
  cmd_build
  cmd_redeploy
}

cmd_smoke(){
  local base="${1:-}"
  [ -z "$base" ] && base=$( cd "$TF_DIR" && terraform output -raw alb_dns_name 2>/dev/null | sed 's#^#http://#' )
  log "冒烟 $base …"
  curl -fsS -m 15 "$base/api/health" && echo
  local code; code=$(curl -s -m 15 -o /dev/null -w '%{http_code}' "$base/api/report?lat=36.092&lon=120.468&days=3")
  [ "$code" = "401" ] && log "未登录 /api/report 正确返回 401 ✅" || die "未登录应 401，实得 $code"
}

cmd_all(){ cmd_test; cmd_validate; cmd_apply; cmd_build; cmd_redeploy; cmd_frontend; sleep 90; cmd_smoke; }

case "${1:-}" in
  test) cmd_test;; validate) cmd_validate;; apply) cmd_apply;; build) cmd_build;;
  redeploy) cmd_redeploy;; frontend) cmd_frontend;; smoke) cmd_smoke "${2:-}";; all) cmd_all;;
  *) echo "用法: $0 {test|validate|apply|build|redeploy|frontend|smoke|all}"; exit 1;;
esac
