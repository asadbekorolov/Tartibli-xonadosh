from typing import Optional
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from html import escape
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
        "(Masalan: <i>Chilonzor 19-mavze, 42-kvartira</i> yoki <i>TTJ 3-bino, 214-xona</i>)",
        reply_markup=get_cancel_kb(),
        parse_mode="HTML"
    )


@router.message(CreateFlatSG.waiting_for_name)
async def process_flat_name(message: Message, state: FSMContext) -> None:
    name = message.text.strip()
    if len(name) < 3:
        await message.answer("⚠️ Nom juda qisqa. Kamida 3 ta belgi kiriting:", parse_mode="HTML")
        return

    await state.update_data(flat_name=name)
    await state.set_state(CreateFlatSG.waiting_for_address)
    await message.answer(
        "📍 Kvartira manzilini kiriting (yoki o'tkazib yuborish uchun <code>-</code> belgisini yozing):",
        reply_markup=get_cancel_kb(),
        parse_mode="HTML"
    )


@router.message(CreateFlatSG.waiting_for_address)
async def process_flat_address(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    current_user: Optional[User] = None
) -> None:
    address_text = message.text.strip()
    address = None if address_text == "-" else address_text

    data = await state.get_data()
    flat_name = data["flat_name"]
    await state.clear()

    user_id = current_user.id if current_user else (message.from_user.id if message.from_user else 0)

    # Create flat and seed initial default student chores
    try:
        flat = await OnboardingService.create_flat_for_user(
            session=session,
            creator_id=user_id,
            flat_name=flat_name,
            address=address,
        )
    except ValueError as e:
        await message.answer(f"⚠️ {escape(str(e))}", reply_markup=get_main_menu_kb(), parse_mode="HTML")
        return

    invite_link = f"https://t.me/{settings.BOT_NAME}?start=join_{flat.invite_code}"
    safe_name = escape(flat.name)
    safe_address = escape(flat.address) if flat.address else "Kiritilmagan"
    safe_code = escape(flat.invite_code)

    await message.answer(
        f"🎉 <b>Kvartira muvaffaqiyatli yaratildi!</b>\n\n"
        f"🏠 <b>Nomi:</b> {safe_name}\n"
        f"📍 <b>Manzili:</b> {safe_address}\n"
        f"🔑 <b>Taklif kodi:</b> <code>{safe_code}</code>\n\n"
        f"👥 Xonadoshlaringizni qo'shish uchun ushbu havolani yuboring:\n"
        f"{invite_link}\n\n"
        "Standart navbatchilik vazifalari (oshxona, musor, suv) avtomatik faollashtirildi!",
        reply_markup=get_main_menu_kb(),
        parse_mode="HTML"
    )


# ------------------- FLAT JOIN FLOW ------------------- #

@router.callback_query(F.data == "flat:join")
async def cb_join_flat(callback: CallbackQuery, state: FSMContext) -> None:
    """Prompts for flat invite code."""
    await callback.answer()
    await state.set_state(JoinFlatSG.waiting_for_code)
    await callback.message.answer(
        "🔑 Kvartira taklif kodini kiriting:\n(Masalan: <code>KV-A1B2C3</code>)",
        reply_markup=get_cancel_kb(),
        parse_mode="HTML"
    )


@router.message(JoinFlatSG.waiting_for_code)
async def process_join_code(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    current_user: Optional[User] = None
) -> None:
    invite_code = message.text.strip()
    await state.clear()

    user_id = current_user.id if current_user else (message.from_user.id if message.from_user else 0)

    success, reply_text, flat = await OnboardingService.join_flat_by_invite(
        session=session,
        user_id=user_id,
        invite_code=invite_code,
    )

    if success and flat:
        safe_reply = escape(reply_text)
        safe_name = escape(flat.name)
        await message.answer(
            f"{safe_reply}\n\n"
            f"🏠 <b>Kvartira:</b> {safe_name}\n\n"
            "Endi siz ham umumiy navbatchilik va xarajatlar ro'yxatidasiz!",
            reply_markup=get_main_menu_kb(),
            parse_mode="HTML"
        )
    else:
        safe_reply = escape(reply_text)
        await message.answer(
            f"{safe_reply}\nKodni qayta tekshirib ko'ring yoki /start bosing.",
            reply_markup=get_main_menu_kb(),
            parse_mode="HTML"
        )


# ------------------- FLAT MEMBERS & SETTINGS ------------------- #

@router.message(F.text == "👥 Xonadoshlar")
async def show_members(
    message: Message,
    session: AsyncSession,
    current_flat: Optional[Flat]
) -> None:
    if not current_flat:
        await message.answer("Siz hali kvartiraga qo'shilmagansiz. /start bosing.", parse_mode="HTML")
        return

    members = await FlatRepository.get_members(session, current_flat.id)
    safe_flat = escape(current_flat.name)
    text_lines = [
        f"👥 <b>'{safe_flat}' kvartirasi a'zolari ({len(members)} kishi):</b>\n"
    ]

    for idx, member in enumerate(members, start=1):
        role_badge = "👑 Admin" if member.role == FlatRole.ADMIN else "👤 Xonadosh"
        safe_user = escape(member.user.display_name)
        text_lines.append(f"{idx}. {safe_user} — {role_badge}")

    text_lines.append(f"\n🔑 Taklif kodi: <code>{escape(current_flat.invite_code)}</code>")
    await message.answer("\n".join(text_lines), parse_mode="HTML")


@router.message(F.text == "⚙️ Kvartira sozlamalari")
async def show_settings(
    message: Message,
    session: AsyncSession,
    current_flat: Optional[Flat]
) -> None:
    if not current_flat:
        await message.answer("Siz hali kvartiraga qo'shilmagansiz. /start bosing.", parse_mode="HTML")
        return

    members = await FlatRepository.get_members(session, current_flat.id)
    safe_name = escape(current_flat.name)
    safe_address = escape(current_flat.address) if current_flat.address else "Mavjud emas"
    safe_code = escape(current_flat.invite_code)
    text = (
        f"⚙️ <b>Kvartira sozlamalari va ma'lumotlari:</b>\n\n"
        f"🏠 <b>Nomi:</b> {safe_name}\n"
        f"📍 <b>Manzili:</b> {safe_address}\n"
        f"👥 <b>A'zolar soni:</b> {len(members)} ta\n"
        f"🔑 <b>Taklif kodi:</b> <code>{safe_code}</code>\n\n"
        f"Xonadoshlarni taklif qilish uchun quyidagi tugmani bosing:"
    )
    await message.answer(
        text,
        reply_markup=get_flat_settings_kb(current_flat.invite_code, settings.BOT_NAME),
        parse_mode="HTML"
    )
