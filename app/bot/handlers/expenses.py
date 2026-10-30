from decimal import Decimal
import re
from typing import Optional
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from html import escape
from aiogram.types import CallbackQuery, Message
import pytz
from sqlalchemy.ext.asyncio import AsyncSession
from app.bot.keyboards.common_kb import get_cancel_kb, get_main_menu_kb
from app.bot.keyboards.expense_kb import (
    get_fund_collect_confirm_kb,
    get_fund_menu_kb,
)
from app.bot.states.fund_states import FundCollectSG, FundExpenseSG
from app.config import get_settings
from app.models.flat import Flat
from app.models.fund import TransactionType
from app.models.user import User
from app.repositories.flat_repo import FlatRepository
from app.repositories.fund_repo import FundRepository
from app.services.fund_service import FundService

router = Router(name="expenses_router")
settings = get_settings()


# ------------------- MAIN COMMUNAL FUND DASHBOARD ------------------- #

@router.message(F.text == "🛒 Bozorlik va Kassa")
async def show_fund_dashboard(
    message: Message,
    session: AsyncSession,
    current_flat: Optional[Flat]
) -> None:
    """Displays communal fund balance overview and interactive actions."""
    if not current_flat:
        await message.answer("Siz hali kvartiraga qo'shilmagansiz. /start bosing.", parse_mode="HTML")
        return

    summary = await FundService.get_fund_summary(session, current_flat.id)
    safe_flat = escape(current_flat.name)

    text = (
        f"🛒 <b>'{safe_flat}' — Bozorlik va Umumiy Kassa</b>\n\n"
        f"💰 <b>Mavjud kassa zaxirasi:</b> <code>{int(summary.fund_balance):,} so'm</code>\n"
        f"📥 <b>Jami yig'ilgan:</b> {int(summary.total_income):,} so'm\n"
        f"🧾 <b>Jami xaridlar:</b> {int(summary.total_expense):,} so'm\n"
        f"👥 <b>Xonadoshlar:</b> {summary.member_count} kishi\n\n"
        "Quyidagi amallardan birini tanlang:"
    )

    await message.answer(text, reply_markup=get_fund_menu_kb(), parse_mode="HTML")


@router.callback_query(F.data == "fund:balance")
async def cb_fund_balance(
    callback: CallbackQuery,
    session: AsyncSession,
    current_flat: Optional[Flat]
) -> None:
    """Displays detailed reserve status."""
    await callback.answer()
    if not current_flat:
        await callback.message.answer("Kvartira topilmadi.", parse_mode="HTML")
        return

    summary = await FundService.get_fund_summary(session, current_flat.id)
    safe_flat = escape(current_flat.name)

    balance_text = (
        f"💰 <b>'{safe_flat}' Kassa Balansi:</b>\n\n"
        f"💵 <b>Hozirgi zaxira:</b> <code>{int(summary.fund_balance):,} so'm</code>\n"
        f"🟢 <b>Jami kirim (yig'imlar):</b> +{int(summary.total_income):,} so'm\n"
        f"🔴 <b>Jami chiqim (bozorliklar):</b> -{int(summary.total_expense):,} so'm\n"
        f"👥 <b>A'zolar soni:</b> {summary.member_count} ta\n"
    )
    await callback.message.answer(balance_text, reply_markup=get_fund_menu_kb(), parse_mode="HTML")


# ------------------- FUND COLLECTION FLOW (PUL YIG'ISH) ------------------- #

@router.callback_query(F.data == "fund:collect")
async def cb_start_collection(
    callback: CallbackQuery,
    state: FSMContext,
    current_flat: Optional[Flat]
) -> None:
    """Initiates communal money collection."""
    await callback.answer()
    if not current_flat:
        await callback.message.answer("Kvartira topilmadi.", parse_mode="HTML")
        return

    await state.set_state(FundCollectSG.waiting_for_amount)
    await callback.message.answer(
        "📥 <b>Kassaga pul yig'ish:</b>\n\n"
        "Har bir xonadoshdan qancha so'm yig'ilmoqda?\n"
        "(Masalan: <code>50000</code> yoki <code>100000</code>)",
        reply_markup=get_cancel_kb(),
        parse_mode="HTML"
    )


