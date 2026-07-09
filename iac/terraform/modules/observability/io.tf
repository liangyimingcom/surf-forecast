variable "name_prefix" { type = string }
variable "region" { type = string }
variable "log_group" { type = string }
variable "alb_arn_suffix" { type = string }
variable "tg_arn_suffix" { type = string }
variable "cluster_name" { type = string }
variable "service_name" { type = string }

output "sns_topic_arn" { value = aws_sns_topic.alerts.arn }
output "dashboard_name" { value = aws_cloudwatch_dashboard.main.dashboard_name }
