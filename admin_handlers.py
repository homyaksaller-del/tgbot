import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.enums import ParseMode

from config import ADMIN_IDS, SUPPORT_USERNAME, DOWNLOAD_URL, INSTALL_FILE_ID
from database import (
    get_setting, set_setting, get_stats, add_keys,
    get_available_keys_count, get_all_available_keys,
    get_issued_keys_stats, get_available_key, mark_key_issued, save_purchase,
    get_bank_request, resolve_bank_request, get_bank_requests, get_orders_stats,
    get_pending_bank_requests_with_buttons
)
from keyboards import (
    admin_panel_keyboard, admin_prices_keyboard, admin_back_keyboard,
    admin_edit_price_keyboard, back_main_keyboard,
    admin_request_keyboard, admin_orders_keyboard
)

logger = logging.getLogger(__name__)
admin_router = Router()


async def _send_download_info(bot, user_id: int):
    """Отправляет пользователю ссылку на установку и/или файл установщика."""
    if not DOWNLOAD_URL and not INSTALL_FILE_ID:
        return  # Ничего не настроено — молча выходим

    # Сначала отправляем ссылку, если она задана
    if DOWNLOAD_URL:
        await bot.send_message(
            user_id,
            f'<tg-emoji emoji-id="5372981976804366741">⬇️</tg-emoji> <b>Ссылка для скачивания программы:</b>\n\n'
            f'<a href="{DOWNLOAD_URL}">Скачать установщик</a>\n\n'
            f'<tg-emoji emoji-id="6028435952299413210">ℹ️</tg-emoji> Установите программу и введите ваш ключ при запуске.',
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=False
        )

    # Отправляем файл по file_id (хранится на серверах Telegram)
    if INSTALL_FILE_ID:
        await bot.send_document(
            user_id,
            document=INSTALL_FILE_ID,
            caption=(
                '📦 <b>Файл установщика</b>\n\n'
                'Скачайте и запустите файл, затем введите ваш ключ.'
            ),
            parse_mode=ParseMode.HTML
        )


class AdminStates(StatesGroup):
    edit_info = State()
    edit_usd = State()
    edit_rub = State()
    edit_uah = State()
    edit_mono_card = State()
    edit_mono_name = State()
    edit_privat_card = State()
    edit_privat_name = State()
    add_keys = State()
    add_keys_plan = State()


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


# ─── ADMIN PANEL ─────────────────────────────────────────────────

