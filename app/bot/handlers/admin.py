from typing import Optional
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from html import escape
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.bot.keyboards.admin_kb import (
    get_admin_panel_kb,
    get_chore_frequency_kb,
    get_chores_admin_menu_kb,
    get_chores_management_list_kb,
    get_chores_picker_kb,
    get_members_for_assignment_kb,
    get_rules_delete_kb,
    get_rules_view_kb,
    get_weekdays_picker_kb,
)
from app.bot.keyboards.common_kb import get_cancel_kb, get_main_menu_kb
from app.bot.states.admin_states import AddRuleSG, AdminAddChoreSG
from app.models.chore import Chore, RotationType
from app.models.flat import Flat, FlatMember, FlatRole
from app.models.user import User
from app.repositories.chore_repo import ChoreRepository
from app.repositories.flat_repo import FlatRepository
from app.repositories.rule_repo import RuleRepository
from app.services.chore_service import (
    WEEKDAYS_DISPLAY,
    WEEKDAYS_MAP,
    ChoreService,
)
from app.services.rule_service import RuleService

router = Router(name="admin_router")


def get_community_rules_text(flat: Flat) -> str:
    safe_flat = escape(flat.name)
    quiet_time = escape(flat.quiet_hours_start)
    return (
        f"📜 <b>'{safe_flat}' Kvartira Qoidalari va Tartibi:</b>\n\n"
        f"🌙 <b>1. Tinchlik va osoyishtalik soati ({quiet_time}):</b>\n"
        f"• Har kuni kechki soat <b>{quiet_time}</b> dan boshlab kvartirada to'liq sukunat saqlanadi.\n\n"
        f"🍽 <b>2. Idish-tovoq siyosati (Dish Policy):</b>\n"
        f"• Har bir xonadosh o'zining shaxsiy idishini ovqatlangandan so'ng <b>darhol</b> yuvishi shart!\n\n"
        f"👥 <b>3. Mehmonlar tartibi:</b>\n"
        f"• Kvartiraga do'st yoki qarindoshlarni taklif qilishdan kamida <b>3–4 soat oldin</b> xabar berilishi kerak.\n\n"
        f"⚠️ <b>4. Navbatchilik intizomi:</b>\n"
        f"• Sababsiz navbatchilikni bajarmaslik holatida jarima belgilanadi."
    )


async def is_flat_admin(session: AsyncSession, flat_id: int, user_id: int) -> bool:
    """Verifies whether the given user is an admin of the specified flat."""
    membership = await FlatRepository.get_membership(session, flat_id, user_id)
    return bool(membership and membership.role == FlatRole.ADMIN)


# =====================================================================
# 1. DYNAMIC APARTMENT RULES MANAGEMENT
# =====================================================================

@router.message(F.text == "📜 Kvartira Qoidalari")
async def show_community_rules(
    message: Message,
    session: AsyncSession,
    current_user: Optional[User],
    current_flat: Optional[Flat],
) -> None:
    """Displays dynamic house rules for the current flat."""
    if not current_flat:
        await message.answer("Siz hali kvartiraga qo'shilmagansiz. /start bosing.", parse_mode="HTML")
        return

    # Fetch rules; seed defaults if none exist
    rules = await RuleService.get_flat_rules(session, current_flat.id)
    if not rules:
        rules = await RuleService.seed_default_rules(
            session, current_flat.id, current_flat.template_type
        )

    user_id = current_user.id if current_user else (message.from_user.id if message.from_user else 0)
    admin_status = await is_flat_admin(session, current_flat.id, user_id)

    safe_flat = escape(current_flat.name)
    lines = [f"📜 <b>'{safe_flat}' Kvartira Qoidalari va Tartibi:</b>\n"]

    digit_emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]

    for idx, r in enumerate(rules):
        prefix = digit_emojis[idx] if idx < len(digit_emojis) else f"📌 {idx+1}."
        safe_title = escape(r.title)
        safe_content = escape(r.content)
        lines.append(f"{prefix} <b>{safe_title}</b>\n{safe_content}\n")

    lines.append("<i>Qoidalarga amal qilish barcha xonadoshlar uchun majburiydir.</i>")
    text = "\n".join(lines)

    await message.answer(
        text,
        reply_markup=get_rules_view_kb(is_admin=admin_status),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "rules:show")
