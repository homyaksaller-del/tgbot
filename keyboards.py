from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Купить ключ", callback_data="buy_key",
                              icon_custom_emoji_id="5904462880941545555")],
        [InlineKeyboardButton(text="👤 Личный кабинет", callback_data="profile")],
        [InlineKeyboardButton(text="Информация о боте", callback_data="bot_info",
                              icon_custom_emoji_id="6028435952299413210")],
        [InlineKeyboardButton(text="Поддержка", callback_data="support",
                              icon_custom_emoji_id="5870994129244131212")],
    ])


# ─── ВЫБОР СТРАНЫ ────────────────────────────────────────────────

def country_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🇺🇦 Украина", callback_data="country:ua"),
            InlineKeyboardButton(text="🌍 Другая страна", callback_data="country:other"),
        ],
        [InlineKeyboardButton(text="Назад", callback_data="back_main",
                              icon_custom_emoji_id="5893057118545646106")],
    ])


# ─── ТАРИФЫ ──────────────────────────────────────────────────────

def plans_keyboard(plans: dict, country: str) -> InlineKeyboardMarkup:
    buttons = []
    plan_order = ["1", "3", "7", "14", "30", "90", "0"]
    for key in plan_order:
        if key not in plans:
            continue
        plan = plans[key]
        price_label = f"{plan['uah']}₴" if country == "ua" else f"{plan['usd']}$"
        buttons.append([InlineKeyboardButton(
            text=f"{plan['name']} — {price_label}",
            callback_data=f"plan:{country}:{key}",
            icon_custom_emoji_id="5886285355279193209"
        )])
    buttons.append([InlineKeyboardButton(text="Назад", callback_data="buy_key",
                                         icon_custom_emoji_id="5893057118545646106")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ─── СПОСОБЫ ОПЛАТЫ ──────────────────────────────────────────────

def payment_method_ua_keyboard(plan_key: str) -> InlineKeyboardMarkup:
    """Украина: Монобанк, ПриватБанк, КриптоБот"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏦 Монобанк", callback_data=f"pay_mono_{plan_key}")],
        [InlineKeyboardButton(text="💳 ПриватБанк", callback_data=f"pay_privat_{plan_key}")],
        [InlineKeyboardButton(text="🤖 КриптоБот", callback_data=f"pay_crypto_ua_{plan_key}",
                              icon_custom_emoji_id="5260752406890711732")],
        [InlineKeyboardButton(text="Назад", callback_data="country:ua",
                              icon_custom_emoji_id="5893057118545646106")],
    ])


def payment_method_other_keyboard(plan_key: str) -> InlineKeyboardMarkup:
    """Другая страна: ФанПей, КриптоБот"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 FunPay", callback_data=f"pay_funpay_{plan_key}",
                              icon_custom_emoji_id="5769126056262898415")],
        [InlineKeyboardButton(text="🤖 КриптоБот", callback_data=f"pay_crypto_other_{plan_key}",
                              icon_custom_emoji_id="5260752406890711732")],
        [InlineKeyboardButton(text="Назад", callback_data="country:other",
                              icon_custom_emoji_id="5893057118545646106")],
    ])


# ─── БАНКОВСКИЙ ПЕРЕВОД ───────────────────────────────────────────

def bank_paid_keyboard(plan_key: str, bank: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Я оплатил(а)",
                              callback_data=f"bank_confirm_{bank}_{plan_key}",
                              icon_custom_emoji_id="5870633910337015697")],
        [InlineKeyboardButton(text="Отмена", callback_data=f"plan:ua:{plan_key}",
                              icon_custom_emoji_id="5870657884844462243")],
    ])


# ─── КРИПТА ──────────────────────────────────────────────────────

def crypto_currency_keyboard(plan_key: str, country: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="USDT", callback_data=f"crypto_USDT_{country}_{plan_key}",
                                 icon_custom_emoji_id="5904462880941545555"),
            InlineKeyboardButton(text="TON",  callback_data=f"crypto_TON_{country}_{plan_key}",
                                 icon_custom_emoji_id="5904462880941545555"),
        ],
        [
            InlineKeyboardButton(text="BTC", callback_data=f"crypto_BTC_{country}_{plan_key}",
                                 icon_custom_emoji_id="5904462880941545555"),
            InlineKeyboardButton(text="ETH", callback_data=f"crypto_ETH_{country}_{plan_key}",
                                 icon_custom_emoji_id="5904462880941545555"),
        ],
        [InlineKeyboardButton(text="Назад", callback_data=f"plan:{country}:{plan_key}",
                              icon_custom_emoji_id="5893057118545646106")],
    ])


