from aiogram.fsm.state import State, StatesGroup


class CreateFlatSG(StatesGroup):
    waiting_for_name = State()
    waiting_for_template = State()


class JoinFlatSG(StatesGroup):
    waiting_for_code = State()
