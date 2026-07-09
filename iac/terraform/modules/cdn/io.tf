# cdn 模块 IO —— ALB 单源（移除 S3/OAC 相关变量）

variable "name_prefix" { type = string }
variable "alb_dns_name" {
  description = "回源 ALB 的 DNS 名（compute 模块输出）"
  type        = string
}

output "cloudfront_domain" {
  description = "公网 HTTPS 入口域名"
  value       = aws_cloudfront_distribution.this.domain_name
}
output "distribution_id" {
  description = "CloudFront 分配 ID（用于失效缓存）"
  value       = aws_cloudfront_distribution.this.id
}
