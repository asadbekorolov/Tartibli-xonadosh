from decimal import Decimal
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_start_unregistered_kb() -> InlineKeyboardMarkup:
    """Keyboard for users not yet enrolled in any flat."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🏠 Yangi kvartira yaratish",
                    callback_data="flat_create"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔑 Kod orqali qo'shilish",
                    callback_data="flat_join"
                )
            ],
            [
                InlineKeyboardButton(
                    text="ℹ️ Bot haqida qo'llanma",
                    callback_data="show_help"
                )
            ],
        ]
    )


def get_flat_dashboard_kb(invite_code: str, bot_username: str) -> InlineKeyboardMarkup:
    """Interactive command dashboard for enrolled roommates."""
    share_url = f"https://t.me/share/url?url=https://t.me/{bot_username}?start=join_{invite_code}&text=Kvartiramizga%20qo%27shiling!"

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🧹 Navbatchilik",
                    callback_data="nav_chores"
                ),
                InlineKeyboardButton(
                    text="➕ Xarajat qo'shish",
                    callback_data="add_expense_btn"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📊 Qarzlar balansi",
                    callback_data="show_balance_btn"
                ),
                InlineKeyboardButton(
                    text="👥 Xonadoshlar",
                    callback_data="show_members_btn"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🔗 Xonadosh taklif qilish",
                    url=share_url
                )
            ],
            [
                InlineKeyboardButton(
                    text="🚪 Kvartiradan chiqish",
                    callback_data="leave_flat_btn"
                )
            ]
        ]
    )


def get_chore_action_kb(chore_id: int) -> InlineKeyboardMarkup:
    """Action buttons for chore completion or skipping."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Bajarildi",
                    callback_data=f"chore_complete:{chore_id}"
                ),
                InlineKeyboardButton(
                    text="⏭ O'tkazib yuborish",
                    callback_data=f"chore_skip:{chore_id}"
                ),
            ]
        ]
    )


def get_cancel_kb() -> InlineKeyboardMarkup:
    """Universal cancellation button for active dialogs."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="❌ Bekor qilish",
                    callback_data="cancel_action"
                )
            ]
        ]
    )


def get_settlement_kb(
    debtor_id: int, creditor_id: int, amount: Decimal
) -> InlineKeyboardMarkup:
    """One-tap debt clearance confirmation button."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"🤝 Qarzni to'ladim/yopdim ({int(amount):,} so'm)",
                    callback_data=f"settle:{debtor_id}:{creditor_id}:{int(amount)}"
                )
            ]
        ]
    )
