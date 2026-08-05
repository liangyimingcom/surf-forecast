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

locals {
  # 剥掉 revision 得到 family 级 ARN：deploy.sh 会在 TF 之外 register 新 revision，
  # 授权/调度若钉死 :N 会在下一次发版后 AccessDenied（2026-07-27 事故根因，R2 P0）。
  task_family_arn = replace(var.task_definition_arn, "/:\\d+$/", "")
}

data "aws_iam_policy_document" "scheduler" {
  statement {
    sid       = "RunTask"
    actions   = ["ecs:RunTask"]
    resources = ["${local.task_family_arn}", "${local.task_family_arn}:*"]
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
  # GMT+8 02:00（覆盖 ECMWF 00Z 同化后）与 14:00（12Z 后）；
  # 06:00 补跑哨兵（R2 决策10）：读 manifest 补缺失点，主跑断链时退化全量兜底。
  crons = {
    morning = { expr = "cron(0 2 * * ? *)", command = ["python", "-m", "web.refresh_cli"] }
    midday  = { expr = "cron(0 14 * * ? *)", command = ["python", "-m", "web.refresh_cli"] }
    retry   = { expr = "cron(0 6 * * ? *)", command = ["python", "-m", "web.refresh_cli", "retry"] }
  }
}

resource "aws_scheduler_schedule" "refresh" {
  for_each = local.crons
  name     = "${var.name_prefix}-refresh-${each.key}"

  flexible_time_window {
    mode = "OFF"
  }

  schedule_expression          = each.value.expr
  schedule_expression_timezone = "Asia/Shanghai"

  target {
    arn      = var.cluster_arn
    role_arn = aws_iam_role.scheduler.arn

    ecs_parameters {
      # family 级 ARN（无 :revision）→ 始终跑最新 revision，发版后无需改调度
      task_definition_arn = local.task_family_arn
      launch_type         = "FARGATE"
      task_count          = 1

      network_configuration {
        subnets          = var.private_subnet_ids
        security_groups  = [var.app_sg_id]
        assign_public_ip = false
      }
    }

    # 覆盖容器命令为 refresh 入口（retry 档带 retry 参数）
    input = jsonencode({
      containerOverrides = [{
        name    = "app"
        command = each.value.command
      }]
    })

    retry_policy {
      maximum_retry_attempts = 2
    }
  }
}
