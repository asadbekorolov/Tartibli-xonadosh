from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from app.models.flat import FlatTemplateType


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


def get_template_picker_kb() -> InlineKeyboardMarkup:
    """Preset template selector for apartment multi-tenant setups."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🏢 Katta Kvartira (6–10 kishi)",
                    callback_data=f"flat_tpl:{FlatTemplateType.LARGE_FLAT.value}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🏠 Ixcham Kvartira (2–5 kishi)",
                    callback_data=f"flat_tpl:{FlatTemplateType.COMPACT_FLAT.value}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🛏 TTJ / Yotoqxona",
                    callback_data=f"flat_tpl:{FlatTemplateType.DORMITORY.value}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⚙️ Shaxsiy (Custom)",
                    callback_data=f"flat_tpl:{FlatTemplateType.CUSTOM.value}"
                )
            ],
        ]
    )


def get_flat_settings_kb(invite_code: str, bot_username: str) -> InlineKeyboardMarkup:
    """Flat settings and member invite keyboard."""
    invite_link = f"https://t.me/{bot_username}?start=join_{invite_code}"
    share_url = f"https://t.me/share/url?url={invite_link}&text=Xonadoshlarimiz%20tizimiga%20qo%27shiling!"

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
                    text="📜 Kvartira qoidalarini ko'rish",
                    callback_data="rules:show"
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
