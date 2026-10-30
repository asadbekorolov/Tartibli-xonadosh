from aiogram.fsm.state import State, StatesGroup


class CreateFlatSG(StatesGroup):
    waiting_for_name = State()


class JoinFlatSG(StatesGroup):
    waiting_for_code = State()
