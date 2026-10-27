from aiogram.fsm.state import State, StatesGroup


class AddExpenseSG(StatesGroup):
    waiting_for_amount = State()
    waiting_for_category = State()
    waiting_for_title = State()
    waiting_for_split = State()


class SettleDebtSG(StatesGroup):
    waiting_for_creditor = State()
    waiting_for_amount = State()
