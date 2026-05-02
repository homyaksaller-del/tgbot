import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import SUPPORT_USERNAME
from database import (
    get_setting, save_invoice, get_invoice as db_get_invoice,
    mark_invoice_paid, save_purchase,
    save_bank_request, update_bank_request_message,
    update_bank_request_receipt,
    get_user_purchases, get_user_bank_requests
)
from keyboards import (
    main_menu_keyboard, country_keyboard, plans_keyboard,
    payment_method_ua_keyboard, payment_method_other_keyboard,
    bank_paid_keyboard, crypto_currency_keyboard,
    payment_check_keyboard, funpay_keyboard, back_main_keyboard
)
from cryptobot import create_invoice as crypto_create_invoice, check_invoice_paid


class BankPaymentStates(StatesGroup):
    waiting_receipt = State()
from keyauth import generate_key

logger = logging.getLogger(__name__)
router = Router()

WELCOME_TEXT = (
    '<b><tg-emoji emoji-id="5870982283724328568">⚙️</tg-emoji> Добро пожаловать!</b>\n\n'
    'Здесь вы можете приобрести лицензионный ключ для нашей программы.\n\n'
    '<tg-emoji emoji-id="5870633910337015697">✅</tg-emoji> Выберите действие:'
)


@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(WELCOME_TEXT, parse_mode=ParseMode.HTML, reply_markup=main_menu_keyboard())


@router.callback_query(F.data == "back_main")
async def back_main(callback: CallbackQuery):
    await callback.message.edit_text(WELCOME_TEXT, parse_mode=ParseMode.HTML, reply_markup=main_menu_keyboard())
    await callback.answer()


# ─── BOT INFO ────────────────────────────────────────────────────

@router.callback_query(F.data == "bot_info")
async def bot_info_callback(callback: CallbackQuery):
    info = await get_setting("bot_info")
    text = (
        f'<b><tg-emoji emoji-id="6028435952299413210">ℹ️</tg-emoji> Информация о боте</b>\n\n'
        f'{info}'
    )
    await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=back_main_keyboard())
    await callback.answer()


# ─── SUPPORT ─────────────────────────────────────────────────────

@router.callback_query(F.data == "support")
async def support_callback(callback: CallbackQuery):
    text = (
        f'<b><tg-emoji emoji-id="5870994129244131212">👤</tg-emoji> Поддержка</b>\n\n'
        f'По всем вопросам обращайтесь к нашему оператору:\n\n'
        f'<tg-emoji emoji-id="5769289093221454192">🔗</tg-emoji> {SUPPORT_USERNAME}'
    )
    await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=back_main_keyboard())
    await callback.answer()


# ─── ШАГ 1: КУПИТЬ КЛЮЧ → ВЫБОР СТРАНЫ ──────────────────────────

@router.callback_query(F.data == "buy_key")
async def buy_key_callback(callback: CallbackQuery):
    text = (
        '<b><tg-emoji emoji-id="5904462880941545555">🪙</tg-emoji> Выберите вашу страну</b>\n\n'
        'От этого зависят доступные способы оплаты:'
    )
    await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=country_keyboard())
    await callback.answer()


# ─── ШАГ 2: СТРАНА ВЫБРАНА → ВЫБОР ТАРИФА ───────────────────────

@router.callback_query(F.data.startswith("country:"))
async def country_selected(callback: CallbackQuery):
    country = callback.data.split(":")[1]   # "ua" или "other"
    plans = await get_setting("plans")

    flag = "🇺🇦 Украина" if country == "ua" else "🌍 Другая страна"
    text = (
        f'<b><tg-emoji emoji-id="5886285355279193209">🏷</tg-emoji> Выберите тариф</b>\n\n'
        f'Страна: <b>{flag}</b>\n'
        f'<tg-emoji emoji-id="5886285355279193209">🏷</tg-emoji> Доступные планы:'
    )
    await callback.message.edit_text(
        text, parse_mode=ParseMode.HTML,
        reply_markup=plans_keyboard(plans, country)
    )
    await callback.answer()


