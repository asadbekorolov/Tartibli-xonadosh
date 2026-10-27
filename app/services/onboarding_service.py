import re
import secrets
import string
from typing import Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import get_settings
from app.models.flat import Flat, FlatMember, FlatRole
from app.models.chore import RotationType
from app.repositories.flat_repo import FlatRepository
from app.repositories.chore_repo import ChoreRepository

settings = get_settings()


class OnboardingService:
    @staticmethod
    def generate_invite_code() -> str:
        """
        Generates a secure 6-character alphanumeric uppercase token: KV-XXXXXX.
        Example: KV-9B4X2A
        """
        alphabet = string.ascii_uppercase + string.digits
        token = "".join(secrets.choice(alphabet) for _ in range(6))
        return f"KV-{token}"

    @staticmethod
    def parse_deep_link_payload(payload: str) -> Optional[str]:
        """
        Extracts clean invite code from deep-link argument:
        Examples:
          - 'join_KV-9B4X2A' -> 'KV-9B4X2A'
          - 'join_9B4X2A'    -> 'KV-9B4X2A'
          - 'KV-9B4X2A'      -> 'KV-9B4X2A'
        """
        if not payload:
            return None
        payload = payload.strip().upper()
        if payload.startswith("JOIN_"):
            payload = payload[5:]
        if not payload.startswith("KV-") and len(payload) == 6:
            payload = f"KV-{payload}"
        return payload if re.match(r"^KV-[A-Z0-9]{6}$", payload) else None

    @classmethod
    async def create_flat_for_user(
        cls,
        session: AsyncSession,
        creator_id: int,
        flat_name: str,
        address: Optional[str] = None,
    ) -> Flat:
        """
        Creates a new flat, binds the creator as ADMIN, and bootstraps default chores.
        Validates that user does not already belong to an active flat.
        """
        existing_flat = await FlatRepository.get_user_active_flat(session, creator_id)
        if existing_flat:
            raise ValueError(f"Siz allaqachon '{existing_flat.name}' kvartirasi a'zosisiz.")

        invite_code = cls.generate_invite_code()
        flat = await FlatRepository.create_flat(
            session=session,
            name=flat_name,
            created_by_id=creator_id,
            invite_code=invite_code,
            address=address,
            max_members=settings.MAX_MEMBERS_PER_FLAT,
        )

        # Bootstrap initial standard student chores (navbatchilik shablonlari)
        default_chores = [
            ("Oshxona va zal tozaligi", "Oshxona stoli, polni artish va idishlarni tartibga keltirish", "21:00"),
            ("Chiqindini olib chiqish", "Oshxona va dahlizdagi musor chelaklarini bo'shatish", "08:30"),
            ("Ichimlik suvi (19L) nazorati", "Suv tugashidan oldin yangi 19L baklajkaga buyurtma berish", "14:00"),
        ]

        for title, desc, time_str in default_chores:
            await ChoreRepository.create_chore(
                session=session,
                flat_id=flat.id,
                title=title,
                description=desc,
                rotation_type=RotationType.ROUND_ROBIN,
                frequency_days=1,
                execution_time=time_str,
            )

        return flat

    @classmethod
    async def join_flat_by_invite(
        cls,
        session: AsyncSession,
        user_id: int,
        invite_code: str,
    ) -> Tuple[bool, str, Optional[Flat]]:
        """
        Validates invite code, prevents conflicting flat memberships,
        and adds user to the designated flat ecosystem.
        """
        clean_code = invite_code.strip().upper()
        # Normalise code format
        if not clean_code.startswith("KV-") and len(clean_code) == 6:
            clean_code = f"KV-{clean_code}"

        flat = await FlatRepository.get_by_invite_code(session, clean_code)
        if not flat:
            return False, "❌ Bunday taklif kodi mavjud emas yoki eskirgan.", None

        # 1. Prevent conflicting flat memberships
        current_active_flat = await FlatRepository.get_user_active_flat(session, user_id)
        if current_active_flat:
            if current_active_flat.id == flat.id:
                return True, f"Siz allaqachon ushbu '{flat.name}' kvartirasi a'zosisiz!", flat
            else:
                return (
                    False,
                    f"⚠️ Siz hozirda '{current_active_flat.name}' kvartirasi faol a'zosisiz.\n"
                    "Boshqa kvartiraga qo'shilishdan avval joriy kvartiradagi hisob-kitobni yakunlab, undan chiqishingiz lozim.",
                    None,
                )

        # 2. Check flat member capacity limit (7-10 students)
        members = await FlatRepository.get_members(session, flat.id)
        if len(members) >= flat.max_members:
            return False, f"⚠️ Kvartirada joy qolmagan (Maksimal hajm: {flat.max_members} kishi).", None

        # 3. Add as regular member
        await FlatRepository.add_member(session, flat.id, user_id, role=FlatRole.MEMBER)
        return True, f"🎉 Tabriklaymiz! Siz '{flat.name}' kvartirasiga muvaffaqiyatli qo'shildingiz.", flat

