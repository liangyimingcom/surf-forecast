# storage 模块 —— DynamoDB(on-demand) + S3(预算JSON缓存 / 前端站点)（D4, design §4）

locals {
  # 单键表：{name = hash_key}
  hash_tables = {
    users         = "email" # 按邮箱登录查找
    sessions      = "token" # 服务端会话，配 TTL 自动过期
    spot_registry = "slug"  # custom-spots 全局去重浪点注册表（PK=slug，作缓存键前缀）
  }
  # 复合键表：{name = {pk, sk}}
  range_tables = {
    saved_spots    = { pk = "email", sk = "slug" } # custom-spots：SK=slug（与 DynamoDBStore 对齐，不可变缓存键）
    accuracy_votes = { pk = "email", sk = "voteId" }
  }
}

resource "aws_dynamodb_table" "single" {
  for_each     = local.hash_tables
  name         = "${var.name_prefix}-${each.key}"
  billing_mode = "PAY_PER_REQUEST" # on-demand（P0 决策）
  hash_key     = each.value

  attribute {
    name = each.value
    type = "S"
  }

  dynamic "ttl" {
    for_each = each.key == "sessions" ? [1] : []
    content {
      attribute_name = "expiresAt"
      enabled        = true
    }
  }

  point_in_time_recovery {
    enabled = true
  }
}

resource "aws_dynamodb_table" "composite" {
  for_each     = local.range_tables
  name         = "${var.name_prefix}-${each.key}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = each.value.pk
  range_key    = each.value.sk

  attribute {
    name = each.value.pk
    type = "S"
  }
  attribute {
    name = each.value.sk
    type = "S"
  }

  point_in_time_recovery {
    enabled = true
  }
}

# —— S3：预算浪报 JSON 缓存（键 spot/date、spot/history/date）——
resource "aws_s3_bucket" "cache" {
  bucket = "${var.name_prefix}-cache-${var.account_id}-apne1"
}

resource "aws_s3_bucket_public_access_block" "cache" {
  bucket                  = aws_s3_bucket.cache.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# —— S3：前端静态站点（经 CloudFront OAC 分发）——
resource "aws_s3_bucket" "web" {
  bucket = "${var.name_prefix}-web-${var.account_id}-apne1"
}

resource "aws_s3_bucket_public_access_block" "web" {
  bucket                  = aws_s3_bucket.web.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "web" {
  bucket = aws_s3_bucket.web.id
  versioning_configuration {
    status = "Enabled"
  }
}
