# 使用官方轻量级 Python 3.9 镜像
FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 设置时区为上海（可选，方便查看日志时间）
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 直接安装依赖，不依赖外部 requirements.txt 文件
# 包含了你要求的: sanic, sanic-ext, httpx, requests, tqdm, aiosqlite
RUN pip install --no-cache-dir \
    sanic[ext] \
    httpx \
    requests \
    tqdm \
    aiosqlite

# 创建数据挂载目录（确保容器内存在此路径）
RUN mkdir -p /app/data

# 将当前目录下的 app.py 复制到容器的 /app 目录
COPY app.py .

# 暴露 Sanic 默认端口
EXPOSE 8000

# 启动命令
CMD ["python", "app.py"]