# ─── ШАГ 3: ТАРИФ ВЫБРАН → СПОСОБ ОПЛАТЫ ────────────────────────

@router.callback_query(F.data.startswith("plan:"))
async def plan_selected(callback: CallbackQuery):
    # plan:ua:7  или  plan:other:30
    _, country, plan_key = callback.data.split(":")
    plans = await get_setting("plans")

    if plan_key not in plans:
        await callback.answer("Тариф не найден", show_alert=True)
        return

    plan = plans[plan_key]

    if country == "ua":
        price_str = f"UAH: <b>{plan['uah']}₴</b>"
        methods_text = "🏦 Монобанк  •  💳 ПриватБанк  •  🤖 КриптоБот"
        kb = payment_method_ua_keyboard(plan_key)
    else:
        price_str = f"USD: <b>{plan['usd']}$</b>"
        methods_text = "🛒 FunPay  •  🤖 КриптоБот"
        kb = payment_method_other_keyboard(plan_key)

    text = (
        f'<b><tg-emoji emoji-id="5886285355279193209">🏷</tg-emoji> Тариф: {plan["name"]}</b>\n\n'
        f'<tg-emoji emoji-id="5904462880941545555">🪙</tg-emoji> Цена: {price_str}\n\n'
        f'<tg-emoji emoji-id="5870753782874246579">✍</tg-emoji> Выберите способ оплаты:\n'
        f'<i>{methods_text}</i>'
    )
    await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
    await callback.answer()


# ─── МОНОБАНК ────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("pay_mono_"))
async def pay_mono(callback: CallbackQuery):
    plan_key = callback.data[len("pay_mono_"):]
    plans = await get_setting("plans")

    if plan_key not in plans:
        await callback.answer("Тариф не найден", show_alert=True)
        return

    plan = plans[plan_key]
    mono_card = await get_setting("mono_card") or "4441 1111 3063 8699"
    mono_name = await get_setting("mono_name") or "Дмитро Г."

    text = (
        f'<b>🏦 Оплата через Монобанк</b>\n\n'
        f'Тариф: <b>{plan["name"]}</b>\n'
        f'Сумма: <b>{plan["uah"]}₴</b>\n\n'
        f'<tg-emoji emoji-id="5870753782874246579">✍</tg-emoji> <b>Реквизиты:</b>\n'
        f'Номер карты: <code>{mono_card}</code>\n'
        f'Получатель: <b>{mono_name}</b>\n\n'
        f'<tg-emoji emoji-id="6028435952299413210">ℹ️</tg-emoji> Переведите точную сумму и нажмите кнопку ниже.\n'
        f'После проверки ключ будет выдан вручную или автоматически.'
    )
    await callback.message.edit_text(
        text, parse_mode=ParseMode.HTML,
        reply_markup=bank_paid_keyboard(plan_key, "mono")
    )
    await callback.answer()


# ─── ПРИВАТБАНК ──────────────────────────────────────────────────

@router.callback_query(F.data.startswith("pay_privat_"))
async def pay_privat(callback: CallbackQuery):
    plan_key = callback.data[len("pay_privat_"):]
    plans = await get_setting("plans")

    if plan_key not in plans:
        await callback.answer("Тариф не найден", show_alert=True)
        return

    plan = plans[plan_key]
    privat_card = await get_setting("privat_card") or "4149 4975 2946 3277"
    privat_name = await get_setting("privat_name") or "Дмитро Г."

    text = (
        f'<b>💳 Оплата через ПриватБанк</b>\n\n'
        f'Тариф: <b>{plan["name"]}</b>\n'
        f'Сумма: <b>{plan["uah"]}₴</b>\n\n'
        f'<tg-emoji emoji-id="5870753782874246579">✍</tg-emoji> <b>Реквизиты:</b>\n'
        f'Номер карты: <code>{privat_card}</code>\n'
        f'Получатель: <b>{privat_name}</b>\n\n'
        f'<tg-emoji emoji-id="6028435952299413210">ℹ️</tg-emoji> Переведите точную сумму и нажмите кнопку ниже.\n'
        f'После проверки ключ будет выдан вручную или автоматически.'
    )
    await callback.message.edit_text(
        text, parse_mode=ParseMode.HTML,
        reply_markup=bank_paid_keyboard(plan_key, "privat")
    )
    await callback.answer()


