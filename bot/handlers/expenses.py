from decimal import Decimal
import re
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from html import escape
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
        "💰 <b>Xarajat qo'shish:</b>\n\n"
        "Xarid summasini so'mda kiriting:\n"
        "<i>(Masalan: <code>160000</code> yoki <code>85000</code>)</i>"
    )
    if isinstance(event, CallbackQuery):
        await event.answer()
        await event.message.answer(text, reply_markup=get_cancel_kb(), parse_mode="HTML")
    else:
        await event.answer(text, reply_markup=get_cancel_kb(), parse_mode="HTML")


@router.message(AddExpenseSG.waiting_for_amount)
async def process_expense_amount(message: Message, state: FSMContext) -> None:
    cleaned = re.sub(r"[^\d.]", "", message.text.strip())
    try:
        amount = Decimal(cleaned)
        if amount <= Decimal("0"):
            raise ValueError
    except Exception:
        await message.answer(
            "⚠️ Iltimos, musbat son ko'rinishida summa kiriting (masalan: <code>150000</code>):",
            parse_mode="HTML",
        )
        return

    await state.update_data(amount=str(amount))
    await state.set_state(AddExpenseSG.waiting_for_title)
    await message.answer(
        "📝 Nima xarid qilinganini yozing:\n<i>(Masalan: 'Bozorlik: go'sht, yog', kartoshka' yoki 'Wi-Fi to'lovi')</i>",
        reply_markup=get_cancel_kb(),
        parse_mode="HTML",
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

    safe_title = escape(expense.title)
    safe_payer = escape(user.full_name)

    text = (
        f"🧾 <b>Xarajat muvaffaqiyatli qayd etildi!</b>\n\n"
        f"📌 <b>Nomi:</b> {safe_title}\n"
        f"💰 <b>Jami summa:</b> {int(amount):,} so'm\n"
        f"👤 <b>To'lovchi:</b> {safe_payer}\n"
        f"👥 <b>Taqsimot:</b> {member_count} kishiga teng taqsimlandi (~{per_person:,} so'mdan)\n\n"
        "Balansni ko'rish uchun <code>/balance</code> buyrug'ini yuboring."
    )
    await message.answer(text, parse_mode="HTML")


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
        "📊 <b>Kvartira umumiy moliyaviy balansi:</b>\n",
        f"💰 <b>Jami umumiy xarajatlar:</b> {int(total_spent):,} so'm\n",
        "👥 <b>Xonadoshlar hisobi:</b>",
    ]

    for uid, b in balances.items():
        if b.net_balance > Decimal("0.01"):
            status_text = f"🟢 +{int(b.net_balance):,} so'm (Haqdor)"
        elif b.net_balance < Decimal("-0.01"):
            status_text = f"🔴 {int(b.net_balance):,} so'm (Qarzdor)"
        else:
            status_text = "⚪️ 0 so'm (Hisobi teng)"

        safe_name = escape(b.user_name)
        report_lines.append(f"• <b>{safe_name}:</b> {status_text} | Sarfladi: {int(b.total_paid):,} so'm")

    report_lines.append("\n" + "—" * 25 + "\n")

    if not transfers:
        report_lines.append("🎉 <b>Hozirda hech kim qarzdor emas!</b> Barcha hisoblar tenglashgan.")
        summary_text = "\n".join(report_lines)
        if isinstance(event, CallbackQuery):
            await event.answer()
            await event.message.answer(summary_text, parse_mode="HTML")
        else:
            await event.answer(summary_text, parse_mode="HTML")
        return

    report_lines.append("💳 <b>Qarzlarni yopish bo'yicha tavsiyalar (Min-Cash-Flow):</b>\n")
    for t in transfers:
        safe_debtor = escape(t.debtor_name)
        safe_creditor = escape(t.creditor_name)
        report_lines.append(f"👉 <b>{safe_debtor}</b> ➔ <b>{safe_creditor}</b>ga: <code>{int(t.amount):,} so'm</code>")

    summary_text = "\n".join(report_lines)
    msg_target = event.message if isinstance(event, CallbackQuery) else event
    if isinstance(event, CallbackQuery):
        await event.answer()

    await msg_target.answer(summary_text, parse_mode="HTML")

    # Send one-tap settlement confirmation buttons
    for t in transfers:
        safe_debtor = escape(t.debtor_name)
        safe_creditor = escape(t.creditor_name)
        await msg_target.answer(
            f"To'lovni tasdiqlash: <b>{safe_debtor}</b> ➔ <b>{safe_creditor}</b> ({int(t.amount):,} so'm):",
            reply_markup=get_settlement_kb(t.debtor_id, t.creditor_id, t.amount),
            parse_mode="HTML",
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
        f"✅ <b>Qarz yopildi!</b>\nSumma: {int(amount):,} so'm to'landi deb qayd etildi.",
        parse_mode="HTML",
    )
