from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.flat import FlatTemplateType
from app.models.rule import FlatRule
from app.repositories.rule_repo import RuleRepository


DEFAULT_COMMUNITY_RULES = [
    (
        "Kechki sukunat (22:30)",
        "Har kuni soat 22:30 dan boshlab kvartirada to'liq sukunat saqlanadi. "
        "Baland ovozda gaplashish, video yoki musiqa eshitish taqiqlanadi (naushnik taqing)."
    ),
    (
        "Shaxsiy idish-tovoq siyosati (Dish Policy)",
        "Har bir xonadosh o'zining shaxsiy idishini (chashka, likopcha, qoshiq) ovqatlangandan so'ng "
        "darhol yuvishi shart! Chanoqda idish to'plab qo'yish taqiqlanadi. "
        "Qozon, tova va umumiy dasturxon anjomlari esa kunlik navbatchi zimmasida."
    ),
    (
        "Mehmonlar tashrifi tartibi",
        "Kvartiraga do'st yoki mehmmonlarni taklif qilishdan kamida 3–4 soat oldin umumiy guruhda "
        "ogohlantirish va barcha xonadoshlar roziligini olish lozim."
    ),
    (
        "Navbatchilik intizomi va jarimalar",
        "O'z navbatchiligini sababsiz bajarmagan xonadosh: navbatdan tashqari navbatchilik "
        "yoki umumiy kassa fondiga kelishilgan miqdorda jarima to'laydi."
    ),
]


class RuleService:
    @classmethod
    async def get_flat_rules(cls, session: AsyncSession, flat_id: int) -> List[FlatRule]:
        """Returns ordered rules list for the given flat."""
        return await RuleRepository.get_flat_rules(session, flat_id)

    @classmethod
    async def add_rule(
        cls,
        session: AsyncSession,
        flat_id: int,
        title: str,
        content: str,
        order_num: Optional[int] = None,
    ) -> FlatRule:
        """Adds a new house rule to the flat."""
        if not title or not title.strip():
            raise ValueError("Qoida sarlavhasi bo'sh bo'lishi mumkin emas.")
        if not content or not content.strip():
            raise ValueError("Qoida matni bo'sh bo'lishi mumkin emas.")

        return await RuleRepository.create_rule(
            session=session,
            flat_id=flat_id,
            title=title.strip(),
            content=content.strip(),
            order_num=order_num,
        )

    @classmethod
    async def delete_rule(cls, session: AsyncSession, rule_id: int, flat_id: int) -> bool:
        """Deletes a house rule safely."""
        return await RuleRepository.delete_rule(session, rule_id=rule_id, flat_id=flat_id)

    @classmethod
    async def seed_default_rules(
        cls,
        session: AsyncSession,
        flat_id: int,
        template_type: FlatTemplateType | str = FlatTemplateType.LARGE_FLAT,
    ) -> List[FlatRule]:
        """Seeds baseline rules based on chosen apartment preset."""
        existing = await RuleRepository.get_flat_rules(session, flat_id)
        if existing:
            return existing

        created = []
        for idx, (title, content) in enumerate(DEFAULT_COMMUNITY_RULES, start=1):
            rule = await RuleRepository.create_rule(
                session=session,
                flat_id=flat_id,
                title=title,
                content=content,
                order_num=idx,
            )
            created.append(rule)
        return created