# ─── ПОДТВЕРЖДЕНИЕ БАНКОВСКОГО ПЕРЕВОДА ──────────────────────────

@router.callback_query(F.data.startswith("bank_confirm_"))
async def bank_confirm(callback: CallbackQuery, state: FSMContext):
    # bank_confirm_mono_7  или  bank_confirm_privat_30
    parts = callback.data.split("_")
    # parts = ["bank", "confirm", "mono"/"privat", plan_key]
    bank = parts[2]
    plan_key = parts[3]

    plans = await get_setting("plans")
    plan = plans.get(plan_key, {})
    bank_name = "Монобанк" if bank == "mono" else "ПриватБанк"

    # Сохраняем данные в FSM и ждём фото квитанции
    await state.set_state(BankPaymentStates.waiting_receipt)
    await state.update_data(bank=bank, plan_key=plan_key)

    text = (
        f'<b>📎 Прикрепите квитанцию</b>\n\n'
        f'Тариф: <b>{plan.get("name", plan_key)}</b>\n'
        f'Банк: <b>{bank_name}</b>\n'
        f'Сумма: <b>{plan.get("uah", 0)}₴</b>\n\n'
        f'📸 Пожалуйста, отправьте <b>скриншот или фото квитанции</b> об оплате.\n\n'
        f'<i>Это ускорит проверку вашего платежа.</i>'
    )
    await callback.message.edit_text(text, parse_mode=ParseMode.HTML)
    await callback.answer()


@router.message(BankPaymentStates.waiting_receipt, F.photo)
async def bank_receipt_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    bank = data.get("bank")
    plan_key = data.get("plan_key")
    await state.clear()

    plans = await get_setting("plans")
    plan = plans.get(plan_key, {})
    bank_name = "Монобанк" if bank == "mono" else "ПриватБанк"
    amount = plan.get("uah", 0)

    from config import ADMIN_IDS, SUPPORT_USERNAME
    from keyboards import admin_request_keyboard

    user = message.from_user
    # Берём наибольший размер фото
    photo = message.photo[-1]
    receipt_file_id = photo.file_id

    # Сохраняем заявку в БД
    request_id = await save_bank_request(
        user_id=user.id,
        user_name=user.full_name,
        plan_key=plan_key,
        bank=bank,
        amount=amount
    )
    # Сохраняем file_id квитанции
    await update_bank_request_receipt(request_id, receipt_file_id)

    text = (
        f'<b>✅ Заявка отправлена!</b>\n\n'
        f'Тариф: <b>{plan.get("name", plan_key)}</b>\n'
        f'Банк: <b>{bank_name}</b>\n'
        f'Сумма: <b>{amount}₴</b>\n\n'
        f'📎 Квитанция получена и отправлена администратору.\n'
        f'ℹ️ Ключ будет выдан в течение нескольких минут.\n\n'
        f'По вопросам: {SUPPORT_USERNAME}'
    )
    await message.answer(text, parse_mode=ParseMode.HTML, reply_markup=back_main_keyboard())

    # Уведомляем админов — сначала фото с подписью, потом кнопки
    bot = message.bot
    admin_caption = (
        f'💰 <b>Новая заявка #{request_id} ({bank_name})</b>\n\n'
        f'👤 Пользователь: <a href="tg://user?id={user.id}">{user.full_name}</a> (<code>{user.id}</code>)\n'
        f'🏷 Тариф: <b>{plan.get("name", plan_key)}</b>\n'
        f'💵 Сумма: <b>{amount}₴</b>\n\n'
        f'📎 Квитанция об оплате:'
    )
    admin_text = (
        f'💰 <b>Заявка #{request_id} — выберите действие:</b>'
    )
    for admin_id in ADMIN_IDS:
        try:
            # Сначала фото квитанции с описанием заявки
            await bot.send_photo(
                admin_id,
                photo=receipt_file_id,
                caption=admin_caption,
                parse_mode=ParseMode.HTML
            )
            # Затем сообщение с кнопками подтверждения/отклонения
            msg = await bot.send_message(
                admin_id, admin_text,
                parse_mode=ParseMode.HTML,
                reply_markup=admin_request_keyboard(request_id, user.id, plan_key)
            )
            await update_bank_request_message(request_id, admin_id, msg.message_id)
        except Exception as e:
            logger.error(f"Failed to notify admin {admin_id}: {e}")


