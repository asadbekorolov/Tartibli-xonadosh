from datetime import date, datetime, timezone
from typing import Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.attributes import flag_modified
from app.models.chore import (
    Chore,
    ChoreAssignment,
    ChoreFrequencyType,
    ChoreStatus,
    RotationType,
)


class ChoreRepository:
    @staticmethod
    async def create_chore(
        session: AsyncSession,
        flat_id: int,
        title: str,
        description: Optional[str] = None,
        rotation_type: RotationType = RotationType.ROUND_ROBIN,
        frequency_type: ChoreFrequencyType = ChoreFrequencyType.DAILY,
        frequency_days: int = 1,
        execution_time: str = "21:00",
        checklist: Optional[List[str]] = None,
        assignee_ids: Optional[List[int]] = None,
        assigned_weekdays: Optional[Dict[str, int]] = None,
        assigned_pairs: Optional[List[List[int]]] = None,
    ) -> Chore:
        chore = Chore(
            flat_id=flat_id,
            title=title,
            description=description,
            rotation_type=rotation_type,
            frequency_type=frequency_type,
            frequency_days=frequency_days,
            execution_time=execution_time,
            current_member_index=0,
            checklist=checklist,
            assignee_ids=assignee_ids,
            assigned_weekdays=assigned_weekdays,
            assigned_pairs=assigned_pairs,
            is_active=True
        )
        session.add(chore)
        await session.flush()
        return chore

    @staticmethod
    async def get_by_id(session: AsyncSession, chore_id: int) -> Optional[Chore]:
        stmt = (
            select(Chore)
            .where(Chore.id == chore_id)
            .options(selectinload(Chore.assignments))
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_flat_chores(
        session: AsyncSession, flat_id: int, active_only: bool = True
    ) -> List[Chore]:
        stmt = select(Chore).where(Chore.flat_id == flat_id)
        if active_only:
            stmt = stmt.where(Chore.is_active.is_(True))
        stmt = stmt.order_by(Chore.id.asc())
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def update_assigned_weekdays(
        session: AsyncSession,
        chore_id: int,
        assigned_weekdays: Dict[str, int],
    ) -> Optional[Chore]:
        chore = await ChoreRepository.get_by_id(session, chore_id)
        if chore:
            chore.assigned_weekdays = dict(assigned_weekdays)
            flag_modified(chore, "assigned_weekdays")
            await session.flush()
        return chore

    @staticmethod
    async def update_assigned_pairs(
        session: AsyncSession,
        chore_id: int,
        assigned_pairs: List[List[int]],
    ) -> Optional[Chore]:
        chore = await ChoreRepository.get_by_id(session, chore_id)
        if chore:
            chore.assigned_pairs = list(assigned_pairs)
            chore.rotation_type = RotationType.PAIR_ROTATION
            flag_modified(chore, "assigned_pairs")
            await session.flush()
        return chore

    @staticmethod
    async def toggle_active(
        session: AsyncSession,
        chore_id: int,
        flat_id: int,
    ) -> Optional[Chore]:
        stmt = select(Chore).where(Chore.id == chore_id, Chore.flat_id == flat_id)
        result = await session.execute(stmt)
        chore = result.scalar_one_or_none()
        if chore:
            chore.is_active = not chore.is_active
            await session.flush()
        return chore

    @staticmethod
    async def delete_chore(
        session: AsyncSession,
        chore_id: int,
        flat_id: int,
    ) -> bool:
        stmt = select(Chore).where(Chore.id == chore_id, Chore.flat_id == flat_id)
        result = await session.execute(stmt)
        chore = result.scalar_one_or_none()
        if chore:
            await session.delete(chore)
            await session.flush()
            return True
        return False

    @staticmethod
    async def get_assignment_by_id(
        session: AsyncSession, assignment_id: int
    ) -> Optional[ChoreAssignment]:
        stmt = (
            select(ChoreAssignment)
            .where(ChoreAssignment.id == assignment_id)
            .options(
                selectinload(ChoreAssignment.chore),
                selectinload(ChoreAssignment.assignee)
            )
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_assignment_for_chore_date(
        session: AsyncSession, chore_id: int, target_date: date
    ) -> Optional[ChoreAssignment]:
        stmt = (
            select(ChoreAssignment)
            .where(
                ChoreAssignment.chore_id == chore_id,
                ChoreAssignment.due_date == target_date
            )
            .options(
                selectinload(ChoreAssignment.chore),
                selectinload(ChoreAssignment.assignee)
            )
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_flat_assignments_by_date(
        session: AsyncSession, flat_id: int, target_date: date
    ) -> List[ChoreAssignment]:
        stmt = (
            select(ChoreAssignment)
            .where(
                ChoreAssignment.flat_id == flat_id,
                ChoreAssignment.due_date == target_date
            )
            .options(
                selectinload(ChoreAssignment.chore),
                selectinload(ChoreAssignment.assignee)
            )
            .order_by(ChoreAssignment.id.asc())
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def create_assignment(
        session: AsyncSession,
        chore_id: int,
        flat_id: int,
        assignee_id: Optional[int],
        due_date: date,
        assignee_ids: Optional[List[int]] = None,
        status: ChoreStatus = ChoreStatus.PENDING
    ) -> ChoreAssignment:
        assignment = ChoreAssignment(
            chore_id=chore_id,
            flat_id=flat_id,
            assignee_id=assignee_id,
            assignee_ids=assignee_ids,
            due_date=due_date,
            status=status
        )
        session.add(assignment)
        await session.flush()
        return assignment

    @staticmethod
    async def update_status(
        session: AsyncSession,
        assignment_id: int,
        status: ChoreStatus,
        notes: Optional[str] = None
    ) -> Optional[ChoreAssignment]:
        assignment = await ChoreRepository.get_assignment_by_id(session, assignment_id)
        if assignment:
            assignment.status = status
            if notes:
                assignment.notes = notes
            if status == ChoreStatus.COMPLETED:
                assignment.completed_at = datetime.now(timezone.utc)
            await session.flush()
        return assignment

    @staticmethod
    async def update_rotation_index(
        session: AsyncSession, chore_id: int, next_index: int
    ) -> None:
        chore = await ChoreRepository.get_by_id(session, chore_id)
        if chore:
            chore.current_member_index = next_index
            await session.flush()
