from typing import Optional
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession
from app.bot.keyboards.common_kb import get_cancel_kb, get_main_menu_kb
from app.bot.keyboards.flat_kb import get_flat_settings_kb
from app.bot.states.flat_states import CreateFlatSG, JoinFlatSG
from app.config import get_settings
from app.models.flat import Flat, FlatRole
from app.models.user import User
from app.repositories.flat_repo import FlatRepository
from app.services.onboarding_service import OnboardingService

router = Router(name="onboarding_router")
settings = get_settings()


# ------------------- FLAT CREATION FLOW ------------------- #

@router.callback_query(F.data == "flat:create")
async def cb_create_flat(callback: CallbackQuery, state: FSMContext) -> None:
    """Initiates flat registration state machine."""
    await callback.answer()
    await state.set_state(CreateFlatSG.waiting_for_name)
    await callback.message.answer(
        "📝 Kvartirangiz uchun nom kiriting:\n"
        "(Masalan: *Chilonzor 19-mavze, 42-kvartira* yoki *TTJ 3-bino, 214-xona*)",
        reply_markup=get_cancel_kb(),
        parse_mode="Markdown"
    )


@router.message(CreateFlatSG.waiting_for_name)
async def process_flat_name(message: Message, state: FSMContext) -> None:
    name = message.text.strip()
    if len(name) < 3:
        await message.answer("⚠️ Nom juda qisqa. Kamida 3 ta belgi kiriting:")
        return

    await state.update_data(flat_name=name)
    await state.set_state(CreateFlatSG.waiting_for_address)
    await message.answer(
        "📍 Kvartira manzilini kiriting (yoki o'tkazib yuborish uchun `-` belgisini yozing):",
        reply_markup=get_cancel_kb()
    )


@router.message(CreateFlatSG.waiting_for_address)
async def process_flat_address(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    current_user: User
) -> None:
    address_text = message.text.strip()
    address = None if address_text == "-" else address_text

    data = await state.get_data()
    flat_name = data["flat_name"]
    await state.clear()

    # Create flat and seed initial default student chores
    try:
        flat = await OnboardingService.create_flat_for_user(
            session=session,
            creator_id=current_user.id,
            flat_name=flat_name,
            address=address,
        )
    except ValueError as e:
        await message.answer(f"⚠️ {e}", reply_markup=get_main_menu_kb())
        return

    invite_link = f"https://t.me/{settings.BOT_NAME}?start=join_{flat.invite_code}"


    await message.answer(
        f"🎉 **Kvartira muvaffaqiyatli yaratildi!**\n\n"
        f"🏠 **Nomi:** {flat.name}\n"
        f"📍 **Manzili:** {flat.address or 'Kiritilmagan'}\n"
        f"🔑 **Taklif kodi:** `{flat.invite_code}`\n\n"
        f"👥 Xonadoshlaringizni qo'shish uchun ushbu havolani yuboring:\n"
        f"{invite_link}\n\n"
        "Standart navbatchilik vazifalari (oshxona, musor, suv) avtomatik faollashtirildi!",
        reply_markup=get_main_menu_kb(),
        parse_mode="Markdown"
    )


# ------------------- FLAT JOIN FLOW ------------------- #

@router.callback_query(F.data == "flat:join")
async def cb_join_flat(callback: CallbackQuery, state: FSMContext) -> None:
    """Prompts for flat invite code."""
    await callback.answer()
    await state.set_state(JoinFlatSG.waiting_for_code)
    await callback.message.answer(
        "🔑 Kvartira taklif kodini kiriting:\n(Masalan: `KV-A1B2C3`)",
        reply_markup=get_cancel_kb(),
        parse_mode="Markdown"
    )


@router.message(JoinFlatSG.waiting_for_code)
async def process_join_code(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    current_user: User
) -> None:
    invite_code = message.text.strip()
    await state.clear()

    success, reply_text, flat = await OnboardingService.join_flat_by_invite(
        session=session,
        user_id=current_user.id,
        invite_code=invite_code,
    )

    if success and flat:
        await message.answer(
            f"{reply_text}\n\n"
            f"🏠 **Kvartira:** {flat.name}\n\n"
            "Endi siz ham umumiy navbatchilik va xarajatlar ro'yxatidasiz!",
            reply_markup=get_main_menu_kb(),
            parse_mode="Markdown"
        )
    else:
        await message.answer(
            f"{reply_text}\nKodni qayta tekshirib ko'ring yoki /start bosing.",
            reply_markup=get_main_menu_kb(),
            parse_mode="Markdown"
        )


# ------------------- FLAT MEMBERS & SETTINGS ------------------- #

@router.message(F.text == "👥 Xonadoshlar")
async def show_members(
    message: Message,
    session: AsyncSession,
    current_flat: Optional[Flat]
) -> None:
    if not current_flat:
        await message.answer("Siz hali kvartiraga qo'shilmagansiz. /start bosing.")
        return

    members = await FlatRepository.get_members(session, current_flat.id)
    text_lines = [
        f"👥 **'{current_flat.name}' kvartirasi a'zolari ({len(members)} kishi):**\n"
    ]

    for idx, member in enumerate(members, start=1):
        role_badge = "👑 Admin" if member.role == FlatRole.ADMIN else "👤 Xonadosh"
        text_lines.append(f"{idx}. {member.user.display_name} — {role_badge}")

    text_lines.append(f"\n🔑 Taklif kodi: `{current_flat.invite_code}`")
    await message.answer("\n".join(text_lines), parse_mode="Markdown")


@router.message(F.text == "⚙️ Kvartira sozlamalari")
async def show_settings(
    message: Message,
    session: AsyncSession,
    current_flat: Optional[Flat]
) -> None:
    if not current_flat:
        await message.answer("Siz hali kvartiraga qo'shilmagansiz. /start bosing.")
        return

    members = await FlatRepository.get_members(session, current_flat.id)
    text = (
        f"⚙️ **Kvartira sozlamalari va ma'lumotlari:**\n\n"
        f"🏠 **Nomi:** {current_flat.name}\n"
        f"📍 **Manzili:** {current_flat.address or 'Mavjud emas'}\n"
        f"👥 **A'zolar soni:** {len(members)} ta\n"
        f"🔑 **Taklif kodi:** `{current_flat.invite_code}`\n\n"
        f"Xonadoshlarni taklif qilish uchun quyidagi tugmani bosing:"
    )
    await message.answer(
        text,
        reply_markup=get_flat_settings_kb(current_flat.invite_code, settings.BOT_NAME),
        parse_mode="Markdown"
    )
