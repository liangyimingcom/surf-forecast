variable "name_prefix" { type = string }
variable "account_id" { type = string }
variable "region" { type = string }

locals {
  all_tables = merge(aws_dynamodb_table.single, aws_dynamodb_table.composite)
}

output "cache_bucket_name" { value = aws_s3_bucket.cache.id }
output "cache_bucket_arn" { value = aws_s3_bucket.cache.arn }
output "web_bucket_name" { value = aws_s3_bucket.web.id }
output "web_bucket_arn" { value = aws_s3_bucket.web.arn }
output "web_bucket_regional_domain" { value = aws_s3_bucket.web.bucket_regional_domain_name }
output "table_names" { value = { for k, t in local.all_tables : k => t.name } }
output "table_arns" { value = [for t in local.all_tables : t.arn] }