def payment_check_keyboard(invoice_id: str, plan_key: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Проверить оплату", callback_data=f"check_pay_{invoice_id}",
                              icon_custom_emoji_id="5870633910337015697")],
        [InlineKeyboardButton(text="Отмена", callback_data="buy_key",
                              icon_custom_emoji_id="5870657884844462243")],
    ])


def funpay_keyboard(funpay_url: str, plan_key: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Оплатить на FunPay", url=funpay_url)],
        [InlineKeyboardButton(text="Назад", callback_data=f"plan:other:{plan_key}")],
    ])


def back_main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="На главную", callback_data="back_main",
                              icon_custom_emoji_id="5873147866364514353")],
    ])


# ─── ADMIN ───────────────────────────────────────────────────────

def admin_panel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Редактировать цены", callback_data="admin_prices",
                              icon_custom_emoji_id="5870676941614354370")],
        [InlineKeyboardButton(text="Редактировать инфо", callback_data="admin_edit_info",
                              icon_custom_emoji_id="5870753782874246579")],
        [InlineKeyboardButton(text="Управление ключами", callback_data="admin_keys",
                              icon_custom_emoji_id="6041731551845159060")],
        [InlineKeyboardButton(text="📦 Заказы", callback_data="admin_orders")],
        [InlineKeyboardButton(text="Статистика", callback_data="admin_stats",
                              icon_custom_emoji_id="5870921681735781843")],
        [InlineKeyboardButton(text="Закрыть", callback_data="admin_close",
                              icon_custom_emoji_id="5870657884844462243")],
    ])


def admin_prices_keyboard(plans: dict) -> InlineKeyboardMarkup:
    buttons = []
    for key in ["1", "3", "7", "14", "30", "90", "0"]:
        if key not in plans:
            continue
        buttons.append([InlineKeyboardButton(text=f"✏️ {plans[key]['name']}",
                                              callback_data=f"edit_plan_{key}",
                                              icon_custom_emoji_id="5870676941614354370")])
    buttons.append([InlineKeyboardButton(text="Назад", callback_data="admin_panel",
                                          icon_custom_emoji_id="5893057118545646106")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Назад в админку", callback_data="admin_panel",
                              icon_custom_emoji_id="5893057118545646106")],
    ])


def admin_edit_price_keyboard(plan_key: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Изменить USD", callback_data=f"edit_usd_{plan_key}",
                                 icon_custom_emoji_id="5870676941614354370"),
            InlineKeyboardButton(text="Изменить RUB", callback_data=f"edit_rub_{plan_key}",
                                 icon_custom_emoji_id="5870676941614354370"),
        ],
        [InlineKeyboardButton(text="Изменить UAH", callback_data=f"edit_uah_{plan_key}",
                              icon_custom_emoji_id="5870676941614354370")],
        [InlineKeyboardButton(text="Назад", callback_data="admin_prices",
                              icon_custom_emoji_id="5893057118545646106")],
    ])


def admin_request_keyboard(request_id: int, user_id: int, plan_key: str) -> InlineKeyboardMarkup:
    """Кнопки для заявки банковской оплаты в уведомлении админу"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="✅ Выдать ключ",
                callback_data=f"req_approve_{request_id}_{user_id}_{plan_key}"
            ),
            InlineKeyboardButton(
                text="❌ Отклонить",
                callback_data=f"req_reject_{request_id}_{user_id}"
            ),
        ],
    ])


def admin_orders_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏳ Ожидающие", callback_data="orders_pending")],
        [InlineKeyboardButton(text="✅ Выполненные", callback_data="orders_approved")],
        [InlineKeyboardButton(text="❌ Отклонённые", callback_data="orders_rejected")],
        [InlineKeyboardButton(text="📋 Все заказы", callback_data="orders_all")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_panel")],
    ])


def profile_keyboard(purchases: list) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="📦 Мои заказы", callback_data="profile_orders")],
        [InlineKeyboardButton(text="🔑 Мои ключи", callback_data="profile_keys")],
        [InlineKeyboardButton(text="На главную", callback_data="back_main",
                              icon_custom_emoji_id="5873147866364514353")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def back_profile_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад в кабинет", callback_data="profile")],
        [InlineKeyboardButton(text="На главную", callback_data="back_main",
                              icon_custom_emoji_id="5873147866364514373")],
    ])
