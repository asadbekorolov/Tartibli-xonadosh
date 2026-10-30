import pytest
import pytest_asyncio
from decimal import Decimal
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.database.base import Base
from app.models.flat import Flat, FlatMember, FlatRole, FlatTemplateType
from app.models.chore import Chore, ChoreAssignment, ChoreStatus, RotationType
from app.models.fund import FundTransaction, TransactionType
from app.models.user import User
from app.repositories.flat_repo import FlatRepository
from app.repositories.chore_repo import ChoreRepository
from app.repositories.fund_repo import FundRepository
from app.repositories.user_repo import UserRepository
from app.services.chore_service import ChoreService
from app.services.fund_service import FundService
from app.services.onboarding_service import OnboardingService
from app.services.templates import (
    LARGE_FLAT_CLEANING_CHECKLIST,
    PRESET_TEMPLATES,
    TemplateService,
)
from app.bot.handlers.admin import get_community_rules_text


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
async def test_preset_templates_injection(test_session: AsyncSession):
    """Verifies that each preset injects the exact expected chores and checklist."""
    # 1. Test user and flat
    user = await UserRepository.upsert(test_session, user_id=1001, first_name="Ali")
    await test_session.flush()

    flat = await FlatRepository.create_flat(
        test_session,
        name="Chilonzor Kvartira",
        created_by_id=user.id,
        invite_code="KV-TEST01",
        template_type=FlatTemplateType.LARGE_FLAT,
    )
    await TemplateService.apply_template_to_flat(test_session, flat.id, FlatTemplateType.LARGE_FLAT)
    chores = await ChoreRepository.get_flat_chores(test_session, flat.id)

    assert len(chores) == 4
    titles = [c.title for c in chores]
    assert "Oshxona va idishlar navbatchiligi" in titles
    assert "10L toza suv navbatchiligi" in titles
    assert "Haftalik katta tozalash (Juftlik)" in titles
    assert "Kir yuvish navbati" in titles

    # Check 11-step checklist on the pair cleaning chore
    pair_chore = next(c for c in chores if c.title == "Haftalik katta tozalash (Juftlik)")
    assert pair_chore.rotation_type == RotationType.PAIR_ROTATION
    assert pair_chore.checklist is not None
    assert len(pair_chore.checklist) == 11
    assert "1. 2 ta katta xonani changyutgichda tozalash" in pair_chore.checklist
    assert "11. Polni tozalab artish / nam tozalash" in pair_chore.checklist

    # 2. Test COMPACT_FLAT
    flat_compact = await FlatRepository.create_flat(
        test_session,
        name="Ixcham Kvartira",
        created_by_id=user.id,
        invite_code="KV-TEST02",
        template_type=FlatTemplateType.COMPACT_FLAT,
    )
    await TemplateService.apply_template_to_flat(test_session, flat_compact.id, FlatTemplateType.COMPACT_FLAT)
    compact_chores = await ChoreRepository.get_flat_chores(test_session, flat_compact.id)
    assert len(compact_chores) == 3
    compact_titles = [c.title for c in compact_chores]
    assert "Kunlik oshxona tozaligi" in compact_titles
    assert "Chiqindini olib chiqish" in compact_titles
    assert "Polni supurish va nam artish" in compact_titles

    # 3. Test DORMITORY
    flat_dorm = await FlatRepository.create_flat(
        test_session,
        name="TTJ 3-bino",
        created_by_id=user.id,
        invite_code="KV-TEST03",
        template_type=FlatTemplateType.DORMITORY,
    )
    await TemplateService.apply_template_to_flat(test_session, flat_dorm.id, FlatTemplateType.DORMITORY)
    dorm_chores = await ChoreRepository.get_flat_chores(test_session, flat_dorm.id)
    assert len(dorm_chores) == 3
    dorm_titles = [c.title for c in dorm_chores]
    assert "Xona tozaligi va tartibi" in dorm_titles
    assert "Chiqindi navbatchiligi" in dorm_titles
    assert "Tinchlik soati nazorati (22:30)" in dorm_titles

    # 4. Test CUSTOM
    flat_custom = await FlatRepository.create_flat(
        test_session,
        name="Shaxsiy Flat",
        created_by_id=user.id,
        invite_code="KV-TEST04",
        template_type=FlatTemplateType.CUSTOM,
    )
    await TemplateService.apply_template_to_flat(test_session, flat_custom.id, FlatTemplateType.CUSTOM)
    custom_chores = await ChoreRepository.get_flat_chores(test_session, flat_custom.id)
    assert len(custom_chores) == 0


