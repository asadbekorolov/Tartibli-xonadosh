from typing import Optional
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from html import escape
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession
from app.bot.keyboards.common_kb import get_main_menu_kb
from app.models.flat import Flat, FlatRole
from app.models.user import User
from app.repositories.chore_repo import ChoreRepository
from app.repositories.flat_repo import FlatRepository
from app.services.chore_service import ChoreService

router = Router(name="admin_router")


def get_community_rules_text(flat: Flat) -> str:
    safe_flat = escape(flat.name)
    quiet_time = escape(flat.quiet_hours_start)
    return (
        f"📜 <b>'{safe_flat}' Kvartira Qoidalari va Tartibi:</b>\n\n"
        f"🌙 <b>1. Tinchlik va osoyishtalik soati ({quiet_time}):</b>\n"
        f"• Har kuni kechki soat <b>{quiet_time}</b> dan boshlab kvartirada to'liq sukunat saqlanadi.\n"
        f"• Baland ovozda gaplashish, video yoki o'yinlarni karnayda eshitish taqiqlanadi (naushnik taqing).\n\n"
        f"🍽 <b>2. Idish-tovoq siyosati (Dish Policy):</b>\n"
        f"• Har bir xonadosh o'zining shaxsiy idishini (chashka, likopcha, qoshiq) ovqatlangandan so'ng <b>darhol</b> yuvishi shart!\n"
        f"• Chanoqda (rakovinada) idish to'plab qo'yish qat'iyan taqiqlanadi.\n"
        f"• Qozon, tova va umumiy dasturxon anjomlari kunlik navbatchi zimmasida.\n\n"
        f"👥 <b>3. Mehmonlar tartibi:</b>\n"
        f"• Kvartiraga do'st yoki qarindoshlarni taklif qilishdan kamida <b>3–4 soat oldin</b> umumiy guruhda xabar berilishi va barcha xonadoshlar roziligi olinishi kerak.\n"
        f"• Kechki tinchlik soatidan keyin begonalarning qolishi qat'iyan taqiqlanadi.\n\n"
        f"⚠️ <b>4. Navbatchilik va intizom jarimalari:</b>\n"
        f"• O'z navbatchiligini sababsiz bajarmagan xonadosh: navbatdan tashqari 2 kunlik navbatchilik yoki umumiy kassaga kelishilgan jarima to'laydi.\n"
        f"• Tozalik va tartib — barcha xonadoshlarning umumiy qulayligi kafolati!"
    )


@router.message(F.text == "📜 Kvartira Qoidalari")
async def show_community_rules(
    message: Message,
    current_flat: Optional[Flat]
) -> None:
    """Displays standard apartment community rules."""
    if not current_flat:
        await message.answer("Siz hali kvartiraga qo'shilmagansiz. /start bosing.", parse_mode="HTML")
        return

    text = get_community_rules_text(current_flat)
    await message.answer(text, parse_mode="HTML")


@router.callback_query(F.data == "rules:show")
async def cb_show_community_rules(
    callback: CallbackQuery,
    current_flat: Optional[Flat]
) -> None:
    await callback.answer()
    if not current_flat:
        await callback.message.answer("Kvartira topilmadi.", parse_mode="HTML")
        return

    text = get_community_rules_text(current_flat)
    await callback.message.answer(text, parse_mode="HTML")


# ------------------- ADMIN CONTROLS ------------------- #

@router.message(F.text == "👑 Admin boshqaruvi")
async def cmd_admin_panel(
    message: Message,
    session: AsyncSession,
    current_user: Optional[User],
    current_flat: Optional[Flat],
) -> None:
    """Admin dashboard for role-based controls."""
    if not current_flat or not current_user:
        await message.answer("Kvartira topilmadi.", parse_mode="HTML")
        return

    membership = await FlatRepository.get_membership(session, current_flat.id, current_user.id)
    if not membership or membership.role != FlatRole.ADMIN:
        await message.answer("⚠️ Ushbu bo'lim faqat kvartira admini uchun ochiq.", parse_mode="HTML")
        return

    members = await FlatRepository.get_members(session, current_flat.id)
    chores = await ChoreRepository.get_flat_chores(session, current_flat.id)

    lines = [
        f"👑 <b>'{escape(current_flat.name)}' Admin Boshqaruv Paneli:</b>\n",
        f"👥 A'zolar soni: {len(members)} ta",
        f"📋 Faol vazifalar soni: {len(chores)} ta",
        f"🌙 Tinchlik soati: {escape(current_flat.quiet_hours_start)}",
        f"💰 Kassa zaxirasi: {int(current_flat.fund_balance):,} so'm\n",
        "Navbatchilik grafigi avtomatik rotatsiya tizimida ishlamoqda."
    ]

    await message.answer("\n".join(lines), reply_markup=get_main_menu_kb(), parse_mode="HTML")