async def cb_show_community_rules(
    callback: CallbackQuery,
    session: AsyncSession,
    current_user: Optional[User],
    current_flat: Optional[Flat],
) -> None:
    await callback.answer()
    if not current_flat:
        await callback.message.answer("Kvartira topilmadi.", parse_mode="HTML")
        return

    rules = await RuleService.get_flat_rules(session, current_flat.id)
    if not rules:
        rules = await RuleService.seed_default_rules(
            session, current_flat.id, current_flat.template_type
        )

    user_id = current_user.id if current_user else (callback.from_user.id if callback.from_user else 0)
    admin_status = await is_flat_admin(session, current_flat.id, user_id)

    safe_flat = escape(current_flat.name)
    lines = [f"📜 <b>'{safe_flat}' Kvartira Qoidalari va Tartibi:</b>\n"]
    digit_emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]

    for idx, r in enumerate(rules):
        prefix = digit_emojis[idx] if idx < len(digit_emojis) else f"📌 {idx+1}."
        lines.append(f"{prefix} <b>{escape(r.title)}</b>\n{escape(r.content)}\n")

    lines.append("<i>Qoidalarga amal qilish barcha xonadoshlar uchun majburiydir.</i>")

    await callback.message.answer(
        "\n".join(lines),
        reply_markup=get_rules_view_kb(is_admin=admin_status),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "rule:add")
async def cb_rule_add_start(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    current_user: Optional[User],
    current_flat: Optional[Flat],
) -> None:
    """Initiates dynamic house rule creation dialog (Admin only)."""
    user_id = current_user.id if current_user else (callback.from_user.id if callback.from_user else 0)
    if not current_flat or not await is_flat_admin(session, current_flat.id, user_id):
        await callback.answer("⚠️ Faqat kvartira admini yangi qoida qo'sha oladi!", show_alert=True)
        return

    await callback.answer()
    await state.set_state(AddRuleSG.waiting_for_title)
    await callback.message.answer(
        "📝 <b>Yangi qoida sarlavhasini kiriting:</b>\n"
        "(Masalan: <i>Mehmonlar tashrifi</i> yoki <i>Wi-Fi va elektr tejamkorligi</i>)",
        reply_markup=get_cancel_kb(),
        parse_mode="HTML"
    )


@router.message(AddRuleSG.waiting_for_title)
async def process_rule_title(message: Message, state: FSMContext) -> None:
    title = message.text.strip()
    if len(title) < 3:
        await message.answer("⚠️ Sarlavha juda qisqa. Kamida 3 ta belgi kiriting:", parse_mode="HTML")
        return

    await state.update_data(title=title)
    await state.set_state(AddRuleSG.waiting_for_content)
    await message.answer(
        f"📋 <b>'{escape(title)}' qoidasi mazmuni va talablarini yozing:</b>\n"
        "(Masalan: <i>Kvartiraga mehmon chaqirishdan oldin guruhda xabar berilishi shart...</i>)",
        reply_markup=get_cancel_kb(),
        parse_mode="HTML"
    )


