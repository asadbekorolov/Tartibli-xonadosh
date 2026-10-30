from datetime import date, datetime, timezone
from typing import Dict, List, Optional, Tuple
import pytz
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import get_settings
from app.models.chore import (
    Chore,
    ChoreAssignment,
    ChoreFrequencyType,
    ChoreStatus,
    RotationType,
)
from app.repositories.chore_repo import ChoreRepository
from app.repositories.flat_repo import FlatRepository

settings = get_settings()

WEEKDAYS_MAP = {
    0: "MON",
    1: "TUE",
    2: "WED",
    3: "THU",
    4: "FRI",
    5: "SAT",
    6: "SUN",
}

WEEKDAYS_DISPLAY = {
    "MON": "Dushanba",
    "TUE": "Seshanba",
    "WED": "Chorshanba",
    "THU": "Payshanba",
    "FRI": "Juma",
    "SAT": "Shanba",
    "SUN": "Yakshanba",
}


class ChoreService:
    @classmethod
    async def ensure_daily_assignments(
        cls,
        session: AsyncSession,
        flat_id: int,
        target_date: Optional[date] = None,
    ) -> List[ChoreAssignment]:
        """
        Idempotent engine that checks all active chores for the flat and generates
        daily assignments using:
        1. Configured weekday fixed assignments (assigned_weekdays),
        2. Configured custom pairs rotation (assigned_pairs),
        3. Cyclic pair rotation or round-robin queues.
        """
        if target_date is None:
            tz = pytz.timezone(settings.TIMEZONE)
            target_date = datetime.now(tz).date()

        members = await FlatRepository.get_members(session, flat_id)
        if not members:
            return []

        chores = await ChoreRepository.get_flat_chores(session, flat_id, active_only=True)
        assignments: List[ChoreAssignment] = []
        member_count = len(members)
        target_weekday = WEEKDAYS_MAP.get(target_date.weekday(), "MON")

        for chore in chores:
            existing = await ChoreRepository.get_assignment_for_chore_date(
                session=session,
                chore_id=chore.id,
                target_date=target_date
            )
            if existing:
                assignments.append(existing)
                continue

            # Frequency check for weekly or multi-day tasks
            if chore.frequency_type == ChoreFrequencyType.WEEKLY or chore.frequency_days == 7:
                if target_date.weekday() != 6:  # Default to Sunday if weekly
                    continue
            elif chore.frequency_days > 1 and chore.frequency_days != 7:
                if target_date.toordinal() % chore.frequency_days != 0:
                    continue

            # 1. Check if chore has fixed weekday assignment for today
            if chore.assigned_weekdays and target_weekday in chore.assigned_weekdays:
                assigned_uid = chore.assigned_weekdays[target_weekday]
                assignment = await ChoreRepository.create_assignment(
                    session=session,
                    chore_id=chore.id,
                    flat_id=flat_id,
                    assignee_id=assigned_uid,
                    assignee_ids=[assigned_uid],
                    due_date=target_date,
                    status=ChoreStatus.PENDING
                )
                assignments.append(assignment)
                continue

            # 2. Check if chore has predefined pairs configured
            if chore.rotation_type == RotationType.PAIR_ROTATION and chore.assigned_pairs:
                pairs_count = len(chore.assigned_pairs)
                if pairs_count > 0:
                    pair_index = chore.current_member_index % pairs_count
                    pair = chore.assigned_pairs[pair_index]
                    primary_assignee = pair[0] if len(pair) > 0 else None
                    assignment = await ChoreRepository.create_assignment(
                        session=session,
                        chore_id=chore.id,
                        flat_id=flat_id,
                        assignee_id=primary_assignee,
                        assignee_ids=pair,
                        due_date=target_date,
                        status=ChoreStatus.PENDING
                    )
                    assignments.append(assignment)

                    next_pair_idx = (pair_index + 1) % pairs_count
                    await ChoreRepository.update_rotation_index(session, chore.id, next_pair_idx)
                    continue

            # 3. Dynamic Pair Rotation from flat members
            if chore.rotation_type == RotationType.PAIR_ROTATION and member_count >= 2:
                idx1 = chore.current_member_index % member_count
                idx2 = (chore.current_member_index + 1) % member_count
                m1 = members[idx1]
                m2 = members[idx2]
                assignee_ids = [m1.user_id, m2.user_id]
                primary_assignee = m1.user_id

                assignment = await ChoreRepository.create_assignment(
                    session=session,
                    chore_id=chore.id,
                    flat_id=flat_id,
                    assignee_id=primary_assignee,
                    assignee_ids=assignee_ids,
                    due_date=target_date,
                    status=ChoreStatus.PENDING
                )
                assignments.append(assignment)

                next_index = (chore.current_member_index + 2) % member_count
                await ChoreRepository.update_rotation_index(session, chore.id, next_index)

            else:
                # 4. Default 1-person ROUND_ROBIN or FIXED_DAYS
                assignee_index = chore.current_member_index % member_count
                assignee = members[assignee_index]
                assignee_ids = [assignee.user_id]

                assignment = await ChoreRepository.create_assignment(
                    session=session,
                    chore_id=chore.id,
                    flat_id=flat_id,
                    assignee_id=assignee.user_id,
                    assignee_ids=assignee_ids,
                    due_date=target_date,
                    status=ChoreStatus.PENDING
                )
                assignments.append(assignment)

                next_index = (assignee_index + 1) % member_count
                await ChoreRepository.update_rotation_index(session, chore.id, next_index)

        return assignments

    @classmethod
    async def get_today_assignments(
        cls,
        session: AsyncSession,
        flat_id: int,
        target_date: Optional[date] = None,
    ) -> List[ChoreAssignment]:
        """Ensures assignments exist and returns all chore assignments for the target date."""
        return await cls.ensure_daily_assignments(session, flat_id, target_date)

    @classmethod
    async def complete_chore(
        cls,
        session: AsyncSession,
        assignment_id: int,
        notes: Optional[str] = None
    ) -> Optional[ChoreAssignment]:
        """Marks a chore assignment as completed."""
        return await ChoreRepository.update_status(
            session=session,
            assignment_id=assignment_id,
            status=ChoreStatus.COMPLETED,
            notes=notes
        )

    @classmethod
    async def defer_chore(
        cls,
        session: AsyncSession,
        assignment_id: int,
        notes: Optional[str] = "Kechiktirildi"
    ) -> Optional[ChoreAssignment]:
        """Defers a chore keeping its status as PENDING."""
        return await ChoreRepository.update_status(
            session=session,
            assignment_id=assignment_id,
            status=ChoreStatus.PENDING,
            notes=notes
        )

    @classmethod
    async def skip_chore(
        cls,
        session: AsyncSession,
        assignment_id: int,
        notes: Optional[str] = "Navbat o'tkazib yuborildi"
    ) -> Optional[ChoreAssignment]:
        """Marks a chore as skipped/deferred."""
        return await ChoreRepository.update_status(
            session=session,
            assignment_id=assignment_id,
            status=ChoreStatus.SKIPPED,
            notes=notes
        )

    # ------------------- ADMIN CONFIGURATION METHODS ------------------- #

    @classmethod
    async def assign_member_to_weekday(
        cls,
        session: AsyncSession,
        chore_id: int,
        weekday: str,
        user_id: int,
    ) -> Optional[Chore]:
        """Binds a specific roommate to a day (MON..SUN) for a given chore."""
        chore = await ChoreRepository.get_by_id(session, chore_id)
        if not chore:
            raise ValueError("Vazifa topilmadi.")

        clean_day = weekday.strip().upper()[:3]
        if clean_day not in WEEKDAYS_MAP.values():
            raise ValueError(f"Noto'g'ri hafta kuni: {weekday}")

        weekdays_dict = dict(chore.assigned_weekdays or {})
        weekdays_dict[clean_day] = user_id
        return await ChoreRepository.update_assigned_weekdays(session, chore_id, weekdays_dict)

    @classmethod
    async def create_paired_rotation(
        cls,
        session: AsyncSession,
        chore_id: int,
        pairs: List[List[int]],
    ) -> Optional[Chore]:
        """Stores weekly paired groups for tasks such as deep cleaning."""
        chore = await ChoreRepository.get_by_id(session, chore_id)
        if not chore:
            raise ValueError("Vazifa topilmadi.")
        if not pairs:
            raise ValueError("Juftliklar ro'yxati bo'sh bo'lishi mumkin emas.")

        return await ChoreRepository.update_assigned_pairs(session, chore_id, pairs)

    @classmethod
    async def create_custom_chore(
        cls,
        session: AsyncSession,
        flat_id: int,
        title: str,
        execution_time: str = "21:00",
        chore_type: str = "DAILY",
        description: Optional[str] = None,
        checklist: Optional[List[str]] = None,
    ) -> Chore:
        """Enables admin to introduce custom ad-hoc or recurring chores."""
        if not title or not title.strip():
            raise ValueError("Vazifa nomi kiritilishi shart.")

        clean_type = chore_type.upper()
        if clean_type == "WEEKLY":
            freq_type = ChoreFrequencyType.WEEKLY
            freq_days = 7
        elif clean_type == "CUSTOM":
            freq_type = ChoreFrequencyType.CUSTOM
            freq_days = 2
        else:
            freq_type = ChoreFrequencyType.DAILY
            freq_days = 1

        return await ChoreRepository.create_chore(
            session=session,
            flat_id=flat_id,
            title=title.strip(),
            description=description.strip() if description else None,
            rotation_type=RotationType.ROUND_ROBIN,
            frequency_type=freq_type,
            frequency_days=freq_days,
            execution_time=execution_time.strip() if execution_time else "21:00",
            checklist=checklist,
        )

    @classmethod
    async def add_custom_chore(
        cls,
        session: AsyncSession,
        flat_id: int,
        title: str,
        description: Optional[str] = None,
        rotation_type: RotationType = RotationType.ROUND_ROBIN,
        execution_time: str = "21:00",
        frequency_days: int = 1,
        checklist: Optional[List[str]] = None,
    ) -> Chore:
        """Backwards compatibility helper."""
        freq_type = ChoreFrequencyType.WEEKLY if frequency_days == 7 else ChoreFrequencyType.DAILY
        return await ChoreRepository.create_chore(
            session=session,
            flat_id=flat_id,
            title=title,
            description=description,
            rotation_type=rotation_type,
            frequency_type=freq_type,
            frequency_days=frequency_days,
            execution_time=execution_time,
            checklist=checklist,
        )

    @classmethod
    async def toggle_chore_active(
        cls,
        session: AsyncSession,
        chore_id: int,
        flat_id: int,
    ) -> Optional[Chore]:
        return await ChoreRepository.toggle_active(session, chore_id, flat_id)

    @classmethod
    async def delete_chore(
        cls,
        session: AsyncSession,
        chore_id: int,
        flat_id: int,
    ) -> bool:
        return await ChoreRepository.delete_chore(session, chore_id, flat_id)
