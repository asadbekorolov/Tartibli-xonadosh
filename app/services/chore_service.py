from datetime import date, datetime, timezone
from typing import List, Optional, Tuple
import pytz
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import get_settings
from app.models.chore import Chore, ChoreAssignment, ChoreStatus, RotationType
from app.repositories.chore_repo import ChoreRepository
from app.repositories.flat_repo import FlatRepository

settings = get_settings()


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
        daily assignments using cyclic round-robin queues or pair rotation if not already present.
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

        for chore in chores:
            existing = await ChoreRepository.get_assignment_for_chore_date(
                session=session,
                chore_id=chore.id,
                target_date=target_date
            )
            if existing:
                assignments.append(existing)
                continue

            # Check frequency: for frequency_days > 1 (e.g. weekly = 7),
            # check if chore should run today based on target_date
            # For simplicity and predictability, if frequency_days == 7, runs on Sunday (weekday 6)
            if chore.frequency_days == 7 and target_date.weekday() != 6:
                continue
            elif chore.frequency_days > 1 and chore.frequency_days != 7:
                # E.g. every 2 or 3 days based on day of year
                if target_date.toordinal() % chore.frequency_days != 0:
                    continue

            # Calculate assignees based on rotation_type
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

                # Advance cyclic queue index by 2
                next_index = (chore.current_member_index + 2) % member_count
                await ChoreRepository.update_rotation_index(session, chore.id, next_index)

            else:
                # Default 1-person ROUND_ROBIN or FIXED_DAYS
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
        """
        Ensures assignments exist and returns all chore assignments for the target date.
        """
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

    @classmethod
    async def add_custom_chore(
        cls,
        session: AsyncSession,
        flat_id: int,
        title: str,
        description: Optional[str] = None,
        rotation_type: RotationType = RotationType.ROUND_ROBIN,
        execution_time: str = "20:00",
        frequency_days: int = 1,
        checklist: Optional[List[str]] = None,
    ) -> Chore:
        """Allows flat admin to add new rotation duties."""
        return await ChoreRepository.create_chore(
            session=session,
            flat_id=flat_id,
            title=title,
            description=description,
            rotation_type=rotation_type,
            frequency_days=frequency_days,
            execution_time=execution_time,
            checklist=checklist,
        )
