import re
import secrets
import string
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.html import quote
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession
from bot.config import get_settings
from bot.database.crud import (
    create_flat,
    get_flat_by_id,
    get_flat_by_invite_code,
    get_flat_members,
    get_user,
    join_flat,
    leave_flat,
)
from bot.keyboards.inline import (
    get_cancel_kb,
    get_flat_dashboard_kb,
    get_start_unregistered_kb,
)

router = Router(name="flat")
settings = get_settings()


class CreateFlatSG(StatesGroup):
    waiting_for_name = State()


class JoinFlatSG(StatesGroup):
    waiting_for_code = State()


def generate_code() -> str:
    """Generates a secure 6-character alphanumeric uppercase invite code (KV-XXXXXX)."""
    alphabet = string.ascii_uppercase + string.digits
    token = "".join(secrets.choice(alphabet) for _ in range(6))
    return f"KV-{token}"


# ------------------- CREATE FLAT ------------------- #

@router.message(Command("create_flat"))
@router.callback_query(F.data == "flat_create")
async def cmd_create_flat(event: Message | CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    """Initiates flat creation state."""
    user_id = event.from_user.id
    user = await get_user(session, user_id)

    if user and user.flat_id:
        msg = "⚠️ Siz allaqachon kvartira a'zosisiz! Yangi kvartira ochishdan avval joriysidan /leave_flat orqali chiqishingiz lozim."
        if isinstance(event, CallbackQuery):
            await event.answer(msg, show_alert=True)
        else:
            await event.answer(msg)
        return

    await state.set_state(CreateFlatSG.waiting_for_name)
    text = (
        "🏠 <b>Yangi kvartira ochish:</b>\n\n"
        "Kvartirangiz uchun nom kiriting:\n"
        "<i>(Masalan: 'Chilonzor 19, 42-kvartira' yoki 'TTJ 2-bino 315-xona')</i>"
    )
    if isinstance(event, CallbackQuery):
        await event.answer()
        await event.message.answer(text, reply_markup=get_cancel_kb(), parse_mode="HTML")
    else:
        await event.answer(text, reply_markup=get_cancel_kb(), parse_mode="HTML")


@router.message(CreateFlatSG.waiting_for_name)
async def process_create_flat_name(message: Message, state: FSMContext, session: AsyncSession) -> None:
    name = message.text.strip()
    if len(name) < 3:
        await message.answer("⚠️ Nom kamida 3 ta belgidan iborat bo'lishi kerak. Qayta kiriting:")
        return

    await state.clear()
    invite_code = generate_code()

    flat = await create_flat(
        session=session,
        name=name,
        creator_id=message.from_user.id,
        invite_code=invite_code,
        max_members=settings.MAX_MEMBERS_PER_FLAT,
    )

    share_url = f"https://t.me/{settings.BOT_NAME}?start=join_{flat.invite_code}"
    safe_name = quote(flat.name)
    safe_code = quote(flat.invite_code)

    text = (
        f"🎉 <b>'{safe_name}' kvartirasi muvaffaqiyatli yaratildi!</b>\n\n"
        f"🔑 <b>Taklif kodi:</b> <code>{safe_code}</code>\n\n"
        "👥 Xonadoshlaringizni qo'shish uchun ushbu havolani ulashing:\n"
        f"{share_url}\n\n"
        "Standart navbatchilik vazifalari (Oshxona, Musor, Suv) avtomatik ishga tushirildi!"
    )
    await message.answer(
        text,
        reply_markup=get_flat_dashboard_kb(flat.invite_code, settings.BOT_NAME),
        parse_mode="HTML",
    )


# ------------------- JOIN FLAT ------------------- #

@router.message(Command("join_flat"))
@router.callback_query(F.data == "flat_join")
async def cmd_join_flat(event: Message | CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    """Handles joining via command argument or triggers FSM code prompt."""
    user_id = event.from_user.id
    user = await get_user(session, user_id)

    if user and user.flat_id:
        msg = "⚠️ Siz allaqachon kvartira a'zosisiz! Avval /leave_flat orqali chiqishingiz lozim."
        if isinstance(event, CallbackQuery):
            await event.answer(msg, show_alert=True)
        else:
            await event.answer(msg)
        return

    # Check if code was passed directly in command: /join_flat KV-XXXXXX
    if isinstance(event, Message):
        parts = event.text.split()
        if len(parts) > 1:
            code = parts[1].strip().upper()
            flat = await get_flat_by_invite_code(session, code)
            if not flat:
                await event.answer("❌ Bunday taklif kodi mavjud emas yoki eskirgan.")
                return
            success, reply_msg = await join_flat(session, user_id, flat.id)
            if success:
                safe_name = quote(flat.name)
                safe_code = quote(flat.invite_code)
                safe_msg = quote(reply_msg)
                await event.answer(
                    f"🎉 <b>{safe_msg}</b>\n\n"
                    f"🏠 <b>Kvartira:</b> {safe_name}\n"
                    f"🔑 <b>Taklif kodi:</b> <code>{safe_code}</code>",
                    reply_markup=get_flat_dashboard_kb(flat.invite_code, settings.BOT_NAME),
                    parse_mode="HTML",
                )
            else:
                await event.answer(f"⚠️ {quote(reply_msg)}")
            return

    await state.set_state(JoinFlatSG.waiting_for_code)
    text = "🔑 Kvartiraga qo'shilish uchun taklif kodini kiriting:\n<i>(Masalan: <code>KV-9B4X2A</code>)</i>"
    if isinstance(event, CallbackQuery):
        await event.answer()
        await event.message.answer(text, reply_markup=get_cancel_kb(), parse_mode="HTML")
    else:
        await event.answer(text, reply_markup=get_cancel_kb(), parse_mode="HTML")


@router.message(JoinFlatSG.waiting_for_code)
async def process_join_flat_code(message: Message, state: FSMContext, session: AsyncSession) -> None:
    raw_code = message.text.strip().upper()
    if not raw_code.startswith("KV-") and len(raw_code) == 6:
        raw_code = f"KV-{raw_code}"

    flat = await get_flat_by_invite_code(session, raw_code)
    if not flat:
        await message.answer("❌ Bunday taklif kodi topilmadi. Kodni tekshirib qayta kiriting:")
        return

    await state.clear()
    success, reply_msg = await join_flat(session, message.from_user.id, flat.id)
    if success:
        safe_name = quote(flat.name)
        safe_code = quote(flat.invite_code)
        safe_msg = quote(reply_msg)
        await message.answer(
            f"🎉 <b>{safe_msg}</b>\n\n"
            f"🏠 <b>Kvartira:</b> {safe_name}\n"
            f"🔑 <b>Taklif kodi:</b> <code>{safe_code}</code>",
            reply_markup=get_flat_dashboard_kb(flat.invite_code, settings.BOT_NAME),
            parse_mode="HTML",
        )
    else:
        await message.answer(f"⚠️ {quote(reply_msg)}", reply_markup=get_start_unregistered_kb())


# ------------------- MEMBERS & LEAVE ------------------- #

@router.message(Command("members"))
@router.callback_query(F.data == "show_members_btn")
async def cmd_members(event: Message | CallbackQuery, session: AsyncSession) -> None:
    """Lists current flatmates residing in the apartment."""
    user_id = event.from_user.id
    user = await get_user(session, user_id)

    if not user or not user.flat_id:
        msg = "Siz hech qanday kvartiraga a'zo emassiz. /start orqali kvartiraga qo'shiling."
        if isinstance(event, CallbackQuery):
            await event.answer(msg, show_alert=True)
        else:
            await event.answer(msg)
        return

    members = await get_flat_members(session, user.flat_id)
    flat = await get_flat_by_id(session, user.flat_id)

    safe_flat_name = quote(flat.name)
    lines = [f"👥 <b>'{safe_flat_name}' kvartirasi a'zolari ({len(members)}/{flat.max_members} kishi):</b>\n"]
    for idx, m in enumerate(members, start=1):
        creator_badge = " 👑 (Admin)" if m.id == flat.creator_id else ""
        safe_full_name = quote(m.full_name)
        safe_mention = quote(m.mention)
        lines.append(f"{idx}. <b>{safe_full_name}</b> ({safe_mention}){creator_badge}")

    lines.append(f"\n🔑 Taklif kodi: <code>{quote(flat.invite_code)}</code>")
    reply_text = "\n".join(lines)

    if isinstance(event, CallbackQuery):
        await event.answer()
        await event.message.answer(reply_text, parse_mode="HTML")
    else:
        await event.answer(reply_text, parse_mode="HTML")


@router.message(Command("leave_flat"))
@router.callback_query(F.data == "leave_flat_btn")
async def cmd_leave_flat(event: Message | CallbackQuery, session: AsyncSession) -> None:
    """Leaves current flat."""
    user_id = event.from_user.id
    success, reply_msg = await leave_flat(session, user_id)

    if isinstance(event, CallbackQuery):
        await event.answer(reply_msg, show_alert=True)
        if success:
            await event.message.answer(
                "Siz kvartirani tark etdingiz.", reply_markup=get_start_unregistered_kb()
            )
    else:
        await event.answer(reply_msg, reply_markup=get_start_unregistered_kb())
