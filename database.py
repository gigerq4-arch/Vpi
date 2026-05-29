import aiosqlite
from config import DB_NAME

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        # Таблица государств (Финансы хранятся в миллиардах: 10 = 10 млрд)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS countries (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            country_name TEXT,
            money INTEGER DEFAULT 10,
            income INTEGER DEFAULT 1,
            counter_intel_level INTEGER DEFAULT 1,
            tanks INTEGER DEFAULT 10,
            artillery INTEGER DEFAULT 5
        );
        """)
        
        # Таблица альянсов (flag_file_id хранит Telegram file_id картинки флага)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS unions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            description TEXT,
            union_type TEXT,
            flag_file_id TEXT,
            creator_id INTEGER,
            members_count INTEGER DEFAULT 1
        );
        """)
        
        # Связующая таблица членства в блоках
        await db.execute("""
        CREATE TABLE IF NOT EXISTS union_members (
            union_id INTEGER,
            user_id INTEGER UNIQUE,
            FOREIGN KEY(union_id) REFERENCES unions(id) ON DELETE CASCADE
        );
        """)
        await db.commit()

async def update_user_activity(user_id: int, username: str):
    """Синхронизация актуального юзернейма при смене ника игроком"""
    if not username:
        return
    formatted_username = f"@{username.lower()}"
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "UPDATE countries SET username = ? WHERE user_id = ?",
            (formatted_username, user_id)
        )
        await db.commit()