@router.message(BankPaymentStates.waiting_receipt)
async def bank_receipt_wrong_type(message: Message, state: FSMContext):
    """Пользователь прислал не фото"""
    await message.answer(
        '📸 <b>Пожалуйста, отправьте именно фото (скриншот) квитанции.</b>\n\n'
        'Просто сфотографируйте или сделайте скриншот подтверждения оплаты и отправьте его сюда.',
        parse_mode=ParseMode.HTML
    )


# ─── CRYPTOBOT (УКРАИНА) ──────────────────────────────────────────

@router.callback_query(F.data.startswith("pay_crypto_ua_"))
async def pay_crypto_ua(callback: CallbackQuery):
    plan_key = callback.data[len("pay_crypto_ua_"):]
    plans = await get_setting("plans")

    if plan_key not in plans:
        await callback.answer("Тариф не найден", show_alert=True)
        return

    plan = plans[plan_key]
    text = (
        f'<b><tg-emoji emoji-id="5260752406890711732">🤖</tg-emoji> Оплата КриптоБот</b>\n\n'
        f'Тариф: <b>{plan["name"]}</b>\n'
        f'Сумма: <b>{plan["usd"]}$</b>\n\n'
        f'<tg-emoji emoji-id="5904462880941545555">🪙</tg-emoji> Выберите криптовалюту:'
    )
    await callback.message.edit_text(
        text, parse_mode=ParseMode.HTML,
        reply_markup=crypto_currency_keyboard(plan_key, "ua")
    )
    await callback.answer()


# ─── CRYPTOBOT (ДРУГАЯ СТРАНА) ────────────────────────────────────

@router.callback_query(F.data.startswith("pay_crypto_other_"))
async def pay_crypto_other(callback: CallbackQuery):
    plan_key = callback.data[len("pay_crypto_other_"):]
    plans = await get_setting("plans")

    if plan_key not in plans:
        await callback.answer("Тариф не найден", show_alert=True)
        return

    plan = plans[plan_key]
    text = (
        f'<b><tg-emoji emoji-id="5260752406890711732">🤖</tg-emoji> Оплата КриптоБот</b>\n\n'
        f'Тариф: <b>{plan["name"]}</b>\n'
        f'Сумма: <b>{plan["usd"]}$</b>\n\n'
        f'<tg-emoji emoji-id="5904462880941545555">🪙</tg-emoji> Выберите криптовалюту:'
    )
    await callback.message.edit_text(
        text, parse_mode=ParseMode.HTML,
        reply_markup=crypto_currency_keyboard(plan_key, "other")
    )
    await callback.answer()


# ─── ВЫБОР ВАЛЮТЫ И СОЗДАНИЕ ИНВОЙСА ─────────────────────────────

