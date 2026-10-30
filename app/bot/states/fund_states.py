from aiogram.fsm.state import State, StatesGroup


class FundCollectSG(StatesGroup):
    waiting_for_amount = State()
    waiting_for_confirmation = State()


class FundExpenseSG(StatesGroup):
    waiting_for_amount = State()
    waiting_for_description = State()
