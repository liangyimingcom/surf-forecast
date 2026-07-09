# 后端镜像 —— FastAPI + surf_forecast 引擎（deploy 1.2）
# 偏好云端 ARM64 t4g 构建；容器内 0.0.0.0:8000 由 ALB(私有子网) 前置，不直接暴露公网。
FROM --platform=linux/arm64 python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    TZ=Asia/Shanghai

WORKDIR /app

# 先装依赖（利用层缓存）
COPY pyproject.toml ./
COPY src ./src
COPY config ./config
COPY templates ./templates
COPY web ./frontend

RUN pip install --upgrade pip && pip install ".[web]"

# 非 root 运行
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# 健康检查命中 /api/health
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health').status==200 else 1)"

CMD ["uvicorn", "web.app:app", "--host", "0.0.0.0", "--port", "8000"]
