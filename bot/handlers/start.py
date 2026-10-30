import re
from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from html import escape
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession
from bot.config import get_settings
from bot.database.crud import (
    get_flat_by_id,
    get_flat_by_invite_code,
    get_user,
    join_flat,
    upsert_user,
)
from bot.keyboards.inline import (
    get_flat_dashboard_kb,
    get_start_unregistered_kb,
)

router = Router(name="start")
settings = get_settings()


def parse_invite_code(arg: str) -> str | None:
    """Parses invite code from deep-link argument."""
    if not arg:
        return None
    cleaned = arg.strip().upper()
    if cleaned.startswith("JOIN_"):
        cleaned = cleaned[5:]
    if not cleaned.startswith("KV-") and len(cleaned) == 6:
        cleaned = f"KV-{cleaned}"
    if re.match(r"^KV-[A-Z0-9]{6}$", cleaned):
        return cleaned
    return None


@router.message(CommandStart())
async def handle_start(message: Message, state: FSMContext, session: AsyncSession) -> None:
    """Entrypoint for /start command, supports deep-link auto joining."""
    await state.clear()
    user = await upsert_user(
        session=session,
        user_id=message.from_user.id,
        full_name=message.from_user.full_name,
        username=message.from_user.username,
    )

    args = message.text.split()[1] if len(message.text.split()) > 1 else ""
    invite_code = parse_invite_code(args)

    # 1. Handle Deep-Link Join
    if invite_code:
        flat = await get_flat_by_invite_code(session, invite_code)
        if not flat:
            await message.answer("❌ Noto'g'ri yoki eskirgan taklif kodi.")
        else:
            success, reply_msg = await join_flat(session, user.id, flat.id)
            if success:
                safe_reply = escape(reply_msg)
                safe_name = escape(flat.name)
                safe_code = escape(flat.invite_code)
                await message.answer(
                    f"🎉 <b>{safe_reply}</b>\n\n"
                    f"🏠 <b>Kvartira:</b> {safe_name}\n"
                    f"🔑 <b>Taklif kodi:</b> <code>{safe_code}</code>\n\n"
                    "Quyidagi boshqaruv paneli orqali kerakli bo'limni tanlang:",
                    reply_markup=get_flat_dashboard_kb(flat.invite_code, settings.BOT_NAME),
                    parse_mode="HTML",
                )
                return
            else:
                await message.answer(f"⚠️ {escape(reply_msg)}")

    # 2. Check if user is already in a flat
    if user.flat_id:
        flat = await get_flat_by_id(session, user.flat_id)
        if flat:
            safe_user = escape(user.full_name)
            safe_flat = escape(flat.name)
            await message.answer(
                f"Assalomu alaykum, <b>{safe_user}</b>!\n\n"
                f"🏠 Siz <b>{safe_flat}</b> kvartirasi a'zosisiz.\n"
                f"👥 Xonadoshlar soni: {len(flat.members)} kishi\n\n"
                "Kerakli bo'limni tanlang:",
                reply_markup=get_flat_dashboard_kb(flat.invite_code, settings.BOT_NAME),
                parse_mode="HTML",
            )
            return

    # 3. New / Unregistered user
    safe_user = escape(user.full_name)
    text = (
        f"Assalomu alaykum, <b>{safe_user}</b>!\n\n"
        "🌟 <b>'Tartibli Xonadosh'</b> tizimiga xush kelibsiz!\n\n"
        "Ushbu bot talabalar kvartirasida quyidagi kundalik ishlarni 24/7 avtomatlashtiradi:\n"
        "🔹 <b>Navbatchilik:</b> Tozalik, musor va suv nazoratini navbatma-navbat (Round-robin) taqsimlash;\n"
        "🔹 <b>Eslatmalar:</b> Har kuni ertalab 08:00 da navbatchiga avtomatik bildirishnoma yuborish;\n"
        "🔹 <b>Xarajatlar:</b> Umumiy bozorlik va to'lovlarni hisoblab, qarzlarni soddalashtirish (Min-Cash-Flow).\n\n"
        "Boshlash uchun yangi kvartira yarating yoki xonadoshingiz bergan kod bilan qo'shiling:"
    )
    await message.answer(text, reply_markup=get_start_unregistered_kb(), parse_mode="HTML")


@router.message(Command("help"))
@router.callback_query(F.data == "show_help")
async def handle_help(event: Message | CallbackQuery) -> None:
    """Detailed user manual."""
    text = (
        "📖 <b>Botdan foydalanish bo'yicha qo'llanma:</b>\n\n"
        "🔹 <b>Kvartira buyruqlari:</b>\n"
        "• <code>/create_flat</code> — Yangi kvartira ochish va taklif kodini olish\n"
        "• <code>/join_flat &lt;code&gt;</code> — Taklif kodi orqali kvartiraga qo'shilish\n"
        "• <code>/members</code> — Kvartiradagi barcha xonadoshlar ro'yxati\n"
        "• <code>/leave_flat</code> — Kvartirani tark etish\n\n"
        "🔹 <b>Navbatchilik (Chores):</b>\n"
        "• <code>/chores</code> — Bugungi navbatchilar va vazifalar holati\n"
        "• <code>/add_chore &lt;nomi&gt;</code> — Yangi navbatchilik vazifasi qo'shish\n"
        "• Har kuni 08:00 da bot navbatchiga eslatma yuboradi. <i>Bajarildi</i> tugmasi bosilgach, navbat avtomatik keyingi talabaga o'tadi.\n\n"
        "🔹 <b>Xarajatlar (Expenses):</b>\n"
        "• <code>/add_expense</code> — Umumiy qilingan xarajatni kiritish va teng bo'lish\n"
        "• <code>/balance</code> — Kim kimga qancha qarz ekanligini ko'rish (Min-Cash-Flow)\n\n"
        "Savollar yoki takliflar bo'lsa, xonadoshlaringiz bilan birgalikda foydalaning!"
    )
    if isinstance(event, CallbackQuery):
        await event.answer()
        await event.message.answer(text, parse_mode="HTML")
    else:
        await event.answer(text, parse_mode="HTML")


@router.callback_query(F.data == "cancel_action")
async def handle_cancel(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    """Cancels ongoing FSM action."""
    await state.clear()
    await callback.answer("Amal bekor qilindi.")
    user = await get_user(session, callback.from_user.id)
    if user and user.flat_id:
        flat = await get_flat_by_id(session, user.flat_id)
        if flat:
            await callback.message.answer(
                "Bosh menyudasiz:",
                reply_markup=get_flat_dashboard_kb(flat.invite_code, settings.BOT_NAME),
            )
            return
    await callback.message.answer("Bosh menyudasiz:", reply_markup=get_start_unregistered_kb())
