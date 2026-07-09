# cdn 模块 —— CloudFront 唯一公网 HTTPS 入口（ALB 单源，design §1 / north_star 目标架构）
# 前端 HTML 与 /api/* 均由 FastAPI 容器提供（前端已内置镜像），故 CloudFront 用单一 ALB 自定义源。
# *.cloudfront.net 自带 HTTPS，无需自定义域名。ALB SG 仅放行 CloudFront 托管前缀列表 → ALB 不再公网直暴露。

locals {
  alb_origin_id = "alb-origin"
}

resource "aws_cloudfront_distribution" "this" {
  enabled         = true
  comment         = "${var.name_prefix} surf forecast (sole public entry)"
  is_ipv6_enabled = true
  price_class     = "PriceClass_200" # 含亚太边缘，控成本

  # —— 唯一源：ALB（HTTP 回源）——
  origin {
    domain_name = var.alb_dns_name
    origin_id   = local.alb_origin_id
    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "http-only" # ALB 仅 HTTP:80；CloudFront↔用户为 HTTPS
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  # 默认行为：全部转发 ALB（前端 HTML + /api 同源），透传 cookie/query/headers，不缓存（动态会员视图）。
  default_cache_behavior {
    target_origin_id       = local.alb_origin_id
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"]
    cached_methods         = ["GET", "HEAD"]
    compress               = true
    forwarded_values {
      query_string = true
      headers      = ["Host", "Origin", "Referer", "Authorization"]
      cookies {
        forward = "all" # 透传会话 cookie（鉴权）
      }
    }
    min_ttl     = 0
    default_ttl = 0
    max_ttl     = 0
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true # *.cloudfront.net 自带 HTTPS（无自定义域名）
  }

  tags = { Name = "${var.name_prefix}-cdn" }
}
