from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession
from bot.database.crud import (
    create_chore,
    get_chore_by_id,
    get_flat_chores,
    get_user,
    mark_chore_completed_and_rotate,
    skip_chore_and_rotate,
)
from bot.keyboards.inline import get_chore_action_kb

router = Router(name="chores")


@router.message(Command("chores"))
@router.callback_query(F.data == "nav_chores")
async def cmd_list_chores(event: Message | CallbackQuery, session: AsyncSession) -> None:
    """Displays all ongoing rotating chores and current assignees."""
    user_id = event.from_user.id
    user = await get_user(session, user_id)

    if not user or not user.flat_id:
        msg = "Siz hech qanday kvartiraga a'zo emassiz. /start bosing."
        if isinstance(event, CallbackQuery):
            await event.answer(msg, show_alert=True)
        else:
            await event.answer(msg)
        return

    chores = await get_flat_chores(session, user.flat_id)
    if not chores:
        text = "Kvartirada hozircha navbatchilik vazifalari yo'q. `/add_chore <nomi>` orqali yangi vazifa qo'shishingiz mumkin."
        if isinstance(event, CallbackQuery):
            await event.answer()
            await event.message.answer(text, parse_mode="Markdown")
        else:
            await event.answer(text, parse_mode="Markdown")
        return

    intro = "📋 **Kvartira navbatchilik vazifalari va bugungi mas'ullar:**\n"
    if isinstance(event, CallbackQuery):
        await event.answer()
        await event.message.answer(intro, parse_mode="Markdown")
    else:
        await event.answer(intro, parse_mode="Markdown")

    for chore in chores:
        assignee_name = chore.current_assignee.full_name if chore.current_assignee else "Tayinlanmagan"
        status_text = "⏳ Kutilmoqda (Bajarilmagan)" if chore.status == "PENDING" else "✅ Bajarilgan"

        text = (
            f"📌 **{chore.title}**\n"
            f"👤 **Navbatchi:** {assignee_name}\n"
            f"📊 **Holati:** {status_text}\n"
            "Vazifani bajarganingizdan so'ng '✅ Bajarildi' tugmasini bosing:"
        )
        msg_target = event.message if isinstance(event, CallbackQuery) else event
        await msg_target.answer(
            text,
            reply_markup=get_chore_action_kb(chore.id),
            parse_mode="Markdown",
        )


@router.message(Command("add_chore"))
async def cmd_add_chore(message: Message, session: AsyncSession) -> None:
    """Adds a new rotating chore: /add_chore <nomi>."""
    user = await get_user(session, message.from_user.id)
    if not user or not user.flat_id:
        await message.answer("Siz kvartiraga a'zo emassiz. /start orqali kvartiraga qo'shiling.")
        return

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("⚠️ Vazifa nomini kiriting:\nMasalan: `/add_chore Oshxona va muzlatgich tozaligi`", parse_mode="Markdown")
        return

    title = parts[1].strip()
    chore = await create_chore(session, user.flat_id, title)

    await message.answer(
        f"✅ **Yangi navbatchilik vazifasi qo'shildi!**\n\n"
        f"📌 **Nomi:** {chore.title}\n"
        f"👤 **Birinchi navbatchi:** {chore.current_assignee.full_name if chore.current_assignee else 'Xonadoshlar'}\n\n"
        "Vazifa bajarilishi bilan navbat avtomatik keyingi talabaga o'tadi.",
        parse_mode="Markdown",
    )


@router.callback_query(F.data.startswith("chore_complete:"))
async def cb_chore_complete(callback: CallbackQuery, session: AsyncSession) -> None:
    """
    Marks chore as completed and advances the round-robin queue:
    assignee = members[(current_idx + 1) % N]
    """
    chore_id = int(callback.data.split(":")[1])
    result = await mark_chore_completed_and_rotate(session, chore_id)

    if not result:
        await callback.answer("Vazifa topilmadi.", show_alert=True)
        return

    chore, prev_assignee, next_assignee = result
    prev_name = prev_assignee.full_name if prev_assignee else "Xonadosh"
    next_name = next_assignee.full_name if next_assignee else "Keyingi xonadosh"
    next_mention = next_assignee.mention if next_assignee else ""

    await callback.answer("🎉 Barakalla! Vazifa bajarildi!", show_alert=True)

    text = (
        f"🌟 **Vazifa muvaffaqiyatli bajarildi!**\n\n"
        f"📌 **Vazifa:** {chore.title}\n"
        f"👤 **Bajaruvchi:** {prev_name}\n\n"
        f"🔄 **Navbat avtomatik keyingi talabaga o'tdi:**\n"
        f"👉 Yangi mas'ul: **{next_name}** ({next_mention})\n\n"
        "Tartibli hayot uchun rahmat! ✨"
    )
    await callback.message.edit_text(text, reply_markup=get_chore_action_kb(chore.id), parse_mode="Markdown")


@router.callback_query(F.data.startswith("chore_skip:"))
async def cb_chore_skip(callback: CallbackQuery, session: AsyncSession) -> None:
    """Skips chore to the next roommate without completing."""
    chore_id = int(callback.data.split(":")[1])
    result = await skip_chore_and_rotate(session, chore_id)

    if not result:
        await callback.answer("Vazifa topilmadi.", show_alert=True)
        return

    chore, prev_assignee, next_assignee = result
    next_name = next_assignee.full_name if next_assignee else "Keyingi xonadosh"

    await callback.answer(f"Navbat {next_name}ga o'tkazildi.", show_alert=True)

    text = (
        f"⏭ **Navbat o'tkazib yuborildi.**\n\n"
        f"📌 **Vazifa:** {chore.title}\n"
        f"👤 Yangi navbatchi: **{next_name}**\n\n"
        "Iltimos, vazifani bajargach tasdiqlang:"
    )
    await callback.message.edit_text(text, reply_markup=get_chore_action_kb(chore.id), parse_mode="Markdown")