@router.message(FundCollectSG.waiting_for_amount)
async def process_collect_amount(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    current_flat: Optional[Flat]
) -> None:
    cleaned = re.sub(r"[^\d.]", "", message.text.strip())
    try:
        amount = Decimal(cleaned)
        if amount <= 0:
            raise ValueError
    except Exception:
        await message.answer(
            "⚠️ Iltimos, to'g'ri musbat summa kiriting (masalan: <code>50000</code>):",
            parse_mode="HTML"
        )
        return

    if not current_flat:
        await message.answer("Kvartira topilmadi.", reply_markup=get_main_menu_kb(), parse_mode="HTML")
        await state.clear()
        return

    members = await FlatRepository.get_members(session, current_flat.id)
    if not members:
        await message.answer("⚠️ Kvartirada a'zolar topilmadi.", parse_mode="HTML")
        await state.clear()
        return

    total_pool = amount * Decimal(len(members))
    await state.update_data(per_person_amount=str(amount))
    await state.set_state(FundCollectSG.waiting_for_confirmation)

    await message.answer(
        f"📥 <b>Yig'im ma'lumotlarini tasdiqlang:</b>\n\n"
        f"👤 <b>Har bir xonadoshdan:</b> {int(amount):,} so'm\n"
        f"👥 <b>Xonadoshlar soni:</b> {len(members)} kishi\n"
        f"💰 <b>Kassaga qo'shiladigan jami mablag':</b> <code>{int(total_pool):,} so'm</code>\n\n"
        "Barcha xonadoshlardan pul qabul qilinganini tasdiqlaysizmi?",
        reply_markup=get_fund_collect_confirm_kb(amount),
        parse_mode="HTML"
    )


@router.callback_query(FundCollectSG.waiting_for_confirmation, F.data.startswith("fund_coll_ok:"))
async def process_confirm_collection(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    current_flat: Optional[Flat]
) -> None:
    await callback.answer()
    data = await state.get_data()
    await state.clear()

    if not current_flat:
        await callback.message.answer("Kvartira topilmadi.", parse_mode="HTML")
        return

    amount_str = data.get("per_person_amount") or callback.data.split(":")[1]
    per_person_amount = Decimal(amount_str)

    members = await FlatRepository.get_members(session, current_flat.id)
    participant_ids = [m.user_id for m in members]

    new_balance = await FundService.create_collection(
        session=session,
        flat_id=current_flat.id,
        per_person_amount=per_person_amount,
        participants=participant_ids,
        description=f"Umumiy yig'im ({int(per_person_amount):,} so'm/kishi)",
    )

    total_added = per_person_amount * len(participant_ids)

    await callback.message.answer(
        f"🎉 <b>Kassa muvaffaqiyatli to'ldirildi!</b>\n\n"
        f"📥 <b>Qo'shilgan summa:</b> +{int(total_added):,} so'm ({len(participant_ids)} kishidan)\n"
        f"💰 <b>Yangi umumiy balans:</b> <code>{int(new_balance):,} so'm</code>\n\n"
        "Barcha a'zolar hisobiga kirim operatsiyasi yozildi.",
        reply_markup=get_main_menu_kb(),
        parse_mode="HTML"
    )


# ------------------- RECORD MARKET EXPENSE (XARID KIRITISH) ------------------- #

@router.callback_query(F.data == "fund:expense")
async def cb_start_expense(
    callback: CallbackQuery,
    state: FSMContext,
    current_flat: Optional[Flat]
) -> None:
    """Initiates market expense logging."""
    await callback.answer()
    if not current_flat:
        await callback.message.answer("Kvartira topilmadi.", parse_mode="HTML")
        return

    await state.set_state(FundExpenseSG.waiting_for_amount)
    await callback.message.answer(
        "🧾 <b>Kassadan xarid kiritish:</b>\n\n"
        "Sarflangan summani so'mda kiriting:\n"
        "(Masalan: <code>370293</code> yoki <code>45000</code>)",
        reply_markup=get_cancel_kb(),
        parse_mode="HTML"
    )


@router.message(FundExpenseSG.waiting_for_amount)
async def process_expense_amount(message: Message, state: FSMContext) -> None:
    cleaned = re.sub(r"[^\d.]", "", message.text.strip())
    try:
        amount = Decimal(cleaned)
        if amount <= 0:
            raise ValueError
    except Exception:
        await message.answer(
            "⚠️ Iltimos, xarid summasini to'g'ri musbat son ko'rinishida kiriting (masalan: <code>150000</code>):",
            parse_mode="HTML"
        )
        return

    await state.update_data(amount=str(amount))
    await state.set_state(FundExpenseSG.waiting_for_description)
    await message.answer(
        "📝 <b>Xarid tavsifini yozing:</b>\n"
        "(Masalan: <i>Korzinka bozorlik (go'sht, guruch, moy)</i> yoki <i>10L suv va non</i>)",
        reply_markup=get_cancel_kb(),
        parse_mode="HTML"
    )


