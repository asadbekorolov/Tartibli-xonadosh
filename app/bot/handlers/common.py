from typing import Optional
from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.html import quote
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
    current_user: User,
    current_flat: Optional[Flat],
) -> None:
    """
    Handles /start command with deep linking support (e.g. /start join_KV_XXXXX).
    """
    await state.clear()
    command_args = message.text.split()[1] if len(message.text.split()) > 1 else ""

    # Check for deep-link invite code (e.g. /start join_KV-9B4X2A or /start KV-9B4X2A)
    invite_code = OnboardingService.parse_deep_link_payload(command_args)
    if invite_code:
        success, reply_text, flat = await OnboardingService.join_flat_by_invite(
            session=session,
            user_id=current_user.id,
            invite_code=invite_code,
        )
        if success and flat:
            safe_name = quote(flat.name)
            safe_reply = quote(reply_text)
            await message.answer(
                f"🏠 <b>{safe_name}</b> kvartirasiga xush kelibsiz!\n\n"
                f"{safe_reply}\n\n"
                "Quyidagi menyu orqali navbatchilik va xarajatlarni boshqarishingiz mumkin:",
                reply_markup=get_main_menu_kb(),
                parse_mode="HTML"
            )
            return
        else:
            await message.answer(quote(reply_text), parse_mode="HTML")

    # Regular start flow
    if current_flat:
        safe_user = quote(current_user.first_name)
        safe_flat = quote(current_flat.name)
        await message.answer(
            f"Assalomu alaykum, <b>{safe_user}</b>!\n\n"
            f"🏠 Siz hozirda <b>{safe_flat}</b> kvartirasi boshqaruvidasiz.\n"
            "Kerakli bo'limni tanlang:",
            reply_markup=get_main_menu_kb(),
            parse_mode="HTML"
        )
    else:
        safe_user = quote(current_user.first_name)
        await message.answer(
            f"Assalomu alaykum, <b>{safe_user}</b>!\n\n"
            "🌟 <b>'Talabalar Kvartira Boshqaruvi'</b> tizimiga xush kelibsiz!\n\n"
            "Bu bot orqali siz xonadoshlaringiz bilan birga:\n"
            "🔹 Kunlik navbatchilikni (tozalash, musor, suv) adolatli taqsimlaysiz\n"
            "🔹 Umumiy oziq-ovqat va kommunal xarajatlarni hisoblab borasiz\n"
            "🔹 Kim kimga qancha qarz ekanligini avtomatik soddalashtirasiz\n\n"
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
            reply_markup=get_main_menu_kb()
        )
    else:
        await message.answer(
            "Amal bekor qilindi.",
            reply_markup=get_welcome_kb()
        )


@router.message(F.text == "ℹ️ Yordam")
@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    """Provides user guide and workflow instructions."""
    text = (
        "📚 <b>Foydalanish bo'yicha qo'llanma:</b>\n\n"
        "1️⃣ <b>Navbatchilik:</b>\n"
        "• Har kuni navbat avtomatik ravishda keyingi xonadoshga o'tadi (Round-robin).\n"
        "• Belgilangan vaqtda bot navbatchiga eslatma yuboradi.\n"
        "• Vazifani bajargach, <code>✅ Bajarildi</code> tugmasini bosing.\n\n"
        "2️⃣ <b>Xarajatlar va Qarzlar:</b>\n"
        "• Umumiy bozorlik yoki to'lov qilganingizda <code>➕ Xarajat qo'shish</code> tugmasi orqali kiriting.\n"
        "• Bot summani barcha xonadoshlarga teng bo'lib, har kimning hisobiga yozib boradi.\n"
        "• <code>📊 Kvartira balansi</code> bo'limida kim qancha sarflagani va kim kimga qancha qarz ekanligi ko'rinadi.\n\n"
        "3️⃣ <b>Yangi a'zolar:</b>\n"
        "• <code>⚙️ Kvartira sozlamalari</code> orqali taklif havolasini olib, yangi xonadoshni qo'shishingiz mumkin."
    )
    await message.answer(text, parse_mode="HTML")
