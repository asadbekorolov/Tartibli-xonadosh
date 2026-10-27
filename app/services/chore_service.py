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
        daily assignments using cyclic round-robin queues if not already present.
        """
        if target_date is None:
            tz = pytz.timezone(settings.TIMEZONE)
            target_date = datetime.now(tz).date()


        members = await FlatRepository.get_members(session, flat_id)
        if not members:
            return []

        chores = await ChoreRepository.get_flat_chores(session, flat_id, active_only=True)
        assignments: List[ChoreAssignment] = []

        for chore in chores:
            existing = await ChoreRepository.get_assignment_for_chore_date(
                session=session,
                chore_id=chore.id,
                target_date=target_date
            )
            if existing:
                assignments.append(existing)
                continue

            # Calculate next member in cyclic round-robin rotation
            member_count = len(members)
            assignee_index = chore.current_member_index % member_count
            assignee = members[assignee_index]

            # Create assignment
            assignment = await ChoreRepository.create_assignment(
                session=session,
                chore_id=chore.id,
                flat_id=flat_id,
                assignee_id=assignee.user_id,
                due_date=target_date,
                status=ChoreStatus.PENDING
            )
            assignments.append(assignment)

            # Advance cyclic queue index
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
        execution_time: str = "20:00",
    ) -> Chore:
        """Allows flat admin to add new rotation duties."""
        return await ChoreRepository.create_chore(
            session=session,
            flat_id=flat_id,
            title=title,
            description=description,
            rotation_type=RotationType.ROUND_ROBIN,
            frequency_days=1,
            execution_time=execution_time
        )