@router.message(FundExpenseSG.waiting_for_description)
async def process_expense_description(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    current_user: Optional[User] = None,
    current_flat: Optional[Flat] = None,
) -> None:
    description = message.text.strip()
    data = await state.get_data()
    await state.clear()

    if not current_flat:
        await message.answer("Xatolik: kvartira topilmadi.", reply_markup=get_main_menu_kb(), parse_mode="HTML")
        return

    amount = Decimal(data["amount"])
    user_id = current_user.id if current_user else (message.from_user.id if message.from_user else 0)

    try:
        tx = await FundService.record_market_expense(
            session=session,
            flat_id=current_flat.id,
            spender_id=user_id,
            amount=amount,
            description=description,
        )
    except ValueError as e:
        await message.answer(f"⚠️ {escape(str(e))}", reply_markup=get_main_menu_kb(), parse_mode="HTML")
        return

    spender_name = current_user.display_name if current_user else (
        message.from_user.full_name if message.from_user else "Xonadosh"
    )
    safe_desc = escape(tx.description)
    safe_spender = escape(spender_name)

    await message.answer(
        f"🧾 <b>Xarid muvaffaqiyatli kiritildi!</b>\n\n"
        f"📌 <b>Xarid:</b> {safe_desc}\n"
        f"💸 <b>Sarflangan summa:</b> <code>{int(amount):,} so'm</code>\n"
        f"👤 <b>Xarid qildi:</b> {safe_spender}\n"
        f"💰 <b>Qolgan kassa zaxirasi:</b> <code>{int(tx.balance_after):,} so'm</code>\n\n"
        "Xarid kassa hisob-kitoblariga kiritildi.",
        reply_markup=get_main_menu_kb(),
        parse_mode="HTML"
    )


# ------------------- TRANSACTION HISTORY (XARIDLAR TARIXI) ------------------- #

@router.callback_query(F.data == "fund:history")
async def cb_fund_history(
    callback: CallbackQuery,
    session: AsyncSession,
    current_flat: Optional[Flat]
) -> None:
    """Displays last 5 transactions of the communal fund."""
    await callback.answer()
    if not current_flat:
        await callback.message.answer("Kvartira topilmadi.", parse_mode="HTML")
        return

    txs = await FundRepository.get_recent_transactions(session, current_flat.id, limit=5)
    if not txs:
        await callback.message.answer(
            "📜 <b>Xaridlar tarixi:</b>\n\nHozircha hech qanday kassa yoki xarid operatsiyalari amalga oshirilmagan.",
            reply_markup=get_fund_menu_kb(),
            parse_mode="HTML"
        )
        return

    tz = pytz.timezone(settings.TIMEZONE)
    lines = [f"📜 <b>So'nggi 5 ta kassa operatsiyasi:</b>\n"]

    for idx, tx in enumerate(txs, start=1):
        # Convert timezone
        local_dt = tx.created_at.astimezone(tz) if tx.created_at.tzinfo else tx.created_at
        time_str = local_dt.strftime("%d.%m.%Y %H:%M")
        badge = "🟢 Kirim" if tx.tx_type == TransactionType.INCOME else "🔴 Chiqim"
        user_name = tx.user.display_name if tx.user else "Foydalanuvchi"
        safe_user = escape(user_name)
        safe_desc = escape(tx.description)

        lines.append(
            f"{idx}. {badge} — <b>{int(tx.amount):,} so'm</b>\n"
            f"   👤 {safe_user} | 🕒 {time_str}\n"
            f"   📝 <i>{safe_desc}</i>\n"
            f"   💰 Qoldiq: {int(tx.balance_after):,} so'm\n"
        )

    await callback.message.answer("\n".join(lines), reply_markup=get_fund_menu_kb(), parse_mode="HTML")


@router.callback_query(F.data == "fund:cancel")
async def cb_cancel_fund(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.answer("Amal bekor qilindi.")
    await callback.message.answer("Amal bekor qilindi.", reply_markup=get_main_menu_kb(), parse_mode="HTML")
