# scheduler 模块 —— EventBridge Scheduler 每日触发 refresh_job（D5, R5.1）
# 2 时段 cron(GMT+8 02:00 & 14:00) → ECS RunTask（覆盖容器命令为 python -m web.refresh_cli）。

# —— IAM：Scheduler 调 ecs:RunTask + passRole ——
data "aws_iam_policy_document" "assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["scheduler.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "scheduler" {
  name               = "${var.name_prefix}-scheduler"
  assume_role_policy = data.aws_iam_policy_document.assume.json
}

data "aws_iam_policy_document" "scheduler" {
  statement {
    sid       = "RunTask"
    actions   = ["ecs:RunTask"]
    resources = ["${var.task_definition_arn}", "${var.task_definition_arn}:*"]
  }
  statement {
    sid       = "PassRoles"
    actions   = ["iam:PassRole"]
    resources = [var.task_role_arn, var.exec_role_arn]
  }
}

resource "aws_iam_role_policy" "scheduler" {
  name   = "${var.name_prefix}-scheduler-policy"
  role   = aws_iam_role.scheduler.id
  policy = data.aws_iam_policy_document.scheduler.json
}

locals {
  # GMT+8 02:00（覆盖 ECMWF 00Z 同化后）与 14:00（12Z 后）
  crons = {
    morning = "cron(0 2 * * ? *)"
    midday  = "cron(0 14 * * ? *)"
  }
  refresh_command = ["python", "-m", "web.refresh_cli"]
}

resource "aws_scheduler_schedule" "refresh" {
  for_each = local.crons
  name     = "${var.name_prefix}-refresh-${each.key}"

  flexible_time_window {
    mode = "OFF"
  }

  schedule_expression          = each.value
  schedule_expression_timezone = "Asia/Shanghai"

  target {
    arn      = var.cluster_arn
    role_arn = aws_iam_role.scheduler.arn

    ecs_parameters {
      task_definition_arn = var.task_definition_arn
      launch_type         = "FARGATE"
      task_count          = 1

      network_configuration {
        subnets          = var.private_subnet_ids
        security_groups  = [var.app_sg_id]
        assign_public_ip = false
      }
    }

    # 覆盖容器命令为 refresh 入口
    input = jsonencode({
      containerOverrides = [{
        name    = "app"
        command = local.refresh_command
      }]
    })

    retry_policy {
      maximum_retry_attempts = 2
    }
  }
}
