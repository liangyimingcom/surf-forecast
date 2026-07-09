# Root 编排 —— 串联各模块（D1）
# 已实现骨架：network / ecr / storage。后续追加：compute(Fargate+ALB) / cdn / scheduler / observability / security。

locals {
  name_prefix = "${var.project}-${var.env}"
}

module "network" {
  source                    = "./modules/network"
  name_prefix               = local.name_prefix
  vpc_cidr                  = var.vpc_cidr
  az_count                  = var.az_count
  region                    = var.region
  cloudfront_prefix_list_id = var.cloudfront_prefix_list_id
}

module "ecr" {
  source      = "./modules/ecr"
  name_prefix = local.name_prefix
}

module "storage" {
  source      = "./modules/storage"
  name_prefix = local.name_prefix
  account_id  = var.account_id
  region      = var.region
}

module "compute" {
  source             = "./modules/compute"
  name_prefix        = local.name_prefix
  vpc_id             = module.network.vpc_id
  public_subnet_ids  = module.network.public_subnet_ids
  private_subnet_ids = module.network.private_subnet_ids
  alb_sg_id          = module.network.alb_sg_id
  app_sg_id          = module.network.app_sg_id
  image_repo_url     = module.ecr.repository_url
  image_tag          = "latest"
  cache_bucket_arn   = module.storage.cache_bucket_arn
  cache_bucket_name  = module.storage.cache_bucket_name
  dynamo_table_arns  = module.storage.table_arns
}

module "scheduler" {
  source              = "./modules/scheduler"
  name_prefix         = local.name_prefix
  cluster_arn         = module.compute.cluster_arn
  task_definition_arn = module.compute.task_definition_arn
  task_role_arn       = module.compute.task_role_arn
  exec_role_arn       = module.compute.exec_role_arn
  private_subnet_ids  = module.network.private_subnet_ids
  app_sg_id           = module.network.app_sg_id
}

module "observability" {
  source         = "./modules/observability"
  name_prefix    = local.name_prefix
  region         = var.region
  log_group      = module.compute.log_group
  alb_arn_suffix = module.compute.alb_arn_suffix
  tg_arn_suffix  = module.compute.tg_arn_suffix
  cluster_name   = module.compute.cluster_name
  service_name   = module.compute.service_name
}

# cdn 模块 —— CloudFront 唯一公网 HTTPS 入口（ALB 单源）。
# ALB SG 仅放行 CloudFront 前缀列表 → ALB 不再公网直暴露，DyePack/Epoxy 风险根治。
module "cdn" {
  source       = "./modules/cdn"
  name_prefix  = local.name_prefix
  alb_dns_name = module.compute.alb_dns_name
}
