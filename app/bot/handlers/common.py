from typing import Optional
from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from html import escape
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession
from app.bot.keyboards.common_kb import get_main_menu_kb
from app.bot.keyboards.flat_kb import get_welcome_kb
from app.models.flat import Flat
from app.models.user import User
from app.services.onboarding_service import OnboardingService

router = Router(name="common_router")


@router.message(CommandStart())
async def cmd_start(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    current_user: Optional[User] = None,
    current_flat: Optional[Flat] = None,
) -> None:
    """
    Handles /start command with deep linking support (e.g. /start join_KV_XXXXX).
    """
    await state.clear()
    command_args = message.text.split()[1] if len(message.text.split()) > 1 else ""

    # Safe user name resolution with fallback
    user_name = (
        current_user.first_name
        if current_user and current_user.first_name
        else (message.from_user.first_name if message.from_user and message.from_user.first_name else "Foydalanuvchi")
    )
    safe_user = escape(user_name)
    user_id = current_user.id if current_user else (message.from_user.id if message.from_user else 0)

    # Check for deep-link invite code (e.g. /start join_KV-9B4X2A or /start KV-9B4X2A)
    invite_code = OnboardingService.parse_deep_link_payload(command_args)
    if invite_code:
        success, reply_text, flat = await OnboardingService.join_flat_by_invite(
            session=session,
            user_id=user_id,
            invite_code=invite_code,
        )
        if success and flat:
            safe_name = escape(flat.name)
            safe_reply = escape(reply_text)
            await message.answer(
                f"🏠 <b>{safe_name}</b> kvartirasiga xush kelibsiz!\n\n"
                f"{safe_reply}\n\n"
                "Quyidagi menyu orqali navbatchilik va kassa-bozorlikni boshqarishingiz mumkin:",
                reply_markup=get_main_menu_kb(),
                parse_mode="HTML"
            )
            return
        else:
            await message.answer(escape(reply_text), parse_mode="HTML")

    # Regular start flow
    if current_flat:
        safe_flat = escape(current_flat.name)
        await message.answer(
            f"Assalomu alaykum, <b>{safe_user}</b>!\n\n"
            f"🏠 Siz hozirda <b>{safe_flat}</b> kvartirasi boshqaruvidasiz.\n"
            "Kerakli bo'limni tanlang:",
            reply_markup=get_main_menu_kb(),
            parse_mode="HTML"
        )
    else:
        await message.answer(
            f"Assalomu alaykum, <b>{safe_user}</b>!\n\n"
            "🌟 <b>'Tartibli Xonadosh'</b> tizimiga xush kelibsiz!\n\n"
            "Bu bot orqali siz xonadoshlaringiz bilan birga:\n"
            "🔹 Kunlik va haftalik navbatchilikni (oshxona, 10L suv, juftlik tozalash) adolatli taqsimlaysiz\n"
            "🔹 Umumiy bozorlik va kassa zaxirasini shaffof boshqarasiz\n"
            "🔹 Kvartira qoidalariga (22:30 tinchlik soati, idish yuvish tartibi) amal qilasiz\n\n"
            "Boshlash uchun yangi kvartira yarating yoki xonadoshingiz bergan kod bilan qo'shiling:",
            reply_markup=get_welcome_kb(),
            parse_mode="HTML"
        )


@router.message(F.text == "❌ Bekor qilish")
@router.message(Command("cancel"))
async def cmd_cancel(
    message: Message,
    state: FSMContext,
    current_flat: Optional[Flat]
) -> None:
    """Cancels active FSM conversation and returns to main menu."""
    await state.clear()
    if current_flat:
        await message.answer(
            "Amal bekor qilindi. Bosh menyudasiz.",
            reply_markup=get_main_menu_kb(),
            parse_mode="HTML"
        )
    else:
        await message.answer(
            "Amal bekor qilindi.",
            reply_markup=get_welcome_kb(),
            parse_mode="HTML"
        )


@router.message(F.text == "ℹ️ Yordam")
@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    """Provides user guide and workflow instructions."""
    text = (
        "📚 <b>Foydalanish bo'yicha qo'llanma:</b>\n\n"
        "1️⃣ <b>Navbatchilik (Chores):</b>\n"
        "• Har kuni navbat avtomatik tarzda xonadoshlar o'rtasida aylanadi (Round-robin va Juftlik navbatchiligi).\n"
        "• 10L toza suv, oshxona, haftalik 11 bosqichli tozalash bo'yicha bot eslatib boradi.\n"
        "• Vazifani bajargach, <code>✅ Bajarildi</code> tugmasini bosing.\n\n"
        "2️⃣ <b>Bozorlik va Umumiy Kassa:</b>\n"
        "• Murakkab o'zaro qarzdorlik o'rniga yagona umumiy kassa tizimi joriy qilingan.\n"
        "• <code>📥 Pul yig'ish</code> orqali barcha xonadoshlardan teng mablag' yig'iladi.\n"
        "• Bozorlik qilinganda <code>🧾 Xarid kiritish</code> orqali chek summasi (masalan, 370 293 so'm) kiritiladi va kassadan avtomatik chegiriladi.\n\n"
        "3️⃣ <b>Kvartira qoidalari:</b>\n"
        "• Soat 22:30 dan keyin tinchlik soati, shaxsiy idishlarni darhol yuvish va mehmondo'stlik odoblari belgilanadi.\n\n"
        "4️⃣ <b>Yangi a'zolar:</b>\n"
        "• <code>⚙️ Kvartira sozlamalari</code> orqali taklif havolasini olib, yangi xonadoshlarni qo'shishingiz mumkin."
    )
    await message.answer(text, parse_mode="HTML")
