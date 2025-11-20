# 使用官方轻量级 Python 镜像
FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 1. 安装依赖 (利用缓存机制，先拷贝 requirements)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 2. 拷贝代码
COPY src/ ./src/

# 3. 暴露端口
EXPOSE 8000

# 4. 设置挂载点目录权限（可选，防止权限问题）
RUN mkdir -p /app/data

# 5. 启动命令
# 注意：这里我们直接运行 src/app.py
CMD ["python", "src/app.py"]
