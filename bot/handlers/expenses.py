from decimal import Decimal
import re
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession
from bot.database.crud import (
    create_expense,
    create_settlement,
    get_flat_members,
    get_user,
)
from bot.keyboards.inline import get_cancel_kb, get_settlement_kb
from bot.services.debt_optimizer import DebtOptimizer

router = Router(name="expenses")


class AddExpenseSG(StatesGroup):
    waiting_for_amount = State()
    waiting_for_title = State()


# ------------------- ADD EXPENSE FLOW ------------------- #

@router.message(Command("add_expense"))
@router.callback_query(F.data == "add_expense_btn")
async def cmd_add_expense(event: Message | CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    """Initiates communal expense logging dialog."""
    user_id = event.from_user.id
    user = await get_user(session, user_id)

    if not user or not user.flat_id:
        msg = "Siz kvartiraga a'zo emassiz. /start orqali kvartiraga qo'shiling."
        if isinstance(event, CallbackQuery):
            await event.answer(msg, show_alert=True)
        else:
            await event.answer(msg)
        return

    await state.set_state(AddExpenseSG.waiting_for_amount)
    text = (
        "💰 **Xarajat qo'shish:**\n\n"
        "Xarid summasini so'mda kiriting:\n"
        "*(Masalan: `160000` yoki `85000`)*"
    )
    if isinstance(event, CallbackQuery):
        await event.answer()
        await event.message.answer(text, reply_markup=get_cancel_kb(), parse_mode="Markdown")
    else:
        await event.answer(text, reply_markup=get_cancel_kb(), parse_mode="Markdown")


@router.message(AddExpenseSG.waiting_for_amount)
async def process_expense_amount(message: Message, state: FSMContext) -> None:
    cleaned = re.sub(r"[^\d.]", "", message.text.strip())
    try:
        amount = Decimal(cleaned)
        if amount <= Decimal("0"):
            raise ValueError
    except Exception:
        await message.answer("⚠️ Iltimos, musbat son ko'rinishida summa kiriting (masalan: `150000`):")
        return

    await state.update_data(amount=str(amount))
    await state.set_state(AddExpenseSG.waiting_for_title)
    await message.answer(
        "📝 Nima xarid qilinganini yozing:\n*(Masalan: 'Bozorlik: go'sht, yog', kartoshka' yoki 'Wi-Fi to'lovi')*",
        reply_markup=get_cancel_kb(),
        parse_mode="Markdown",
    )


@router.message(AddExpenseSG.waiting_for_title)
async def process_expense_title(message: Message, state: FSMContext, session: AsyncSession) -> None:
    title = message.text.strip()
    data = await state.get_data()
    await state.clear()

    user = await get_user(session, message.from_user.id)
    if not user or not user.flat_id:
        await message.answer("Xatolik: kvartira topilmadi.")
        return

    amount = Decimal(data["amount"])
    members = await get_flat_members(session, user.flat_id)
    member_count = len(members)

    expense = await create_expense(
        session=session,
        flat_id=user.flat_id,
        payer_id=user.id,
        title=title,
        amount=amount,
    )

    per_person = int(amount // member_count) if member_count else int(amount)

    text = (
        f"🧾 **Xarajat muvaffaqiyatli qayd etildi!**\n\n"
        f"📌 **Nomi:** {expense.title}\n"
        f"💰 **Jami summa:** {int(amount):,} so'm\n"
        f"👤 **To'lovchi:** {user.full_name}\n"
        f"👥 **Taqsimot:** {member_count} kishiga teng taqsimlandi (~{per_person:,} so'mdan)\n\n"
        "Balansni ko'rish uchun `/balance` buyrug'ini yuboring."
    )
    await message.answer(text, parse_mode="Markdown")


# ------------------- VIEW BALANCES & SETTLE ------------------- #

@router.message(Command("balance"))
@router.callback_query(F.data == "show_balance_btn")
async def cmd_balance(event: Message | CallbackQuery, session: AsyncSession) -> None:
    """Displays total spend, net balances, and optimized debt clearance paths."""
    user_id = event.from_user.id
    user = await get_user(session, user_id)

    if not user or not user.flat_id:
        msg = "Siz kvartiraga a'zo emassiz. /start orqali kvartiraga qo'shiling."
        if isinstance(event, CallbackQuery):
            await event.answer(msg, show_alert=True)
        else:
            await event.answer(msg)
        return

    balances, transfers, total_spent = await DebtOptimizer.get_flat_ledger(session, user.flat_id)

    report_lines = [
        "📊 **Kvartira umumiy moliyaviy balansi:**\n",
        f"💰 **Jami umumiy xarajatlar:** {int(total_spent):,} so'm\n",
        "👥 **Xonadoshlar hisobi:**",
    ]

    for uid, b in balances.items():
        if b.net_balance > Decimal("0.01"):
            status_text = f"🟢 +{int(b.net_balance):,} so'm (Haqdor)"
        elif b.net_balance < Decimal("-0.01"):
            status_text = f"🔴 {int(b.net_balance):,} so'm (Qarzdor)"
        else:
            status_text = "⚪️ 0 so'm (Hisobi teng)"

        report_lines.append(f"• **{b.user_name}:** {status_text} | Sarfladi: {int(b.total_paid):,} so'm")

    report_lines.append("\n" + "—" * 25 + "\n")

    if not transfers:
        report_lines.append("🎉 **Hozirda hech kim qarzdor emas!** Barcha hisoblar tenglashgan.")
        summary_text = "\n".join(report_lines)
        if isinstance(event, CallbackQuery):
            await event.answer()
            await event.message.answer(summary_text, parse_mode="Markdown")
        else:
            await event.answer(summary_text, parse_mode="Markdown")
        return

    report_lines.append("💳 **Qarzlarni yopish bo'yicha tavsiyalar (Min-Cash-Flow):**\n")
    for t in transfers:
        report_lines.append(f"👉 **{t.debtor_name}** ➔ **{t.creditor_name}**ga: `{int(t.amount):,} so'm`")

    summary_text = "\n".join(report_lines)
    msg_target = event.message if isinstance(event, CallbackQuery) else event
    if isinstance(event, CallbackQuery):
        await event.answer()

    await msg_target.answer(summary_text, parse_mode="Markdown")

    # Send one-tap settlement confirmation buttons
    for t in transfers:
        await msg_target.answer(
            f"To'lovni tasdiqlash: **{t.debtor_name}** ➔ **{t.creditor_name}** ({int(t.amount):,} so'm):",
            reply_markup=get_settlement_kb(t.debtor_id, t.creditor_id, t.amount),
            parse_mode="Markdown",
        )


@router.callback_query(F.data.startswith("settle:"))
async def cb_settle(callback: CallbackQuery, session: AsyncSession) -> None:
    """Records payment clearance between two flatmates."""
    parts = callback.data.split(":")
    debtor_id = int(parts[1])
    creditor_id = int(parts[2])
    amount = Decimal(parts[3])

    user = await get_user(session, callback.from_user.id)
    if not user or not user.flat_id:
        await callback.answer("Kvartira topilmadi.", show_alert=True)
        return

    await create_settlement(
        session=session,
        flat_id=user.flat_id,
        debtor_id=debtor_id,
        creditor_id=creditor_id,
        amount=amount,
    )

    await callback.answer("🤝 To'lov muvaffaqiyatli tasdiqlandi va hisobdan chiqarildi!", show_alert=True)
    await callback.message.edit_text(
        f"✅ **Qarz yopildi!**\nSumma: {int(amount):,} so'm to'landi deb qayd etildi.",
        parse_mode="Markdown",
    )
