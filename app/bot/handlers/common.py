from typing import Optional
from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
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
            await message.answer(
                f"🏠 **{flat.name}** kvartirasiga xush kelibsiz!\n\n"
                f"{reply_text}\n\n"
                "Quyidagi menyu orqali navbatchilik va xarajatlarni boshqarishingiz mumkin:",
                reply_markup=get_main_menu_kb(),
                parse_mode="Markdown"
            )
            return
        else:
            await message.answer(reply_text, parse_mode="Markdown")

    # Regular start flow
    if current_flat:
        await message.answer(
            f"Assalomu alaykum, **{current_user.first_name}**!\n\n"
            f"🏠 Siz hozirda **{current_flat.name}** kvartirasi boshqaruvidasiz.\n"
            "Kerakli bo'limni tanlang:",
            reply_markup=get_main_menu_kb(),
            parse_mode="Markdown"
        )
    else:
        await message.answer(
            f"Assalomu alaykum, **{current_user.first_name}**!\n\n"
            "🌟 **'Talabalar Kvartira Boshqaruvi'** tizimiga xush kelibsiz!\n\n"
            "Bu bot orqali siz xonadoshlaringiz bilan birga:\n"
            "🔹 Kunlik navbatchilikni (tozalash, musor, suv) adolatli taqsimlaysiz\n"
            "🔹 Umumiy oziq-ovqat va kommunal xarajatlarni hisoblab borasiz\n"
            "🔹 Kim kimga qancha qarz ekanligini avtomatik soddalashtirasiz\n\n"
            "Boshlash uchun yangi kvartira yarating yoki xonadoshingiz bergan kod bilan qo'shiling:",
            reply_markup=get_welcome_kb(),
            parse_mode="Markdown"
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
        "📚 **Foydalanish bo'yicha qo'llanma:**\n\n"
        "1️⃣ **Navbatchilik:**\n"
        "• Har kuni navbat avtomatik ravishda keyingi xonadoshga o'tadi (Round-robin).\n"
        "• Belgilangan vaqtda bot navbatchiga eslatma yuboradi.\n"
        "• Vazifani bajargach, `✅ Bajarildi` tugmasini bosing.\n\n"
        "2️⃣ **Xarajatlar va Qarzlar:**\n"
        "• Umumiy bozorlik yoki to'lov qilganingizda `➕ Xarajat qo'shish` tugmasi orqali kiriting.\n"
        "• Bot summani barcha xonadoshlarga teng bo'lib, har kimning hisobiga yozib boradi.\n"
        "• `📊 Kvartira balansi` bo'limida kim qancha sarflagani va kim kimga qancha qarz ekanligi ko'rinadi.\n\n"
        "3️⃣ **Yangi a'zolar:**\n"
        "• `⚙️ Kvartira sozlamalari` orqali taklif havolasini olib, yangi xonadoshni qo'shishingiz mumkin."
    )
    await message.answer(text, parse_mode="Markdown")
