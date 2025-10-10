import asyncpg
import os
from typing import Optional
from datetime import datetime

pool = None

DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_NAME = os.getenv('DB_NAME')
DB_HOST = os.getenv('DB_HOST')
DB_PORT = int(os.getenv('DB_PORT', 5432))


async def init_db():
    global pool
    try:
        pool = await asyncpg.create_pool(
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            host=DB_HOST,
            port=DB_PORT,
            min_size=1,
            max_size=10
        )
        print("[LOG] Подключение к базе данных установлено")
        await create_tables()
    except Exception as e:
        print(f"[ERROR] Ошибка подключения к базе данных: {e}")
        raise


async def create_tables():
    async with pool.acquire() as conn:
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                user_id BIGINT UNIQUE NOT NULL,
                username VARCHAR(255),
                first_name VARCHAR(255),
                last_name VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        print("[LOG] Таблицы созданы/проверены")


async def get_or_create_user(user_id: int, username: str = None, first_name: str = None, last_name: str = None):
    async with pool.acquire() as conn:
        user = await conn.fetchrow(
            'SELECT * FROM users WHERE user_id = $1',
            user_id
        )
        if not user:
            user = await conn.fetchrow('''
                INSERT INTO users (user_id, username, first_name, last_name)
                VALUES ($1, $2, $3, $4)
                RETURNING *
            ''', user_id, username, first_name, last_name)
            print(f"[LOG] Создан новый пользователь {user_id}")
        else:
            user = await conn.fetchrow('''
                UPDATE users 
                SET username = $2, first_name = $3, last_name = $4, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = $1
                RETURNING *
            ''', user_id, username, first_name, last_name)
            print(f"[LOG] Обновлен пользователь {user_id}")
        return user


async def get_user(user_id: int):
    async with pool.acquire() as conn:
        return await conn.fetchrow(
            'SELECT * FROM users WHERE user_id = $1', user_id
        )


async def get_all_users():
    async with pool.acquire() as conn:
        return await conn.fetch('SELECT * FROM users ORDER BY created_at DESC')


async def save_user(user_id: int, username: str = None, first_name: str = None, last_name: str = None):
    return await get_or_create_user(user_id, username, first_name, last_name)


async def close_db():
    global pool
    if pool:
        await pool.close()
        print("[LOG] Подключение к базе данных закрыто") 