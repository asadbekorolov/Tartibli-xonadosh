from decimal import Decimal
import re
from typing import Optional
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession
from app.bot.keyboards.common_kb import get_cancel_kb, get_main_menu_kb
from app.bot.keyboards.expense_kb import (
    get_expense_categories_kb,
    get_settlement_confirm_kb,
)
from app.bot.states.expense_states import AddExpenseSG
from app.models.expense import ExpenseCategory
from app.models.flat import Flat
from app.models.user import User
from app.services.expense_service import ExpenseService

router = Router(name="expenses_router")


# ------------------- ADD EXPENSE FLOW ------------------- #

@router.message(F.text == "➕ Xarajat qo'shish")
async def start_add_expense(
    message: Message,
    state: FSMContext,
    current_flat: Optional[Flat]
) -> None:
    """Initiates communal expense logging dialog."""
    if not current_flat:
        await message.answer("Siz hali kvartiraga qo'shilmagansiz. /start bosing.")
        return

    await state.set_state(AddExpenseSG.waiting_for_amount)
    await message.answer(
        "💰 Xarajat summasini so'mda kiriting:\n(Masalan: `140000` yoki `85000`)",
        reply_markup=get_cancel_kb(),
        parse_mode="Markdown"
    )


@router.message(AddExpenseSG.waiting_for_amount)
async def process_expense_amount(message: Message, state: FSMContext) -> None:
    # Clean input of spaces and commas
    cleaned_input = re.sub(r"[^\d.]", "", message.text.strip())
    try:
        amount = Decimal(cleaned_input)
        if amount <= 0:
            raise ValueError
    except Exception:
        await message.answer("⚠️ Iltimos, musbat son ko'rinishida summa kiriting (masalan: `120000`):")
        return

    await state.update_data(amount=str(amount))
    await state.set_state(AddExpenseSG.waiting_for_category)
    await message.answer(
        "📂 Xarajat kategoriyasini tanlang:",
        reply_markup=get_expense_categories_kb()
    )


@router.callback_query(AddExpenseSG.waiting_for_category, F.data.startswith("exp_cat:"))
async def process_expense_category(callback: CallbackQuery, state: FSMContext) -> None:
    category_val = callback.data.split(":")[1]
    await callback.answer()
    await state.update_data(category=category_val)
    await state.set_state(AddExpenseSG.waiting_for_title)
    await callback.message.answer(
        "📝 Nima sotib olinganini yozing:\n(Masalan: *Bozorlik (go'sht, guruch, sabzi)* yoki *19L Suv*)",
        reply_markup=get_cancel_kb(),
        parse_mode="Markdown"
    )


@router.message(AddExpenseSG.waiting_for_title)
async def process_expense_title(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    current_user: User,
    current_flat: Optional[Flat],
) -> None:
    title = message.text.strip()
    data = await state.get_data()
    await state.clear()

    if not current_flat:
        await message.answer("Xatolik: kvartira topilmadi.", reply_markup=get_main_menu_kb())
        return

    amount = Decimal(data["amount"])
    category = ExpenseCategory(data["category"])

    expense = await ExpenseService.add_communal_expense(
        session=session,
        flat_id=current_flat.id,
        payer_id=current_user.id,
        title=title,
        category=category,
        amount=amount,
    )

    participant_count = len(expense.splits)
    per_person = amount / participant_count if participant_count else amount

    category_labels = {
        ExpenseCategory.GROCERY: "🛒 Oziq-ovqat / Bozorlik",
        ExpenseCategory.UTILITIES: "💡 Kommunal / Wi-Fi",
        ExpenseCategory.CLEANING: "🧼 Tozalash vositalari",
        ExpenseCategory.WATER: "💧 19L Suv",
        ExpenseCategory.OTHER: "📦 Boshqa",
    }

    await message.answer(
        f"🧾 **Yangi xarajat muvaffaqiyatli qo'shildi!**\n\n"
        f"📌 **Nomi:** {expense.title}\n"
        f"📂 **Kategoriya:** {category_labels.get(expense.category, expense.category.value)}\n"
        f"💰 **Umumiy summa:** {int(expense.amount):,} so'm\n"
        f"👤 **To'ladi:** {current_user.display_name}\n"
        f"👥 **Taqsimot:** {participant_count} kishiga teng bo'lindi (har biriga ~{int(per_person):,} so'mdan)\n\n"
        f"📊 Kvartiraning yangilangan hisobini ko'rish uchun **'📊 Kvartira balansi'** tugmasini bosing.",
        reply_markup=get_main_menu_kb(),
        parse_mode="Markdown"
    )


# ------------------- VIEW LEDGER BALANCES ------------------- #

@router.message(F.text == "📊 Kvartira balansi")
async def show_ledger_balances(
    message: Message,
    session: AsyncSession,
    current_flat: Optional[Flat]
) -> None:
    """Calculates ledger balances and displays simplified debt settlement paths."""
    if not current_flat:
        await message.answer("Siz hali kvartiraga qo'shilmagansiz. /start bosing.")
        return

    balances, simplified_debts, total_spent = await ExpenseService.get_flat_ledger(
        session=session,
        flat_id=current_flat.id
    )

    report_lines = [
        f"📊 **'{current_flat.name}' kvartirasi moliyaviy balansi:**\n",
        f"💰 **Jami umumiy xarajatlar:** {int(total_spent):,} so'm\n",
        "👥 **Xonadoshlar holati:**"
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

    if not simplified_debts:
        report_lines.append("🎉 **Hozirda hech kimda o'zaro qarz yo'q!** Barcha hisoblar tenglashgan.")
        await message.answer("\n".join(report_lines), parse_mode="Markdown")
        return

    report_lines.append("💳 **O'zaro hisob-kitob (Tavsiya etilgan to'lovlar):**\n")
    for t in simplified_debts:
        report_lines.append(
            f"👉 **{t.debtor_name}** ➔ **{t.creditor_name}**ga: `{int(t.amount):,} so'm`"
        )

    await message.answer("\n".join(report_lines), parse_mode="Markdown")

    # Send interactive settlement buttons for quick clearing
    for t in simplified_debts:
        await message.answer(
            f"To'lovni tasdiqlash: **{t.debtor_name}** ➔ **{t.creditor_name}** ({int(t.amount):,} so'm):",
            reply_markup=get_settlement_confirm_kb(t.debtor_id, t.creditor_id, t.amount),
            parse_mode="Markdown"
        )


# ------------------- SETTLE DEBT CALLBACK ------------------- #

@router.callback_query(F.data.startswith("settle_confirm:"))
async def cb_settle_confirm(
    callback: CallbackQuery,
    session: AsyncSession,
    current_flat: Optional[Flat]
) -> None:
    """Registers direct repayment between two flatmates."""
    parts = callback.data.split(":")
    debtor_id = int(parts[1])
    creditor_id = int(parts[2])
    amount = Decimal(parts[3])

    if not current_flat:
        await callback.answer("Kvartira topilmadi.", show_alert=True)
        return

    await ExpenseService.settle_debt(
        session=session,
        flat_id=current_flat.id,
        from_user_id=debtor_id,
        to_user_id=creditor_id,
        amount=amount,
        note="Bot orqali tasdiqlangan to'lov",
    )

    await callback.answer("🤝 To'lov muvaffaqiyatli qayd etildi va hisobdan chiqarildi!", show_alert=True)
    await callback.message.edit_text(
        f"✅ **Qarz to'liq uzildi!**\n"
        f"Summa: {int(amount):,} so'm to'landi deb belgilandi.",
        parse_mode="Markdown"
    )
