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
: "${PROD_URL:=https://d2hmhl7n8yga53.cloudfront.net}"
export AWS_PROFILE AWS_REGION

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TF_DIR="$ROOT/iac/terraform"
ECR="$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"
REPO="$ECR/$NAME_PREFIX-backend"
CACHE_BUCKET="$NAME_PREFIX-cache-$ACCOUNT_ID-apne1"
WEB_BUCKET="$NAME_PREFIX-web-$ACCOUNT_ID-apne1"
# AL2023 ARM64：默认走 SSM 别名解析最新（AMI id 会随 AL2023 滚动下线，钉死会 InvalidAMIID，2026-07-28 实踩）
AMI="${AMI:-$(aws ssm get-parameter --name /aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-arm64 --query 'Parameter.Value' --output text 2>/dev/null || echo ami-05bfa8036543cdeb3)}"

log(){ printf '\033[36m[deploy]\033[0m %s\n' "$*"; }
die(){ printf '\033[31m[deploy] ERROR:\033[0m %s\n' "$*" >&2; exit 1; }

# 审计链：发布/回滚成功后追加 CHANGELOG（时间·版本·commit·摘要·结果，GMT+8）
changelog_add(){
  local summary="${1:-发布}" result="${2:-成功}"
  local ver; ver=$(tr -d '[:space:]' < "$ROOT/VERSION" 2>/dev/null); ver="${ver:-0.0.0}"
  local commit; commit=$(cd "$ROOT" && git rev-parse --short HEAD 2>/dev/null || echo unknown)
  local ts; ts=$(TZ=Asia/Shanghai date '+%Y-%m-%d %H:%M')
  printf -- '- %s GMT+8 · v%s · %s · %s · %s\n' "$ts" "$ver" "$commit" "$summary" "$result" >> "$ROOT/CHANGELOG.md"
  log "CHANGELOG 已记：v$ver · $commit · $summary · $result"
}

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
  log "terraform apply（${TFVARS}）…"
  ( cd "$TF_DIR" && terraform init -no-color >/dev/null && terraform apply -var-file="$TFVARS" )
}

cmd_build(){
  log "打包代码 → S3 → 临时 t4g EC2 构建推镜像…"
  local tgz=/tmp/$NAME_PREFIX-build.tgz
  ( cd "$ROOT" && tar --exclude='./.venv' --exclude='./.git' --exclude='./iac/terraform/.terraform' \
      --exclude='./web/frontend/node_modules' --exclude='./web/frontend/dist' \
      --exclude='*.tfstate*' --exclude='__pycache__' -czf "$tgz" pyproject.toml src config templates web Dockerfile )
  aws s3api put-object --bucket "$CACHE_BUCKET" --key build/build.tgz --body "$tgz" >/dev/null
  local stamp; stamp=$(date +%s)
  local ver; ver=$(tr -d '[:space:]' < "$ROOT/VERSION" 2>/dev/null); ver="${ver:-0.0.0}"
  # ${ver} 必须带花括号：本行含全角括号等多字节字符，某些 locale 下 bash 词法把
  # 紧随 $ver 的多字节字符并进变量名 → "ver�: unbound variable"（2026-07-28 实踩）
  log "构建版本 v${ver}（同时打 :latest 与 :v${ver} 不可变 tag）"
  local subnet; subnet=$(aws ec2 describe-subnets --filters Name=default-for-az,Values=true \
      --query 'Subnets[0].SubnetId' --output text)
  local ud; ud=$(cat <<EOF | base64
#!/bin/bash
set -xe
dnf install -y docker; systemctl start docker
for i in \$(seq 1 12); do aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR && break || sleep 5; done
cd /root && aws s3 cp s3://$CACHE_BUCKET/build/build.tgz . --region $AWS_REGION
mkdir -p b && tar -xzf build.tgz -C b && cd b
docker build -t $REPO:latest . && docker tag $REPO:latest $REPO:v$ver && docker push $REPO:latest && docker push $REPO:v$ver && echo done | aws s3 cp - s3://$CACHE_BUCKET/build/done-$stamp.txt --region $AWS_REGION
sleep 5; shutdown -h now
EOF
)
  local iid; iid=$(aws ec2 run-instances --image-id "$AMI" --instance-type t4g.medium \
      --subnet-id "$subnet" --associate-public-ip-address \
      --iam-instance-profile Name="$BUILDER_PROFILE" \
      --instance-initiated-shutdown-behavior terminate --user-data "$ud" \
      --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$NAME_PREFIX-builder}]" \
      --query 'Instances[0].InstanceId' --output text)
  log "构建机 $iid 启动，等待构建成功标记 done-${stamp}…"
  if [ -n "${SF_BUILD_NOWAIT:-}" ]; then
    printf '%s' "$stamp" > /tmp/sf_build_stamp
    log "NOWAIT：已启动 ${iid}，跳过阻塞轮询（stamp=$stamp 存 /tmp/sf_build_stamp，外部轮询 done-\${stamp}）"
    return 0
  fi
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
  changelog_add "${SF_RELEASE_NOTE:-frontend 发布}" "已滚动部署"
}

