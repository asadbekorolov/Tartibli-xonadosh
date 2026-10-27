from datetime import datetime, timezone
from typing import Optional
import pytz
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession
from app.bot.keyboards.chore_kb import get_chore_actions_kb
from app.bot.keyboards.common_kb import get_cancel_kb, get_main_menu_kb
from app.bot.states.chore_states import AddChoreSG
from app.config import get_settings
from app.models.chore import ChoreStatus
from app.models.flat import Flat
from app.services.chore_service import ChoreService

router = Router(name="chores_router")
settings = get_settings()


# ------------------- VIEW TODAY'S CHORES ------------------- #

@router.message(F.text == "📋 Bugungi navbatchilik")
async def show_today_chores(
    message: Message,
    session: AsyncSession,
    current_flat: Optional[Flat]
) -> None:
    """Fetches and displays all assigned rotating chores for today."""
    if not current_flat:
        await message.answer("Siz hali kvartiraga qo'shilmagansiz. /start bosing.")
        return

    tz = pytz.timezone(settings.TIMEZONE)
    today = datetime.now(tz).date()
    assignments = await ChoreService.get_today_assignments(
        session=session,
        flat_id=current_flat.id,
        target_date=today,
    )


    if not assignments:
        await message.answer(
            f"📅 Bugungi kunda (*{today}*) kvartirada faol navbatchilik vazifalari topilmadi.\n"
            "Yangi vazifa qo'shish uchun '⚙️ Kvartira sozlamalari' bo'limiga o'ting.",
            parse_mode="Markdown"
        )
        return

    await message.answer(
        f"📅 **Bugungi navbatchilik ro'yxati ({today.strftime('%d.%m.%Y')}):**\n"
        "Xonadoshlar o'z vazifalarini bajargach, tegishli tugmani bosishlari lozim:"
    )

    for a in assignments:
        status_emoji = "⏳ Kutilmoqda"
        if a.status == ChoreStatus.COMPLETED:
            status_emoji = "✅ Bajarildi"
        elif a.status == ChoreStatus.SKIPPED:
            status_emoji = "⏭ O'tkazib yuborildi"

        text = (
            f"📌 **Vazifa:** {a.chore.title}\n"
            f"👤 **Mas'ul:** {a.assignee.display_name}\n"
            f"⏰ **Belgilangan vaqt:** {a.chore.execution_time}\n"
            f"📋 **Izoh:** {a.chore.description or 'Izoh yoq'}\n"
            f"📊 **Holati:** {status_emoji}"
        )

        await message.answer(
            text,
            reply_markup=get_chore_actions_kb(a.id, a.status),
            parse_mode="Markdown"
        )


# ------------------- CHORE INTERACTION CALLBACKS ------------------- #

@router.callback_query(F.data.startswith("chore_done:"))
async def cb_chore_done(
    callback: CallbackQuery,
    session: AsyncSession,
) -> None:
    """Marks task as completed by user."""
    assignment_id = int(callback.data.split(":")[1])
    assignment = await ChoreService.complete_chore(session, assignment_id)

    if not assignment:
        await callback.answer("Vazifa topilmadi.", show_alert=True)
        return

    await callback.answer("🎉 Barakalla! Vazifa muvaffaqiyatli bajarildi deb belgilandi!", show_alert=True)

    tz = pytz.timezone(settings.TIMEZONE)
    now_tashkent = datetime.now(tz).strftime('%H:%M')

    text = (
        f"📌 **Vazifa:** {assignment.chore.title}\n"
        f"👤 **Mas'ul:** {assignment.assignee.display_name}\n"
        f"⏰ **Vaqti:** {assignment.chore.execution_time}\n"
        f"📊 **Holati:** ✅ Bajarildi ({now_tashkent})"
    )
    await callback.message.edit_text(
        text,
        reply_markup=get_chore_actions_kb(assignment.id, ChoreStatus.COMPLETED),
        parse_mode="Markdown"
    )



