import pytest
import pytest_asyncio
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.database.base import Base
from app.models.chore import Chore, ChoreAssignment, ChoreFrequencyType, ChoreStatus, RotationType
from app.models.flat import Flat, FlatMember, FlatRole, FlatTemplateType
from app.models.rule import FlatRule
from app.models.user import User
from app.repositories.chore_repo import ChoreRepository
from app.repositories.flat_repo import FlatRepository
from app.repositories.rule_repo import RuleRepository
from app.repositories.user_repo import UserRepository
from app.services.chore_service import (
    WEEKDAYS_DISPLAY,
    WEEKDAYS_MAP,
    ChoreService,
)
from app.services.onboarding_service import OnboardingService
from app.services.rule_service import DEFAULT_COMMUNITY_RULES, RuleService


@pytest_asyncio.fixture
async def test_session():
    """Provides a fresh in-memory SQLite database session for each test."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with session_maker() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_rules_service_crud_and_seed(test_session: AsyncSession):
    """Verifies baseline rule seeding, dynamic addition, ordering, and deletion."""
    user = await UserRepository.upsert(test_session, user_id=4001, first_name="Admin")
    await test_session.flush()

    flat = await FlatRepository.create_flat(
        test_session,
        name="Chilanzar Central",
        created_by_id=user.id,
        invite_code="KV-RULE01",
    )

    # 1. Seed baseline rules
    rules = await RuleService.seed_default_rules(test_session, flat.id)
    assert len(rules) == 4
    assert rules[0].order_num == 1
    assert "Kechki sukunat" in rules[0].title
    assert "Dish Policy" in rules[1].title

    # 2. Add custom rule
    new_rule = await RuleService.add_rule(
        session=test_session,
        flat_id=flat.id,
        title="Elektr energiyasi",
        content="Xonadan chiqayotganda chiroq va konditsionerni o'chiring.",
    )
    assert new_rule.order_num == 5
    assert new_rule.title == "Elektr energiyasi"

    all_rules = await RuleService.get_flat_rules(test_session, flat.id)
    assert len(all_rules) == 5

    # 3. Delete rule
    del_success = await RuleService.delete_rule(test_session, rule_id=new_rule.id, flat_id=flat.id)
    assert del_success is True

    rules_after_del = await RuleService.get_flat_rules(test_session, flat.id)
    assert len(rules_after_del) == 4
    assert not any(r.id == new_rule.id for r in rules_after_del)

    # 4. Delete nonexistent rule returns False
    del_nonexistent = await RuleService.delete_rule(test_session, rule_id=99999, flat_id=flat.id)
    assert del_nonexistent is False


@pytest.mark.asyncio
async def test_rules_validation_errors(test_session: AsyncSession):
    """Verifies that empty title or content raises ValueError."""
    user = await UserRepository.upsert(test_session, user_id=4002, first_name="TestUser")
    flat = await FlatRepository.create_flat(
        test_session, name="Rule Test Flat", created_by_id=user.id, invite_code="KV-RULE02"
    )

    with pytest.raises(ValueError, match="sarlavhasi"):
        await RuleService.add_rule(test_session, flat.id, "   ", "Content here")

    with pytest.raises(ValueError, match="matni"):
        await RuleService.add_rule(test_session, flat.id, "Valid Title", "   ")


@pytest.mark.asyncio
async def test_chore_weekday_assignment(test_session: AsyncSession):
    """
    Tests binding specific roommates to days of the week (e.g. MON -> u1, TUE -> u2)
    and verifying ensure_daily_assignments honors that schedule.
    """
    u1 = await UserRepository.upsert(test_session, user_id=5001, first_name="DushanbaNavbatchi")
    u2 = await UserRepository.upsert(test_session, user_id=5002, first_name="SeshanbaNavbatchi")
    await test_session.flush()

    flat = await FlatRepository.create_flat(
        test_session, name="Weekday Flat", created_by_id=u1.id, invite_code="KV-WDAY01"
    )
    await FlatRepository.add_member(test_session, flat.id, u2.id)
    await test_session.flush()

    # Create daily chore
    chore = await ChoreService.create_custom_chore(
        session=test_session,
        flat_id=flat.id,
        title="Oshxona Tozalash",
        execution_time="21:00",
        chore_type="DAILY",
    )

    # Assign u1 to Monday, u2 to Tuesday
    await ChoreService.assign_member_to_weekday(test_session, chore.id, "MON", u1.id)
    await ChoreService.assign_member_to_weekday(test_session, chore.id, "TUE", u2.id)

    updated_chore = await ChoreRepository.get_by_id(test_session, chore.id)
    assert updated_chore.assigned_weekdays["MON"] == u1.id
    assert updated_chore.assigned_weekdays["TUE"] == u2.id

    # Test assignment on a Monday (e.g., 2026-11-02 is Monday)
    monday_date = date(2026, 11, 2)
    assert monday_date.weekday() == 0  # Monday
    assignments = await ChoreService.ensure_daily_assignments(test_session, flat.id, monday_date)
    assert len(assignments) == 1
    assert assignments[0].assignee_id == u1.id

    # Test assignment on a Tuesday (e.g., 2026-11-03 is Tuesday)
    tuesday_date = date(2026, 11, 3)
    assert tuesday_date.weekday() == 1  # Tuesday
    assignments2 = await ChoreService.ensure_daily_assignments(test_session, flat.id, tuesday_date)
    assert len(assignments2) == 1
    assert assignments2[0].assignee_id == u2.id


@pytest.mark.asyncio
async def test_chore_paired_rotation_configuration(test_session: AsyncSession):
    """
    Tests configuring predefined pair teams [[u1, u2], [u3, u4]] and rotating across days.
    """
    u1 = await UserRepository.upsert(test_session, user_id=6001, first_name="Ali")
    u2 = await UserRepository.upsert(test_session, user_id=6002, first_name="Vali")
    u3 = await UserRepository.upsert(test_session, user_id=6003, first_name="G'ani")
    u4 = await UserRepository.upsert(test_session, user_id=6004, first_name="Sami")
    await test_session.flush()

    flat = await FlatRepository.create_flat(
        test_session, name="Pairs Flat", created_by_id=u1.id, invite_code="KV-PAIR01"
    )
    await FlatRepository.add_member(test_session, flat.id, u2.id)
    await FlatRepository.add_member(test_session, flat.id, u3.id)
    await FlatRepository.add_member(test_session, flat.id, u4.id)
    await test_session.flush()

    chore = await ChoreService.create_custom_chore(
        session=test_session,
        flat_id=flat.id,
        title="Weekly Deep Clean",
        execution_time="11:00",
        chore_type="DAILY",
    )

    # Store pairs: Team 1 = [u1, u2], Team 2 = [u3, u4]
    pairs = [[u1.id, u2.id], [u3.id, u4.id]]
    await ChoreService.create_paired_rotation(test_session, chore.id, pairs)

    # First execution -> Team 1
    d1 = date(2026, 11, 10)
    assignments1 = await ChoreService.ensure_daily_assignments(test_session, flat.id, d1)
    assert len(assignments1) == 1
    assert assignments1[0].assignee_ids == [u1.id, u2.id]

    # Second execution -> Team 2
    d2 = date(2026, 11, 11)
    assignments2 = await ChoreService.ensure_daily_assignments(test_session, flat.id, d2)
    assert len(assignments2) == 1
    assert assignments2[0].assignee_ids == [u3.id, u4.id]

    # Third execution -> wraps around to Team 1
    d3 = date(2026, 11, 12)
    assignments3 = await ChoreService.ensure_daily_assignments(test_session, flat.id, d3)
    assert len(assignments3) == 1
    assert assignments3[0].assignee_ids == [u1.id, u2.id]


@pytest.mark.asyncio
async def test_chore_toggle_and_delete(test_session: AsyncSession):
    """Tests toggling active status and deletion of chores."""
    user = await UserRepository.upsert(test_session, user_id=7001, first_name="Manager")
    flat = await FlatRepository.create_flat(
        test_session, name="Manage Flat", created_by_id=user.id, invite_code="KV-MNG01"
    )

    chore = await ChoreService.create_custom_chore(
        test_session, flat.id, "Balkon tozalash", "18:00"
    )
    assert chore.is_active is True

    # Toggle off
    toggled = await ChoreService.toggle_chore_active(test_session, chore.id, flat.id)
    assert toggled.is_active is False

    # Toggle back on
    toggled2 = await ChoreService.toggle_chore_active(test_session, chore.id, flat.id)
    assert toggled2.is_active is True

    # Delete
    del_ok = await ChoreService.delete_chore(test_session, chore.id, flat.id)
    assert del_ok is True

    chores = await ChoreRepository.get_flat_chores(test_session, flat.id, active_only=False)
    assert len(chores) == 0
