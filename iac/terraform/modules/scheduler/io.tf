variable "name_prefix" { type = string }
variable "cluster_arn" { type = string }
variable "task_definition_arn" { type = string }
variable "task_role_arn" { type = string }
variable "exec_role_arn" { type = string }
variable "private_subnet_ids" { type = list(string) }
variable "app_sg_id" { type = string }

output "schedule_names" { value = [for s in aws_scheduler_schedule.refresh : s.name] }
