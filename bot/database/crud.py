from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from bot.database.models import (
    Chore,
    Expense,
    ExpenseParticipant,
    Flat,
    Settlement,
    User,
)


# ------------------- USER CRUD ------------------- #

async def upsert_user(
    session: AsyncSession,
    user_id: int,
    full_name: str,
    username: Optional[str] = None,
) -> User:
    """Creates a user or updates existing user details."""
    stmt = select(User).where(User.id == user_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if user:
        user.full_name = full_name
        user.username = username
        user.is_active = True
    else:
        user = User(
            id=user_id,
            username=username,
            full_name=full_name,
            is_active=True,
        )
        session.add(user)

    await session.flush()
    return user


async def get_user(session: AsyncSession, user_id: int) -> Optional[User]:
    """Retrieves user with active flat eagerly loaded."""
    stmt = (
        select(User)
        .where(User.id == user_id)
        .options(selectinload(User.flat))
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


# ------------------- FLAT CRUD ------------------- #

async def create_flat(
    session: AsyncSession,
    name: str,
    creator_id: int,
    invite_code: str,
    max_members: int = 10,
) -> Flat:
    """Creates flat and binds creator as the first member."""
    flat = Flat(
        name=name,
        invite_code=invite_code,
        creator_id=creator_id,
        max_members=max_members,
    )
    session.add(flat)
    await session.flush()

    # Bind creator user to the flat
    creator = await session.get(User, creator_id)
    if creator:
        creator.flat_id = flat.id
        await session.flush()

    # Seed default standard chores for students
    default_chores = [
        "🧹 Oshxona va zal tozaligi",
        "🗑 Chiqindini olib chiqish",
        "💧 19L Ichimlik suvi nazorati",
    ]
    for title in default_chores:
        chore = Chore(
            flat_id=flat.id,
            title=title,
            current_assignee_id=creator_id,
            status="PENDING",
        )
        session.add(chore)

    await session.flush()
    return flat


async def get_flat_by_id(session: AsyncSession, flat_id: int) -> Optional[Flat]:
    """Fetches flat by primary ID."""
    stmt = (
        select(Flat)
        .where(Flat.id == flat_id)
        .options(
            selectinload(Flat.members),
            selectinload(Flat.chores),
            selectinload(Flat.expenses),
        )
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_flat_by_invite_code(session: AsyncSession, invite_code: str) -> Optional[Flat]:
    """Fetches flat by invite code."""
    stmt = (
        select(Flat)
        .where(Flat.invite_code == invite_code.strip().upper())
        .options(selectinload(Flat.members))
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def join_flat(session: AsyncSession, user_id: int, flat_id: int) -> Tuple[bool, str]:
    """Attaches a student to the specified flat validating membership rules."""
    user = await session.get(User, user_id)
    if not user:
        return False, "Foydalanuvchi profili topilmadi."

    if user.flat_id is not None:
        if user.flat_id == flat_id:
            return True, "Siz allaqachon ushbu kvartira a'zosisiz!"
        return False, "Siz boshqa kvartira a'zosisiz. Avval undan chiqishingiz lozim."

    flat = await get_flat_by_id(session, flat_id)
    if not flat:
        return False, "Kvartira topilmadi."

    if len(flat.members) >= flat.max_members:
        return False, f"Kvartirada bo'sh joy qolmagan (Maksimal: {flat.max_members} kishi)."

    user.flat_id = flat.id
    await session.flush()
    return True, f"Tabriklaymiz! Siz '{flat.name}' kvartirasiga muvaffaqiyatli qo'shildingiz."


async def leave_flat(session: AsyncSession, user_id: int) -> Tuple[bool, str]:
    """Removes user from their current flat."""
    user = await session.get(User, user_id)
    if not user or not user.flat_id:
        return False, "Siz hech qanday kvartiraga a'zo emassiz."

    user.flat_id = None
    await session.flush()
    return True, "Siz kvartirani tark etdingiz."


async def get_flat_members(session: AsyncSession, flat_id: int) -> List[User]:
    """Returns all active students residing in the flat."""
    stmt = (
        select(User)
        .where(User.flat_id == flat_id, User.is_active.is_(True))
        .order_by(User.id.asc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


# ------------------- CHORE CRUD ------------------- #

async def create_chore(session: AsyncSession, flat_id: int, title: str) -> Chore:
    """Adds a new rotating chore and assigns it to the first available member."""
    members = await get_flat_members(session, flat_id)
    assignee_id = members[0].id if members else None

    chore = Chore(
        flat_id=flat_id,
        title=title,
        current_assignee_id=assignee_id,
        status="PENDING",
    )
    session.add(chore)
    await session.flush()
    return chore


async def get_flat_chores(session: AsyncSession, flat_id: int) -> List[Chore]:
    """Returns all rotating duties for the flat."""
    stmt = (
        select(Chore)
        .where(Chore.flat_id == flat_id)
        .options(selectinload(Chore.current_assignee))
        .order_by(Chore.id.asc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_chore_by_id(session: AsyncSession, chore_id: int) -> Optional[Chore]:
    stmt = (
        select(Chore)
        .where(Chore.id == chore_id)
        .options(selectinload(Chore.current_assignee), selectinload(Chore.flat))
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def mark_chore_completed_and_rotate(
    session: AsyncSession, chore_id: int
) -> Optional[Tuple[Chore, Optional[User], Optional[User]]]:
    """
    Marks the chore as completed and safely advances the round-robin queue:
    Assignee = members[(current_index + 1) % N]
    """
    chore = await get_chore_by_id(session, chore_id)
    if not chore:
        return None

    members = await get_flat_members(session, chore.flat_id)
    if not members:
        return chore, None, None

    prev_assignee = chore.current_assignee
    chore.last_completed_at = datetime.now(timezone.utc)

    # Cyclic Round-Robin calculation
    member_ids = [m.id for m in members]
    if chore.current_assignee_id in member_ids:
        cur_idx = member_ids.index(chore.current_assignee_id)
        next_idx = (cur_idx + 1) % len(member_ids)
    else:
        next_idx = 0

    next_assignee = members[next_idx]
    chore.current_assignee_id = next_assignee.id
    chore.status = "PENDING"

    await session.flush()
    return chore, prev_assignee, next_assignee


async def skip_chore_and_rotate(
    session: AsyncSession, chore_id: int
) -> Optional[Tuple[Chore, Optional[User], Optional[User]]]:
    """Skips the chore to the next roommate in the queue without marking completed."""
    chore = await get_chore_by_id(session, chore_id)
    if not chore:
        return None

    members = await get_flat_members(session, chore.flat_id)
    if not members:
        return chore, None, None

    prev_assignee = chore.current_assignee
    member_ids = [m.id for m in members]
    if chore.current_assignee_id in member_ids:
        cur_idx = member_ids.index(chore.current_assignee_id)
        next_idx = (cur_idx + 1) % len(member_ids)
    else:
        next_idx = 0

    next_assignee = members[next_idx]
    chore.current_assignee_id = next_assignee.id
    chore.status = "PENDING"

    await session.flush()
    return chore, prev_assignee, next_assignee


# ------------------- EXPENSE & SETTLEMENT CRUD ------------------- #

async def create_expense(
    session: AsyncSession,
    flat_id: int,
    payer_id: int,
    title: str,
    amount: Decimal,
    participant_ids: Optional[List[int]] = None,
) -> Expense:
    """
    Logs shared expense purchase and evenly distributes shares to participants.
    """
    members = await get_flat_members(session, flat_id)
    if not members:
        raise ValueError("Kvartirada a'zolar topilmadi.")

    if not participant_ids:
        participant_ids = [m.id for m in members]

    n = len(participant_ids)
    if n == 0:
        raise ValueError("Xarajat ishtirokchilari tanlanmadi.")

    expense = Expense(
        flat_id=flat_id,
        payer_id=payer_id,
        title=title,
        amount=amount,
    )
    session.add(expense)
    await session.flush()

    # Exact division for currency
    total_cents = int(amount)
    base_share = total_cents // n
    remainder = total_cents % n

    for idx, uid in enumerate(participant_ids):
        share = base_share + (1 if idx < remainder else 0)
        split = ExpenseParticipant(
            expense_id=expense.id,
            user_id=uid,
            share_amount=Decimal(str(share)),
        )
        session.add(split)

    await session.flush()
    return expense


async def get_flat_expenses(session: AsyncSession, flat_id: int) -> List[Expense]:
    """Returns all recorded expenses with payer and split details."""
    stmt = (
        select(Expense)
        .where(Expense.flat_id == flat_id)
        .options(
            selectinload(Expense.payer),
            selectinload(Expense.splits).selectinload(ExpenseParticipant.user),
        )
        .order_by(Expense.created_at.desc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def create_settlement(
    session: AsyncSession,
    flat_id: int,
    debtor_id: int,
    creditor_id: int,
    amount: Decimal,
) -> Settlement:
    """Records debt payment between two flatmates."""
    settlement = Settlement(
        flat_id=flat_id,
        debtor_id=debtor_id,
        creditor_id=creditor_id,
        amount=amount,
        status="CONFIRMED",
    )
    session.add(settlement)
    await session.flush()
    return settlement


async def get_flat_settlements(session: AsyncSession, flat_id: int) -> List[Settlement]:
    """Returns all settled payments."""
    stmt = (
        select(Settlement)
        .where(Settlement.flat_id == flat_id)
        .options(selectinload(Settlement.debtor), selectinload(Settlement.creditor))
        .order_by(Settlement.created_at.desc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())
