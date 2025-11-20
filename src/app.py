import os
import time
from datetime import datetime
from sanic import Sanic, response
from sanic.log import logger
import httpx
import aiosqlite

app = Sanic("TelegramBotService")

# 配置：优先从环境变量获取
BOT_TOKEN = os.getenv("BOT_TOKEN")
DEFAULT_CHAT_ID = os.getenv("CHAT_ID")
DB_PATH = "/app/data/history.db"  # 数据库存在卷挂载的目录里

# 1. 数据库初始化
@app.before_server_start
async def setup_db(app, loop):
    # 确保数据目录存在
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender_ip TEXT,
                send_time TEXT,
                content TEXT,
                success BOOLEAN,
                api_response TEXT
            )
        """)
        await db.commit()

# 2. 发送消息接口
@app.post("/send")
async def send_message(request):
    """
    接收 JSON: { "text": "**Hello** World", "chat_id": "可选" }
    """
    data = request.json
    text = data.get("text", "")
    # 如果请求里没带chat_id，就用环境变量里的默认值
    target_chat_id = data.get("chat_id", DEFAULT_CHAT_ID)
    
    if not text or not target_chat_id:
        return response.json({"error": "Missing text or chat_id"}, status=400)

    sender_ip = request.ip
    send_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    success = False
    api_res_text = ""

    # 调用 Telegram API
    tg_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": target_chat_id,
        "text": text,
        "parse_mode": "Markdown" # 注意：Telegram MarkdownV2 需要转义很多字符，这里暂时用旧版 Markdown 兼容性更好
    }

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(tg_url, json=payload, timeout=10.0)
            api_res_text = resp.text
            if resp.status_code == 200:
                success = True
            else:
                logger.error(f"Telegram Error: {resp.text}")
    except Exception as e:
        api_res_text = str(e)
        logger.error(f"Request Error: {e}")

    # 记录日志到数据库
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO logs (sender_ip, send_time, content, success, api_response) VALUES (?, ?, ?, ?, ?)",
            (sender_ip, send_time, text, success, api_res_text)
        )
        await db.commit()

    return response.json({
        "status": "sent" if success else "failed",
        "telegram_response": api_res_text
    }, status=200 if success else 500)

# 3. 查看历史记录接口
@app.get("/history")
async def get_history(request):
    limit = int(request.args.get("limit", 50)) # 默认只看最近50条
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM logs ORDER BY id DESC LIMIT ?", (limit,))
        rows = await cursor.fetchall()
        
        results = []
        for row in rows:
            results.append({
                "id": row["id"],
                "ip": row["sender_ip"],
                "time": row["send_time"],
                "content": row["content"],
                "success": bool(row["success"])
            })
            
    return response.json(results)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