@router.message(AddRuleSG.waiting_for_content)
async def process_rule_content(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    current_flat: Optional[Flat],
) -> None:
    content = message.text.strip()
    if len(content) < 5:
        await message.answer("⚠️ Matn juda qisqa. Batafsilroq yozing:", parse_mode="HTML")
        return

    data = await state.get_data()
    await state.clear()

    if not current_flat:
        await message.answer("Xatolik: kvartira topilmadi.", reply_markup=get_main_menu_kb(), parse_mode="HTML")
        return

    title = data["title"]
    rule = await RuleService.add_rule(
        session=session,
        flat_id=current_flat.id,
        title=title,
        content=content,
    )

    safe_title = escape(rule.title)
    await message.answer(
        f"✅ <b>'{safe_title}' qoidasi muvaffaqiyatli saqlandi!</b>\n\n"
        "Qoidalarning yangilangan ro'yxatini ko'rish uchun <b>'📜 Kvartira Qoidalari'</b> tugmasini bosing.",
        reply_markup=get_main_menu_kb(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "rule:delete_menu")
async def cb_rule_delete_menu(
    callback: CallbackQuery,
    session: AsyncSession,
    current_user: Optional[User],
    current_flat: Optional[Flat],
) -> None:
    """Lists rules with deletion buttons (Admin only)."""
    user_id = current_user.id if current_user else (callback.from_user.id if callback.from_user else 0)
    if not current_flat or not await is_flat_admin(session, current_flat.id, user_id):
        await callback.answer("⚠️ Faqat admin qoidalarni o'chira oladi!", show_alert=True)
        return

    await callback.answer()
    rules = await RuleService.get_flat_rules(session, current_flat.id)
    if not rules:
        await callback.message.answer("O'chirish uchun qoidalar mavjud emas.", parse_mode="HTML")
        return

    await callback.message.answer(
        "🗑 <b>O'chirmoqchi bo'lgan qoidani tanlang:</b>",
        reply_markup=get_rules_delete_kb(rules),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("rule_del:"))
async def cb_rule_delete_confirm(
    callback: CallbackQuery,
    session: AsyncSession,
    current_user: Optional[User],
    current_flat: Optional[Flat],
) -> None:
    rule_id = int(callback.data.split(":")[1])
    user_id = current_user.id if current_user else (callback.from_user.id if callback.from_user else 0)

    if not current_flat or not await is_flat_admin(session, current_flat.id, user_id):
        await callback.answer("⚠️ Faqat admin qoidalarni o'chira oladi!", show_alert=True)
        return

    success = await RuleService.delete_rule(session, rule_id=rule_id, flat_id=current_flat.id)
    if success:
        await callback.answer("🗑 Qoida muvaffaqiyatli o'chirildi!", show_alert=True)
        # Re-fetch rules and show updated view
        rules = await RuleService.get_flat_rules(session, current_flat.id)
        if rules:
            await callback.message.edit_text(
                "🗑 <b>O'chirmoqchi bo'lgan qoidani tanlang:</b>",
                reply_markup=get_rules_delete_kb(rules),
                parse_mode="HTML"
            )
        else:
            await callback.message.edit_text(
                "Barcha qoidalar o'chirildi. Yangi qoidalar kiritishingiz mumkin.",
                reply_markup=get_rules_view_kb(is_admin=True),
                parse_mode="HTML"
            )
    else:
        await callback.answer("Qoida topilmadi.", show_alert=True)


@router.callback_query(F.data == "rule:reset_defaults")
async def cb_rule_reset_defaults(
    callback: CallbackQuery,
    session: AsyncSession,
    current_user: Optional[User],
    current_flat: Optional[Flat],
) -> None:
    user_id = current_user.id if current_user else (callback.from_user.id if callback.from_user else 0)
    if not current_flat or not await is_flat_admin(session, current_flat.id, user_id):
        await callback.answer("⚠️ Faqat admin uchun ruxsat berilgan!", show_alert=True)
        return

    await RuleService.seed_default_rules(session, current_flat.id, current_flat.template_type)
    await callback.answer("🔄 Standart qoidalar qayta tiklandi!", show_alert=True)
    rules = await RuleService.get_flat_rules(session, current_flat.id)

    safe_flat = escape(current_flat.name)
    lines = [f"📜 <b>'{safe_flat}' Kvartira Qoidalari va Tartibi:</b>\n"]
    for idx, r in enumerate(rules, start=1):
        lines.append(f"{idx}. <b>{escape(r.title)}</b>\n{escape(r.content)}\n")

    await callback.message.answer(
        "\n".join(lines),
        reply_markup=get_rules_view_kb(is_admin=True),
        parse_mode="HTML"
    )


# =====================================================================
# 2. ADVANCED CHORE ASSIGNMENT & DUTY SCHEDULER
# =====================================================================

@router.message(F.text == "👑 Admin boshqaruvi")
@router.callback_query(F.data == "admin:menu")
async def cmd_admin_panel(
    event: Message | CallbackQuery,
    session: AsyncSession,
    current_user: Optional[User],
    current_flat: Optional[Flat],
) -> None:
    """Admin dashboard for role-based controls."""
    if isinstance(event, CallbackQuery):
        await event.answer()
        message = event.message
        user_id = event.from_user.id
    else:
        message = event
        user_id = current_user.id if current_user else message.from_user.id

    if not current_flat or not await is_flat_admin(session, current_flat.id, user_id):
        await message.answer("⚠️ Ushbu bo'lim faqat kvartira admini uchun ochiq.", parse_mode="HTML")
        return

    members = await FlatRepository.get_members(session, current_flat.id)
    chores = await ChoreRepository.get_flat_chores(session, current_flat.id, active_only=False)

    lines = [
        f"👑 <b>'{escape(current_flat.name)}' Admin Boshqaruv Paneli:</b>\n",
        f"👥 A'zolar soni: <b>{len(members)} ta</b>",
        f"📋 Navbatchilik vazifalari: <b>{len(chores)} ta</b>",
        f"🌙 Tinchlik soati: <b>{escape(current_flat.quiet_hours_start)}</b>",
        f"💰 Kassa zaxirasi: <b>{int(current_flat.fund_balance):,} so'm</b>\n",
        "Quyidagi boshqaruv bo'limlaridan birini tanlang:"
    ]

    await message.answer("\n".join(lines), reply_markup=get_admin_panel_kb(), parse_mode="HTML")


@router.callback_query(F.data == "admin:chores_menu")
async def cb_chores_admin_menu(
    callback: CallbackQuery,
    session: AsyncSession,
    current_user: Optional[User],
    current_flat: Optional[Flat],
) -> None:
    user_id = current_user.id if current_user else callback.from_user.id
    if not current_flat or not await is_flat_admin(session, current_flat.id, user_id):
        await callback.answer("⚠️ Faqat admin uchun ruxsat berilgan!", show_alert=True)
        return

    await callback.answer()
    await callback.message.answer(
        "🛠 <b>Navbatchilik va jadval sozlamalari:</b>\n\n"
        "• Kunlik aniq xonadoshni biriktirish (hafta kunlari bo'yicha)\n"
        "• Juftlik navbatlarini belgilash (katta tozalash uchun)\n"
        "• Yangi maxsus vazifa qo'shish yoki o'chirish",
        reply_markup=get_chores_admin_menu_kb(),
        parse_mode="HTML"
    )


# --- WEEKDAY CHORE ASSIGNMENT --- #

@router.callback_query(F.data == "admin:assign_weekday")
async def cb_assign_weekday_pick_chore(
    callback: CallbackQuery,
    session: AsyncSession,
    current_user: Optional[User],
    current_flat: Optional[Flat],
) -> None:
    user_id = current_user.id if current_user else callback.from_user.id
    if not current_flat or not await is_flat_admin(session, current_flat.id, user_id):
        await callback.answer("⚠️ Faqat admin uchun ruxsat berilgan!", show_alert=True)
        return

    await callback.answer()
    chores = await ChoreRepository.get_flat_chores(session, current_flat.id, active_only=True)
    if not chores:
        await callback.message.answer("Kvartirada faol vazifalar topilmadi.", parse_mode="HTML")
        return

    await callback.message.answer(
        "📅 <b>Kunlik navbatchi biriktirish uchun vazifani tanlang:</b>",
        reply_markup=get_chores_picker_kb(chores, prefix="chore_sel"),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("chore_sel:"))
async def cb_chore_selected_show_weekdays(
    callback: CallbackQuery,
    session: AsyncSession,
    current_user: Optional[User],
    current_flat: Optional[Flat],
) -> None:
    chore_id = int(callback.data.split(":")[1])
    user_id = current_user.id if current_user else callback.from_user.id
    if not current_flat or not await is_flat_admin(session, current_flat.id, user_id):
        await callback.answer("⚠️ Ruxsat berilmagan.", show_alert=True)
        return

    await callback.answer()
    chore = await ChoreRepository.get_by_id(session, chore_id)
    if not chore:
        await callback.message.answer("Vazifa topilmadi.", parse_mode="HTML")
        return

    members = await FlatRepository.get_members(session, current_flat.id)
    member_map = {m.user_id: m.user.display_name for m in members}

    schedule_lines = []
    for code, uz_name in WEEKDAYS_DISPLAY.items():
        assigned_uid = (chore.assigned_weekdays or {}).get(code)
        assigned_name = member_map.get(assigned_uid, "— (Avtomatik navbat)")
        schedule_lines.append(f"• <b>{uz_name}:</b> {escape(assigned_name)}")

    safe_title = escape(chore.title)
    text = (
        f"📅 <b>'{safe_title}'</b> vazifasi uchun kunlik jadval:\n\n"
        + "\n".join(schedule_lines)
        + "\n\nXonadosh biriktirmoqchi bo'lgan hafta kunini tanlang:"
    )

    await callback.message.answer(
        text,
        reply_markup=get_weekdays_picker_kb(chore_id),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("wday_sel:"))
async def cb_weekday_selected_show_members(
    callback: CallbackQuery,
    session: AsyncSession,
    current_user: Optional[User],
    current_flat: Optional[Flat],
) -> None:
    parts = callback.data.split(":")
    chore_id = int(parts[1])
    weekday = parts[2]

    user_id = current_user.id if current_user else callback.from_user.id
    if not current_flat or not await is_flat_admin(session, current_flat.id, user_id):
        await callback.answer("⚠️ Ruxsat berilmagan.", show_alert=True)
        return

    await callback.answer()
    members = await FlatRepository.get_members(session, current_flat.id)
    day_name = WEEKDAYS_DISPLAY.get(weekday, weekday)

    await callback.message.answer(
        f"👤 <b>{day_name}</b> kuni uchun mas'ul xonadoshni tanlang:",
        reply_markup=get_members_for_assignment_kb(chore_id, weekday, members),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("assign_usr:"))
async def cb_confirm_user_weekday_assignment(
    callback: CallbackQuery,
    session: AsyncSession,
    current_user: Optional[User],
    current_flat: Optional[Flat],
) -> None:
    parts = callback.data.split(":")
    chore_id = int(parts[1])
    weekday = parts[2]
    assigned_user_id = int(parts[3])

    user_id = current_user.id if current_user else callback.from_user.id
    if not current_flat or not await is_flat_admin(session, current_flat.id, user_id):
        await callback.answer("⚠️ Ruxsat berilmagan.", show_alert=True)
        return

    chore = await ChoreService.assign_member_to_weekday(
        session=session,
        chore_id=chore_id,
        weekday=weekday,
        user_id=assigned_user_id,
    )

    day_name = WEEKDAYS_DISPLAY.get(weekday, weekday)
    await callback.answer(f"✅ {day_name} kuniga muvaffaqiyatli biriktirildi!", show_alert=True)

    # Re-display updated schedule
    members = await FlatRepository.get_members(session, current_flat.id)
    member_map = {m.user_id: m.user.display_name for m in members}
    schedule_lines = []
    for code, uz_name in WEEKDAYS_DISPLAY.items():
        assigned_uid = (chore.assigned_weekdays or {}).get(code)
        assigned_name = member_map.get(assigned_uid, "— (Avtomatik navbat)")
        schedule_lines.append(f"• <b>{uz_name}:</b> {escape(assigned_name)}")

    safe_title = escape(chore.title)
    text = (
        f"📅 <b>'{safe_title}'</b> vazifasi jadvali yangilandi!\n\n"
        + "\n".join(schedule_lines)
        + "\n\nBoshqa kunni tanlash:"
    )
    await callback.message.answer(
        text,
        reply_markup=get_weekdays_picker_kb(chore_id),
        parse_mode="HTML"
    )


# --- PAIRED ROTATION CONFIGURATION --- #

@router.callback_query(F.data == "admin:assign_pairs")
async def cb_assign_pairs_start(
    callback: CallbackQuery,
    session: AsyncSession,
    current_user: Optional[User],
    current_flat: Optional[Flat],
) -> None:
    user_id = current_user.id if current_user else callback.from_user.id
    if not current_flat or not await is_flat_admin(session, current_flat.id, user_id):
        await callback.answer("⚠️ Faqat admin uchun ruxsat berilgan!", show_alert=True)
        return

    await callback.answer()
    chores = await ChoreRepository.get_flat_chores(session, current_flat.id, active_only=True)
    pair_chores = [c for c in chores if c.rotation_type == RotationType.PAIR_ROTATION]
    target_chores = pair_chores if pair_chores else chores

    await callback.message.answer(
        "👥 <b>Juftliklar (Pairs) navbatini sozlash uchun vazifani tanlang:</b>\n"
        "(Haftalik katta tozalash va juftlik vazifalari uchun)",
        reply_markup=get_chores_picker_kb(target_chores, prefix="pair_sel"),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("pair_sel:"))
async def cb_pair_selected_auto_configure(
    callback: CallbackQuery,
    session: AsyncSession,
    current_user: Optional[User],
    current_flat: Optional[Flat],
) -> None:
    chore_id = int(callback.data.split(":")[1])
    user_id = current_user.id if current_user else callback.from_user.id
    if not current_flat or not await is_flat_admin(session, current_flat.id, user_id):
        await callback.answer("⚠️ Ruxsat berilmagan.", show_alert=True)
        return

    await callback.answer()
    members = await FlatRepository.get_members(session, current_flat.id)
    if len(members) < 2:
        await callback.message.answer("⚠️ Juftlik tuzish uchun kvartirada kamida 2 nafar a'zo bo'lishi lozim.", parse_mode="HTML")
        return

    # Automatically construct balanced round-robin pairs from active members
    pairs: list[list[int]] = []
    member_ids = [m.user_id for m in members]
    for i in range(0, len(member_ids) - 1, 2):
        pairs.append([member_ids[i], member_ids[i + 1]])

    if len(member_ids) % 2 != 0:
        # If odd number of members, pair the last with the first
        pairs.append([member_ids[-1], member_ids[0]])

    chore = await ChoreService.create_paired_rotation(session, chore_id, pairs)

    member_map = {m.user_id: m.user.display_name for m in members}
    pair_lines = []
    for idx, p in enumerate(pairs, start=1):
        names = [escape(member_map.get(uid, f"ID:{uid}")) for uid in p]
        pair_lines.append(f"{idx}-juftlik: <b>{' va '.join(names)}</b>")

    safe_title = escape(chore.title)
    text = (
        f"🎉 <b>'{safe_title}' uchun juftliklar muvaffaqiyatli shakllantirildi:</b>\n\n"
        + "\n".join(pair_lines)
        + "\n\nNavbat haftalik ravishda ushbu juftliklar o'rtasida aylanadi.",
    )
    await callback.message.answer(text[0], reply_markup=get_chores_admin_menu_kb(), parse_mode="HTML")


# --- CREATE CUSTOM CHORE FLOW (ADMIN) --- #

@router.callback_query(F.data == "admin:add_chore")
async def cb_admin_add_chore_start(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    current_user: Optional[User],
    current_flat: Optional[Flat],
) -> None:
    user_id = current_user.id if current_user else callback.from_user.id
    if not current_flat or not await is_flat_admin(session, current_flat.id, user_id):
        await callback.answer("⚠️ Faqat admin vazifa qo'sha oladi!", show_alert=True)
        return

    await callback.answer()
    await state.set_state(AdminAddChoreSG.waiting_for_title)
    await callback.message.answer(
        "📝 <b>Yangi navbatchilik vazifasi nomini kiriting:</b>\n"
        "(Masalan: <i>10L suv olib kelish</i> yoki <i>Balkon tozaligi</i>)",
        reply_markup=get_cancel_kb(),
        parse_mode="HTML"
    )


@router.message(AdminAddChoreSG.waiting_for_title)
async def process_admin_chore_title(message: Message, state: FSMContext) -> None:
    title = message.text.strip()
    if len(title) < 3:
        await message.answer("⚠️ Vazifa nomi juda qisqa. Kamida 3 ta belgi kiriting:", parse_mode="HTML")
        return

    await state.update_data(title=title)
    await state.set_state(AdminAddChoreSG.waiting_for_time)
    await message.answer(
        "⏰ <b>Vazifa bajarilish vaqtini kiriting (HH:MM formatida):</b>\n"
        "(Masalan: <code>21:00</code> yoki <code>18:30</code>)",
        reply_markup=get_cancel_kb(),
        parse_mode="HTML"
    )


@router.message(AdminAddChoreSG.waiting_for_time)
async def process_admin_chore_time(message: Message, state: FSMContext) -> None:
    time_str = message.text.strip()
    await state.update_data(execution_time=time_str)
    await state.set_state(AdminAddChoreSG.waiting_for_frequency)
    await message.answer(
        "🗓 <b>Vazifaning takrorlanish tartibini tanlang:</b>",
        reply_markup=get_chore_frequency_kb(),
        parse_mode="HTML"
    )


@router.callback_query(AdminAddChoreSG.waiting_for_frequency, F.data.startswith("cfreq:"))
async def process_admin_chore_freq(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    current_flat: Optional[Flat],
) -> None:
    freq_type = callback.data.split(":")[1]
    data = await state.get_data()
    await state.clear()
    await callback.answer()

    if not current_flat:
        await callback.message.answer("Xatolik: kvartira topilmadi.", parse_mode="HTML")
        return

    chore = await ChoreService.create_custom_chore(
        session=session,
        flat_id=current_flat.id,
        title=data["title"],
        execution_time=data.get("execution_time", "21:00"),
        chore_type=freq_type,
    )

    safe_title = escape(chore.title)
    safe_time = escape(chore.execution_time)
    await callback.message.answer(
        f"✅ <b>'{safe_title}' vazifasi muvaffaqiyatli yaratildi!</b>\n\n"
        f"⏰ Vaqti: <b>{safe_time}</b>\n"
        f"🗓 Takrorlanishi: <b>{freq_type}</b>\n\n"
        "Vazifa avtomatik ravishda xonadoshlar navbatiga kiritildi.",
        reply_markup=get_chores_admin_menu_kb(),
        parse_mode="HTML"
    )


# --- CHORES MANAGEMENT (TOGGLE & DELETE) --- #

@router.callback_query(F.data == "admin:chore_list")
async def cb_chore_management_list(
    callback: CallbackQuery,
    session: AsyncSession,
    current_user: Optional[User],
    current_flat: Optional[Flat],
) -> None:
    user_id = current_user.id if current_user else callback.from_user.id
    if not current_flat or not await is_flat_admin(session, current_flat.id, user_id):
        await callback.answer("⚠️ Faqat admin uchun ruxsat berilgan!", show_alert=True)
        return

    await callback.answer()
    chores = await ChoreRepository.get_flat_chores(session, current_flat.id, active_only=False)
    if not chores:
        await callback.message.answer("Kvartirada vazifalar mavjud emas.", parse_mode="HTML")
        return

    await callback.message.answer(
        "📋 <b>Navbatchilik vazifalari ro'yxati va holati:</b>\n"
        "Holatini o'zgartirish uchun vazifa ustiga, o'chirish uchun 🗑 tugmasiga bosing:",
        reply_markup=get_chores_management_list_kb(chores),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("chore_toggle:"))
async def cb_chore_toggle_status(
    callback: CallbackQuery,
    session: AsyncSession,
    current_user: Optional[User],
    current_flat: Optional[Flat],
) -> None:
    chore_id = int(callback.data.split(":")[1])
    user_id = current_user.id if current_user else callback.from_user.id
    if not current_flat or not await is_flat_admin(session, current_flat.id, user_id):
        await callback.answer("⚠️ Ruxsat berilmagan.", show_alert=True)
        return

    chore = await ChoreService.toggle_chore_active(session, chore_id, current_flat.id)
    if chore:
        status_msg = "faollashtirildi" if chore.is_active else "to'xtatildi"
        await callback.answer(f"Vazifa {status_msg}!", show_alert=True)
        chores = await ChoreRepository.get_flat_chores(session, current_flat.id, active_only=False)
        await callback.message.edit_text(
            "📋 <b>Navbatchilik vazifalari ro'yxati va holati:</b>",
            reply_markup=get_chores_management_list_kb(chores),
            parse_mode="HTML"
        )


@router.callback_query(F.data.startswith("chore_del:"))
async def cb_chore_delete(
    callback: CallbackQuery,
    session: AsyncSession,
    current_user: Optional[User],
    current_flat: Optional[Flat],
) -> None:
    chore_id = int(callback.data.split(":")[1])
    user_id = current_user.id if current_user else callback.from_user.id
    if not current_flat or not await is_flat_admin(session, current_flat.id, user_id):
        await callback.answer("⚠️ Ruxsat berilmagan.", show_alert=True)
        return

    deleted = await ChoreService.delete_chore(session, chore_id, current_flat.id)
    if deleted:
        await callback.answer("🗑 Vazifa o'chirildi!", show_alert=True)
        chores = await ChoreRepository.get_flat_chores(session, current_flat.id, active_only=False)
        if chores:
            await callback.message.edit_text(
                "📋 <b>Navbatchilik vazifalari ro'yxati va holati:</b>",
                reply_markup=get_chores_management_list_kb(chores),
                parse_mode="HTML"
            )
        else:
            await callback.message.edit_text(
                "Barcha vazifalar o'chirildi.",
                reply_markup=get_chores_admin_menu_kb(),
                parse_mode="HTML"
            )
    else:
        await callback.answer("Vazifa topilmadi.", show_alert=True)


@router.callback_query(F.data == "rule:cancel")
async def cb_cancel_rule_dialog(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.answer("Amal bekor qilindi.")
    await callback.message.answer("Bekor qilindi.", reply_markup=get_main_menu_kb(), parse_mode="HTML")