cmd_smoke(){
  local base="${1:-}"
  [ -z "$base" ] && base=$( cd "$TF_DIR" && terraform output -raw alb_dns_name 2>/dev/null | sed 's#^#http://#' )
  log "冒烟 ${base} …"
  curl -fsS -m 15 "${base}/api/health" && echo
  # 公开面：v0.3.x 诚实分层鉴权后，一期 report/recommend/catalog/status 匿名即可取
  # （旧断言"未登录 /api/report 应 401"已随 member_gate 分层作废，会误报）
  local p code
  for p in "/api/report?lat=36.092&lon=120.468&days=3" "/api/recommend?region=%E5%B9%BF%E4%B8%9C" "/api/catalog" "/api/status"; do
    code=$(curl -s -m 20 -o /dev/null -w '%{http_code}' "${base}${p}")
    [ "${code}" = "200" ] || die "公开端点 ${p} 应 200，实得 ${code}"
    log "公开端点 ${p} → 200 ✅"
  done
  # 合规红线（不可放宽）：/api/cams 直播源为逆向所得、仅研究用途，必须对匿名返回 401
  code=$(curl -s -m 20 -o /dev/null -w '%{http_code}' "${base}/api/cams")
  [ "${code}" = "401" ] || die "合规红线破防：未登录 /api/cams 必须 401，实得 ${code}"
  log "合规红线 /api/cams 未登录 401 ✅"
}

cmd_all(){ cmd_test; cmd_validate; cmd_apply; cmd_build; cmd_redeploy; cmd_frontend; sleep 90; cmd_smoke; }

# 回滚：切 ECS 到指定/上一个不可变版本镜像 :vX.Y.Z（不重建镜像）。用法: rollback [vX.Y.Z]
cmd_rollback(){
  local target="${1:-}"; [ -n "$target" ] && target="${target#v}" && target="v$target"   # 归一化带 v 前缀
  # ECR 上按推送时间倒序的 :vX.Y.Z tag 列表（去重保序）
  local vtags; vtags=$(aws ecr describe-images --repository-name "$NAME_PREFIX-backend" \
      --query "reverse(sort_by(imageDetails,&imagePushedAt))[].imageTags" --output json 2>/dev/null \
      | python3 -c "import sys,json;seen=[];[seen.append(t) for g in json.load(sys.stdin) if g for t in g if str(t).startswith('v') and t not in seen];print('\n'.join(seen))")
  [ -z "$vtags" ] && die "ECR 无 :vX.Y.Z 版本 tag，无法回滚（需先按 P0.1 发过带版本镜像）"
  if [ -z "$target" ]; then
    target=$(echo "$vtags" | sed -n '2p')   # 第 2 新 = 上一版
    [ -z "$target" ] && die "只有一个版本($(echo "$vtags"|head -1))，无上一版可回滚"
    log "未指定目标，回滚到上一版：$target"
  fi
  echo "$vtags" | grep -qx "$target" || die "目标 $target 不在 ECR 版本列表中：$(echo "$vtags"|tr '\n' ' ')"
  local td; td=$(aws ecs describe-services --cluster "$NAME_PREFIX-cluster" --service "$NAME_PREFIX-svc" \
      --query 'services[0].taskDefinition' --output text)
  local newdef; newdef=$(aws ecs describe-task-definition --task-definition "$td" \
      --query 'taskDefinition' --output json \
      | jq --arg img "$REPO:$target" 'del(.taskDefinitionArn,.revision,.status,.registeredAt,.registeredBy,.requiresAttributes,.compatibilities) | .containerDefinitions[0].image=$img')
  local arn; arn=$(aws ecs register-task-definition --cli-input-json "$newdef" \
      --query 'taskDefinition.taskDefinitionArn' --output text)
  log "回滚：注册新 task def ${arn}（image=$REPO:${target}）→ 切服务"
  aws ecs update-service --cluster "$NAME_PREFIX-cluster" --service "$NAME_PREFIX-svc" \
      --task-definition "$arn" --force-new-deployment --query 'service.serviceName' --output text
  changelog_add "rollback → $target" "已切 task def+滚动"
}

# 金丝雀：部署后对目标(默认生产)跑冻结基线真浏览器 E2E + 0 JS 报错；失败→自动 rollback。用法: canary [URL]
cmd_canary(){
  local base="${1:-$PROD_URL}"
  # 金丝雀必须跑**生产实际服的那套前端**的 E2E。
  # 2026-08-05 修：此处原为冻结基线 new_features.mjs（单 HTML 时代的 DOM：window.showTab/#maintab），
  # 而自 v0.2.0 起 Dockerfile 设 SF_SPA_DIST=/app/spa，生产服的是 Vue SPA
  # → 旧套件对生产必然失败 → 触发对一个**健康版本**的自动回滚（误回滚陷阱）。
  # 单 HTML 现仅作镜像内兜底，其套件不再代表生产。
  log "金丝雀：对 $base 跑真浏览器 E2E（vue_spa.mjs，生产服的是 Vue SPA）…"
  if ( cd "$ROOT" && node web/e2e/vue_spa.mjs "$base" ); then
    log "金丝雀通过 ✅"
    changelog_add "canary@$base" "通过"
  else
    log "金丝雀失败 ✗ → 自动 rollback 上一版本"
    changelog_add "canary@$base" "失败→触发rollback"
    cmd_rollback || die "金丝雀失败且 rollback 亦失败——需人工介入"
    die "金丝雀失败，已触发 rollback（详见 CHANGELOG）"
  fi
}

case "${1:-}" in
  test) cmd_test;; validate) cmd_validate;; apply) cmd_apply;; build) cmd_build;;
  redeploy) cmd_redeploy;; frontend) cmd_frontend;; smoke) cmd_smoke "${2:-}";; all) cmd_all;;
  rollback) cmd_rollback "${2:-}";;
  canary) cmd_canary "${2:-}";;
  *) echo "用法: $0 {test|validate|apply|build|redeploy|frontend|smoke|rollback [vX.Y.Z]|canary [URL]|all}"; exit 1;;
esac
