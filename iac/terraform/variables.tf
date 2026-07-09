# Root 变量 —— 环境参数化（D1.2，禁硬编码账号/区域/域名）

variable "region" {
  description = "AWS 区域"
  type        = string
  default     = "ap-northeast-1"
}

variable "env" {
  description = "环境：dev/staging/prod"
  type        = string
  default     = "dev"
}

variable "project" {
  description = "项目前缀"
  type        = string
  default     = "surf-forecast"
}

variable "account_id" {
  description = "AWS 账号 ID（用于桶命名等）"
  type        = string
  default     = "153705321444"
}

variable "vpc_cidr" {
  description = "VPC CIDR"
  type        = string
  default     = "10.40.0.0/16"
}

variable "az_count" {
  description = "可用区数量（≥2 以满足 ALB）"
  type        = number
  default     = 2
}

variable "domain_name" {
  description = "对外公网域名（留空则暂不创建 Route53/ACM；people.aws.dev 为内部域，不可对外）"
  type        = string
  default     = ""
}

variable "spot_facing_deg" {
  description = "默认浪点朝向（青岛山东头 SSE）"
  type        = number
  default     = 157
}

variable "cloudfront_prefix_list_id" {
  description = "CloudFront origin-facing 托管前缀列表 ID（ap-northeast-1 = pl-58a04531）。ALB SG 仅放行此前缀列表，公网入口唯一为 CloudFront(HTTPS)。安全红线：禁用 0.0.0.0/0 与裸 CIDR。"
  type        = string
  default     = "pl-58a04531"
}
