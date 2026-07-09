# Root 输出

output "vpc_id" {
  value = module.network.vpc_id
}

output "private_subnet_ids" {
  value = module.network.private_subnet_ids
}

output "public_subnet_ids" {
  value = module.network.public_subnet_ids
}

output "ecr_repository_url" {
  value = module.ecr.repository_url
}

output "cache_bucket" {
  value = module.storage.cache_bucket_name
}

output "web_bucket" {
  value = module.storage.web_bucket_name
}

output "dynamodb_tables" {
  value = module.storage.table_names
}

output "alb_dns_name" {
  value = module.compute.alb_dns_name
}

output "ecs_cluster" {
  value = module.compute.cluster_name
}

output "ecs_service" {
  value = module.compute.service_name
}

# 公网唯一入口 = CloudFront(HTTPS)；ALB 仅 CloudFront 前缀列表可达（不再公网直暴露）。
output "cloudfront_domain" {
  description = "公网 HTTPS 入口（唯一对外入口）"
  value       = module.cdn.cloudfront_domain
}

output "distribution_id" {
  description = "CloudFront 分配 ID（前端发布后失效缓存用）"
  value       = module.cdn.distribution_id
}
