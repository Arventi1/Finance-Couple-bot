from aiogram.dispatcher.filters.state import State, StatesGroup

# ========== СОСТОЯНИЯ ДЛЯ ДОБАВЛЕНИЯ ==========

class AddExpense(StatesGroup):
    waiting_for_amount = State()
    waiting_for_category = State()
    waiting_for_description = State()

class AddIncome(StatesGroup):
    waiting_for_amount = State()
    waiting_for_category = State()
    waiting_for_description = State()

class AddPlan(StatesGroup):
    waiting_for_title = State()
    waiting_for_description = State()
    waiting_for_date = State()
    waiting_for_time = State()
    waiting_for_category = State()
    waiting_for_shared = State()

class AddPurchase(StatesGroup):
    waiting_for_name = State()
    waiting_for_cost = State()
    waiting_for_priority = State()
    waiting_for_date = State()
    waiting_for_notes = State()

# ========== СОСТОЯНИЯ ДЛЯ РЕДАКТИРОВАНИЯ ==========

class EditExpense(StatesGroup):
    waiting_for_amount = State()
    waiting_for_category = State()
    waiting_for_description = State()

class EditIncome(StatesGroup):
    waiting_for_amount = State()
    waiting_for_category = State()
    waiting_for_description = State()

class EditPlan(StatesGroup):
    waiting_for_title = State()
    waiting_for_description = State()
    waiting_for_date = State()
    waiting_for_time = State()
    waiting_for_category = State()

class EditPurchase(StatesGroup):
    waiting_for_name = State()
    waiting_for_cost = State()
    waiting_for_priority = State()
    waiting_for_date = State()
    waiting_for_notes = State()

# ========== СОСТОЯНИЯ ДЛЯ ПОИСКА ==========

class SearchStates(StatesGroup):
    waiting_for_description = State()
    waiting_for_category = State()
    waiting_for_min_amount = State()
    waiting_for_max_amount = State()
    waiting_for_date = State()
    waiting_for_date_range = State()

class SearchPlanStates(StatesGroup):
    waiting_for_text = State()
    waiting_for_category = State()
    waiting_for_date_from = State()
    waiting_for_date_to = State()

class SearchPurchaseStates(StatesGroup):
    waiting_for_text = State()
    waiting_for_priority = State()
    waiting_for_min_cost = State()
    waiting_for_max_cost = State()

# ========== СОСТОЯНИЯ ДЛЯ УДАЛЕНИЯ ==========

class DeleteStates(StatesGroup):
    waiting_for_confirmation = State()
    waiting_for_transaction_id = State()
    waiting_for_plan_id = State()
    waiting_for_purchase_id = State()