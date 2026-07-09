variable "name_prefix" { type = string }
variable "vpc_cidr" { type = string }
variable "az_count" { type = number }
variable "region" { type = string }

variable "cloudfront_prefix_list_id" {
  description = "CloudFront origin-facing 托管前缀列表 ID（ap-northeast-1 = pl-58a04531）。ALB SG 仅放行此前缀列表的 HTTP:80，杜绝公网直暴露。"
  type        = string

  validation {
    condition     = can(regex("^pl-", var.cloudfront_prefix_list_id))
    error_message = "必须是 AWS 托管前缀列表 ID（pl-...）。禁止用 0.0.0.0/0 或裸 CIDR，否则会被 DyePack/Epoxy 判定公网无认证并删监听器。"
  }
}