@router.callback_query(F.data.startswith("crypto_"))
async def crypto_currency_selected(callback: CallbackQuery):
    # crypto_USDT_ua_7  или  crypto_TON_other_30
    parts = callback.data.split("_")
    # parts = ["crypto", "USDT", "ua"/"other", plan_key]
    currency = parts[1]
    country = parts[2]
    plan_key = parts[3]

    plans = await get_setting("plans")
    if plan_key not in plans:
        await callback.answer("Тариф не найден", show_alert=True)
        return

    plan = plans[plan_key]
    amount = plan["usd"]

    await callback.answer("⏳ Создаём счёт...")

    description = f"Лицензионный ключ — {plan['name']}"
    payload = f"{plan_key}:{callback.from_user.id}:{country}"

    invoice = await crypto_create_invoice(
        amount=amount,
        currency=currency,
        description=description,
        payload=payload
    )

    if not invoice:
        await callback.message.edit_text(
            '<tg-emoji emoji-id="5870657884844462243">❌</tg-emoji> <b>Ошибка создания счёта.</b>\n\n'
            'Попробуйте позже или обратитесь в поддержку.',
            parse_mode=ParseMode.HTML,
            reply_markup=back_main_keyboard()
        )
        return

    invoice_id = str(invoice["invoice_id"])
    pay_url = invoice["pay_url"]

    await save_invoice(
        invoice_id=invoice_id,
        user_id=callback.from_user.id,
        plan_key=plan_key,
        amount=amount,
        currency=currency
    )

    text = (
        f'<b><tg-emoji emoji-id="5260752406890711732">🤖</tg-emoji> Счёт создан!</b>\n\n'
        f'<tg-emoji emoji-id="5886285355279193209">🏷</tg-emoji> Тариф: <b>{plan["name"]}</b>\n'
        f'<tg-emoji emoji-id="5904462880941545555">🪙</tg-emoji> Сумма: <b>{amount} {currency}</b>\n'
        f'<tg-emoji emoji-id="5983150113483134607">⏰</tg-emoji> Счёт действует <b>1 час</b>\n\n'
        f'<tg-emoji emoji-id="5769289093221454192">🔗</tg-emoji> <a href="{pay_url}">Нажмите для оплаты</a>\n\n'
        f'После оплаты нажмите кнопку <b>«Проверить оплату»</b>:'
    )
    await callback.message.edit_text(
        text, parse_mode=ParseMode.HTML,
        reply_markup=payment_check_keyboard(invoice_id, plan_key),
        disable_web_page_preview=True
    )


# ─── FUNPAY ──────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("pay_funpay_"))
async def pay_funpay(callback: CallbackQuery):
    plan_key = callback.data[len("pay_funpay_"):]
    plans = await get_setting("plans")

    if plan_key not in plans:
        await callback.answer("Тариф не найден", show_alert=True)
        return

    plan = plans[plan_key]
    text = (
        f'<b><tg-emoji emoji-id="5769126056262898415">🛒</tg-emoji> Оплата через FunPay</b>\n\n'
        f'Тариф: <b>{plan["name"]}</b>\n'
        f'Цена: <b>{plan["usd"]}$</b>\n\n'
        f'<tg-emoji emoji-id="6028435952299413210">ℹ️</tg-emoji> После оплаты на FunPay ключ будет выдан автоматически!\n\n'
        f'Нажмите кнопку ниже для оплаты:'
    )
    await callback.message.edit_text(
        text, parse_mode=ParseMode.HTML,
        reply_markup=funpay_keyboard(plan["funpay"], plan_key)
    )
    await callback.answer()


# ─── ПРОВЕРКА ОПЛАТЫ (КРИПТОБОТ) ─────────────────────────────────

