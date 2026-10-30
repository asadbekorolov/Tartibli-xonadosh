from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def get_main_menu_kb() -> ReplyKeyboardMarkup:
    """Primary Reply Keyboard with persistent command buttons."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="📋 Bugungi navbatchilik"),
                KeyboardButton(text="🛒 Bozorlik va Kassa"),
            ],
            [
                KeyboardButton(text="👥 Xonadoshlar"),
                KeyboardButton(text="📜 Kvartira Qoidalari"),
            ],
            [
                KeyboardButton(text="⚙️ Kvartira sozlamalari"),
                KeyboardButton(text="ℹ️ Yordam"),
            ],
        ],
        resize_keyboard=True,
        persistent=True,
    )


def get_cancel_kb() -> ReplyKeyboardMarkup:
    """Cancel action keyboard for FSM dialogs."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="❌ Bekor qilish")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
