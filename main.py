import asyncio
import os
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, ChatJoinRequest, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from dotenv import load_dotenv
from database import init_db, save_user, close_db, get_all_users
from mailing_system import setup_mailing_handlers

load_dotenv()
TOKEN = os.getenv('TOKEN')
CHANNEL_LINK = os.getenv("CHANNEL_LINK", "https://t.me/+eXOltHvhsk81NTgy")
RESERVE_LINKS = os.getenv("RESERVE_LINKS")
TEXT_MESSAGE = os.getenv("TEXT_MESSAGE", "Для доступа в канал необходимо подписаться на наши резервы 👇\n\n")

bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()
dp.include_router(router)

CHANNEL_ID = -1002788956369

ADMIN_IDS = [7118184736, 889158373]

@router.message(Command("start"))
async def start_command(message: Message):
    user = message.from_user
    print(f"[LOG] Команда /start от пользователя {user.id} (@{user.username})")
    
    await save_user(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )
    
    if user.id in ADMIN_IDS:
        admin_text = f"👋 Привет, {user.first_name}!\n\n🔧 Панель администратора\n\nВыберите действие:"
        admin_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💬 Рассылка", callback_data="admin:mailing")],
            [InlineKeyboardButton(text="📊 Статистика", callback_data="admin:stats")]
        ])
        await message.answer(admin_text, reply_markup=admin_keyboard)
        print(f"[LOG] Админ панель показана пользователю {user.id}")
    else:
        print(f"[LOG] Пользователь {user.id} (@{user.username}) не является админом - панель не показана")


@router.callback_query(F.data.startswith('admin:'))
async def admin_callback(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        return
    
    action = callback.data.split(':')[1]
    
    if action == "mailing":
        await callback.message.edit_text(
            "📧 **СИСТЕМА РАССЫЛКИ**\n\n"
            "/mailing.",
            parse_mode="Markdown"
        )
        
    elif action == "stats":
        users = await get_all_users()
        stats_text = f"📊 **СТАТИСТИКА**\n\n👥 Всего пользователей: {len(users)}"
        await callback.message.edit_text(stats_text, parse_mode="Markdown")
        
    elif action == "users":
        users = await get_all_users()
        if users:
            users_text = "👥 **ПОСЛЕДНИЕ ПОЛЬЗОВАТЕЛИ:**\n\n"
            for i, user in enumerate(users[:10], 1):
                username = f"@{user['username']}" if user['username'] else "Нет username"
                name = f"{user['first_name'] or ''} {user['last_name'] or ''}".strip()
                name = name if name else "Имя не указано"
                users_text += f"{i}. {name} ({username})\n"
        else:
            users_text = "👥 Пользователей пока нет"
        
        await callback.message.edit_text(users_text, parse_mode="Markdown")



@router.chat_join_request()
async def on_join_request(event: ChatJoinRequest):
    user_id = event.from_user.id
    username = event.from_user.username
    print(f"[LOG] Заявка на вступление от {user_id} (@{username})")
    
    await save_user(user_id, event.from_user.username, event.from_user.first_name, event.from_user.last_name)
    
    markup = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Я человек")]], resize_keyboard=True)
    
    try:
        await bot.send_message(
            user_id,
            "Для доступа в канал необходимо подтвердить, что вы человек:",
            reply_markup=markup
        )
        print(f"[LOG] Отправлена кнопка 'Я человек' пользователю {user_id}")
    except Exception as e:
        if "bot was blocked by the user" in str(e):
            print(f"[WARNING] Пользователь {user_id} заблокировал бота - не удалось отправить сообщение")
        else:
            print(f"[ERROR] Ошибка отправки сообщения пользователю {user_id}: {e}")

@router.message(F.text == "Я человек")
async def verify_human_message(message: Message):
    user = message.from_user
    print(f"[LOG] Пользователь {user.id} (@{user.username}) нажал 'Я человек'")
    
    # Разбираем ссылки из одной переменной
    reserve_links = RESERVE_LINKS.split(',')
    
    # Формируем текст с ссылками
    text = TEXT_MESSAGE
    for i, link in enumerate(reserve_links, 1):
        text += f"Резерв {i} – {link.strip()}\n\n"
    
    try:
        await message.answer(
            text,
            parse_mode="HTML",
            disable_web_page_preview=True
        )
        print(f"[LOG] Отправлены ссылки на резервы пользователю {user.id}")
    except Exception as e:
        if "bot was blocked by the user" in str(e):
            print(f"[WARNING] Пользователь {user.id} заблокировал бота - не удалось отправить сообщение")
        else:
            print(f"[ERROR] Ошибка отправки сообщения пользователю {user.id}: {e}")

async def get_all_user_ids():
    users = await get_all_users()
    return [user['user_id'] for user in users]

async def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

async def main():
    print("[LOG] Подключение к базе данных...")
    await init_db()
    
    setup_mailing_handlers(router, bot, get_all_user_ids, is_admin)
    
    print("[LOG] Бот запущен и ожидает события...")
    try:
        await dp.start_polling(bot, skip_updates=True)
    finally:
        await close_db()

if __name__ == "__main__":
    asyncio.run(main())