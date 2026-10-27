from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from app.models.chore import ChoreStatus


def get_chore_actions_kb(
    assignment_id: int, status: ChoreStatus
) -> InlineKeyboardMarkup:
    """Action buttons for interactive task completion and skipping."""
    if status == ChoreStatus.COMPLETED:
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✅ Bajarilgan",
                        callback_data="chore:noop"
                    )
                ]
            ]
        )

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Bajarildi",
                    callback_data=f"chore_done:{assignment_id}"
                ),
                InlineKeyboardButton(
                    text="⏳ Kechiktirish",
                    callback_data=f"chore_defer:{assignment_id}"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="⏭ O'tkazib yuborish",
                    callback_data=f"chore_skip:{assignment_id}"
                )
            ]
        ]
    )

