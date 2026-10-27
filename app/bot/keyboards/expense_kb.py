from decimal import Decimal
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from app.models.expense import ExpenseCategory


def get_expense_categories_kb() -> InlineKeyboardMarkup:
    """Category picker for shared expenses."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🛒 Oziq-ovqat / Bozorlik",
                    callback_data=f"exp_cat:{ExpenseCategory.GROCERY.value}"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="💡 Kommunal / Wi-Fi",
                    callback_data=f"exp_cat:{ExpenseCategory.UTILITIES.value}"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🧼 Tozalash vositalari",
                    callback_data=f"exp_cat:{ExpenseCategory.CLEANING.value}"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="💧 19L Suv",
                    callback_data=f"exp_cat:{ExpenseCategory.WATER.value}"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📦 Boshqa",
                    callback_data=f"exp_cat:{ExpenseCategory.OTHER.value}"
                ),
            ],
        ]
    )


def get_settlement_confirm_kb(
    debtor_id: int, creditor_id: int, amount: Decimal
) -> InlineKeyboardMarkup:
    """Confirmation button for debt settlement."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"🤝 Qarzni to'ladim/yopdim ({int(amount):,} so'm)",
                    callback_data=f"settle_confirm:{debtor_id}:{creditor_id}:{int(amount)}"
                )
            ]
        ]
    )