@router.callback_query(F.data.startswith("check_pay_"))
async def check_payment(callback: CallbackQuery):
    invoice_id = callback.data[len("check_pay_"):]

    db_invoice = await db_get_invoice(invoice_id)
    if not db_invoice:
        await callback.answer("Счёт не найден", show_alert=True)
        return

    if db_invoice["status"] == "paid":
        await callback.answer("Этот счёт уже был оплачен ранее ✅", show_alert=True)
        return

    await callback.answer("⏳ Проверяем оплату...")

    is_paid = await check_invoice_paid(int(invoice_id))

    if not is_paid:
        await callback.answer(
            "❌ Оплата не найдена. Подождите немного и попробуйте снова.",
            show_alert=True
        )
        return

    await mark_invoice_paid(invoice_id)

    plans = await get_setting("plans")
    plan_key = db_invoice["plan_key"]
    plan = plans.get(plan_key, {})

    await callback.message.edit_text(
        '<tg-emoji emoji-id="5345906554510012647">🔄</tg-emoji> <b>Оплата подтверждена! Выдаём ключ...</b>',
        parse_mode=ParseMode.HTML
    )

    license_key = await generate_key(plan_key, callback.from_user.id)

    if not license_key:
        await callback.message.edit_text(
            '<tg-emoji emoji-id="5870657884844462243">❌</tg-emoji> <b>Ошибка генерации ключа.</b>\n\n'
            'Оплата прошла успешно, но ключ не удалось создать автоматически.\n'
            f'Обратитесь в поддержку с ID счёта: <code>{invoice_id}</code>',
            parse_mode=ParseMode.HTML,
            reply_markup=back_main_keyboard()
        )
        return

    await save_purchase(
        user_id=callback.from_user.id,
        plan_key=plan_key,
        license_key=license_key,
        payment_method="cryptobot",
        amount=db_invoice["amount"],
        currency=db_invoice["currency"]
    )

    text = (
        f'<b><tg-emoji emoji-id="6041731551845159060">🎉</tg-emoji> Оплата прошла успешно!</b>\n\n'
        f'<tg-emoji emoji-id="5886285355279193209">🏷</tg-emoji> Тариф: <b>{plan.get("name", plan_key)}</b>\n\n'
        f'<tg-emoji emoji-id="6037249452824072506">🔒</tg-emoji> <b>Ваш лицензионный ключ:</b>\n\n'
        f'<code>{license_key}</code>\n\n'
        f'<tg-emoji emoji-id="6028435952299413210">ℹ️</tg-emoji> Скопируйте ключ и введите его в программе.\n'
        f'По вопросам обращайтесь в поддержку.'
    )
    await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=back_main_keyboard())


# ─── ЛИЧНЫЙ КАБИНЕТ ──────────────────────────────────────────────

@router.callback_query(F.data == "profile")
async def profile_callback(callback: CallbackQuery):
    user = callback.from_user
    purchases = await get_user_purchases(user.id)
    bank_requests = await get_user_bank_requests(user.id)

    from keyboards import profile_keyboard

    # Ищем последний активный ключ
    active_key = None
    for p in purchases:
        if p.get("key_status") == "issued":
            active_key = p
            break

    total_spent = sum(p["amount"] for p in purchases)
    currency = purchases[0]["currency"] if purchases else "UAH"

    # Считаем pending заявки
    pending_requests = [r for r in bank_requests if r["status"] == "pending"]

    text = (
        f'<b>👤 Личный кабинет</b>\n\n'
        f'🪪 ID: <code>{user.id}</code>\n'
        f'📛 Имя: <b>{user.full_name}</b>\n\n'
    )

    if active_key:
        from config import SUPPORT_USERNAME
        plans = await get_setting("plans")
        plan_name = plans.get(active_key["plan_key"], {}).get("name", active_key["plan_key"])
        dt = active_key["created_at"][:10] if active_key.get("created_at") else "—"
        text += (
            f'🔑 <b>Активный ключ:</b>\n'
            f'<code>{active_key["license_key"]}</code>\n'
            f'🏷 Тариф: <b>{plan_name}</b>\n'
            f'📅 Получен: <b>{dt}</b>\n\n'
        )
    else:
        text += '🔑 <b>Активных ключей нет</b>\n\n'

    text += f'📦 Всего покупок: <b>{len(purchases)}</b>\n'
    if total_spent > 0:
        text += f'💰 Потрачено: <b>{total_spent:.0f} {currency}</b>\n'
    if pending_requests:
        text += f'⏳ Заявок на рассмотрении: <b>{len(pending_requests)}</b>\n'

    await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=profile_keyboard(purchases))
    await callback.answer()


