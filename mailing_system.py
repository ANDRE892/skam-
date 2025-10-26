from aiogram import Router, Bot, F
from aiogram.types import ContentType
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery
from aiogram.fsm.state import StatesGroup, State
from aiogram.filters import Command
import asyncio

class MailingStates(StatesGroup):
    waiting_for_content = State()
    preview_sent = State()
    waiting_for_button_text = State()
    waiting_for_button_url = State()

def get_mailing_confirmation_keyboard(buttons=None):
    keyboard = []
    
    if buttons:
        for button in buttons:
            keyboard.append([InlineKeyboardButton(text=button['text'], url=button['url'])])
    
    if not buttons or len(buttons) < 4:
        keyboard.append([InlineKeyboardButton(text="➕ Добавить кнопку", callback_data="mailing:add_button")])
    
    keyboard.append([
        InlineKeyboardButton(text="✅ Отправить", callback_data="mailing:confirm_send"),
        InlineKeyboardButton(text="❌ Отменить", callback_data="mailing:confirm_cancel")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

async def process_mailing_content(message: Message, state: FSMContext):
    if message.content_type == ContentType.TEXT:
        user_text = message.text
        entities = message.entities
        
        await state.update_data({
            'content_type': ContentType.TEXT,
            'text': user_text,
            'entities': entities,
            'buttons': []
        })
        
        await message.answer(
            user_text,
            entities=entities,
            reply_markup=get_mailing_confirmation_keyboard()
        )
        
    elif message.content_type == ContentType.PHOTO:
        photo = message.photo[-1].file_id
        caption = message.caption or ""
        caption_entities = message.caption_entities
        
        await state.update_data({
            'content_type': ContentType.PHOTO,
            'photo': photo,
            'caption': caption,
            'caption_entities': caption_entities,
            'buttons': []
        })
        
        await message.answer_photo(
            photo=photo,
            caption=caption,
            caption_entities=caption_entities,
            reply_markup=get_mailing_confirmation_keyboard()
        )
        
    else:
        await message.answer(
            "❌ Поддерживаются только текстовые сообщения или фото с подписью.\n"
            "Попробуйте еще раз."
        )
        return
    
    await state.set_state(MailingStates.preview_sent)

async def send_mailing_to_all_users(callback: CallbackQuery, state: FSMContext, bot: Bot, get_all_user_ids_func):
    data = await state.get_data()
    content_type = data.get('content_type')
    buttons = data.get('buttons', [])
    
    if not content_type:
        await callback.answer("❌ Данные рассылки не найдены", show_alert=True)
        return
    
    user_ids = await get_all_user_ids_func()
    
    if not user_ids:
        await callback.answer("❌ Нет пользователей для рассылки", show_alert=True)
        return
    
    if callback.message.text:
        await callback.message.edit_text("📤 **ОТПРАВКА РАССЫЛКИ...**\n\nПожалуйста, подождите...")
    else:
        await callback.message.answer("📤 **ОТПРАВКА РАССЫЛКИ...**\n\nПожалуйста, подождите...")
    
    success_count = 0
    error_count = 0
    
    keyboard = []
    if buttons:
        for button in buttons:
            keyboard.append([InlineKeyboardButton(text=button['text'], url=button['url'])])
    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard) if keyboard else None
    
    print(f"[MAILING] Начинаем рассылку для {len(user_ids)} пользователей")
    for i, user_id in enumerate(user_ids, 1):
        try:
            if content_type == ContentType.TEXT:
                text = data.get('text')
                entities = data.get('entities')
                await bot.send_message(
                    chat_id=user_id,
                    text=text,
                    entities=entities,
                    reply_markup=reply_markup
                )
                print(f"[MAILING] ✅ [{i}/{len(user_ids)}] Текст отправлен пользователю {user_id}")
                
            elif content_type == ContentType.PHOTO:
                photo = data.get('photo')
                caption = data.get('caption')
                caption_entities = data.get('caption_entities')
                await bot.send_photo(
                    chat_id=user_id,
                    photo=photo,
                    caption=caption,
                    caption_entities=caption_entities,
                    reply_markup=reply_markup
                )
                print(f"[MAILING] ✅ [{i}/{len(user_ids)}] Фото отправлено пользователю {user_id}")
            
            success_count += 1
            
            await asyncio.sleep(0.05)
            
        except Exception as e:
            error_count += 1
            error_msg = str(e)
            
            # Определяем тип ошибки для более информативного лога
            if "bot was blocked by the user" in error_msg:
                print(f"[MAILING] ❌ [{i}/{len(user_ids)}] Пользователь {user_id} заблокировал бота")
            elif "bot can't initiate conversation with a user" in error_msg:
                print(f"[MAILING] ❌ [{i}/{len(user_ids)}] Пользователь {user_id} не инициировал диалог с ботом (никогда не писал /start)")
            elif "user is deactivated" in error_msg:
                print(f"[MAILING] ❌ [{i}/{len(user_ids)}] Пользователь {user_id} деактивирован")
            else:
                print(f"[MAILING] ❌ [{i}/{len(user_ids)}] Ошибка отправки пользователю {user_id}: {e}")
    
    result_text = (
        f"✅ **РАССЫЛКА ЗАВЕРШЕНА!**\n\n"
        f"📊 **Статистика:**\n"
        f"✅ Успешно отправлено: {success_count}\n"
        f"❌ Ошибок: {error_count}\n"
        f"📈 Всего пользователей: {len(user_ids)}"
    )
    
    print(f"[MAILING] 🎯 РАССЫЛКА ЗАВЕРШЕНА! Успешно: {success_count}, Ошибок: {error_count}, Всего: {len(user_ids)}")
    
    if callback.message.text:
        await callback.message.edit_text(result_text)
    else:
        await callback.message.answer(result_text)
    
    await state.clear()

async def cancel_mailing(callback: CallbackQuery, state: FSMContext):
    if callback.message.text:
        await callback.message.edit_text("❌ **РАССЫЛКА ОТМЕНЕНА**")
    else:
        await callback.message.answer("❌ **РАССЫЛКА ОТМЕНЕНА**")
    await state.clear()

async def add_button_start(callback: CallbackQuery, state: FSMContext):
    if callback.message.text:
        await callback.message.edit_text(
            "📝 **ДОБАВЛЕНИЕ КНОПКИ**\n\n"
            "Отправьте название кнопки (например: 'Наш сайт', 'Подписаться', 'Купить')",
            parse_mode="Markdown"
        )
    else:
        await callback.message.answer(
            "📝 **ДОБАВЛЕНИЕ КНОПКИ**\n\n"
            "Отправьте название кнопки (например: 'Наш сайт', 'Подписаться', 'Купить')",
            parse_mode="Markdown"
        )
    await state.set_state(MailingStates.waiting_for_button_text)

async def process_button_text(message: Message, state: FSMContext):
    button_text = message.text.strip()
    
    if len(button_text) > 64:
        await message.answer("❌ Название кнопки слишком длинное (максимум 64 символа). Попробуйте еще раз.")
        return
    
    await state.update_data(temp_button_text=button_text)
    
    await message.answer(
        "🔗 **ССЫЛКА КНОПКИ**\n\n"
        "Отправьте ссылку для кнопки (например: https://example.com)",
        parse_mode="Markdown"
    )
    await state.set_state(MailingStates.waiting_for_button_url)

async def process_button_url(message: Message, state: FSMContext):
    button_url = message.text.strip()
    
    if not button_url.startswith(('http://', 'https://', 'tg://')):
        await message.answer("❌ Неверный формат ссылки. Ссылка должна начинаться с http://, https:// или tg://")
        return
    
    data = await state.get_data()
    button_text = data.get('temp_button_text')
    buttons = data.get('buttons', [])
    
    new_button = {'text': button_text, 'url': button_url}
    buttons.append(new_button)
    
    await state.update_data(buttons=buttons)
    await state.update_data(temp_button_text=None)
    
    content_type = data.get('content_type')
    
    if content_type == ContentType.TEXT:
        text = data.get('text')
        entities = data.get('entities')
        await message.answer(
            text,
            entities=entities,
            reply_markup=get_mailing_confirmation_keyboard(buttons)
        )
    elif content_type == ContentType.PHOTO:
        photo = data.get('photo')
        caption = data.get('caption')
        caption_entities = data.get('caption_entities')
        await message.answer_photo(
            photo=photo,
            caption=caption,
            caption_entities=caption_entities,
            reply_markup=get_mailing_confirmation_keyboard(buttons)
        )
    
    await state.set_state(MailingStates.preview_sent)

def setup_mailing_handlers(router: Router, bot: Bot, get_all_user_ids_func, is_admin_func=None):
    
    @router.message(Command("mailing"))
    async def start_mailing_command(message: Message, state: FSMContext):
        if is_admin_func and not await is_admin_func(message.from_user.id):
            return
        
        await message.answer(
            "📧 **СИСТЕМА РАССЫЛКИ**\n\n"
            "Отправьте сообщение или фото с подписью для рассылки.\n"
            "Поддерживается форматирование текста!\n\n"
            "После отправки вы увидите предварительный просмотр.",
            parse_mode="Markdown"
        )
        await state.set_state(MailingStates.waiting_for_content)
    
    @router.message(MailingStates.waiting_for_content)
    async def handle_mailing_content(message: Message, state: FSMContext):
        if is_admin_func and not await is_admin_func(message.from_user.id):
            await message.answer("❌ У вас нет прав для использования рассылки.")
            await state.clear()
            return
        await process_mailing_content(message, state)
    
    @router.callback_query(F.data == "mailing:add_button")
    async def add_button_callback(callback: CallbackQuery, state: FSMContext):
        if is_admin_func and not await is_admin_func(callback.from_user.id):
            await callback.answer("❌ У вас нет прав для использования рассылки.", show_alert=True)
            await state.clear()
            return
        await add_button_start(callback, state)
    
    @router.message(MailingStates.waiting_for_button_text)
    async def handle_button_text(message: Message, state: FSMContext):
        if is_admin_func and not await is_admin_func(message.from_user.id):
            await message.answer("❌ У вас нет прав для использования рассылки.")
            await state.clear()
            return
        await process_button_text(message, state)
    
    @router.message(MailingStates.waiting_for_button_url)
    async def handle_button_url(message: Message, state: FSMContext):
        if is_admin_func and not await is_admin_func(message.from_user.id):
            await message.answer("❌ У вас нет прав для использования рассылки.")
            await state.clear()
            return
        await process_button_url(message, state)
    
    @router.callback_query(F.data == "mailing:confirm_send")
    async def confirm_send_mailing(callback: CallbackQuery, state: FSMContext):
        if is_admin_func and not await is_admin_func(callback.from_user.id):
            await callback.answer("❌ У вас нет прав для использования рассылки.", show_alert=True)
            await state.clear()
            return
        await send_mailing_to_all_users(callback, state, bot, get_all_user_ids_func)
    
    @router.callback_query(F.data == "mailing:confirm_cancel")
    async def cancel_mailing_callback(callback: CallbackQuery, state: FSMContext):
        if is_admin_func and not await is_admin_func(callback.from_user.id):
            await callback.answer("❌ У вас нет прав для использования рассылки.", show_alert=True)
            await state.clear()
            return
        await cancel_mailing(callback, state)
