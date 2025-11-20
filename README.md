# sanic_bot



1. 构建镜像

在包含 Dockerfile 的目录下运行：

~~~Bash
docker build -t sanic-tg-bot
~~~
2. 运行容器（核心步骤）

假设：

你想通过主机的 8080 端口访问容器的 8000 端口。

你想把主机当前目录下的 data 文件夹挂载到容器里，用于保存数据库。

你需要填入你的 Telegram Bot Token 和你的 Chat ID。

~~~Bash
# 先在主机创建数据文件夹，防止 Docker 自动创建为 root 权限
mkdir -p $(pwd)/data

docker run -d \
  --name my-tg-bot \
  -p 8080:8000 \
  -v $(pwd)/data:/app/data \
  -e BOT_TOKEN="你的_TELEGRAM_BOT_TOKEN" \
  -e CHAT_ID="你的_默认_CHAT_ID" \
  sanic-tg-bot
-p 8080:8000: 主机端口:容器端口。

-v $(pwd)/data:/app/data: 将主机的 data 目录映射到容器内的 /app/data。容器写入的数据库文件会直接出现在你主机的 data 文件夹里。
~~~
如何测试与使用

1. 发送 Markdown 消息

使用 curl 或 Postman 向主机端口发送请求：

~~~Bash
curl -X POST http://localhost:8080/send \
     -H "Content-Type: application/json" \
     -d '{
           "text": "*重要通知*：\n服务器备份已完成！\n状态：`Success`"
         }'
~~~
如果成功，你的 Telegram 机器人会收到加粗的“重要通知”和代码格式的“Success”。

2. 查看发送历史

~~~Bash
curl http://localhost:8080/history
~~~

返回示例：

~~~JSON
[
  {
    "id": 1,
    "ip": "172.17.0.1",
    "time": "2023-10-27 10:00:00",
    "content": "*重要通知*...",
    "success": true
  }
]
~~~
