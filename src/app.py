import os
import aiosqlite
import httpx
from datetime import datetime
from sanic import Sanic, response, Request
from sanic.log import logger

app = Sanic("TelegramBotService")

# --- 配置区域 ---
# 优先读取环境变量，如果没有则使用默认值（方便本地测试）
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
DEFAULT_CHAT_ID = os.getenv("CHAT_ID", "")

# 数据库路径固定在 /app/data 下，方便通过 Docker 卷挂载到外部
DB_PATH = "/app/data/history.db"

# --- 1. 服务启动时初始化数据库 ---
@app.before_server_start
async def setup_db(app, loop):
    # 确保数据库表存在
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
    logger.info(f"Database initialized at {DB_PATH}")

# --- 2. 发送消息接口 ---
@app.post("/send")
async def send_message(request: Request):
    """
    接口功能：接收 markdown 文本并发送到 Telegram
    参数(JSON): { "text": "...", "chat_id": "可选" }
    """
    data = request.json or {}
    text = data.get("text", "")
    chat_id = data.get("chat_id", DEFAULT_CHAT_ID)

    if not text:
        return response.json({"error": "Content 'text' is required"}, status=400)
    if not chat_id:
        return response.json({"error": "Target 'chat_id' is required (env or param)"}, status=400)

    # 准备记录的数据
    sender_ip = request.ip
    send_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    success = False
    api_res_text = ""

    # 准备 Telegram API 请求
    tg_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown" 
    }

    # 异步发送请求
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(tg_url, json=payload, timeout=10.0)
            api_res_text = resp.text
            if resp.status_code == 200:
                success = True
            else:
                logger.error(f"Telegram API Error: {resp.text}")
    except Exception as e:
        api_res_text = f"Internal Error: {str(e)}"
        logger.error(f"Request Exception: {e}")

    # 异步写入数据库
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT INTO logs (sender_ip, send_time, content, success, api_response) VALUES (?, ?, ?, ?, ?)",
                (sender_ip, send_time, text, success, api_res_text)
            )
            await db.commit()
    except Exception as e:
        logger.error(f"Database Write Error: {e}")

    # 返回结果
    return response.json({
        "status": "success" if success else "failed",
        "telegram_response": api_res_text,
        "timestamp": send_time
    }, status=200 if success else 502)

# --- 3. 查看历史记录接口 ---
@app.get("/history")
async def get_history(request: Request):
    """
    接口功能：查看发送记录
    参数(URL): ?limit=20 (默认20条)
    """
    try:
        limit = int(request.args.get("limit", 20))
    except ValueError:
        limit = 20

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row # 允许通过列名访问
        cursor = await db.execute("SELECT * FROM logs ORDER BY id DESC LIMIT ?", (limit,))
        rows = await cursor.fetchall()
        
        results = []
        for row in rows:
            results.append({
                "id": row["id"],
                "ip": row["sender_ip"],
                "time": row["send_time"],
                "content": row["content"],
                "success": bool(row["success"]),
                # "details": row["api_response"] # 如果不想看详细API回包，可以注释掉这行
            })
            
    return response.json(results)

if __name__ == "__main__":
    # 监听所有网卡，端口8000
    app.run(host="0.0.0.0", port=8000)
