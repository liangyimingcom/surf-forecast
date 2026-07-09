variable "name_prefix" { type = string }
variable "vpc_id" { type = string }
variable "public_subnet_ids" { type = list(string) }
variable "private_subnet_ids" { type = list(string) }
variable "alb_sg_id" { type = string }
variable "app_sg_id" { type = string }
variable "image_repo_url" { type = string }
variable "image_tag" {
  type    = string
  default = "latest"
}
variable "cache_bucket_arn" { type = string }
variable "cache_bucket_name" { type = string }
variable "dynamo_table_arns" { type = list(string) }
variable "container_port" {
  type    = number
  default = 8000
}
variable "cpu" {
  type    = string
  default = "256"
}
variable "memory" {
  type    = string
  default = "512"
}
variable "desired_count" {
  type    = number
  default = 1
}
variable "cookie_secure" {
  description = "会话 cookie secure 标志；内网 HTTP 验证设 0，接 ACM/HTTPS 域名后置 1"
  type        = string
  default     = "0"
}

output "alb_dns_name" { value = aws_lb.this.dns_name }
output "cluster_name" { value = aws_ecs_cluster.this.name }
output "cluster_arn" { value = aws_ecs_cluster.this.arn }
output "service_name" { value = aws_ecs_service.this.name }
output "task_definition_arn" { value = aws_ecs_task_definition.this.arn }
output "log_group" { value = aws_cloudwatch_log_group.app.name }
output "task_role_arn" { value = aws_iam_role.task.arn }
output "exec_role_arn" { value = aws_iam_role.exec.arn }
output "alb_arn_suffix" { value = aws_lb.this.arn_suffix }
output "tg_arn_suffix" { value = aws_lb_target_group.this.arn_suffix }
