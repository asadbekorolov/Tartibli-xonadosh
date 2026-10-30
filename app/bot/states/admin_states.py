from aiogram.fsm.state import State, StatesGroup


class AddRuleSG(StatesGroup):
    waiting_for_title = State()
    waiting_for_content = State()


class AdminAddChoreSG(StatesGroup):
    waiting_for_title = State()
    waiting_for_time = State()
    waiting_for_frequency = State()
    waiting_for_description = State()
