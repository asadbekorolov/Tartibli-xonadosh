from dataclasses import dataclass
from typing import Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.chore import Chore, RotationType
from app.models.flat import FlatTemplateType
from app.repositories.chore_repo import ChoreRepository


@dataclass
class ChoreTemplateDefinition:
    title: str
    description: str
    rotation_type: RotationType
    frequency_days: int
    execution_time: str
    checklist: Optional[List[str]] = None


# 11-step deep cleaning checklist for large flats (weekly pair rotation)
LARGE_FLAT_CLEANING_CHECKLIST = [
    "1. 2 ta katta xonani changyutgichda tozalash",
    "2. Pastki stollarni artish",
    "3. Balkon, dahliz va oshxonani changyutgich qilish",
    "4. Gaz plitasi ustidagi folgani almashtirish",
    "5. Dasturxon va pol latta/brezentini yuvish",
    "6. Hojatxona, cho'tka va gilamchani xlorlab yuvish",
    "7. Deraza tokchalarini artish",
    "8. Vanna va rakovinani chuqur tozalash",
    "9. Poyabzal javonini tartibga keltirish",
    "10. Barcha xonalardagi chiqindi chelaklarini bo'shatish",
    "11. Polni tozalab artish / nam tozalash",
]


PRESET_TEMPLATES: Dict[FlatTemplateType, List[ChoreTemplateDefinition]] = {
    FlatTemplateType.LARGE_FLAT: [
        ChoreTemplateDefinition(
            title="Oshxona va idishlar navbatchiligi",
            description=(
                "Ovqat tayyorlash, non, dasturxonni yig'ishtirish, qozon va umumiy idishlarni yuvish, "
                "oshxona va hojatxona chiqindisini to'kish. (Qoida: shaxsiy idishlar har kim o'zi yuvadi!)"
            ),
            rotation_type=RotationType.ROUND_ROBIN,
            frequency_days=1,
            execution_time="21:00",
        ),
        ChoreTemplateDefinition(
            title="10L toza suv navbatchiligi",
            description="Filtrlangan 10L toza suv baklajkalarini olib kelish va suv zaxirasini to'ldirish",
            rotation_type=RotationType.ROUND_ROBIN,
            frequency_days=1,
            execution_time="18:00",
        ),
        ChoreTemplateDefinition(
            title="Haftalik katta tozalash (Juftlik)",
            description="Kvartirani to'liq tozalash (11 bosqichli checklist bo'yicha 2 kishi)",
            rotation_type=RotationType.PAIR_ROTATION,
            frequency_days=7,
            execution_time="11:00",
            checklist=LARGE_FLAT_CLEANING_CHECKLIST,
        ),
        ChoreTemplateDefinition(
            title="Kir yuvish navbati",
            description="Kiryuvish mashinasidan navbat bilan foydalanish va kiyimlarni yuvish",
            rotation_type=RotationType.ROUND_ROBIN,
            frequency_days=3,
            execution_time="19:00",
        ),
    ],
    FlatTemplateType.COMPACT_FLAT: [
        ChoreTemplateDefinition(
            title="Kunlik oshxona tozaligi",
            description="Oshxona stoli, gaz plitasi va umumiy idishlarni tozalash",
            rotation_type=RotationType.ROUND_ROBIN,
            frequency_days=1,
            execution_time="21:00",
        ),
        ChoreTemplateDefinition(
            title="Chiqindini olib chiqish",
            description="Oshxona va dahlizdagi barcha musor chelaklarini bo'shatish",
            rotation_type=RotationType.ROUND_ROBIN,
            frequency_days=1,
            execution_time="08:30",
        ),
        ChoreTemplateDefinition(
            title="Polni supurish va nam artish",
            description="Xonalar va dahliz polini supurgi/changyutgich bilan tozalab, nam latta bilan artish",
            rotation_type=RotationType.ROUND_ROBIN,
            frequency_days=2,
            execution_time="20:00",
        ),
    ],
    FlatTemplateType.DORMITORY: [
        ChoreTemplateDefinition(
            title="Xona tozaligi va tartibi",
            description="Xona polini supurish/artish, stollar va changlarni tozalash",
            rotation_type=RotationType.ROUND_ROBIN,
            frequency_days=1,
            execution_time="19:00",
        ),
        ChoreTemplateDefinition(
            title="Chiqindi navbatchiligi",
            description="Xona chiqindisini TTJ umumiy chiqindixonasiga olib chiqish",
            rotation_type=RotationType.ROUND_ROBIN,
            frequency_days=1,
            execution_time="08:30",
        ),
        ChoreTemplateDefinition(
            title="Tinchlik soati nazorati (22:30)",
            description="Soat 22:30 tinchlik tartibiga rioya qilish, chiroqlarni nazorat qilish, dars/uyqu muhitini ta'minlash",
            rotation_type=RotationType.ROUND_ROBIN,
            frequency_days=1,
            execution_time="22:30",
        ),
    ],
    FlatTemplateType.CUSTOM: [
        # Blank slate allowing admins to define custom recurring tasks
    ],
}


class TemplateService:
    @staticmethod
    def get_template_display_name(template_type: FlatTemplateType) -> str:
        labels = {
            FlatTemplateType.LARGE_FLAT: "🏢 Katta Kvartira (6–10 kishi)",
            FlatTemplateType.COMPACT_FLAT: "🏠 Ixcham Kvartira (2–5 kishi)",
            FlatTemplateType.DORMITORY: "🛏 TTJ / Yotoqxona",
            FlatTemplateType.CUSTOM: "⚙️ Shaxsiy (Custom)",
        }
        return labels.get(template_type, template_type.value)

    @classmethod
    async def apply_template_to_flat(
        cls,
        session: AsyncSession,
        flat_id: int,
        template_type: FlatTemplateType,
    ) -> List[Chore]:
        """
        Injects the preset chores for the flat into the database.
        """
        templates = PRESET_TEMPLATES.get(template_type, [])
        created_chores: List[Chore] = []

        for item in templates:
            chore = await ChoreRepository.create_chore(
                session=session,
                flat_id=flat_id,
                title=item.title,
                description=item.description,
                rotation_type=item.rotation_type,
                frequency_days=item.frequency_days,
                execution_time=item.execution_time,
                checklist=item.checklist,
            )
            created_chores.append(chore)

        return created_chores
