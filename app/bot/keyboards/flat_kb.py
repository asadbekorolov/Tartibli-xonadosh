from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_welcome_kb() -> InlineKeyboardMarkup:
    """Welcome inline keyboard for onboarding new flatmates."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🏠 Yangi kvartira yaratish",
                    callback_data="flat:create"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔑 Kod orqali qo'shilish",
                    callback_data="flat:join"
                )
            ],
        ]
    )


def get_flat_settings_kb(invite_code: str, bot_username: str) -> InlineKeyboardMarkup:
    """Flat settings and member invite keyboard."""
    invite_link = f"https://t.me/{bot_username}?start=join_{invite_code}"
    share_url = f"https://t.me/share/url?url={invite_link}&text=Xonadoshlarimiz%20guruhiga%20qo%27shiling!"

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔗 Xonadoshlarga taklif havolasini yuborish",
                    url=share_url
                )
            ],
            [
                InlineKeyboardButton(
                    text="➕ Yangi navbatchilik qo'shish",
                    callback_data="chore:add_new"
                )
            ],
        ]
    )
