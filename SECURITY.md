# 安全 · 密钥与端点约定（surf-forecast，public 仓库）

> 本仓库 **public**。任何密钥/内部端点绝不入库。

## 红线
1. **LLM/网关 key、DB 凭据、任何 secret** 只放 **AWS Secrets Manager**（ECS 任务 `secrets: valueFrom` 注入），代码只 `os.getenv("SF_LLM_KEY")` 引用名字，**绝不硬编码/写进文档/回显**。
2. **内部端点/主机名**（如 `*.people.aws.dev` 的 LLM 网关）用占位符 `<LLM_GATEWAY_URL>` / `<llm-gateway-host>`；实值仅存 Secrets/task def env，不写进仓库。
3. 已建密钥：`surf-forecast-dev/llm-key`（Secrets Manager）；生产 task def 以 `SF_LLM_KEY` valueFrom 注入 + `SF_LLM_URL`/`SF_LLM_MODEL` 为 env。

## 防泄漏（pre-commit 钩子）
启用一次（每个 clone）：
```bash
git config core.hooksPath .githooks
```
`.githooks/pre-commit` 扫描暂存文件，命中即拦：
- OpenAI 风格 key `sk-…` / AWS `AKIA…` / 私钥块 `-----BEGIN … PRIVATE KEY-----`
- 内部网关 host `*.people.aws.dev` / 明文 `SF_LLM_KEY=值`
- 白名单：占位符 `<…>`、示例 `EXAMPLE`/`sk-ABCDEF`。确认误报用 `git commit --no-verify`。

## 历史说明
- key `sk-…` **从未入库**（git 全历史 0 命中，仅经 shell/Secrets 使用）。
- 网关 URL/IP 曾出现在历史提交的设计文档中（端点非密钥）；当前树已脱敏。如需彻底清历史，用 `git filter-repo` 重写并 force-push（会破坏既有 clone，慎用）。

## .gitignore 覆盖
`.venv/`、`__pycache__/`、terraform state/tfvars、`.env`、`*.key`/`*.pem`、`secrets/`、运行时产物(`pipeline_audit.jsonl`/`ddd/`/`.pipeline-artifacts/`)。