@admin_router.message(Command("admin"))
async def admin_cmd(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Нет доступа")
        return
    await message.answer(
        '<b><tg-emoji emoji-id="5870982283724328568">⚙️</tg-emoji> Панель администратора</b>\n\n'
        'Управляйте ботом через кнопки ниже:',
        parse_mode=ParseMode.HTML,
        reply_markup=admin_panel_keyboard()
    )


@admin_router.callback_query(F.data == "admin_panel")
async def admin_panel_cb(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    await state.clear()
    await callback.message.edit_text(
        '<b><tg-emoji emoji-id="5870982283724328568">⚙️</tg-emoji> Панель администратора</b>\n\n'
        'Управляйте ботом через кнопки ниже:',
        parse_mode=ParseMode.HTML,
        reply_markup=admin_panel_keyboard()
    )
    await callback.answer()


@admin_router.callback_query(F.data == "admin_close")
async def admin_close(callback: CallbackQuery):
    await callback.message.delete()
    await callback.answer()


# ─── /givekey — ВЫДАТЬ КЛЮЧ ВРУЧНУЮ (после банка) ────────────────

@admin_router.message(Command("givekey"))
async def givekey_cmd(message: Message):
    """
    Использование: /givekey <user_id> <plan_key>
    Выдаёт ключ пользователю вручную (для оплаты через Моно/Приват).
    """
    if not is_admin(message.from_user.id):
        await message.answer("❌ Нет доступа")
        return

    args = message.text.split()[1:]
    if len(args) < 2:
        await message.answer(
            "⚠️ Использование: <code>/givekey &lt;user_id&gt; &lt;plan_key&gt;</code>\n\n"
            "Пример: <code>/givekey 123456789 30</code>",
            parse_mode=ParseMode.HTML
        )
        return

    try:
        user_id = int(args[0])
        plan_key = args[1]
    except ValueError:
        await message.answer("❌ Неверный формат. user_id должен быть числом.", parse_mode=ParseMode.HTML)
        return

    plans = await get_setting("plans")
    if plan_key not in plans:
        await message.answer(f"❌ Тариф <code>{plan_key}</code> не найден.", parse_mode=ParseMode.HTML)
        return

    plan = plans[plan_key]
    license_key = await get_available_key(plan_key)

    if not license_key:
        await message.answer(
            f"❌ Нет доступных ключей для тарифа <b>{plan['name']}</b>.\n"
            "Добавьте ключи через /admin → Управление ключами.",
            parse_mode=ParseMode.HTML
        )
        return

    await mark_key_issued(license_key, user_id)
    await save_purchase(
        user_id=user_id,
        plan_key=plan_key,
        license_key=license_key,
        payment_method="bank_manual",
        amount=plan["uah"],
        currency="UAH"
    )

    # Отправляем ключ пользователю
    try:
        await message.bot.send_message(
            user_id,
            f'<b><tg-emoji emoji-id="6041731551845159060">🎉</tg-emoji> Оплата подтверждена!</b>\n\n'
            f'<tg-emoji emoji-id="5886285355279193209">🏷</tg-emoji> Тариф: <b>{plan["name"]}</b>\n\n'
            f'<tg-emoji emoji-id="6037249452824072506">🔒</tg-emoji> <b>Ваш лицензионный ключ:</b>\n\n'
            f'<code>{license_key}</code>\n\n'
            f'<tg-emoji emoji-id="6028435952299413210">ℹ️</tg-emoji> Скопируйте ключ и введите его в программе.\n'
            f'По вопросам: {SUPPORT_USERNAME}',
            parse_mode=ParseMode.HTML,
            reply_markup=back_main_keyboard()
        )
        await _send_download_info(message.bot, user_id)
        await message.answer(
            f'✅ Ключ успешно выдан пользователю <code>{user_id}</code>\n'
            f'Тариф: <b>{plan["name"]}</b>\n'
            f'Ключ: <code>{license_key}</code>',
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        await message.answer(
            f'⚠️ Ключ создан, но не удалось отправить пользователю {user_id}.\n'
            f'Ключ: <code>{license_key}</code>\n'
            f'Ошибка: {e}',
            parse_mode=ParseMode.HTML
        )


# ─── STATS ───────────────────────────────────────────────────────

@admin_router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    stats = await get_stats()
    text = (
        f'<b><tg-emoji emoji-id="5870921681735781843">📊</tg-emoji> Статистика</b>\n\n'
        f'<tg-emoji emoji-id="5870633910337015697">✅</tg-emoji> Всего продаж: <b>{stats["total_purchases"]}</b>\n'
        f'<tg-emoji emoji-id="5870994129244131212">👤</tg-emoji> Уникальных покупателей: <b>{stats["unique_buyers"]}</b>\n'
        f'<tg-emoji emoji-id="5983150113483134607">⏰</tg-emoji> Ожидают оплаты: <b>{stats["pending_invoices"]}</b>'
    )
    await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=admin_back_keyboard())
    await callback.answer()


# ─── EDIT BOT INFO ────────────────────────────────────────────────

@admin_router.callback_query(F.data == "admin_edit_info")
async def admin_edit_info(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    current = await get_setting("bot_info")
    await callback.message.edit_text(
        f'<b>✍ Редактирование информации о боте</b>\n\nТекущий текст:\n<i>{current}</i>\n\nОтправьте новый текст:',
        parse_mode=ParseMode.HTML,
        reply_markup=admin_back_keyboard()
    )
    await state.set_state(AdminStates.edit_info)
    await callback.answer()


@admin_router.message(AdminStates.edit_info)
async def save_bot_info(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await set_setting("bot_info", message.text or "")
    await state.clear()
    await message.answer('✅ <b>Информация обновлена!</b>', parse_mode=ParseMode.HTML, reply_markup=admin_panel_keyboard())


# ─── EDIT PRICES ─────────────────────────────────────────────────

@admin_router.callback_query(F.data == "admin_prices")
async def admin_prices(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    plans = await get_setting("plans")

    mono_card = await get_setting("mono_card") or "—"
    privat_card = await get_setting("privat_card") or "—"

    text = (
        '<b>🖋 Редактирование цен и реквизитов</b>\n\n'
        f'🏦 Моно: <code>{mono_card}</code>\n'
        f'💳 Приват: <code>{privat_card}</code>\n\n'
        'Выберите тариф для изменения цен:'
    )
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    plan_kb = admin_prices_keyboard(plans)
    # Добавляем кнопки реквизитов сверху
    extra_buttons = [
        [InlineKeyboardButton(text="🏦 Реквизиты Монобанк", callback_data="edit_mono")],
        [InlineKeyboardButton(text="💳 Реквизиты ПриватБанк", callback_data="edit_privat")],
    ]
    all_buttons = extra_buttons + plan_kb.inline_keyboard
    kb = InlineKeyboardMarkup(inline_keyboard=all_buttons)

    await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    await callback.answer()


# ─── EDIT BANK DETAILS ────────────────────────────────────────────

@admin_router.callback_query(F.data == "edit_mono")
async def edit_mono(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    card = await get_setting("mono_card") or "—"
    name = await get_setting("mono_name") or "—"
    await callback.message.edit_text(
        f'<b>🏦 Реквизиты Монобанк</b>\n\nКарта: <code>{card}</code>\nПолучатель: <b>{name}</b>\n\n'
        f'Отправьте новые данные в формате:\n<code>4441 1111 2222 3333\nІван І.</code>',
        parse_mode=ParseMode.HTML, reply_markup=admin_back_keyboard()
    )
    await state.set_state(AdminStates.edit_mono_card)
    await callback.answer()


@admin_router.message(AdminStates.edit_mono_card)
async def save_mono(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    lines = (message.text or "").strip().split("\n")
    await set_setting("mono_card", lines[0].strip())
    if len(lines) > 1:
        await set_setting("mono_name", lines[1].strip())
    await state.clear()
    await message.answer('✅ <b>Реквизиты Монобанк обновлены!</b>', parse_mode=ParseMode.HTML, reply_markup=admin_panel_keyboard())


@admin_router.callback_query(F.data == "edit_privat")
async def edit_privat(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    card = await get_setting("privat_card") or "—"
    name = await get_setting("privat_name") or "—"
    await callback.message.edit_text(
        f'<b>💳 Реквизиты ПриватБанк</b>\n\nКарта: <code>{card}</code>\nПолучатель: <b>{name}</b>\n\n'
        f'Отправьте новые данные в формате:\n<code>5168 7421 0000 1234\nІван І.</code>',
        parse_mode=ParseMode.HTML, reply_markup=admin_back_keyboard()
    )
    await state.set_state(AdminStates.edit_privat_card)
    await callback.answer()


@admin_router.message(AdminStates.edit_privat_card)
async def save_privat(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    lines = (message.text or "").strip().split("\n")
    await set_setting("privat_card", lines[0].strip())
    if len(lines) > 1:
        await set_setting("privat_name", lines[1].strip())
    await state.clear()
    await message.answer('✅ <b>Реквизиты ПриватБанк обновлены!</b>', parse_mode=ParseMode.HTML, reply_markup=admin_panel_keyboard())


# ─── EDIT PLAN PRICES ────────────────────────────────────────────

@admin_router.callback_query(F.data.startswith("edit_plan_"))
async def edit_plan(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    plan_key = callback.data.split("_", 2)[2]
    plans = await get_setting("plans")
    if plan_key not in plans:
        await callback.answer("Тариф не найден", show_alert=True)
        return
    plan = plans[plan_key]
    text = (
        f'<b>🏷 Тариф: {plan["name"]}</b>\n\n'
        f'🪙 Текущие цены:\n'
        f'  • USD: <b>{plan["usd"]}$</b>\n'
        f'  • RUB: <b>{plan["rub"]}₽</b>\n'
        f'  • UAH: <b>{plan["uah"]}₴</b>\n\n'
        f'Выберите что изменить:'
    )
    await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=admin_edit_price_keyboard(plan_key))
    await callback.answer()


@admin_router.callback_query(F.data.startswith("edit_usd_"))
async def edit_usd_prompt(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    plan_key = callback.data.split("_", 2)[2]
    await state.update_data(plan_key=plan_key, field="usd")
    await callback.message.edit_text(
        f'<b>🖋 Введите новую цену USD:</b>\n\nПример: <code>3.5</code>',
        parse_mode=ParseMode.HTML, reply_markup=admin_back_keyboard()
    )
    await state.set_state(AdminStates.edit_usd)
    await callback.answer()


@admin_router.callback_query(F.data.startswith("edit_rub_"))
async def edit_rub_prompt(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    plan_key = callback.data.split("_", 2)[2]
    await state.update_data(plan_key=plan_key, field="rub")
    await callback.message.edit_text(
        f'<b>🖋 Введите новую цену RUB:</b>\n\nПример: <code>250</code>',
        parse_mode=ParseMode.HTML, reply_markup=admin_back_keyboard()
    )
    await state.set_state(AdminStates.edit_rub)
    await callback.answer()


@admin_router.callback_query(F.data.startswith("edit_uah_"))
async def edit_uah_prompt(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    plan_key = callback.data.split("_", 2)[2]
    await state.update_data(plan_key=plan_key, field="uah")
    await callback.message.edit_text(
        f'<b>🖋 Введите новую цену UAH:</b>\n\nПример: <code>140</code>',
        parse_mode=ParseMode.HTML, reply_markup=admin_back_keyboard()
    )
    await state.set_state(AdminStates.edit_uah)
    await callback.answer()


async def _save_price(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    data = await state.get_data()
    plan_key = data.get("plan_key")
    field = data.get("field")
    try:
        value = float(message.text.strip().replace(",", "."))
    except (ValueError, AttributeError):
        await message.answer("❌ Введите корректное число. Пример: <code>3.5</code>", parse_mode=ParseMode.HTML)
        return
    plans = await get_setting("plans")
    if plan_key in plans:
        plans[plan_key][field] = value
        await set_setting("plans", plans)
    await state.clear()
    await message.answer(
        f'✅ <b>Цена обновлена!</b>\n\nТариф: <b>{plans[plan_key]["name"]}</b>\n{field.upper()}: <b>{value}</b>',
        parse_mode=ParseMode.HTML, reply_markup=admin_panel_keyboard()
    )


@admin_router.message(AdminStates.edit_usd)
async def save_usd(message: Message, state: FSMContext):
    await _save_price(message, state)

@admin_router.message(AdminStates.edit_rub)
async def save_rub(message: Message, state: FSMContext):
    await _save_price(message, state)

@admin_router.message(AdminStates.edit_uah)
async def save_uah(message: Message, state: FSMContext):
    await _save_price(message, state)


# ─── KEY MANAGEMENT ──────────────────────────────────────────────

@admin_router.callback_query(F.data == "admin_keys")
async def admin_keys_menu(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    key_stats = await get_issued_keys_stats()
    text = (
        f'<b>🔑 Управление ключами</b>\n\n'
        f'✅ Доступных: <b>{key_stats["available"]}</b>\n'
        f'❌ Выданных: <b>{key_stats["issued"]}</b>\n'
        f'🪙 Всего: <b>{key_stats["total_keys"]}</b>\n\n'
        f'Для ручной выдачи ключа (Моно/Приват):\n'
        f'<code>/givekey &lt;user_id&gt; &lt;plan_key&gt;</code>'
    )
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить ключи", callback_data="add_keys_menu")],
        [InlineKeyboardButton(text="📋 Список ключей", callback_data="list_keys")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_panel")],
    ])
    await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    await callback.answer()


@admin_router.callback_query(F.data == "add_keys_menu")
async def add_keys_menu(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    plans = await get_setting("plans")
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    buttons = [
        [InlineKeyboardButton(text=plan.get("name", f"План {key}"), callback_data=f"add_keys_select_{key}")]
        for key, plan in sorted(plans.items())
    ]
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_keys")])
    await callback.message.edit_text(
        '<b>🔑 Выберите тариф для добавления ключей:</b>',
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )
    await callback.answer()


@admin_router.callback_query(F.data.startswith("add_keys_select_"))
async def add_keys_select_plan(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    plan_key = callback.data.split("_", 3)[3]
    plans = await get_setting("plans")
    plan = plans.get(plan_key)
    if not plan:
        await callback.answer("Тариф не найден", show_alert=True)
        return
    await state.update_data(plan_key=plan_key)
    await callback.message.edit_text(
        f'<b>🔑 Добавление ключей для тарифа: {plan["name"]}</b>\n\n'
        f'Отправьте ключи (по одному на строку или через запятую):\n\n'
        f'<i>Пример:</i>\n'
        f'<code>KEY-1-XXXXX-XXXXX\nKEY-2-XXXXX-XXXXX</code>',
        parse_mode=ParseMode.HTML,
        reply_markup=admin_back_keyboard()
    )
    await state.set_state(AdminStates.add_keys)
    await callback.answer()


@admin_router.message(AdminStates.add_keys)
async def save_keys(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    data = await state.get_data()
    plan_key = data.get("plan_key")
    text = message.text or ""
    keys = [k.strip() for k in text.replace(",", "\n").split("\n") if k.strip()]
    if not keys:
        await message.answer("❌ Ключи не найдены. Попробуйте снова.")
        return
    added = await add_keys(keys, plan_key)
    await state.clear()
    await message.answer(
        f'✅ <b>Ключи добавлены!</b>\n\nТариф: <b>{plan_key}</b>\nДобавлено: <b>{added}</b> ключей',
        parse_mode=ParseMode.HTML,
        reply_markup=admin_panel_keyboard()
    )


@admin_router.callback_query(F.data == "list_keys")
async def list_keys_handler(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    keys = await get_all_available_keys(limit=20)
    if not keys:
        await callback.message.edit_text(
            '<b>🔑 Список ключей</b>\n\n❌ Доступных ключей нет',
            parse_mode=ParseMode.HTML, reply_markup=admin_back_keyboard()
        )
        await callback.answer()
        return
    text = '<b>🔑 Доступные ключи (первые 20):</b>\n\n'
    for i, key in enumerate(keys, 1):
        text += f'{i}. <code>{key["license_key"]}</code> <b>[{key["plan_key"]}]</b>\n'
    await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=admin_back_keyboard())
    await callback.answer()


# ─── APPROVE / REJECT BANK REQUEST ───────────────────────────────

@admin_router.callback_query(F.data.startswith("req_approve_"))
async def req_approve(callback: CallbackQuery):
    """Одобрить заявку и выдать ключ. callback: req_approve_{request_id}_{user_id}_{plan_key}"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    parts = callback.data.split("_")
    # req_approve_{id}_{user_id}_{plan_key}  → parts[2], parts[3], parts[4]
    request_id = int(parts[2])
    user_id = int(parts[3])
    plan_key = parts[4]

    req = await get_bank_request(request_id)
    if not req:
        await callback.answer("Заявка не найдена", show_alert=True)
        return
    if req["status"] != "pending":
        await callback.answer("Заявка уже обработана", show_alert=True)
        return

    plans = await get_setting("plans")
    plan = plans.get(plan_key, {})

    license_key = await get_available_key(plan_key)
    if not license_key:
        await callback.answer(f"❌ Нет ключей для тарифа {plan_key}", show_alert=True)
        return

    await mark_key_issued(license_key, user_id)
    await save_purchase(
        user_id=user_id,
        plan_key=plan_key,
        license_key=license_key,
        payment_method=f"bank_{req.get('bank', 'manual')}",
        amount=req.get("amount", plan.get("uah", 0)),
        currency="UAH"
    )
    await resolve_bank_request(request_id, "approved")

    # Уведомляем пользователя
    from config import SUPPORT_USERNAME
    try:
        await callback.bot.send_message(
            user_id,
            f'<b><tg-emoji emoji-id="6041731551845159060">🎉</tg-emoji> Оплата подтверждена!</b>\n\n'
            f'<tg-emoji emoji-id="5886285355279193209">🏷</tg-emoji> Тариф: <b>{plan.get("name", plan_key)}</b>\n\n'
            f'<tg-emoji emoji-id="6037249452824072506">🔒</tg-emoji> <b>Ваш лицензионный ключ:</b>\n\n'
            f'<code>{license_key}</code>\n\n'
            f'<tg-emoji emoji-id="6028435952299413210">ℹ️</tg-emoji> Скопируйте ключ и введите его в программе.\n'
            f'По вопросам: {SUPPORT_USERNAME}',
            parse_mode=ParseMode.HTML,
            reply_markup=back_main_keyboard()
        )
        await _send_download_info(callback.bot, user_id)
    except Exception as e:
        logger.error(f"Cannot send key to user {user_id}: {e}")

    # Обновляем сообщение у всех админов
    bank_name = "Монобанк" if req.get("bank") == "mono" else "ПриватБанк"
    done_text = (
        f'✅ <b>Заявка #{request_id} ОДОБРЕНА</b>\n\n'
        f'👤 <a href="tg://user?id={user_id}">{req.get("user_name", str(user_id))}</a> (<code>{user_id}</code>)\n'
        f'🏷 Тариф: <b>{plan.get("name", plan_key)}</b> · {bank_name}\n'
        f'🔑 Ключ выдан: <code>{license_key}</code>\n'
        f'👮 Обработал: {callback.from_user.full_name}'
    )
    try:
        await callback.message.edit_text(done_text, parse_mode=ParseMode.HTML)
    except Exception:
        pass
    await callback.answer("✅ Ключ выдан!")


@admin_router.callback_query(F.data.startswith("req_reject_"))
async def req_reject(callback: CallbackQuery):
    """Отклонить заявку. callback: req_reject_{request_id}_{user_id}"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    parts = callback.data.split("_")
    request_id = int(parts[2])
    user_id = int(parts[3])

    req = await get_bank_request(request_id)
    if not req:
        await callback.answer("Заявка не найдена", show_alert=True)
        return
    if req["status"] != "pending":
        await callback.answer("Заявка уже обработана", show_alert=True)
        return

    await resolve_bank_request(request_id, "rejected")

    # Уведомляем пользователя
    from config import SUPPORT_USERNAME
    try:
        await callback.bot.send_message(
            user_id,
            f'<b>❌ Заявка отклонена</b>\n\n'
            f'К сожалению, ваша заявка на оплату была отклонена.\n\n'
            f'Если вы считаете, что это ошибка — обратитесь в поддержку: {SUPPORT_USERNAME}',
            parse_mode=ParseMode.HTML,
            reply_markup=back_main_keyboard()
        )
    except Exception as e:
        logger.error(f"Cannot notify user {user_id} about rejection: {e}")

    # Обновляем сообщение
    bank_name = "Монобанк" if req.get("bank") == "mono" else "ПриватБанк"
    plans = await get_setting("plans")
    plan = plans.get(req.get("plan_key", ""), {})
    done_text = (
        f'❌ <b>Заявка #{request_id} ОТКЛОНЕНА</b>\n\n'
        f'👤 <a href="tg://user?id={user_id}">{req.get("user_name", str(user_id))}</a> (<code>{user_id}</code>)\n'
        f'🏷 Тариф: <b>{plan.get("name", req.get("plan_key", "?"))}</b> · {bank_name}\n'
        f'👮 Обработал: {callback.from_user.full_name}'
    )
    try:
        await callback.message.edit_text(done_text, parse_mode=ParseMode.HTML)
    except Exception:
        pass
    await callback.answer("❌ Заявка отклонена")


# ─── ORDERS MENU ─────────────────────────────────────────────────

@admin_router.callback_query(F.data == "admin_orders")
async def admin_orders_menu(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    stats = await get_orders_stats()
    text = (
        f'<b>📦 Управление заказами</b>\n\n'
        f'⏳ Ожидают: <b>{stats["pending"]}</b>\n'
        f'✅ Выполнено: <b>{stats["approved"]}</b>\n'
        f'❌ Отклонено: <b>{stats["rejected"]}</b>\n'
        f'🛒 Всего покупок: <b>{stats["total_purchases"]}</b>'
    )
    await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=admin_orders_keyboard())
    await callback.answer()


def _format_orders_list(orders: list, plans: dict, title: str) -> str:
    if not orders:
        return f'<b>{title}</b>\n\n📭 Нет заказов'
    text = f'<b>{title}</b>\n\n'
    for o in orders:
        plan_name = plans.get(o["plan_key"], {}).get("name", o["plan_key"])
        bank_name = "🏦 Моно" if o["bank"] == "mono" else "💳 Приват"
        status_icon = {"pending": "⏳", "approved": "✅", "rejected": "❌"}.get(o["status"], "❓")
        dt = o["created_at"][:16].replace("T", " ") if o.get("created_at") else "—"
        text += (
            f'{status_icon} <b>#{o["id"]}</b> · '
            f'<a href="tg://user?id={o["user_id"]}">{o.get("user_name", str(o["user_id"]))}</a>\n'
            f'   🏷 {plan_name} · {bank_name} · {o["amount"]}₴\n'
            f'   📅 {dt}\n\n'
        )
    return text.rstrip()


def _pending_orders_keyboard(orders: list) -> "InlineKeyboardMarkup":
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    buttons = []
    for o in orders:
        bank_icon = "🏦" if o["bank"] == "mono" else "💳"
        name = (o.get("user_name") or str(o["user_id"]))[:20]
        buttons.append([
            InlineKeyboardButton(
                text=f"⏳ #{o['id']} {bank_icon} {name} · {o['amount']}₴",
                callback_data=f"order_view_{o['id']}"
            )
        ])
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_orders")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def _show_orders(callback: CallbackQuery, status: str | None, title: str):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    plans = await get_setting("plans")
    orders = await get_bank_requests(status=status, limit=20)
    text = _format_orders_list(orders, plans, title)
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_orders")]
    ])
    await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    await callback.answer()


@admin_router.callback_query(F.data == "orders_pending")
async def orders_pending(callback: CallbackQuery):
    """Список ожидающих — каждая строка кликабельна"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    orders = await get_pending_bank_requests_with_buttons()
    if not orders:
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_orders")]
        ])
        await callback.message.edit_text(
            '<b>⏳ Ожидающие заявки</b>\n\n📭 Нет ожидающих заявок',
            parse_mode=ParseMode.HTML, reply_markup=kb
        )
        await callback.answer()
        return
    kb = _pending_orders_keyboard(orders)
    await callback.message.edit_text(
        '<b>⏳ Ожидающие заявки</b>\n\nНажмите на заявку для управления:',
        parse_mode=ParseMode.HTML, reply_markup=kb
    )
    await callback.answer()


@admin_router.callback_query(F.data.startswith("order_view_"))
async def order_view(callback: CallbackQuery):
    """Карточка одной заявки с кнопками Одобрить/Отклонить"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    request_id = int(callback.data.split("_")[2])
    req = await get_bank_request(request_id)
    if not req:
        await callback.answer("Заявка не найдена", show_alert=True)
        return

    plans = await get_setting("plans")
    plan = plans.get(req["plan_key"], {})
    bank_name = "🏦 Монобанк" if req["bank"] == "mono" else "💳 ПриватБанк"
    status_map = {"pending": "⏳ Ожидает", "approved": "✅ Одобрена", "rejected": "❌ Отклонена"}
    status_text = status_map.get(req["status"], req["status"])
    dt = req["created_at"][:16].replace("T", " ") if req.get("created_at") else "—"

    receipt_file_id = req.get("receipt_file_id")
    receipt_line = "📎 Квитанция: <b>есть</b> (кнопка ниже)" if receipt_file_id else "📎 Квитанция: <i>не прикреплена</i>"

    text = (
        f'<b>📋 Заявка #{req["id"]}</b>\n\n'
        f'👤 Пользователь: <a href="tg://user?id={req["user_id"]}">{req.get("user_name", str(req["user_id"]))}</a> '
        f'(<code>{req["user_id"]}</code>)\n'
        f'🏷 Тариф: <b>{plan.get("name", req["plan_key"])}</b>\n'
        f'💳 Банк: <b>{bank_name}</b>\n'
        f'💵 Сумма: <b>{req["amount"]}₴</b>\n'
        f'📅 Дата: <b>{dt}</b>\n'
        f'📌 Статус: <b>{status_text}</b>\n'
        f'{receipt_line}'
    )

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    if req["status"] == "pending":
        action_row = [
            InlineKeyboardButton(
                text="✅ Одобрить",
                callback_data=f"req_approve_{request_id}_{req['user_id']}_{req['plan_key']}"
            ),
            InlineKeyboardButton(
                text="❌ Отклонить",
                callback_data=f"req_reject_{request_id}_{req['user_id']}"
            ),
        ]
        rows = [action_row]
        if receipt_file_id:
            rows.append([InlineKeyboardButton(
                text="📎 Показать квитанцию",
                callback_data=f"show_receipt_{request_id}"
            )])
        rows.append([InlineKeyboardButton(text="⬅️ К списку", callback_data="orders_pending")])
        kb = InlineKeyboardMarkup(inline_keyboard=rows)
    else:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_orders")]
        ])

    await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    await callback.answer()


@admin_router.callback_query(F.data == "orders_approved")
async def orders_approved(callback: CallbackQuery):
    await _show_orders(callback, "approved", "✅ Выполненные заказы")


@admin_router.callback_query(F.data == "orders_rejected")
async def orders_rejected(callback: CallbackQuery):
    await _show_orders(callback, "rejected", "❌ Отклонённые заявки")


@admin_router.callback_query(F.data == "orders_all")
async def orders_all(callback: CallbackQuery):
    await _show_orders(callback, None, "📋 Все заказы")


@admin_router.callback_query(F.data.startswith("show_receipt_"))
async def show_receipt(callback: CallbackQuery):
    """Отправить квитанцию администратору"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    request_id = int(callback.data.split("_")[2])
    req = await get_bank_request(request_id)
    if not req:
        await callback.answer("Заявка не найдена", show_alert=True)
        return

    receipt_file_id = req.get("receipt_file_id")
    if not receipt_file_id:
        await callback.answer("📎 Квитанция не прикреплена", show_alert=True)
        return

    bank_name = "Монобанк" if req.get("bank") == "mono" else "ПриватБанк"
    plans = await get_setting("plans")
    plan = plans.get(req["plan_key"], {})

    await callback.answer()
    await callback.bot.send_photo(
        callback.from_user.id,
        photo=receipt_file_id,
        caption=(
            f'📎 <b>Квитанция к заявке #{request_id}</b>\n\n'
            f'👤 {req.get("user_name", str(req["user_id"]))} (<code>{req["user_id"]}</code>)\n'
            f'🏷 {plan.get("name", req["plan_key"])} · {bank_name} · {req["amount"]}₴'
        ),
        parse_mode=ParseMode.HTML
    )