@pytest.mark.asyncio
async def test_communal_fund_service(test_session: AsyncSession):
    """
    Tests unified communal fund operations:
    - Collection across flatmates
    - Exact deduction (e.g. 370,293 UZS spent from 400,000 UZS fund leaving 29,707 UZS)
    - Fund summary and history reporting
    """
    admin = await UserRepository.upsert(test_session, user_id=2001, first_name="Adminbek")
    u2 = await UserRepository.upsert(test_session, user_id=2002, first_name="Bobur")
    u3 = await UserRepository.upsert(test_session, user_id=2003, first_name="Jasur")
    u4 = await UserRepository.upsert(test_session, user_id=2004, first_name="Sardor")
    await test_session.flush()

    flat = await FlatRepository.create_flat(
        test_session,
        name="Yunusobod 4-mavze",
        created_by_id=admin.id,
        invite_code="KV-FUND01",
    )
    await FlatRepository.add_member(test_session, flat.id, u2.id, FlatRole.MEMBER)
    await FlatRepository.add_member(test_session, flat.id, u3.id, FlatRole.MEMBER)
    await FlatRepository.add_member(test_session, flat.id, u4.id, FlatRole.MEMBER)
    await test_session.flush()

    # 1. Create collection of 100,000 UZS from each of 4 members -> total pool = 400,000 UZS
    participants = [admin.id, u2.id, u3.id, u4.id]
    new_balance = await FundService.create_collection(
        session=test_session,
        flat_id=flat.id,
        per_person_amount=Decimal("100000.00"),
        participants=participants,
        description="Bozorlik uchun yig'im",
    )
    assert new_balance == Decimal("400000.00")

    # 2. Record market expense of 370,293 UZS for Korzinka
    tx = await FundService.record_market_expense(
        session=test_session,
        flat_id=flat.id,
        spender_id=u2.id,
        amount=Decimal("370293.00"),
        description="Korzinka bozorlik",
    )
    # Check exact balance preservation: 400,000 - 370,293 = 29,707 UZS
    assert tx.balance_after == Decimal("29707.00")
    assert tx.tx_type == TransactionType.EXPENSE
    assert tx.amount == Decimal("370293.00")

    # 3. Check Fund Summary
    summary = await FundService.get_fund_summary(test_session, flat.id)
    assert summary.fund_balance == Decimal("29707.00")
    assert summary.total_income == Decimal("400000.00")
    assert summary.total_expense == Decimal("370293.00")
    assert summary.member_count == 4
    # Recent transactions should include 4 income + 1 expense
    assert len(summary.recent_transactions) == 5
    assert summary.recent_transactions[0].description == "Korzinka bozorlik"


