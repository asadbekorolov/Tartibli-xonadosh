from decimal import Decimal
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_fund_menu_kb() -> InlineKeyboardMarkup:
    """Primary communal fund and market dashboard inline actions."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💰 Kassa balansi",
                    callback_data="fund:balance"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📥 Pul yig'ish",
                    callback_data="fund:collect"
                ),
                InlineKeyboardButton(
                    text="🧾 Xarid kiritish",
                    callback_data="fund:expense"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📜 Xaridlar tarixi",
                    callback_data="fund:history"
                ),
            ],
        ]
    )


def get_fund_collect_confirm_kb(per_person_amount: Decimal) -> InlineKeyboardMarkup:
    """Confirmation button for communal fund collection."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Barcha a'zolardan yig'ishni tasdiqlash",
                    callback_data=f"fund_coll_ok:{int(per_person_amount)}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Bekor qilish",
                    callback_data="fund:cancel"
                )
            ]
        ]
    )
