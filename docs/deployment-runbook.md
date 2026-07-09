# 部署 Runbook —— 浪报 Surf Forecast（deployment-and-ops D9 8.3）

> 区域 ap-northeast-1 ｜ profile oversea1 ｜ account 153705321444 ｜ 形态 B（Fargate+ALB+DynamoDB+S3/CloudFront）。
> 凭证过期先在终端 `ada credentials update`（被安全过滤拦截，须人工执行）。

## 一键部署
```bash
# 全流程：测试门禁 → tf 校验 → apply → EC2 构建镜像 → 滚动部署 → 发布前端 → 冒烟
./deploy.sh all
```

## 分步
```bash
./deploy.sh test       # pytest 门禁（失败阻断）
./deploy.sh validate   # terraform fmt + validate
./deploy.sh apply      # 创建/更新 AWS 资源（先人工审阅 plan）
./deploy.sh build      # 临时 t4g EC2 构建 arm64 镜像推 ECR（自终止）
./deploy.sh redeploy   # 强制 ECS 拉新镜像
./deploy.sh frontend   # 发布 web/浪报MVP.html → S3 + CloudFront 失效
./deploy.sh smoke      # /api/health + 未登录 401 冒烟
```

## 当前线上资源（dev）
| 资源 | 值 |
|------|----|
| ALB | surf-forecast-dev-alb-1774951441.ap-northeast-1.elb.amazonaws.com |
| ECR | 153705321444.dkr.ecr.ap-northeast-1.amazonaws.com/surf-forecast-dev-backend |
| 集群/服务 | surf-forecast-dev-cluster / surf-forecast-dev-svc |
| DynamoDB | surf-forecast-dev-{users,sessions,accuracy_votes,saved_spots} |
| 缓存桶/站点桶 | surf-forecast-dev-cache/web-153705321444-apne1 |
| CloudFront | apply cdn 后 `terraform output cloudfront_domain` |

## 回滚
- **应用回滚**：ECR 保留近 10 镜像 → 重 tag 旧镜像为 latest 后 `./deploy.sh redeploy`；或回退代码重 build。
- **基础设施回滚**：`git checkout <prev> -- iac/terraform && terraform apply`。
- **紧急下线**：`aws ecs update-service --desired-count 0`（或 `terraform destroy` 全拆，省成本）。

## 切到 HTTPS/CloudFront 后的收尾
1. apply cdn 模块 → 拿到 `*.cloudfront.net`。
2. `./deploy.sh frontend` 发布前端（同源 `/api/*` 经 CloudFront 回源 ALB）。
3. 把任务定义 `cookie_secure` 改回 `"1"`（HTTPS 下安全 cookie），重 apply + redeploy。

## 踩坑备忘（已固化进 deploy.sh / 教训库）
- **Fargate 须设 `AWS_REGION` env**，否则容器 boto3 无 region → DynamoDB/S3 调用失败（应用 500）。
- **同名 DynamoDB 表 replace** 与异步删除竞态 → `ResourceInUseException`；删尽后重 `apply` 即补建。
- **内存 store 仅 dev**；生产须 `SF_STORE=dynamo`（任务定义已设），否则重启丢用户。
- **cookie_secure**：内网 HTTP 验证=0；HTTPS/CloudFront=1。

## 成本与停机
方案 B 约 $50–75/月（NAT+ALB+Fargate 常驻为大头）。长期不用 `terraform destroy` 全拆。