@router.callback_query(F.data == "profile_orders")
async def profile_orders(callback: CallbackQuery):
    user = callback.from_user
    purchases = await get_user_purchases(user.id)
    bank_requests = await get_user_bank_requests(user.id)

    from keyboards import back_profile_keyboard
    plans = await get_setting("plans")

    if not purchases and not bank_requests:
        await callback.message.edit_text(
            '<b>📦 Мои заказы</b>\n\n📭 У вас пока нет заказов',
            parse_mode=ParseMode.HTML,
            reply_markup=back_profile_keyboard()
        )
        await callback.answer()
        return

    text = '<b>📦 Мои заказы</b>\n\n'

    # Банковские заявки (ожидающие / отклонённые)
    pending_or_rejected = [r for r in bank_requests if r["status"] in ("pending", "rejected")]
    if pending_or_rejected:
        text += '<b>— Заявки на оплату —</b>\n'
        for r in pending_or_rejected:
            plan_name = plans.get(r["plan_key"], {}).get("name", r["plan_key"])
            bank_n = "🏦 Моно" if r["bank"] == "mono" else "💳 Приват"
            status_icon = "⏳" if r["status"] == "pending" else "❌"
            dt = r["created_at"][:10] if r.get("created_at") else "—"
            text += f'{status_icon} {plan_name} · {bank_n} · {r["amount"]}₴ · {dt}\n'
        text += '\n'

    # Выполненные покупки
    if purchases:
        text += '<b>— Выполненные покупки —</b>\n'
        for p in purchases[:10]:
            plan_name = plans.get(p["plan_key"], {}).get("name", p["plan_key"])
            method = p.get("payment_method", "")
            if "mono" in method:
                pay_icon = "🏦"
            elif "privat" in method:
                pay_icon = "💳"
            elif "crypto" in method or "invoice" in method:
                pay_icon = "🤖"
            else:
                pay_icon = "💰"
            dt = p["created_at"][:10] if p.get("created_at") else "—"
            text += f'✅ {plan_name} · {pay_icon} {p["amount"]}₴ · {dt}\n'

    await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=back_profile_keyboard())
    await callback.answer()


@router.callback_query(F.data == "profile_keys")
async def profile_keys(callback: CallbackQuery):
    user = callback.from_user
    purchases = await get_user_purchases(user.id)
    plans = await get_setting("plans")

    from keyboards import back_profile_keyboard
    from config import SUPPORT_USERNAME

    if not purchases:
        await callback.message.edit_text(
            '<b>🔑 Мои ключи</b>\n\n📭 У вас ещё нет ключей',
            parse_mode=ParseMode.HTML,
            reply_markup=back_profile_keyboard()
        )
        await callback.answer()
        return

    text = '<b>🔑 Мои ключи</b>\n\n'
    for p in purchases:
        plan_name = plans.get(p["plan_key"], {}).get("name", p["plan_key"])
        dt = p["created_at"][:10] if p.get("created_at") else "—"
        text += (
            f'🏷 <b>{plan_name}</b> · {dt}\n'
            f'<code>{p["license_key"]}</code>\n\n'
        )

    text += f'По вопросам: {SUPPORT_USERNAME}'
    await callback.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=back_profile_keyboard())
    await callback.answer()