@pytest.mark.asyncio
async def test_fund_validation_errors(test_session: AsyncSession):
    """Verifies that invalid fund operations raise ValueErrors."""
    user = await UserRepository.upsert(test_session, user_id=2501, first_name="Tohir")
    flat = await FlatRepository.create_flat(
        test_session, name="Test Flat", created_by_id=user.id, invite_code="KV-VAL01"
    )

    # Empty participants
    with pytest.raises(ValueError, match="tanlanmadi"):
        await FundService.create_collection(test_session, flat.id, Decimal("50000"), [])

    # Negative collection amount
    with pytest.raises(ValueError, match="musbat"):
        await FundService.create_collection(test_session, flat.id, Decimal("-100"), [user.id])

    # Negative expense amount
    with pytest.raises(ValueError, match="musbat"):
        await FundService.record_market_expense(test_session, flat.id, user.id, Decimal("-500"), "test")

    # Empty description
    with pytest.raises(ValueError, match="tavsifi"):
        await FundService.record_market_expense(test_session, flat.id, user.id, Decimal("5000"), "   ")


@pytest.mark.asyncio
async def test_chore_service_pair_rotation(test_session: AsyncSession):
    """
    Tests ChoreService cyclic rotation and PAIR_ROTATION mechanics.
    """
    u1 = await UserRepository.upsert(test_session, user_id=3001, first_name="User1")
    u2 = await UserRepository.upsert(test_session, user_id=3002, first_name="User2")
    u3 = await UserRepository.upsert(test_session, user_id=3003, first_name="User3")
    u4 = await UserRepository.upsert(test_session, user_id=3004, first_name="User4")
    await test_session.flush()

    flat = await FlatRepository.create_flat(
        test_session,
        name="Sergeli 7",
        created_by_id=u1.id,
        invite_code="KV-ROT001",
    )
    await FlatRepository.add_member(test_session, flat.id, u2.id)
    await FlatRepository.add_member(test_session, flat.id, u3.id)
    await FlatRepository.add_member(test_session, flat.id, u4.id)
    await test_session.flush()

    # Create a PAIR_ROTATION chore
    chore = await ChoreRepository.create_chore(
        test_session,
        flat_id=flat.id,
        title="Katta Tozalash",
        rotation_type=RotationType.PAIR_ROTATION,
        frequency_days=1,
        checklist=LARGE_FLAT_CLEANING_CHECKLIST,
    )

    # First day assignment
    day1 = date(2026, 11, 1)
    assignments1 = await ChoreService.ensure_daily_assignments(
        session=test_session,
        flat_id=flat.id,
        target_date=day1,
    )
    assert len(assignments1) == 1
    a1 = assignments1[0]
    assert a1.assignee_ids == [u1.id, u2.id]
    assert a1.assignee_id == u1.id

    # Second day assignment (index advanced by 2 -> u3 and u4)
    day2 = date(2026, 11, 2)
    assignments2 = await ChoreService.ensure_daily_assignments(
        session=test_session,
        flat_id=flat.id,
        target_date=day2,
    )
    assert len(assignments2) == 1
    a2 = assignments2[0]
    assert a2.assignee_ids == [u3.id, u4.id]

    # Third day assignment (index wraps around -> u1 and u2)
    day3 = date(2026, 11, 3)
    assignments3 = await ChoreService.ensure_daily_assignments(
        session=test_session,
        flat_id=flat.id,
        target_date=day3,
    )
    assert len(assignments3) == 1
    a3 = assignments3[0]
    assert a3.assignee_ids == [u1.id, u2.id]


def test_onboarding_deep_link_and_rules():
    """Tests deep-link invite code resolution and community rules text."""
    assert OnboardingService.parse_deep_link_payload("join_KV-ABC123") == "KV-ABC123"
    assert OnboardingService.parse_deep_link_payload("join_ABC123") == "KV-ABC123"
    assert OnboardingService.parse_deep_link_payload("KV-XYZ789") == "KV-XYZ789"
    assert OnboardingService.parse_deep_link_payload("invalid") is None

    # Test community rules rendering
    flat = Flat(name="Oqtepa 15", quiet_hours_start="22:30")
    rules_text = get_community_rules_text(flat)
    assert "22:30" in rules_text
    assert "Dish Policy" in rules_text
    assert "3–4 soat oldin" in rules_text
    assert "Oqtepa 15" in rules_text
