# ============== Builder ==============
FROM python:3.11-slim AS builder

WORKDIR /build

# 安装依赖到独立目录
COPY pyproject.toml .
RUN pip install --no-cache-dir --prefix=/install .

# ============== Runtime ==============
FROM python:3.11-slim

WORKDIR /app

# 从 builder 复制已安装的依赖
COPY --from=builder /install /usr/local

# 复制应用代码
COPY app/ ./app/
COPY SKILL.md .

# 创建数据目录
RUN mkdir -p /app/data

# 非 root 用户
RUN adduser --disabled-password --gecos "" appuser && \
    chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
