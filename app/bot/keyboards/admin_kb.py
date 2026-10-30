from typing import List, Optional
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from app.models.chore import Chore
from app.models.flat import FlatMember
from app.models.rule import FlatRule
from app.services.chore_service import WEEKDAYS_DISPLAY


# ------------------- RULES MANAGEMENT KEYBOARDS ------------------- #

def get_rules_view_kb(is_admin: bool = False) -> Optional[InlineKeyboardMarkup]:
    """Action buttons attached to community rules view."""
    if not is_admin:
        return None

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="➕ Yangi qoida qo'shish",
                    callback_data="rule:add"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🗑 Qoidani o'chirish",
                    callback_data="rule:delete_menu"
                ),
                InlineKeyboardButton(
                    text="🔄 Standart qoidalar",
                    callback_data="rule:reset_defaults"
                ),
            ],
        ]
    )


def get_rules_delete_kb(rules: List[FlatRule]) -> InlineKeyboardMarkup:
    """Inline buttons listing rules that can be deleted by admin."""
    keyboard = []
    for r in rules:
        keyboard.append([
            InlineKeyboardButton(
                text=f"🗑 {r.order_num}. {r.title}",
                callback_data=f"rule_del:{r.id}"
            )
        ])

    keyboard.append([
        InlineKeyboardButton(
            text="🔙 Bekor qilish",
            callback_data="rules:show"
        )
    ])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# ------------------- ADMIN DASHBOARD & CHORE SETTINGS ------------------- #

def get_admin_panel_kb() -> InlineKeyboardMarkup:
    """Main administrative dashboard actions."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🛠 Navbatchilikni sozlash",
                    callback_data="admin:chores_menu"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📜 Kvartira qoidalarini boshqarish",
                    callback_data="rules:show"
                ),
            ],
        ]
    )


def get_chores_admin_menu_kb() -> InlineKeyboardMarkup:
    """Chore duty scheduler settings menu."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📅 Kunlik navbatchi biriktirish",
                    callback_data="admin:assign_weekday"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="👥 Juftliklarni belgilash",
                    callback_data="admin:assign_pairs"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="➕ Yangi vazifa qo'shish",
                    callback_data="admin:add_chore"
                ),
                InlineKeyboardButton(
                    text="📋 Vazifalar nazorati",
                    callback_data="admin:chore_list"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🔙 Admin panel",
                    callback_data="admin:menu"
                ),
            ],
        ]
    )


def get_chores_picker_kb(chores: List[Chore], prefix: str = "chore_sel") -> InlineKeyboardMarkup:
    """Renders selectable list of chores."""
    keyboard = []
    for c in chores:
        keyboard.append([
            InlineKeyboardButton(
                text=f"📌 {c.title}",
                callback_data=f"{prefix}:{c.id}"
            )
        ])
    keyboard.append([
        InlineKeyboardButton(
            text="🔙 Orqaga",
            callback_data="admin:chores_menu"
        )
    ])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_weekdays_picker_kb(chore_id: int) -> InlineKeyboardMarkup:
    """Weekday selector buttons (Monday-Sunday)."""
    keyboard = [
        [
            InlineKeyboardButton(text="Dushanba (MON)", callback_data=f"wday_sel:{chore_id}:MON"),
            InlineKeyboardButton(text="Seshanba (TUE)", callback_data=f"wday_sel:{chore_id}:TUE"),
        ],
        [
            InlineKeyboardButton(text="Chorshanba (WED)", callback_data=f"wday_sel:{chore_id}:WED"),
            InlineKeyboardButton(text="Payshanba (THU)", callback_data=f"wday_sel:{chore_id}:THU"),
        ],
        [
            InlineKeyboardButton(text="Juma (FRI)", callback_data=f"wday_sel:{chore_id}:FRI"),
            InlineKeyboardButton(text="Shanba (SAT)", callback_data=f"wday_sel:{chore_id}:SAT"),
        ],
        [
            InlineKeyboardButton(text="Yakshanba (SUN)", callback_data=f"wday_sel:{chore_id}:SUN"),
        ],
        [
            InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin:assign_weekday"),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_members_for_assignment_kb(
    chore_id: int, weekday: str, members: List[FlatMember]
) -> InlineKeyboardMarkup:
    """Lists members for weekday chore binding."""
    keyboard = []
    for m in members:
        name = m.user.display_name if m.user else f"ID: {m.user_id}"
        keyboard.append([
            InlineKeyboardButton(
                text=f"👤 {name}",
                callback_data=f"assign_usr:{chore_id}:{weekday}:{m.user_id}"
            )
        ])
    keyboard.append([
        InlineKeyboardButton(
            text="🔙 Kunlar tanloviga qaytish",
            callback_data=f"chore_sel:{chore_id}"
        )
    ])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_chore_frequency_kb() -> InlineKeyboardMarkup:
    """Frequency selector for custom chores."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🗓 Har kuni (DAILY)", callback_data="cfreq:DAILY"),
            ],
            [
                InlineKeyboardButton(text="📅 Haftada 1 marta (WEEKLY)", callback_data="cfreq:WEEKLY"),
            ],
            [
                InlineKeyboardButton(text="⚙️ Maxsus kunlar (CUSTOM)", callback_data="cfreq:CUSTOM"),
            ],
            [
                InlineKeyboardButton(text="🔙 Bekor qilish", callback_data="admin:chores_menu"),
            ],
        ]
    )


def get_chores_management_list_kb(chores: List[Chore]) -> InlineKeyboardMarkup:
    """Interactive toggle and delete controls for flat chores."""
    keyboard = []
    for c in chores:
        status_icon = "🟢 Faol" if c.is_active else "🔴 To'xtatilgan"
        keyboard.append([
            InlineKeyboardButton(
                text=f"{status_icon}: {c.title}",
                callback_data=f"chore_toggle:{c.id}"
            ),
            InlineKeyboardButton(
                text="🗑",
                callback_data=f"chore_del:{c.id}"
            )
        ])
    keyboard.append([
        InlineKeyboardButton(
            text="🔙 Orqaga",
            callback_data="admin:chores_menu"
        )
    ])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