@router.callback_query(F.data.startswith("chore_defer:"))
async def cb_chore_defer(
    callback: CallbackQuery,
    session: AsyncSession,
) -> None:
    """Handles chore deferral by assignee."""
    assignment_id = int(callback.data.split(":")[1])
    assignment = await ChoreService.complete_chore(
        session, assignment_id, notes="Kechiktirildi (Vazifa keyinroqqa qoldirildi)"
    )
    # We keep status as PENDING or update notes
    # Let's update notes keeping it pending
    stmt = await ChoreService.get_today_assignments(session, assignment.flat_id)
    await callback.answer(
        "⏳ Vazifa kechiktirildi deb belgilandi. Iltimos, bugun uni bajarishni unutmang!",
        show_alert=True
    )


@router.callback_query(F.data.startswith("chore_skip:"))
async def cb_chore_skip(
    callback: CallbackQuery,
    session: AsyncSession,
) -> None:
    """Marks task as skipped or deferred."""
    assignment_id = int(callback.data.split(":")[1])
    assignment = await ChoreService.skip_chore(session, assignment_id)

    if not assignment:
        await callback.answer("Vazifa topilmadi.", show_alert=True)
        return

    await callback.answer("Vazifa o'tkazib yuborildi deb belgilandi.", show_alert=True)

    text = (
        f"📌 **Vazifa:** {assignment.chore.title}\n"
        f"👤 **Mas'ul:** {assignment.assignee.display_name}\n"
        f"📊 **Holati:** ⏭ O'tkazib yuborildi"
    )
    await callback.message.edit_text(text, parse_mode="Markdown")



# ------------------- CREATE NEW CHORE FLOW ------------------- #

@router.callback_query(F.data == "chore:add_new")
async def cb_add_chore_start(callback: CallbackQuery, state: FSMContext) -> None:
    """Initiates custom chore creation dialog."""
    await callback.answer()
    await state.set_state(AddChoreSG.waiting_for_title)
    await callback.message.answer(
        "📝 Yangi navbatchilik vazifasi nomini kiriting:\n(Masalan: *Vanna va dahliz tozaligi*)",
        reply_markup=get_cancel_kb(),
        parse_mode="Markdown"
    )


@router.message(AddChoreSG.waiting_for_title)
async def process_chore_title(message: Message, state: FSMContext) -> None:
    title = message.text.strip()
    await state.update_data(title=title)
    await state.set_state(AddChoreSG.waiting_for_description)
    await message.answer(
        "📋 Vazifa bo'yicha qisqacha tavsif yoki talablarni kiriting:\n(O'tkazib yuborish uchun `-` yozing)",
        reply_markup=get_cancel_kb()
    )


@router.message(AddChoreSG.waiting_for_description)
async def process_chore_description(message: Message, state: FSMContext) -> None:
    desc = message.text.strip()
    description = None if desc == "-" else desc
    await state.update_data(description=description)
    await state.set_state(AddChoreSG.waiting_for_time)
    await message.answer(
        "⏰ Vazifa bajarilishi kerak bo'lgan vaqtni kiriting (HH:MM formatida):\n(Masalan: `21:00` yoki `09:30`)",
        reply_markup=get_cancel_kb(),
        parse_mode="Markdown"
    )


@router.message(AddChoreSG.waiting_for_time)
async def process_chore_time(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    current_flat: Optional[Flat]
) -> None:
    time_str = message.text.strip()
    data = await state.get_data()
    await state.clear()

    if not current_flat:
        await message.answer("Xatolik: kvartira topilmadi.", reply_markup=get_main_menu_kb())
        return

    chore = await ChoreService.add_custom_chore(
        session=session,
        flat_id=current_flat.id,
        title=data["title"],
        description=data["description"],
        execution_time=time_str,
    )

    await message.answer(
        f"✅ **Yangi navbatchilik vazifasi yaratildi!**\n\n"
        f"📌 **Nomi:** {chore.title}\n"
        f"⏰ **Vaqti:** {chore.execution_time}\n"
        f"🔄 **Tartibi:** Xonadoshlar navbati bo'yicha (Round-robin)",
        reply_markup=get_main_menu_kb(),
        parse_mode="Markdown"
    )
