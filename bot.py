import asyncio
import logging
import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.utils import executor
from datetime import datetime, date, timedelta
import html

from config import BOT_TOKEN, MY_USER_ID, GIRLFRIEND_USER_ID
from database import *
from keyboards import *
from states import *
from reminders import schedule_reminders

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Инициализация бота
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Инициализация базы данных
init_db()

# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========

def is_authorized_user(user_id):
    """Проверка авторизации пользователя"""
    return user_id in [MY_USER_ID, GIRLFRIEND_USER_ID]

def format_transaction(trans, include_id=False):
    """Форматирование транзакции для отображения"""
    if len(trans) == 6:  # Сегодняшние транзакции
        trans_id, trans_type, amount, category, description, time = trans
        date_str = "сегодня"
    else:  # Транзакции за период
        trans_id, trans_type, amount, category, description, date_str, time = trans[:7]
    
    emoji = "💵" if trans_type == 'income' else "💸"
    type_text = "Доход" if trans_type == 'income' else "Расход"
    time_str = f" ({time})" if time else ""
    
    # Экранируем специальные символы
    category_escaped = html.escape(category)
    description_escaped = html.escape(description) if description else ""
    
    result = f"{emoji} <b>{type_text}:</b> {amount:.2f} руб.\n"
    result += f"   📂 Категория: {category_escaped}\n"
    result += f"   📅 Дата: {date_str}{time_str}\n"
    
    if description_escaped:
        result += f"   📝 Описание: {description_escaped}\n"
    
    if include_id:
        result += f"   🆔 ID: {trans_id}\n"
    
    return result

def format_plan(plan, include_id=False):
    """Форматирование плана для отображения"""
    plan_id, title, description, plan_date, time, category, is_shared = plan[:7]
    
    # Экранируем специальные символы
    title_escaped = html.escape(title)
    category_escaped = html.escape(category)
    description_escaped = html.escape(description) if description else ""
    
    shared_icon = " 👥" if is_shared else ""
    time_str = f" в {time}" if time else ""
    
    result = f"📅 <b>{title_escaped}</b>{shared_icon}\n"
    result += f"   📅 Дата: {plan_date}{time_str}\n"
    result += f"   🏷️ Категория: {category_escaped}\n"
    
    if description_escaped:
        result += f"   📋 Описание: {description_escaped}\n"
    
    if include_id:
        result += f"   🆔 ID: {plan_id}\n"
    
    return result

def format_purchase(purchase, include_id=False):
    """Форматирование покупки для отображения"""
    purchase_id, item_name, cost, priority, target_date, notes, status = purchase[:7]
    
    # Экранируем специальные символы
    item_name_escaped = html.escape(item_name)
    notes_escaped = html.escape(notes) if notes else ""
    
    emoji = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}[priority]
    date_str = f"до {target_date}" if target_date else ""
    status_emoji = "✅" if status == 'bought' else "📋"
    
    result = f"{emoji} <b>{item_name_escaped}</b> {status_emoji}\n"
    result += f"   💰 Стоимость: {cost:.2f} руб.\n"
    
    if date_str:
        result += f"   📅 {date_str}\n"
    
    if notes_escaped:
        result += f"   📝 Заметки: {notes_escaped}\n"
    
    if include_id:
        result += f"   🆔 ID: {purchase_id}\n"
    
    return result

async def cancel_operation(message: types.Message, state: FSMContext, operation_name: str):
    """Отмена текущей операции"""
    await state.finish()
    await message.answer(f"❌ {operation_name} отменено.", reply_markup=get_main_keyboard())

# ========== ОБЩИЙ ОБРАБОТЧИК ОТМЕНЫ ==========

@dp.message_handler(commands=['отмена', 'cancel', 'стоп'], state='*')
async def cmd_cancel(message: types.Message, state: FSMContext):
    """Обработчик команды отмены"""
    current_state = await state.get_state()
    if current_state is None:
        return
    
    await state.finish()
    await message.answer("❌ Операция отменена.", reply_markup=get_main_keyboard())

# ========== ОБРАБОТЧИКИ КОМАНД ==========

@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    """Обработчик команды /start"""
    if not is_authorized_user(message.from_user.id):
        await message.answer("❌ Доступ запрещен. Этот бот предназначен только для определенных пользователей.")
        return
    
    add_user(message.from_user.id, message.from_user.username, message.from_user.full_name)
    
    welcome_text = f"""
👋 Привет, {message.from_user.first_name}!

Я твой личный финансовый помощник и планировщик для двоих!

📌 <b>Основные возможности:</b>
• 💰 Учет расходов и доходов
• 📊 Статистика и аналитика
• 👥 Общие финансы и сравнение
• 📅 Планировщик с напоминаниями
• 🛒 Список желаемых покупок

🆕 <b>Новые функции:</b>
• ✏️ Редактирование записей
• 🗑️ Удаление с подтверждением
• 🔍 Расширенный поиск
• 👥 Общие планы

<b>Для отмены операции</b> в любой момент отправьте "отмена" или "cancel"

Используй кнопки ниже или команды:
/edit - редактирование записей
/search - поиск записей
/shared - общие расходы сегодня
/last - последние транзакции
/help - справка по командам
"""
    
    await message.answer(welcome_text, parse_mode='HTML', reply_markup=get_main_keyboard())

@dp.message_handler(commands=['help'])
async def cmd_help(message: types.Message):
    """Обработчик команды /help"""
    help_text = """
📚 <b>Справка по командам:</b>

<b>Основные команды:</b>
/start - запустить бота
/help - эта справка
/edit - редактирование записей
/search - поиск записей
/shared - общие расходы сегодня
/last - последние 10 транзакций
/weekly - недельная сводка

<b>Управление записями:</b>
✏️ Редактировать - изменить запись
🗑️ Удалить - удалить запись (с подтверждением)

<b>Общие планы:</b>
👥 Общие планы - просмотр и создание

<b>Отмена операций:</b>
В любой момент при добавлении/редактировании
отправьте "отмена", "cancel" или "стоп" для возврата в меню
"""
    
    await message.answer(help_text, parse_mode='HTML')

@dp.message_handler(commands=['last'])
async def cmd_last(message: types.Message):
    """Последние транзакции"""
    if not is_authorized_user(message.from_user.id):
        return
    
    transactions = get_recent_transactions(message.from_user.id, 10)
    
    if not transactions:
        await message.answer("📭 У вас еще нет транзакций")
        return
    
    response = "📊 <b>Последние 10 транзакций:</b>\n\n"
    
    for trans in transactions:
        trans_type, amount, category, description, datetime_str = trans
        
        # Экранируем специальные символы
        category_escaped = html.escape(category)
        description_escaped = html.escape(description) if description else ""
        
        emoji = "💵" if trans_type == 'income' else "💸"
        type_text = "Доход" if trans_type == 'income' else "Расход"
        
        response += f"{emoji} <b>{type_text}: {amount:.2f} руб.</b>\n"
        response += f"   📂 Категория: {category_escaped}\n"
        response += f"   📅 Дата: {datetime_str}\n"
        if description_escaped:
            response += f"   📝 Описание: {description_escaped}\n"
        response += "\n"
    
    await message.answer(response, parse_mode='HTML')

@dp.message_handler(commands=['weekly'])
async def cmd_weekly(message: types.Message):
    """Недельная сводка"""
    if not is_authorized_user(message.from_user.id):
        return
    
    weekly_data = get_weekly_summary()
    
    if not weekly_data:
        await message.answer("📊 Нет данных за последние 4 недели")
        return
    
    response = "📊 <b>Еженедельная сводка (последние 4 недели):</b>\n\n"
    
    current_week = None
    for data in weekly_data:
        username, week_start, income, expense = data
        
        if week_start != current_week:
            current_week = week_start
            response += f"\n<b>📅 Неделя с {week_start}:</b>\n"
        
        balance = income - expense
        response += f"  👤 {username}:\n"
        response += f"    💵 Доходы: {income:.2f} руб.\n"
        response += f"    💸 Расходы: {expense:.2f} руб.\n"
        response += f"    ⚖️ Баланс: {balance:.2f} руб.\n"
    
    await message.answer(response, parse_mode='HTML')

@dp.message_handler(commands=['shared'])
async def cmd_shared(message: types.Message):
    """Общие расходы сегодня"""
    if not is_authorized_user(message.from_user.id):
        return
    
    today_expenses = get_daily_combined_expenses()
    
    if not today_expenses:
        await message.answer("💸 <b>Сегодня еще не было общих расходов</b>", parse_mode='HTML')
        return
    
    response = "👫 <b>Общие расходы сегодня:</b>\n\n"
    user_totals = {}
    overall_total = 0
    
    for expense in today_expenses:
        username, category, amount, description = expense
        
        if username not in user_totals:
            user_totals[username] = 0
        
        user_totals[username] += amount
        overall_total += amount
    
    for username, total in user_totals.items():
        response += f"<b>{username}:</b> {total:.2f} руб.\n"
    
    response += f"\n💰 <b>Всего: {overall_total:.2f} руб.</b>"
    
    await message.answer(response, parse_mode='HTML')

# ========== ОБРАБОТЧИКИ ДОБАВЛЕНИЯ РАСХОДОВ ==========

@dp.message_handler(lambda message: message.text == '💰 Добавить расход')
async def add_expense_start(message: types.Message):
    """Начало добавления расхода"""
    if not is_authorized_user(message.from_user.id):
        return
    
    await AddExpense.waiting_for_amount.set()
    await message.answer("💸 Введите сумму расхода:\n\nДля отмены отправьте 'отмена' или 'cancel'")

@dp.message_handler(state=AddExpense.waiting_for_amount)
async def process_expense_amount(message: types.Message, state: FSMContext):
    """Обработка суммы расхода"""
    text = message.text.lower()
    if text in ['отмена', 'cancel', 'стоп', 'отменить']:
        await cancel_operation(message, state, "Добавление расхода")
        return
    
    try:
        amount = float(message.text.replace(',', '.'))
        if amount <= 0:
            await message.answer("❌ Сумма должна быть больше 0")
            return
        
        await state.update_data(amount=amount)
        await AddExpense.next()
        await message.answer("📂 Выберите категорию:", reply_markup=get_expense_categories_keyboard())
    
    except ValueError:
        await message.answer("❌ Пожалуйста, введите корректную сумму (например: 1500.50)")

@dp.callback_query_handler(lambda c: c.data.startswith('expense_cat_'), state=AddExpense.waiting_for_category)
async def process_expense_category(callback_query: types.CallbackQuery, state: FSMContext):
    """Обработка категории расхода"""
    category = callback_query.data[11:]  # Убираем 'expense_cat_'
    await state.update_data(category=category)
    await AddExpense.next()
    await bot.send_message(callback_query.from_user.id, 
                          "📝 Добавьте описание (или отправьте '-' если не нужно):\n\nДля отмены отправьте 'отмена' или 'cancel'")
    await callback_query.answer()

@dp.message_handler(state=AddExpense.waiting_for_category)
async def cancel_expense_category(message: types.Message, state: FSMContext):
    """Отмена выбора категории расхода"""
    text = message.text.lower()
    if text in ['отмена', 'cancel', 'стоп', 'отменить']:
        await cancel_operation(message, state, "Добавление расхода")
    else:
        await message.answer("Пожалуйста, выберите категорию из предложенных кнопок.")

@dp.message_handler(state=AddExpense.waiting_for_description)
async def process_expense_description(message: types.Message, state: FSMContext):
    """Обработка описания расхода"""
    text = message.text.lower()
    if text in ['отмена', 'cancel', 'стоп', 'отменить']:
        await cancel_operation(message, state, "Добавление расхода")
        return
    
    data = await state.get_data()
    description = message.text if message.text != '-' else None
    
    transaction_id = add_transaction(
        user_id=message.from_user.id,
        trans_type='expense',
        amount=data['amount'],
        category=data['category'],
        description=description
    )
    
    await state.finish()
    
    response = f"""
✅ <b>Расход успешно добавлен!</b>

💰 Сумма: {data['amount']:.2f} руб.
📂 Категория: {html.escape(data['category'])}
📅 Дата: {date.today().strftime('%Y-%m-%d')}
"""
    if description:
        response += f"📝 Описание: {html.escape(description)}\n"
    
    response += f"🆔 ID: {transaction_id}"
    
    await message.answer(response, parse_mode='HTML', reply_markup=get_main_keyboard())

# ========== ОБРАБОТЧИКИ ДОБАВЛЕНИЯ ДОХОДОВ ==========

@dp.message_handler(lambda message: message.text == '💵 Добавить доход')
async def add_income_start(message: types.Message):
    """Начало добавления дохода"""
    if not is_authorized_user(message.from_user.id):
        return
    
    await AddIncome.waiting_for_amount.set()
    await message.answer("💰 Введите сумму дохода:\n\nДля отмены отправьте 'отмена' или 'cancel'")

@dp.message_handler(state=AddIncome.waiting_for_amount)
async def process_income_amount(message: types.Message, state: FSMContext):
    """Обработка суммы дохода"""
    text = message.text.lower()
    if text in ['отмена', 'cancel', 'стоп', 'отменить']:
        await cancel_operation(message, state, "Добавление дохода")
        return
    
    try:
        amount = float(message.text.replace(',', '.'))
        if amount <= 0:
            await message.answer("❌ Сумма должна быть больше 0")
            return
        
        await state.update_data(amount=amount)
        await AddIncome.next()
        await message.answer("📂 Выберите категорию:", reply_markup=get_income_categories_keyboard())
    
    except ValueError:
        await message.answer("❌ Пожалуйста, введите корректную сумму (например: 1500.50)")

@dp.callback_query_handler(lambda c: c.data.startswith('income_cat_'), state=AddIncome.waiting_for_category)
async def process_income_category(callback_query: types.CallbackQuery, state: FSMContext):
    """Обработка категории дохода"""
    category = callback_query.data[10:]  # Убираем 'income_cat_'
    await state.update_data(category=category)
    await AddIncome.next()
    await bot.send_message(callback_query.from_user.id,
                          "📝 Добавьте описание (или отправьте '-' если не нужно):\n\nДля отмены отправьте 'отмена' или 'cancel'")
    await callback_query.answer()

@dp.message_handler(state=AddIncome.waiting_for_category)
async def cancel_income_category(message: types.Message, state: FSMContext):
    """Отмена выбора категории дохода"""
    text = message.text.lower()
    if text in ['отмена', 'cancel', 'стоп', 'отменить']:
        await cancel_operation(message, state, "Добавление дохода")
    else:
        await message.answer("Пожалуйста, выберите категорию из предложенных кнопок.")

@dp.message_handler(state=AddIncome.waiting_for_description)
async def process_income_description(message: types.Message, state: FSMContext):
    """Обработка описания дохода"""
    text = message.text.lower()
    if text in ['отмена', 'cancel', 'стоп', 'отменить']:
        await cancel_operation(message, state, "Добавление дохода")
        return
    
    data = await state.get_data()
    description = message.text if message.text != '-' else None
    
    transaction_id = add_transaction(
        user_id=message.from_user.id,
        trans_type='income',
        amount=data['amount'],
        category=data['category'],
        description=description
    )
    
    await state.finish()
    
    response = f"""
✅ <b>Доход успешно добавлен!</b>

💰 Сумма: {data['amount']:.2f} руб.
📂 Категория: {html.escape(data['category'])}
📅 Дата: {date.today().strftime('%Y-%m-%d')}
"""
    if description:
        response += f"📝 Описание: {html.escape(description)}\n"
    
    response += f"🆔 ID: {transaction_id}"
    
    await message.answer(response, parse_mode='HTML', reply_markup=get_main_keyboard())

# ========== ОБРАБОТЧИКИ ДОБАВЛЕНИЯ ПЛАНОВ ==========

@dp.message_handler(lambda message: message.text == '📅 Добавить план')
async def add_plan_start(message: types.Message):
    """Начало добавления плана"""
    if not is_authorized_user(message.from_user.id):
        return
    
    await AddPlan.waiting_for_title.set()
    await message.answer("📝 Введите название плана:\n\nДля отмены отправьте 'отмена' или 'cancel'")

@dp.message_handler(state=AddPlan.waiting_for_title)
async def process_plan_title(message: types.Message, state: FSMContext):
    """Обработка названия плана"""
    text = message.text.lower()
    if text in ['отмена', 'cancel', 'стоп', 'отменить']:
        await cancel_operation(message, state, "Добавление плана")
        return
    
    await state.update_data(title=message.text)
    await AddPlan.next()
    await message.answer("📋 Введите описание плана (или '-' если не нужно):\n\nДля отмены отправьте 'отмена' или 'cancel'")

@dp.message_handler(state=AddPlan.waiting_for_description)
async def process_plan_description(message: types.Message, state: FSMContext):
    """Обработка описания плана"""
    text = message.text.lower()
    if text in ['отмена', 'cancel', 'стоп', 'отменить']:
        await cancel_operation(message, state, "Добавление плана")
        return
    
    description = message.text if message.text != '-' else None
    await state.update_data(description=description)
    await AddPlan.next()
    await message.answer("📅 Введите дату (в формате ГГГГ-ММ-ДД, или 'сегодня', 'завтра'):\n\nДля отмены отправьте 'отмена' или 'cancel'")

@dp.message_handler(state=AddPlan.waiting_for_date)
async def process_plan_date(message: types.Message, state: FSMContext):
    """Обработка даты плана"""
    text = message.text.lower()
    if text in ['отмена', 'cancel', 'стоп', 'отменить']:
        await cancel_operation(message, state, "Добавление плана")
        return
    
    date_str = text
    
    if date_str == 'сегодня':
        plan_date = date.today().isoformat()
    elif date_str == 'завтра':
        plan_date = (date.today() + timedelta(days=1)).isoformat()
    else:
        try:
            datetime.strptime(date_str, '%Y-%m-%d')
            plan_date = date_str
        except ValueError:
            await message.answer("❌ Неверный формат даты. Используйте ГГГГ-ММ-ДД")
            return
    
    await state.update_data(date=plan_date)
    await AddPlan.next()
    await message.answer("⏰ Введите время (в формате ЧЧ:ММ, или '-' если не нужно):\n\nДля отмены отправьте 'отмена' или 'cancel'")

@dp.message_handler(state=AddPlan.waiting_for_time)
async def process_plan_time(message: types.Message, state: FSMContext):
    """Обработка времени плана"""
    text = message.text.lower()
    if text in ['отмена', 'cancel', 'стоп', 'отменить']:
        await cancel_operation(message, state, "Добавление плана")
        return
    
    time_str = message.text if message.text != '-' else None
    
    if time_str and time_str != '-':
        try:
            datetime.strptime(time_str, '%H:%M')
        except ValueError:
            await message.answer("❌ Неверный формат времени. Используйте ЧЧ:ММ")
            return
    
    await state.update_data(time=time_str)
    await AddPlan.next()
    await message.answer("🏷️ Выберите категорию плана:", reply_markup=get_plan_categories_keyboard())

@dp.callback_query_handler(lambda c: c.data.startswith('plan_cat_'), state=AddPlan.waiting_for_category)
async def process_plan_category(callback_query: types.CallbackQuery, state: FSMContext):
    """Обработка категории плана"""
    category = callback_query.data[9:]  # Убираем 'plan_cat_'
    await state.update_data(category=category)
    await AddPlan.next()
    
    await bot.send_message(callback_query.from_user.id,
                          "👥 Сделать план общим? (Общие планы видны обоим пользователям)\n"
                          "Отправьте 'да' или 'нет':\n\nДля отмены отправьте 'отмена' или 'cancel'")
    await callback_query.answer()

@dp.message_handler(state=AddPlan.waiting_for_category)
async def cancel_plan_category(message: types.Message, state: FSMContext):
    """Отмена выбора категории плана"""
    text = message.text.lower()
    if text in ['отмена', 'cancel', 'стоп', 'отменить']:
        await cancel_operation(message, state, "Добавление плана")
    else:
        await message.answer("Пожалуйста, выберите категорию из предложенных кнопок.")

@dp.message_handler(state=AddPlan.waiting_for_shared)
async def process_plan_shared(message: types.Message, state: FSMContext):
    """Обработка общего статуса плана"""
    text = message.text.lower()
    if text in ['отмена', 'cancel', 'стоп', 'отменить']:
        await cancel_operation(message, state, "Добавление плана")
        return
    
    is_shared = text in ['да', 'yes', 'y', 'д']
    
    data = await state.get_data()
    
    plan_id = add_plan(
        user_id=message.from_user.id,
        title=data['title'],
        description=data['description'],
        plan_date=data['date'],
        time=data['time'],
        category=data['category'],
        is_shared=is_shared
    )
    
    await state.finish()
    
    shared_text = "общий" if is_shared else "личный"
    time_text = f" в {data['time']}" if data['time'] else ""
    
    response = f"""
✅ <b>План успешно добавлен!</b>

📝 Название: {html.escape(data['title'])}
📅 Дата: {data['date']}{time_text}
🏷️ Категория: {html.escape(data['category'])}
👥 Статус: {shared_text}
"""
    if data['description']:
        response += f"📋 Описание: {html.escape(data['description'])}\n"
    
    response += f"🆔 ID: {plan_id}"
    
    await message.answer(response, parse_mode='HTML', reply_markup=get_main_keyboard())

# ========== ОБРАБОТЧИКИ ДОБАВЛЕНИЯ ПОКУПОК ==========

@dp.message_handler(lambda message: message.text == '🛒 Добавить покупку')
async def add_purchase_start(message: types.Message):
    """Начало добавления покупки"""
    if not is_authorized_user(message.from_user.id):
        return
    
    await AddPurchase.waiting_for_name.set()
    await message.answer("🛍️ Введите название покупки:\n\nДля отмены отправьте 'отмена' или 'cancel'")

@dp.message_handler(state=AddPurchase.waiting_for_name)
async def process_purchase_name(message: types.Message, state: FSMContext):
    """Обработка названия покупки"""
    text = message.text.lower()
    if text in ['отмена', 'cancel', 'стоп', 'отменить']:
        await cancel_operation(message, state, "Добавление покупки")
        return
    
    await state.update_data(name=message.text)
    await AddPurchase.next()
    await message.answer("💰 Введите примерную стоимость:\n\nДля отмены отправьте 'отмена' или 'cancel'")

@dp.message_handler(state=AddPurchase.waiting_for_cost)
async def process_purchase_cost(message: types.Message, state: FSMContext):
    """Обработка стоимости покупки"""
    text = message.text.lower()
    if text in ['отмена', 'cancel', 'стоп', 'отменить']:
        await cancel_operation(message, state, "Добавление покупки")
        return
    
    try:
        cost = float(message.text.replace(',', '.'))
        if cost <= 0:
            await message.answer("❌ Стоимость должна быть больше 0")
            return
        
        await state.update_data(cost=cost)
        await AddPurchase.next()
        await message.answer("🎯 Выберите приоритет:", reply_markup=get_priority_keyboard())
    
    except ValueError:
        await message.answer("❌ Пожалуйста, введите корректную сумму")

@dp.callback_query_handler(lambda c: c.data.startswith('priority_'), state=AddPurchase.waiting_for_priority)
async def process_purchase_priority(callback_query: types.CallbackQuery, state: FSMContext):
    """Обработка приоритета покупки"""
    priority = callback_query.data[9:]  # Убираем 'priority_'
    await state.update_data(priority=priority)
    await AddPurchase.next()
    
    await bot.send_message(callback_query.from_user.id,
                          "📅 Введите дату, к которой нужна покупка (ГГГГ-ММ-ДД или '-'):\n\nДля отмены отправьте 'отмена' или 'cancel'")
    await callback_query.answer()

@dp.message_handler(state=AddPurchase.waiting_for_priority)
async def cancel_purchase_priority(message: types.Message, state: FSMContext):
    """Отмена выбора приоритета покупки"""
    text = message.text.lower()
    if text in ['отмена', 'cancel', 'стоп', 'отменить']:
        await cancel_operation(message, state, "Добавление покупки")
    else:
        await message.answer("Пожалуйста, выберите приоритет из предложенных кнопок.")

@dp.message_handler(state=AddPurchase.waiting_for_date)
async def process_purchase_date(message: types.Message, state: FSMContext):
    """Обработка даты покупки"""
    text = message.text.lower()
    if text in ['отмена', 'cancel', 'стоп', 'отменить']:
        await cancel_operation(message, state, "Добавление покупки")
        return
    
    date_str = message.text if message.text != '-' else None
    
    if date_str and date_str != '-':
        try:
            datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError:
            await message.answer("❌ Неверный формат даты. Используйте ГГГГ-ММ-ДД")
            return
    
    await state.update_data(date=date_str)
    await AddPurchase.next()
    await message.answer("📝 Добавьте заметки (или отправьте '-' если не нужно):\n\nДля отмены отправьте 'отмена' или 'cancel'")

@dp.message_handler(state=AddPurchase.waiting_for_notes)
async def process_purchase_notes(message: types.Message, state: FSMContext):
    """Обработка заметок покупки"""
    text = message.text.lower()
    if text in ['отмена', 'cancel', 'стоп', 'отменить']:
        await cancel_operation(message, state, "Добавление покупки")
        return
    
    data = await state.get_data()
    notes = message.text if message.text != '-' else None
    
    purchase_id = add_planned_purchase(
        user_id=message.from_user.id,
        item_name=data['name'],
        estimated_cost=data['cost'],
        priority=data['priority'],
        target_date=data['date'],
        notes=notes
    )
    
    await state.finish()
    
    date_text = f"до {data['date']}" if data['date'] else ""
    
    response = f"""
✅ <b>Покупка успешно добавлена!</b>

🛍️ Название: {html.escape(data['name'])}
💰 Стоимость: {data['cost']:.2f} руб.
🎯 Приоритет: {data['priority']}
"""
    if date_text:
        response += f"📅 {date_text}\n"
    
    if notes:
        response += f"📝 Заметки: {html.escape(notes)}\n"
    
    response += f"🆔 ID: {purchase_id}"
    
    await message.answer(response, parse_mode='HTML', reply_markup=get_main_keyboard())

# ========== ОБРАБОТЧИКИ ПРОСМОТРА ==========

@dp.message_handler(lambda message: message.text == '📝 Мои планы')
async def show_plans(message: types.Message):
    """Показать планы на сегодня"""
    if not is_authorized_user(message.from_user.id):
        return
    
    plans = get_user_plans(message.from_user.id)
    
    if not plans:
        await message.answer("📭 На сегодня планов нет!")
        return
    
    response = "📅 <b>Ваши планы на сегодня:</b>\n\n"
    
    for plan in plans:
        response += format_plan(plan, include_id=True) + "\n"
    
    await message.answer(response, parse_mode='HTML')

@dp.message_handler(lambda message: message.text == '📋 Мои покупки')
async def show_purchases(message: types.Message):
    """Показать планируемые покупки"""
    if not is_authorized_user(message.from_user.id):
        return
    
    purchases = get_user_purchases(message.from_user.id)
    
    if not purchases:
        await message.answer("🛍️ Список планируемых покупок пуст!")
        return
    
    response = "📋 <b>Ваши планируемые покупки:</b>\n\n"
    total = 0
    
    for purchase in purchases:
        response += format_purchase(purchase, include_id=True) + "\n"
        total += purchase[2]  # estimated_cost
    
    response += f"\n💰 <b>Общая сумма: {total:.2f} руб.</b>"
    
    await message.answer(response, parse_mode='HTML')

# ========== ОБРАБОТЧИКИ СТАТИСТИКИ ==========

@dp.message_handler(lambda message: message.text == '📊 Статистика')
async def show_statistics_menu(message: types.Message):
    """Показать меню статистики"""
    if not is_authorized_user(message.from_user.id):
        return
    
    await message.answer("📊 Выберите тип статистики:", reply_markup=get_statistics_menu_keyboard())

@dp.callback_query_handler(lambda c: c.data.startswith('stats_'))
async def process_stats_menu(callback_query: types.CallbackQuery):
    """Обработка меню статистики"""
    action = callback_query.data[6:]
    user_id = callback_query.from_user.id
    
    if action == 'my':
        await bot.send_message(user_id, 
                              "📊 Выберите период для статистики:", 
                              reply_markup=get_period_selection_keyboard())
    
    elif action == 'partner':
        await bot.send_message(user_id, 
                              "👤 <b>Данные партнера:</b>", 
                              parse_mode='HTML', 
                              reply_markup=get_partner_view_keyboard())
    
    elif action == 'combined':
        await bot.send_message(user_id, 
                              "👫 <b>Общая статистика:</b>", 
                              parse_mode='HTML', 
                              reply_markup=get_combined_stats_keyboard())
    
    elif action == 'comparison':
        comparison = get_monthly_comparison()
        
        if comparison:
            response = "📊 <b>Сравнение за месяц:</b>\n\n"
            total_combined_income = 0
            total_combined_expense = 0
            
            for user_data in comparison:
                username = user_data[0]
                income = user_data[1] or 0
                expense = user_data[2] or 0
                balance = user_data[3] or 0
                
                response += f"<b>{username}:</b>\n"
                response += f"  💵 Доходы: {income:.2f} руб.\n"
                response += f"  💸 Расходы: {expense:.2f} руб.\n"
                response += f"  ⚖️ Баланс: {balance:.2f} руб.\n\n"
                
                total_combined_income += income
                total_combined_expense += expense
            
            total_balance = total_combined_income - total_combined_expense
            response += f"<b>Общие итоги:</b>\n"
            response += f"  📈 Общий доход: {total_combined_income:.2f} руб.\n"
            response += f"  📉 Общий расход: {total_combined_expense:.2f} руб.\n"
            response += f"  ⚖️ Общий баланс: {total_balance:.2f} руб."
        
        else:
            response = "📊 Данных для сравнения нет"
        
        await bot.send_message(user_id, response, parse_mode='HTML')
    
    elif action == 'categories':
        categories_stats = get_common_categories_statistics()
        
        if categories_stats:
            response = "📂 <b>Топ категорий по расходам за месяц:</b>\n\n"
            total_expenses = 0
            
            for i, (category, expense, count) in enumerate(categories_stats, 1):
                if expense > 0:
                    total_expenses += expense
                    response += f"{i}. <b>{html.escape(category)}:</b> {expense:.2f} руб. ({count} записей)\n"
            
            response += f"\n💸 <b>Всего расходов:</b> {total_expenses:.2f} руб."
        
        else:
            response = "📊 Данных по категориям нет"
        
        await bot.send_message(user_id, response, parse_mode='HTML')
    
    elif action == 'today':
        today_expenses = get_daily_combined_expenses()
        
        if today_expenses:
            response = "📅 <b>Расходы за сегодня:</b>\n\n"
            current_user = None
            user_total = 0
            overall_total = 0
            
            for expense in today_expenses:
                username, category, amount, description = expense
                
                if username != current_user:
                    if current_user:
                        response += f"<b>Итого: {user_total:.2f} руб.</b>\n\n"
                        user_total = 0
                    
                    current_user = username
                    response += f"<b>👤 {username}:</b>\n"
                
                user_total += amount
                overall_total += amount
                
                desc = f" - {html.escape(description)}" if description else ""
                response += f"  • {html.escape(category)}: {amount:.2f} руб.{desc}\n"
            
            if current_user:
                response += f"\n<b>Итого: {user_total:.2f} руб.</b>"
            
            response += f"\n\n💰 <b>Общая сумма: {overall_total:.2f} руб.</b>"
        
        else:
            response = "💸 <b>Сегодня еще не было расходов</b>"
        
        await bot.send_message(user_id, response, parse_mode='HTML')
    
    await callback_query.answer()

# ========== ОБРАБОТЧИКИ ПЕРИОДОВ СТАТИСТИКИ ==========

@dp.callback_query_handler(lambda c: c.data.startswith('period_'))
async def process_period_statistics(callback_query: types.CallbackQuery):
    """Обработка статистики по периодам"""
    action = callback_query.data[7:]  # Убираем 'period_'
    user_id = callback_query.from_user.id
    
    period_texts = {
        'today': 'сегодня',
        'week': 'неделю', 
        'month': 'месяц',
        'all': 'всё время'
    }
    period_text = period_texts.get(action, action)
    
    stats = get_period_statistics(user_id, action)
    
    if stats and (stats[0] or stats[1]):
        total_income = stats[0] or 0
        total_expense = stats[1] or 0
        count = stats[2] or 0
        balance = total_income - total_expense
        
        response = f"""
📊 <b>Статистика за {period_text}:</b>

📈 <b>Доходы:</b> {total_income:.2f} руб.
📉 <b>Расходы:</b> {total_expense:.2f} руб.
💰 <b>Баланс:</b> {balance:.2f} руб.
📋 <b>Количество операций:</b> {count}
        """
        
        transactions = get_user_transactions(user_id, action)
        
        if transactions:
            response += "\n\n📝 <b>Детали операций:</b>\n\n"
            
            if action == 'today':
                for trans in transactions:
                    response += format_transaction(trans) + "\n"
            
            else:
                current_date = None
                for trans in transactions:
                    trans_date = trans[5] if len(trans) > 5 else "Сегодня"
                    
                    if trans_date != current_date:
                        current_date = trans_date
                        response += f"\n📅 <b>{trans_date}:</b>\n"
                    
                    response += "  " + format_transaction(trans)
    
    else:
        response = f"📊 <b>Нет данных за {period_text}</b>"
    
    await bot.send_message(user_id, response, parse_mode='HTML')
    await callback_query.answer()

# ========== ОБРАБОТЧИКИ ОБЩИХ ФИНАНСОВ ==========

@dp.message_handler(lambda message: message.text == '👫 Общие финансы')
async def show_combined_finances(message: types.Message):
    """Показать меню общих финансов"""
    if not is_authorized_user(message.from_user.id):
        return
    
    await message.answer("👫 <b>Общие финансы:</b>\n\n"
                        "Выберите действие:", 
                        parse_mode='HTML',
                        reply_markup=get_combined_stats_keyboard())

# ========== ОБРАБОТЧИКИ КНОПОК ОБЩИХ ФИНАНСОВ ==========

@dp.callback_query_handler(lambda c: c.data.startswith('combined_'))
async def process_combined_finances(callback_query: types.CallbackQuery):
    """Обработка кнопок общих финансов"""
    action = callback_query.data[9:]  # Убираем 'combined_'
    user_id = callback_query.from_user.id
    
    if action == 'expenses':
        # Общие расходы
        shared_expenses = get_shared_expenses_by_category()
        
        if shared_expenses:
            response = "📊 <b>Общие расходы по категориям за месяц:</b>\n\n"
            total_expenses = 0
            user1_total = 0
            user2_total = 0
            
            for category, user1_exp, user2_exp, total in shared_expenses:
                if total > 0:
                    total_expenses += total
                    user1_total += user1_exp or 0
                    user2_total += user2_exp or 0
                    
                    response += f"<b>{html.escape(category)}:</b>\n"
                    response += f"  • Ты: {user1_exp:.2f} руб.\n"
                    response += f"  • Партнер: {user2_exp:.2f} руб.\n"
                    response += f"  • <b>Всего: {total:.2f} руб.</b>\n\n"
            
            response += f"<b>Итоги:</b>\n"
            response += f"  • Твои расходы: {user1_total:.2f} руб.\n"
            response += f"  • Расходы партнера: {user2_total:.2f} руб.\n"
            response += f"  • <b>Общие расходы: {total_expenses:.2f} руб.</b>"
        else:
            response = "📊 Нет данных об общих расходах за месяц"
        
        await bot.send_message(user_id, response, parse_mode='HTML')
    
    elif action == 'incomes':
        # Общие доходы
        combined_stats = get_combined_statistics('month')
        
        if combined_stats:
            response = "💰 <b>Общие доходы за месяц:</b>\n\n"
            total_combined_income = 0
            total_combined_expense = 0
            
            for user_data in combined_stats:
                total_income, total_expense, user_id_db = user_data
                total_combined_income += total_income or 0
                total_combined_expense += total_expense or 0
            
            # Получаем имена пользователей
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute('SELECT full_name FROM users WHERE id IN (?, ?)', 
                         (MY_USER_ID, GIRLFRIEND_USER_ID))
            users = cursor.fetchall()
            conn.close()
            
            if len(users) >= 2:
                user1_name = users[0][0] if users[0] else "Пользователь 1"
                user2_name = users[1][0] if users[1] else "Пользователь 2"
                
                # Получаем доходы по каждому пользователю
                user1_income = 0
                user2_income = 0
                
                for user_data in combined_stats:
                    total_income, total_expense, user_id_db = user_data
                    if user_id_db == MY_USER_ID:
                        user1_income = total_income or 0
                    elif user_id_db == GIRLFRIEND_USER_ID:
                        user2_income = total_income or 0
                
                response += f"<b>{user1_name}:</b> {user1_income:.2f} руб.\n"
                response += f"<b>{user2_name}:</b> {user2_income:.2f} руб.\n"
                response += f"\n<b>Общие доходы:</b> {total_combined_income:.2f} руб."
            else:
                response += f"<b>Общие доходы:</b> {total_combined_income:.2f} руб."
        else:
            response = "💰 Нет данных об общих доходах за месяц"
        
        await bot.send_message(user_id, response, parse_mode='HTML')
    
    elif action == 'categories':
        # Сравнение по категориям
        categories_stats = get_shared_expenses_by_category()
        
        if categories_stats:
            response = "📊 <b>Сравнение расходов по категориям за месяц:</b>\n\n"
            
            for category, user1_exp, user2_exp, total in categories_stats:
                if total > 0:
                    user1_percent = (user1_exp / total * 100) if total > 0 else 0
                    user2_percent = (user2_exp / total * 100) if total > 0 else 0
                    
                    response += f"<b>{html.escape(category)}</b> - {total:.2f} руб.\n"
                    response += f"  • Ты: {user1_exp:.2f} руб. ({user1_percent:.1f}%)\n"
                    response += f"  • Партнер: {user2_exp:.2f} руб. ({user2_percent:.1f}%)\n\n"
        else:
            response = "📊 Нет данных для сравнения по категориям"
        
        await bot.send_message(user_id, response, parse_mode='HTML')
    
    elif action == 'monthly':
        # Итоги за месяц
        comparison = get_monthly_comparison()
        
        if comparison:
            response = "📈 <b>Итоги за месяц:</b>\n\n"
            total_combined_income = 0
            total_combined_expense = 0
            
            for user_data in comparison:
                username = user_data[0]
                income = user_data[1] or 0
                expense = user_data[2] or 0
                balance = user_data[3] or 0
                
                response += f"<b>{username}:</b>\n"
                response += f"  💵 Доходы: {income:.2f} руб.\n"
                response += f"  💸 Расходы: {expense:.2f} руб.\n"
                response += f"  ⚖️ Баланс: {balance:.2f} руб.\n\n"
                
                total_combined_income += income
                total_combined_expense += expense
            
            total_balance = total_combined_income - total_combined_expense
            
            response += f"<b>Общие итоги:</b>\n"
            response += f"  📈 Общий доход: {total_combined_income:.2f} руб.\n"
            response += f"  📉 Общий расход: {total_combined_expense:.2f} руб.\n"
            response += f"  ⚖️ Общий баланс: {total_balance:.2f} руб."
        else:
            response = "📈 Нет данных за месяц"
        
        await bot.send_message(user_id, response, parse_mode='HTML')
    
    elif action == 'plans':
        # Совместные планы
        shared_plans = get_shared_plans()
        
        if shared_plans:
            response = "📅 <b>Совместные планы:</b>\n\n"
            
            current_date = None
            for plan in shared_plans:
                # Структура данных из get_shared_plans():
                # id, user_id, title, description, date, time, category, is_shared, 
                # notification_enabled, notification_time, is_deleted, created_at, updated_at, username, full_name
                
                if len(plan) >= 14:
                    plan_date = plan[4]
                    title = plan[2]
                    description = plan[3]
                    time = plan[5]
                    category = plan[6]
                    username = plan[13] or plan[12]  # full_name или username
                    
                    if plan_date != current_date:
                        current_date = plan_date
                        response += f"\n<b>📅 {plan_date}:</b>\n"
                    
                    time_str = f" в {time}" if time else ""
                    response += f"  • <b>{html.escape(title)}</b>{time_str}\n"
                    response += f"    👤 {username} | 🏷️ {html.escape(category)}\n"
                    
                    if description:
                        desc_short = description[:50] + "..." if len(description) > 50 else description
                        response += f"    📝 {html.escape(desc_short)}\n"
                    
                    response += "\n"
        else:
            response = "📅 Нет совместных планов"
        
        await bot.send_message(user_id, response, parse_mode='HTML')
    
    elif action == 'back_to_stats':
        # Возврат в меню статистики
        await bot.send_message(user_id,
                              "📊 Выберите тип статистики:",
                              reply_markup=get_statistics_menu_keyboard())
    
    await callback_query.answer()

# ========== ОБРАБОТЧИКИ ДАННЫХ ПАРТНЕРА ==========

@dp.callback_query_handler(lambda c: c.data.startswith('partner_'))
async def process_partner_data(callback_query: types.CallbackQuery):
    """Обработка кнопок данных партнера"""
    action = callback_query.data[8:]  # Убираем 'partner_'
    user_id = callback_query.from_user.id
    
    # Определяем ID партнера
    current_user_id = callback_query.from_user.id
    partner_id = GIRLFRIEND_USER_ID if current_user_id == MY_USER_ID else MY_USER_ID
    
    if action == 'expenses':
        # Расходы партнера
        partner_expenses = get_user_transactions(partner_id, 'month', 'expense')
        
        if partner_expenses:
            response = f"💸 <b>Расходы партнера за месяц:</b>\n\n"
            total = 0
            
            for expense in partner_expenses:
                if len(expense) >= 6:
                    trans_id, trans_type, amount, category, description, trans_date, time = expense[:7]
                    total += amount
                    
                    time_str = f" ({time})" if time else ""
                    response += f"• {category}: {amount:.2f} руб. ({trans_date}{time_str})\n"
                    if description:
                        response += f"  {description}\n"
            
            response += f"\n<b>Всего: {total:.2f} руб.</b>"
        else:
            response = "💸 У партнера нет расходов за месяц"
        
        await bot.send_message(user_id, response, parse_mode='HTML')
    
    elif action == 'incomes':
        # Доходы партнера
        partner_incomes = get_user_transactions(partner_id, 'month', 'income')
        
        if partner_incomes:
            response = f"💵 <b>Доходы партнера за месяц:</b>\n\n"
            total = 0
            
            for income in partner_incomes:
                if len(income) >= 6:
                    trans_id, trans_type, amount, category, description, trans_date, time = income[:7]
                    total += amount
                    
                    time_str = f" ({time})" if time else ""
                    response += f"• {category}: {amount:.2f} руб. ({trans_date}{time_str})\n"
                    if description:
                        response += f"  {description}\n"
            
            response += f"\n<b>Всего: {total:.2f} руб.</b>"
        else:
            response = "💵 У партнера нет доходов за месяц"
        
        await bot.send_message(user_id, response, parse_mode='HTML')
    
    elif action == 'plans':
        # Планы партнера на сегодня
        partner_plans = get_user_plans(partner_id)
        
        if partner_plans:
            response = f"📅 <b>Планы партнера на сегодня:</b>\n\n"
            
            for plan in partner_plans:
                if len(plan) >= 7:
                    plan_id, title, description, plan_date, time, category, is_shared = plan[:7]
                    
                    time_str = f" в {time}" if time else ""
                    response += f"• <b>{html.escape(title)}</b>{time_str}\n"
                    response += f"  🏷️ {html.escape(category)}\n"
                    if description:
                        response += f"  📝 {html.escape(description)}\n"
                    response += "\n"
        else:
            response = "📅 У партнера нет планов на сегодня"
        
        await bot.send_message(user_id, response, parse_mode='HTML')
    
    elif action == 'purchases':
        # Покупки партнера
        partner_purchases = get_user_purchases(partner_id)
        
        if partner_purchases:
            response = f"🛍️ <b>Планируемые покупки партнера:</b>\n\n"
            total = 0
            
            for purchase in partner_purchases:
                if len(purchase) >= 7:
                    purchase_id, item_name, cost, priority, target_date, notes, status = purchase[:7]
                    total += cost
                    
                    emoji = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}[priority]
                    date_str = f"до {target_date}" if target_date else ""
                    
                    response += f"{emoji} <b>{html.escape(item_name)}</b> - {cost:.2f} руб. {date_str}\n"
                    if notes:
                        response += f"  📝 {html.escape(notes)}\n"
                    response += "\n"
            
            response += f"<b>Общая сумма: {total:.2f} руб.</b>"
        else:
            response = "🛍️ У партнера нет планируемых покупок"
        
        await bot.send_message(user_id, response, parse_mode='HTML')
    
    elif action == 'full_stats':
        # Полная статистика партнера
        partner_stats = get_period_statistics(partner_id, 'month')
        
        if partner_stats:
            total_income = partner_stats[0] or 0
            total_expense = partner_stats[1] or 0
            count = partner_stats[2] or 0
            balance = total_income - total_expense
            
            response = f"📊 <b>Полная статистика партнера за месяц:</b>\n\n"
            response += f"📈 <b>Доходы:</b> {total_income:.2f} руб.\n"
            response += f"📉 <b>Расходы:</b> {total_expense:.2f} руб.\n"
            response += f"💰 <b>Баланс:</b> {balance:.2f} руб.\n"
            response += f"📋 <b>Количество операций:</b> {count}\n"
            
            # Последние 5 транзакций
            recent = get_recent_transactions(partner_id, 5)
            if recent:
                response += f"\n<b>Последние операции:</b>\n"
                for trans in recent:
                    trans_type, amount, category, description, datetime_str = trans
                    emoji = "💵" if trans_type == 'income' else "💸"
                    type_text = "Доход" if trans_type == 'income' else "Расход"
                    
                    response += f"{emoji} {type_text}: {amount:.2f} руб. - {category}\n"
                    if description:
                        response += f"  {description}\n"
        else:
            response = "📊 Нет статистики по партнеру"
        
        await bot.send_message(user_id, response, parse_mode='HTML')
    
    elif action == 'back_to_stats':
        # Возврат в меню статистики
        await bot.send_message(user_id,
                              "📊 Выберите тип статистики:",
                              reply_markup=get_statistics_menu_keyboard())
    
    await callback_query.answer()

# ========== ОБРАБОТЧИКИ УПРАВЛЕНИЯ ЗАПИСЯМИ ==========

@dp.message_handler(lambda message: message.text == '🔧 Управление')
async def show_management(message: types.Message):
    """Показать меню управления"""
    if not is_authorized_user(message.from_user.id):
        return
    
    await message.answer("🔧 <b>Управление записями:</b>\n\n"
                        "Выберите действие:", 
                        parse_mode='HTML',
                        reply_markup=get_management_keyboard())

# ========== ОБРАБОТЧИКИ ПОИСКА ==========

@dp.message_handler(lambda message: message.text == '🔍 Поиск')
async def show_search_menu(message: types.Message):
    """Показать меню поиска"""
    if not is_authorized_user(message.from_user.id):
        return
    
    await message.answer("🔍 <b>Поиск записей:</b>\n\n"
                        "Выберите тип поиска:",
                        parse_mode='HTML',
                        reply_markup=get_search_keyboard())

# ========== ОБРАБОТЧИКИ КНОПОК НАЗАД ==========

@dp.callback_query_handler(lambda c: c.data == 'cancel_edit')
async def cancel_edit(callback_query: types.CallbackQuery):
    """Отмена редактирования"""
    await bot.send_message(callback_query.from_user.id,
                          "❌ Редактирование отменено",
                          reply_markup=get_main_keyboard())
    await callback_query.answer()

@dp.callback_query_handler(lambda c: c.data == 'back_to_main')
async def back_to_main(callback_query: types.CallbackQuery):
    """Возврат в главное меню"""
    await bot.send_message(callback_query.from_user.id,
                          "Главное меню:",
                          reply_markup=get_main_keyboard())
    await callback_query.answer()

@dp.callback_query_handler(lambda c: c.data == 'back_to_stats')
async def back_to_stats(callback_query: types.CallbackQuery):
    """Возврат в меню статистики"""
    await bot.send_message(callback_query.from_user.id,
                          "📊 Выберите тип статистики:",
                          reply_markup=get_statistics_menu_keyboard())
    await callback_query.answer()

@dp.callback_query_handler(lambda c: c.data == 'back_to_management')
async def back_to_management(callback_query: types.CallbackQuery):
    """Возврат в меню управления"""
    await bot.send_message(callback_query.from_user.id,
                          "🔧 <b>Управление записями:</b>",
                          parse_mode='HTML',
                          reply_markup=get_management_keyboard())
    await callback_query.answer()

@dp.callback_query_handler(lambda c: c.data == 'back_to_search')
async def back_to_search(callback_query: types.CallbackQuery):
    """Возврат в меню поиска"""
    await bot.send_message(callback_query.from_user.id,
                          "🔍 <b>Поиск записей:</b>",
                          parse_mode='HTML',
                          reply_markup=get_search_keyboard())
    await callback_query.answer()

# ========== ОБРАБОТЧИКИ УПРАВЛЕНИЯ ЗАПИСЯМИ ==========

@dp.message_handler(lambda message: message.text == '🔧 Управление')
async def show_management(message: types.Message):
    """Показать меню управления"""
    if not is_authorized_user(message.from_user.id):
        return
    
    await message.answer("🔧 <b>Управление записями:</b>\n\n"
                        "Выберите действие:", 
                        parse_mode='HTML',
                        reply_markup=get_management_keyboard())

@dp.callback_query_handler(lambda c: c.data.startswith('manage_'))
async def process_management(callback_query: types.CallbackQuery, state: FSMContext):
    """Обработка меню управления"""
    action = callback_query.data[7:]  # Убираем 'manage_'
    user_id = callback_query.from_user.id
    
    if action == 'expense':
        transactions = get_user_transactions(user_id, 'month', 'expense')
        if not transactions:
            await bot.send_message(user_id, "💸 У вас нет расходов за месяц для редактирования")
            return
        
        await bot.send_message(user_id, 
                              "📝 <b>Выберите расход для редактирования:</b>",
                              parse_mode='HTML',
                              reply_markup=create_transactions_keyboard(transactions, 'expense'))
    
    elif action == 'income':
        transactions = get_user_transactions(user_id, 'month', 'income')
        if not transactions:
            await bot.send_message(user_id, "💵 У вас нет доходов за месяц для редактирования")
            return
        
        await bot.send_message(user_id,
                              "📝 <b>Выберите доход для редактирования:</b>",
                              parse_mode='HTML',
                              reply_markup=create_transactions_keyboard(transactions, 'income'))
    
    elif action == 'plan':
        plans = get_user_plans(user_id)
        if not plans:
            await bot.send_message(user_id, "📅 У вас нет планов для редактирования")
            return
        
        await bot.send_message(user_id,
                              "📝 <b>Выберите план для редактирования:</b>",
                              parse_mode='HTML',
                              reply_markup=create_plans_keyboard(plans))
    
    elif action == 'purchase':
        purchases = get_user_purchases(user_id)
        if not purchases:
            await bot.send_message(user_id, "🛍️ У вас нет покупок для редактирования")
            return
        
        await bot.send_message(user_id,
                              "📝 <b>Выберите покупку для редактирования:</b>",
                              parse_mode='HTML',
                              reply_markup=create_purchases_keyboard(purchases))
    
    await callback_query.answer()

@dp.callback_query_handler(lambda c: c.data.startswith('select_'))
async def select_for_edit(callback_query: types.CallbackQuery):
    """Выбор записи для редактирования"""
    data = callback_query.data[7:]  # Убираем 'select_'
    user_id = callback_query.from_user.id
    
    if data.startswith('expense_'):
        trans_id = int(data[8:])
        transaction = get_transaction(trans_id)
        
        if transaction and transaction[1] == user_id:  # Проверка владельца
            await bot.send_message(user_id,
                                  f"✏️ <b>Редактирование расхода:</b>\n\n"
                                  f"{format_transaction(transaction, include_id=True)}",
                                  parse_mode='HTML',
                                  reply_markup=get_edit_transaction_keyboard(trans_id, 'expense'))
        else:
            await bot.send_message(user_id, "❌ Запись не найдена или нет доступа")
    
    elif data.startswith('income_'):
        trans_id = int(data[7:])
        transaction = get_transaction(trans_id)
        
        if transaction and transaction[1] == user_id:
            await bot.send_message(user_id,
                                  f"✏️ <b>Редактирование дохода:</b>\n\n"
                                  f"{format_transaction(transaction, include_id=True)}",
                                  parse_mode='HTML',
                                  reply_markup=get_edit_transaction_keyboard(trans_id, 'income'))
        else:
            await bot.send_message(user_id, "❌ Запись не найдена или нет доступа")
    
    elif data.startswith('plan_'):
        plan_id = int(data[5:])
        plan = get_plan(plan_id)
        
        if plan and plan[1] == user_id:  # plan[1] = user_id
            await bot.send_message(user_id,
                                  f"✏️ <b>Редактирование плана:</b>\n\n"
                                  f"{format_plan(plan, include_id=True)}",
                                  parse_mode='HTML',
                                  reply_markup=get_edit_plan_keyboard(plan_id))
        else:
            await bot.send_message(user_id, "❌ План не найден или нет доступа")
    
    elif data.startswith('purchase_'):
        purchase_id = int(data[9:])
        purchase = get_purchase(purchase_id)
        
        if purchase and purchase[1] == user_id:  # purchase[1] = user_id
            await bot.send_message(user_id,
                                  f"✏️ <b>Редактирование покупки:</b>\n\n"
                                  f"{format_purchase(purchase, include_id=True)}",
                                  parse_mode='HTML',
                                  reply_markup=get_edit_purchase_keyboard(purchase_id))
        else:
            await bot.send_message(user_id, "❌ Покупка не найдена или нет доступа")
    
    await callback_query.answer()

# ========== ОБРАБОТЧИКИ РЕДАКТИРОВАНИЯ ==========

@dp.callback_query_handler(lambda c: c.data.startswith('edit_'))
async def edit_record(callback_query: types.CallbackQuery, state: FSMContext):
    """Начало редактирования записи"""
    data = callback_query.data[5:]  # Убираем 'edit_'
    user_id = callback_query.from_user.id
    
    if data.startswith('amount_expense_'):
        trans_id = int(data[15:])
        await EditExpense.waiting_for_amount.set()
        await state.update_data(trans_id=trans_id, trans_type='expense')
        await bot.send_message(user_id, "💰 Введите новую сумму расхода:")
    
    elif data.startswith('category_expense_'):
        trans_id = int(data[17:])
        await EditExpense.waiting_for_category.set()
        await state.update_data(trans_id=trans_id, trans_type='expense')
        await bot.send_message(user_id, "📂 Выберите новую категорию:",
                              reply_markup=get_expense_categories_keyboard())
    
    elif data.startswith('desc_expense_'):
        trans_id = int(data[13:])
        await EditExpense.waiting_for_description.set()
        await state.update_data(trans_id=trans_id, trans_type='expense')
        await bot.send_message(user_id, "📝 Введите новое описание (или '-' для удаления):")
    
    elif data.startswith('amount_income_'):
        trans_id = int(data[14:])
        await EditIncome.waiting_for_amount.set()
        await state.update_data(trans_id=trans_id, trans_type='income')
        await bot.send_message(user_id, "💰 Введите новую сумму дохода:")
    
    elif data.startswith('category_income_'):
        trans_id = int(data[16:])
        await EditIncome.waiting_for_category.set()
        await state.update_data(trans_id=trans_id, trans_type='income')
        await bot.send_message(user_id, "📂 Выберите новую категорию:",
                              reply_markup=get_income_categories_keyboard())
    
    elif data.startswith('desc_income_'):
        trans_id = int(data[12:])
        await EditIncome.waiting_for_description.set()
        await state.update_data(trans_id=trans_id, trans_type='income')
        await bot.send_message(user_id, "📝 Введите новое описание (или '-' для удаления):")
    
    elif data.startswith('plan_title_'):
        plan_id = int(data[11:])
        await EditPlan.waiting_for_title.set()
        await state.update_data(plan_id=plan_id)
        await bot.send_message(user_id, "📝 Введите новое название плана:")
    
    elif data.startswith('plan_desc_'):
        plan_id = int(data[10:])
        await EditPlan.waiting_for_description.set()
        await state.update_data(plan_id=plan_id)
        await bot.send_message(user_id, "📋 Введите новое описание (или '-' для удаления):")
    
    elif data.startswith('plan_date_'):
        plan_id = int(data[10:])
        await EditPlan.waiting_for_date.set()
        await state.update_data(plan_id=plan_id)
        await bot.send_message(user_id, "📅 Введите новую дату (ГГГГ-ММ-ДД, 'сегодня', 'завтра'):")
    
    elif data.startswith('plan_time_'):
        plan_id = int(data[10:])
        await EditPlan.waiting_for_time.set()
        await state.update_data(plan_id=plan_id)
        await bot.send_message(user_id, "⏰ Введите новое время (ЧЧ:ММ или '-'):")
    
    elif data.startswith('plan_cat_'):
        plan_id = int(data[9:])
        await EditPlan.waiting_for_category.set()
        await state.update_data(plan_id=plan_id)
        await bot.send_message(user_id, "🏷️ Выберите новую категорию:",
                              reply_markup=get_plan_categories_keyboard())
    
    elif data.startswith('purchase_name_'):
        purchase_id = int(data[14:])
        await EditPurchase.waiting_for_name.set()
        await state.update_data(purchase_id=purchase_id)
        await bot.send_message(user_id, "🛍️ Введите новое название покупки:")
    
    elif data.startswith('purchase_cost_'):
        purchase_id = int(data[14:])
        await EditPurchase.waiting_for_cost.set()
        await state.update_data(purchase_id=purchase_id)
        await bot.send_message(user_id, "💰 Введите новую стоимость:")
    
    elif data.startswith('purchase_priority_'):
        purchase_id = int(data[18:])
        await EditPurchase.waiting_for_priority.set()
        await state.update_data(purchase_id=purchase_id)
        await bot.send_message(user_id, "🎯 Выберите новый приоритет:",
                              reply_markup=get_priority_keyboard())
    
    elif data.startswith('purchase_date_'):
        purchase_id = int(data[14:])
        await EditPurchase.waiting_for_date.set()
        await state.update_data(purchase_id=purchase_id)
        await bot.send_message(user_id, "📅 Введите новую дату (ГГГГ-ММ-ДД или '-'):")
    
    elif data.startswith('purchase_notes_'):
        purchase_id = int(data[15:])
        await EditPurchase.waiting_for_notes.set()
        await state.update_data(purchase_id=purchase_id)
        await bot.send_message(user_id, "📝 Введите новые заметки (или '-' для удаления):")
    
    await callback_query.answer()

# ========== ОБРАБОТЧИКИ УДАЛЕНИЯ ==========

@dp.callback_query_handler(lambda c: c.data.startswith('delete_'))
async def delete_record(callback_query: types.CallbackQuery):
    """Удаление записи"""
    data = callback_query.data[7:]  # Убираем 'delete_'
    user_id = callback_query.from_user.id
    
    if data.startswith('confirm_expense_'):
        trans_id = int(data[16:])
        transaction = get_transaction(trans_id)
        
        if transaction and transaction[1] == user_id:
            await bot.send_message(user_id,
                                  f"🗑️ <b>Подтвердите удаление расхода:</b>\n\n"
                                  f"{format_transaction(transaction, include_id=True)}\n\n"
                                  f"Вы уверены, что хотите удалить эту запись?",
                                  parse_mode='HTML',
                                  reply_markup=get_delete_confirmation_keyboard('expense', trans_id))
        else:
            await bot.send_message(user_id, "❌ Запись не найдена или нет доступа")
    
    elif data.startswith('confirm_income_'):
        trans_id = int(data[15:])
        transaction = get_transaction(trans_id)
        
        if transaction and transaction[1] == user_id:
            await bot.send_message(user_id,
                                  f"🗑️ <b>Подтвердите удаление дохода:</b>\n\n"
                                  f"{format_transaction(transaction, include_id=True)}\n\n"
                                  f"Вы уверены, что хотите удалить эту запись?",
                                  parse_mode='HTML',
                                  reply_markup=get_delete_confirmation_keyboard('income', trans_id))
        else:
            await bot.send_message(user_id, "❌ Запись не найдена или нет доступа")
    
    elif data.startswith('plan_confirm_'):
        plan_id = int(data[13:])
        plan = get_plan(plan_id)
        
        if plan and plan[1] == user_id:
            await bot.send_message(user_id,
                                  f"🗑️ <b>Подтвердите удаление плана:</b>\n\n"
                                  f"{format_plan(plan, include_id=True)}\n\n"
                                  f"Вы уверены, что хотите удалить этот план?",
                                  parse_mode='HTML',
                                  reply_markup=get_delete_confirmation_keyboard('plan', plan_id))
        else:
            await bot.send_message(user_id, "❌ План не найден или нет доступа")
    
    elif data.startswith('purchase_confirm_'):
        purchase_id = int(data[17:])
        purchase = get_purchase(purchase_id)
        
        if purchase and purchase[1] == user_id:
            await bot.send_message(user_id,
                                  f"🗑️ <b>Подтвердите удаление покупки:</b>\n\n"
                                  f"{format_purchase(purchase, include_id=True)}\n\n"
                                  f"Вы уверены, что хотите удалить эту покупку?",
                                  parse_mode='HTML',
                                  reply_markup=get_delete_confirmation_keyboard('purchase', purchase_id))
        else:
            await bot.send_message(user_id, "❌ Покупка не найдена или нет доступа")
    
    await callback_query.answer()

@dp.callback_query_handler(lambda c: c.data.startswith('delete_expense_yes_'))
async def confirm_delete_expense(callback_query: types.CallbackQuery):
    """Подтверждение удаления расхода"""
    trans_id = int(callback_query.data[20:])
    delete_transaction(trans_id)
    await bot.send_message(callback_query.from_user.id,
                          "✅ Расход успешно удален!",
                          reply_markup=get_main_keyboard())
    await callback_query.answer()

@dp.callback_query_handler(lambda c: c.data.startswith('delete_expense_no_'))
async def cancel_delete_expense(callback_query: types.CallbackQuery):
    """Отмена удаления расхода"""
    await bot.send_message(callback_query.from_user.id,
                          "❌ Удаление расхода отменено",
                          reply_markup=get_main_keyboard())
    await callback_query.answer()

@dp.callback_query_handler(lambda c: c.data.startswith('delete_income_yes_'))
async def confirm_delete_income(callback_query: types.CallbackQuery):
    """Подтверждение удаления дохода"""
    trans_id = int(callback_query.data[19:])
    delete_transaction(trans_id)
    await bot.send_message(callback_query.from_user.id,
                          "✅ Доход успешно удален!",
                          reply_markup=get_main_keyboard())
    await callback_query.answer()

@dp.callback_query_handler(lambda c: c.data.startswith('delete_income_no_'))
async def cancel_delete_income(callback_query: types.CallbackQuery):
    """Отмена удаления дохода"""
    await bot.send_message(callback_query.from_user.id,
                          "❌ Удаление дохода отменено",
                          reply_markup=get_main_keyboard())
    await callback_query.answer()

@dp.callback_query_handler(lambda c: c.data.startswith('delete_plan_yes_'))
async def confirm_delete_plan(callback_query: types.CallbackQuery):
    """Подтверждение удаления плана"""
    plan_id = int(callback_query.data[17:])
    delete_plan(plan_id)
    await bot.send_message(callback_query.from_user.id,
                          "✅ План успешно удален!",
                          reply_markup=get_main_keyboard())
    await callback_query.answer()

@dp.callback_query_handler(lambda c: c.data.startswith('delete_plan_no_'))
async def cancel_delete_plan(callback_query: types.CallbackQuery):
    """Отмена удаления плана"""
    await bot.send_message(callback_query.from_user.id,
                          "❌ Удаление плана отменено",
                          reply_markup=get_main_keyboard())
    await callback_query.answer()

@dp.callback_query_handler(lambda c: c.data.startswith('delete_purchase_yes_'))
async def confirm_delete_purchase(callback_query: types.CallbackQuery):
    """Подтверждение удаления покупки"""
    purchase_id = int(callback_query.data[21:])
    delete_purchase(purchase_id)
    await bot.send_message(callback_query.from_user.id,
                          "✅ Покупка успешно удалена!",
                          reply_markup=get_main_keyboard())
    await callback_query.answer()

@dp.callback_query_handler(lambda c: c.data.startswith('delete_purchase_no_'))
async def cancel_delete_purchase(callback_query: types.CallbackQuery):
    """Отмена удаления покупки"""
    await bot.send_message(callback_query.from_user.id,
                          "❌ Удаление покупки отменено",
                          reply_markup=get_main_keyboard())
    await callback_query.answer()

# ========== ОБРАБОТЧИКИ ДЛЯ ПОКУПОК ==========

@dp.callback_query_handler(lambda c: c.data.startswith('purchase_done_'))
async def mark_purchase_done(callback_query: types.CallbackQuery):
    """Отметить покупку как купленную"""
    purchase_id = int(callback_query.data[14:])
    purchase = get_purchase(purchase_id)
    
    if purchase and purchase[1] == callback_query.from_user.id:
        update_purchase(purchase_id, status='bought')
        await bot.send_message(callback_query.from_user.id,
                              "✅ Покупка отмечена как купленная!",
                              reply_markup=get_main_keyboard())
    else:
        await bot.send_message(callback_query.from_user.id,
                              "❌ Покупка не найдена или нет доступа")
    
    await callback_query.answer()

@dp.callback_query_handler(lambda c: c.data.startswith('toggle_shared_'))
async def toggle_shared_plan(callback_query: types.CallbackQuery):
    """Переключение общего статуса плана"""
    plan_id = int(callback_query.data[14:])
    plan = get_plan(plan_id)
    
    if plan and plan[1] == callback_query.from_user.id:
        current_shared = bool(plan[7])  # plan[7] = is_shared
        new_shared = not current_shared
        
        update_plan(plan_id, is_shared=new_shared)
        
        status = "общим" if new_shared else "личным"
        await bot.send_message(callback_query.from_user.id,
                              f"✅ План теперь {status}!",
                              reply_markup=get_main_keyboard())
    else:
        await bot.send_message(callback_query.from_user.id,
                              "❌ План не найден или нет доступа")
    
    await callback_query.answer()

# ========== ОБРАБОТЧИКИ ОБЩИХ ПЛАНОВ ==========

@dp.callback_query_handler(lambda c: c.data == 'shared_plans')
async def show_shared_plans_menu(callback_query: types.CallbackQuery):
    """Меню общих планов"""
    await bot.send_message(callback_query.from_user.id,
                          "👥 <b>Общие планы:</b>\n\n"
                          "Выберите действие:",
                          parse_mode='HTML',
                          reply_markup=get_shared_plans_keyboard())
    await callback_query.answer()

@dp.callback_query_handler(lambda c: c.data == 'show_shared_plans')
async def show_all_shared_plans(callback_query: types.CallbackQuery):
    """Показать все общие планы"""
    shared_plans = get_shared_plans()
    
    if not shared_plans:
        await bot.send_message(callback_query.from_user.id,
                              "📅 Нет общих планов",
                              reply_markup=get_shared_plans_keyboard())
        return
    
    response = "👥 <b>Все общие планы:</b>\n\n"
    current_date = None
    
    for plan in shared_plans:
        if len(plan) >= 14:
            plan_date = plan[4]  # date
            title = plan[2]      # title
            description = plan[3] # description
            time = plan[5]       # time
            category = plan[6]   # category
            username = plan[13] or plan[12]  # full_name или username
            
            if plan_date != current_date:
                current_date = plan_date
                response += f"\n<b>📅 {plan_date}:</b>\n"
            
            time_str = f" в {time}" if time else ""
            response += f"  • <b>{html.escape(title)}</b>{time_str}\n"
            response += f"    👤 {username} | 🏷️ {html.escape(category)}\n"
            
            if description:
                desc_short = description[:50] + "..." if len(description) > 50 else description
                response += f"    📝 {html.escape(desc_short)}\n"
            
            response += "\n"
    
    await bot.send_message(callback_query.from_user.id, response, parse_mode='HTML')
    await callback_query.answer()

@dp.callback_query_handler(lambda c: c.data == 'create_shared_plan')
async def create_shared_plan_start(callback_query: types.CallbackQuery):
    """Создание общего плана"""
    await AddPlan.waiting_for_title.set()
    await bot.send_message(callback_query.from_user.id,
                          "📝 Введите название общего плана:\n\n"
                          "Для отмены отправьте 'отмена' или 'cancel'")
    await callback_query.answer()

@dp.callback_query_handler(lambda c: c.data == 'show_personal_plans')
async def show_personal_plans(callback_query: types.CallbackQuery):
    """Показать личные планы"""
    plans = get_user_plans(callback_query.from_user.id)
    
    if not plans:
        await bot.send_message(callback_query.from_user.id,
                              "📅 У вас нет личных планов",
                              reply_markup=get_shared_plans_keyboard())
        return
    
    response = "📅 <b>Ваши личные планы:</b>\n\n"
    
    for plan in plans:
        response += format_plan(plan, include_id=True) + "\n"
    
    await bot.send_message(callback_query.from_user.id, response, parse_mode='HTML')
    await callback_query.answer()

# ========== ОБРАБОТЧИКИ ПОИСКА ==========

@dp.message_handler(lambda message: message.text == '🔍 Поиск')
async def show_search_menu(message: types.Message):
    """Показать меню поиска"""
    if not is_authorized_user(message.from_user.id):
        return
    
    await message.answer("🔍 <b>Поиск записей:</b>\n\n"
                        "Выберите тип поиска:",
                        parse_mode='HTML',
                        reply_markup=get_search_keyboard())

@dp.callback_query_handler(lambda c: c.data.startswith('search_'))
async def process_search_menu(callback_query: types.CallbackQuery, state: FSMContext):
    """Обработка меню поиска"""
    action = callback_query.data[7:]  # Убираем 'search_'
    user_id = callback_query.from_user.id
    
    if action == 'expenses':
        await bot.send_message(user_id,
                              "🔍 <b>Поиск расходов:</b>\n\n"
                              "Выберите тип поиска:",
                              parse_mode='HTML',
                              reply_markup=get_search_filters_keyboard('expenses'))
    
    elif action == 'incomes':
        await bot.send_message(user_id,
                              "🔍 <b>Поиск доходов:</b>\n\n"
                              "Выберите тип поиска:",
                              parse_mode='HTML',
                              reply_markup=get_search_filters_keyboard('incomes'))
    
    elif action == 'plans':
        await bot.send_message(user_id,
                              "🔍 <b>Поиск планов:</b>\n\n"
                              "Выберите тип поиска:",
                              parse_mode='HTML',
                              reply_markup=get_search_filters_keyboard('plans'))
    
    elif action == 'purchases':
        await bot.send_message(user_id,
                              "🔍 <b>Поиск покупок:</b>\n\n"
                              "Выберите тип поиска:",
                              parse_mode='HTML',
                              reply_markup=get_search_filters_keyboard('purchases'))
    
    elif action == 'show_recent':
        # Показать последние записи всех типов
        await show_recent_all(user_id)
    
    await callback_query.answer()

async def show_recent_all(user_id):
    """Показать последние записи всех типов"""
    # Последние 5 расходов
    recent_expenses = get_user_transactions(user_id, 'all', 'expense')[:5]
    # Последние 5 доходов
    recent_incomes = get_user_transactions(user_id, 'all', 'income')[:5]
    # Последние 5 планов
    recent_plans = get_user_plans(user_id)
    # Последние 5 покупок
    recent_purchases = get_user_purchases(user_id)
    
    response = "📋 <b>Последние записи:</b>\n\n"
    
    if recent_expenses:
        response += "💸 <b>Последние расходы:</b>\n"
        for trans in recent_expenses[:3]:  # Показываем только 3
            if len(trans) >= 6:
                amount = trans[2]
                category = trans[3]
                description = trans[4]
                date_str = trans[5] if len(trans) > 5 else "сегодня"
                
                desc = f" - {description}" if description else ""
                response += f"  • {amount:.2f} руб. - {category}{desc} ({date_str})\n"
        response += "\n"
    
    if recent_incomes:
        response += "💵 <b>Последние доходы:</b>\n"
        for trans in recent_incomes[:3]:
            if len(trans) >= 6:
                amount = trans[2]
                category = trans[3]
                description = trans[4]
                date_str = trans[5] if len(trans) > 5 else "сегодня"
                
                desc = f" - {description}" if description else ""
                response += f"  • {amount:.2f} руб. - {category}{desc} ({date_str})\n"
        response += "\n"
    
    if recent_plans:
        response += "📅 <b>Ближайшие планы:</b>\n"
        for plan in recent_plans[:3]:
            if len(plan) >= 7:
                title = plan[1]
                date = plan[3]
                time = plan[4]
                time_str = f" в {time}" if time else ""
                response += f"  • {title} ({date}{time_str})\n"
        response += "\n"
    
    if recent_purchases:
        response += "🛍️ <b>Планируемые покупки:</b>\n"
        for purchase in recent_purchases[:3]:
            if len(purchase) >= 7:
                item_name = purchase[1]
                cost = purchase[2]
                priority = purchase[3]
                emoji = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}[priority]
                response += f"  • {emoji} {item_name} - {cost:.2f} руб.\n"
    
    await bot.send_message(user_id, response, parse_mode='HTML')

# ========== ПОИСК РАСХОДОВ/ДОХОДОВ ==========

@dp.callback_query_handler(lambda c: c.data.startswith('search_expenses_by_') or c.data.startswith('search_incomes_by_'))
async def start_search_transactions(callback_query: types.CallbackQuery, state: FSMContext):
    """Начало поиска транзакций"""
    data = callback_query.data[7:]  # Убираем 'search_'
    user_id = callback_query.from_user.id
    
    # Определяем тип транзакции
    if data.startswith('expenses_by_'):
        trans_type = 'expense'
        search_type = data[12:]  # Убираем 'expenses_by_'
    else:
        trans_type = 'income'
        search_type = data[11:]  # Убираем 'incomes_by_'
    
    await state.update_data(trans_type=trans_type, search_type=search_type)
    
    if search_type == 'desc':
        await SearchStates.waiting_for_description.set()
        await bot.send_message(user_id, "📝 Введите текст для поиска в описании:")
    
    elif search_type == 'cat':
        await SearchStates.waiting_for_category.set()
        if trans_type == 'expense':
            await bot.send_message(user_id, "📂 Выберите категорию для поиска:",
                                  reply_markup=get_expense_categories_keyboard())
        else:
            await bot.send_message(user_id, "📂 Выберите категорию для поиска:",
                                  reply_markup=get_income_categories_keyboard())
    
    elif search_type == 'amount':
        await SearchStates.waiting_for_min_amount.set()
        await bot.send_message(user_id, "💰 Введите минимальную сумму (или '-' для пропуска):")
    
    elif search_type == 'date':
        await SearchStates.waiting_for_date.set()
        await bot.send_message(user_id, "📅 Введите дату для поиска (ГГГГ-ММ-ДД, 'сегодня', 'неделя', 'месяц'):")
    
    await callback_query.answer()

@dp.message_handler(state=SearchStates.waiting_for_description)
async def search_by_description(message: types.Message, state: FSMContext):
    """Поиск по описанию"""
    text = message.text.lower()
    if text in ['отмена', 'cancel', 'стоп', 'отменить']:
        await state.finish()
        await message.answer("❌ Поиск отменен", reply_markup=get_main_keyboard())
        return
    
    data = await state.get_data()
    trans_type = data.get('trans_type')
    
    results = search_transactions(
        user_id=message.from_user.id,
        trans_type=trans_type,
        description=text
    )
    
    await show_search_results(message, results, f"результатов по описанию '{text}'", trans_type)
    await state.finish()

@dp.callback_query_handler(lambda c: c.data.startswith('expense_cat_') or c.data.startswith('income_cat_'), 
                          state=SearchStates.waiting_for_category)
async def search_by_category_callback(callback_query: types.CallbackQuery, state: FSMContext):
    """Поиск по категории (callback)"""
    data = await state.get_data()
    trans_type = data.get('trans_type')
    
    if trans_type == 'expense':
        category = callback_query.data[11:]  # Убираем 'expense_cat_'
    else:
        category = callback_query.data[10:]  # Убираем 'income_cat_'
    
    results = search_transactions(
        user_id=callback_query.from_user.id,
        trans_type=trans_type,
        category=category
    )
    
    await show_search_results_chat(callback_query.from_user.id, results, 
                                 f"результатов в категории '{category}'", trans_type)
    await state.finish()
    await callback_query.answer()

@dp.message_handler(state=SearchStates.waiting_for_category)
async def search_by_category_message(message: types.Message, state: FSMContext):
    """Обработка текстового ввода для категории"""
    text = message.text.lower()
    if text in ['отмена', 'cancel', 'стоп', 'отменить']:
        await state.finish()
        await message.answer("❌ Поиск отменен", reply_markup=get_main_keyboard())
        return
    
    data = await state.get_data()
    trans_type = data.get('trans_type')
    
    results = search_transactions(
        user_id=message.from_user.id,
        trans_type=trans_type,
        category=text
    )
    
    await show_search_results(message, results, f"результатов в категории '{text}'", trans_type)
    await state.finish()

@dp.message_handler(state=SearchStates.waiting_for_min_amount)
async def search_by_min_amount(message: types.Message, state: FSMContext):
    """Поиск по минимальной сумме"""
    text = message.text.lower()
    if text in ['отмена', 'cancel', 'стоп', 'отменить']:
        await state.finish()
        await message.answer("❌ Поиск отменен", reply_markup=get_main_keyboard())
        return
    
    data = await state.get_data()
    
    if text == '-':
        min_amount = None
    else:
        try:
            min_amount = float(text.replace(',', '.'))
        except ValueError:
            await message.answer("❌ Неверный формат суммы. Введите число или '-'")
            return
    
    await state.update_data(min_amount=min_amount)
    await SearchStates.waiting_for_max_amount.set()
    await message.answer("💰 Введите максимальную сумму (или '-' для пропуска):")

@dp.message_handler(state=SearchStates.waiting_for_max_amount)
async def search_by_max_amount(message: types.Message, state: FSMContext):
    """Поиск по максимальной сумме"""
    text = message.text.lower()
    if text in ['отмена', 'cancel', 'стоп', 'отменить']:
        await state.finish()
        await message.answer("❌ Поиск отменен", reply_markup=get_main_keyboard())
        return
    
    data = await state.get_data()
    trans_type = data.get('trans_type')
    min_amount = data.get('min_amount')
    
    if text == '-':
        max_amount = None
    else:
        try:
            max_amount = float(text.replace(',', '.'))
        except ValueError:
            await message.answer("❌ Неверный формат суммы. Введите число или '-'")
            return
    
    results = search_transactions(
        user_id=message.from_user.id,
        trans_type=trans_type,
        min_amount=min_amount,
        max_amount=max_amount
    )
    
    range_text = ""
    if min_amount is not None:
        range_text += f"от {min_amount} руб. "
    if max_amount is not None:
        range_text += f"до {max_amount} руб."
    
    await show_search_results(message, results, f"результатов в диапазоне {range_text}", trans_type)
    await state.finish()

@dp.message_handler(state=SearchStates.waiting_for_date)
async def search_by_date(message: types.Message, state: FSMContext):
    """Поиск по дате"""
    text = message.text.lower()
    if text in ['отмена', 'cancel', 'стоп', 'отменить']:
        await state.finish()
        await message.answer("❌ Поиск отменен", reply_markup=get_main_keyboard())
        return
    
    data = await state.get_data()
    trans_type = data.get('trans_type')
    
    results = search_transactions(
        user_id=message.from_user.id,
        trans_type=trans_type,
        date_filter=text
    )
    
    await show_search_results(message, results, f"результатов за '{text}'", trans_type)
    await state.finish()

# ========== ПОИСК ПЛАНОВ ==========

@dp.callback_query_handler(lambda c: c.data.startswith('search_plans_'))
async def start_search_plans(callback_query: types.CallbackQuery, state: FSMContext):
    """Начало поиска планов"""
    search_type = callback_query.data[13:]  # Убираем 'search_plans_'
    user_id = callback_query.from_user.id
    
    await state.update_data(search_type=search_type)
    
    if search_type == 'by_text':
        await SearchPlanStates.waiting_for_text.set()
        await bot.send_message(user_id, "📝 Введите текст для поиска в названии или описании:")
    
    elif search_type == 'by_cat':
        await SearchPlanStates.waiting_for_category.set()
        await bot.send_message(user_id, "🏷️ Выберите категорию для поиска:",
                              reply_markup=get_plan_categories_keyboard())
    
    elif search_type == 'by_date':
        await SearchPlanStates.waiting_for_date_from.set()
        await bot.send_message(user_id, "📅 Введите начальную дату (ГГГГ-ММ-ДД или '-'):")
    
    elif search_type == 'shared':
        # Поиск только общих планов
        results = search_plans(
            user_id=user_id,
            is_shared=True
        )
        await show_plan_search_results(user_id, results, "общих планов")
    
    await callback_query.answer()

@dp.message_handler(state=SearchPlanStates.waiting_for_text)
async def search_plans_by_text(message: types.Message, state: FSMContext):
    """Поиск планов по тексту"""
    text = message.text.lower()
    if text in ['отмена', 'cancel', 'стоп', 'отменить']:
        await state.finish()
        await message.answer("❌ Поиск отменен", reply_markup=get_main_keyboard())
        return
    
    results = search_plans(
        user_id=message.from_user.id,
        search_text=text
    )
    
    await show_plan_search_results(message.from_user.id, results, f"результатов по тексту '{text}'")
    await state.finish()

@dp.callback_query_handler(lambda c: c.data.startswith('plan_cat_'), state=SearchPlanStates.waiting_for_category)
async def search_plans_by_category_callback(callback_query: types.CallbackQuery, state: FSMContext):
    """Поиск планов по категории (callback)"""
    category = callback_query.data[9:]  # Убираем 'plan_cat_'
    
    results = search_plans(
        user_id=callback_query.from_user.id,
        category=category
    )
    
    await show_plan_search_results_chat(callback_query.from_user.id, results, 
                                       f"результатов в категории '{category}'")
    await state.finish()
    await callback_query.answer()

@dp.message_handler(state=SearchPlanStates.waiting_for_category)
async def search_plans_by_category_message(message: types.Message, state: FSMContext):
    """Поиск планов по категории (текст)"""
    text = message.text.lower()
    if text in ['отмена', 'cancel', 'стоп', 'отменить']:
        await state.finish()
        await message.answer("❌ Поиск отменен", reply_markup=get_main_keyboard())
        return
    
    results = search_plans(
        user_id=message.from_user.id,
        category=text
    )
    
    await show_plan_search_results(message.from_user.id, results, f"результатов в категории '{text}'")
    await state.finish()

@dp.message_handler(state=SearchPlanStates.waiting_for_date_from)
async def search_plans_by_date_from(message: types.Message, state: FSMContext):
    """Поиск планов по начальной дате"""
    text = message.text.lower()
    if text in ['отмена', 'cancel', 'стоп', 'отменить']:
        await state.finish()
        await message.answer("❌ Поиск отменен", reply_markup=get_main_keyboard())
        return
    
    if text == '-':
        date_from = None
    else:
        date_from = text
    
    await state.update_data(date_from=date_from)
    await SearchPlanStates.waiting_for_date_to.set()
    await message.answer("📅 Введите конечную дату (ГГГГ-ММ-ДД или '-'):")

@dp.message_handler(state=SearchPlanStates.waiting_for_date_to)
async def search_plans_by_date_to(message: types.Message, state: FSMContext):
    """Поиск планов по конечной дате"""
    text = message.text.lower()
    if text in ['отмена', 'cancel', 'стоп', 'отменить']:
        await state.finish()
        await message.answer("❌ Поиск отменен", reply_markup=get_main_keyboard())
        return
    
    data = await state.get_data()
    date_from = data.get('date_from')
    
    if text == '-':
        date_to = None
    else:
        date_to = text
    
    results = search_plans(
        user_id=message.from_user.id,
        date_from=date_from,
        date_to=date_to
    )
    
    date_range = ""
    if date_from:
        date_range += f"с {date_from} "
    if date_to:
        date_range += f"по {date_to}"
    
    await show_plan_search_results(message.from_user.id, results, f"результатов за период {date_range}")
    await state.finish()

# ========== ПОИСК ПОКУПОК ==========

@dp.callback_query_handler(lambda c: c.data.startswith('search_purchases_'))
async def start_search_purchases(callback_query: types.CallbackQuery, state: FSMContext):
    """Начало поиска покупок"""
    search_type = callback_query.data[17:]  # Убираем 'search_purchases_'
    user_id = callback_query.from_user.id
    
    await state.update_data(search_type=search_type)
    
    if search_type == 'by_text':
        await SearchPurchaseStates.waiting_for_text.set()
        await bot.send_message(user_id, "📝 Введите текст для поиска в названии или заметках:")
    
    elif search_type == 'by_priority':
        await SearchPurchaseStates.waiting_for_priority.set()
        await bot.send_message(user_id, "🎯 Выберите приоритет для поиска:",
                              reply_markup=get_priority_keyboard())
    
    elif search_type == 'by_cost':
        await SearchPurchaseStates.waiting_for_min_cost.set()
        await bot.send_message(user_id, "💰 Введите минимальную стоимость (или '-' для пропуска):")
    
    elif search_type == 'by_status':
        # Поиск по статусу
        keyboard = InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            InlineKeyboardButton('✅ Купленные', callback_data='search_status_bought'),
            InlineKeyboardButton('📋 Планируемые', callback_data='search_status_planned')
        )
        keyboard.add(InlineKeyboardButton('🔙 Назад', callback_data='back_to_search'))
        
        await bot.send_message(user_id, "📋 Выберите статус покупок:", reply_markup=keyboard)
    
    await callback_query.answer()

@dp.message_handler(state=SearchPurchaseStates.waiting_for_text)
async def search_purchases_by_text(message: types.Message, state: FSMContext):
    """Поиск покупок по тексту"""
    text = message.text.lower()
    if text in ['отмена', 'cancel', 'стоп', 'отменить']:
        await state.finish()
        await message.answer("❌ Поиск отменен", reply_markup=get_main_keyboard())
        return
    
    results = search_purchases(
        user_id=message.from_user.id,
        search_text=text
    )
    
    await show_purchase_search_results(message.from_user.id, results, f"результатов по тексту '{text}'")
    await state.finish()

@dp.callback_query_handler(lambda c: c.data.startswith('priority_'), state=SearchPurchaseStates.waiting_for_priority)
async def search_purchases_by_priority_callback(callback_query: types.CallbackQuery, state: FSMContext):
    """Поиск покупок по приоритету (callback)"""
    priority = callback_query.data[9:]  # Убираем 'priority_'
    
    results = search_purchases(
        user_id=callback_query.from_user.id,
        priority=priority
    )
    
    await show_purchase_search_results_chat(callback_query.from_user.id, results, 
                                           f"результатов с приоритетом '{priority}'")
    await state.finish()
    await callback_query.answer()

@dp.callback_query_handler(lambda c: c.data.startswith('search_status_'))
async def search_purchases_by_status(callback_query: types.CallbackQuery):
    """Поиск покупок по статусу"""
    status = callback_query.data[13:]  # Убираем 'search_status_'
    
    results = search_purchases(
        user_id=callback_query.from_user.id,
        status=status
    )
    
    status_text = 'купленные' if status == 'bought' else 'планируемые'
    await show_purchase_search_results_chat(callback_query.from_user.id, results, 
                                           f"{status_text} покупок")
    await callback_query.answer()

@dp.message_handler(state=SearchPurchaseStates.waiting_for_min_cost)
async def search_purchases_by_min_cost(message: types.Message, state: FSMContext):
    """Поиск покупок по минимальной стоимости"""
    text = message.text.lower()
    if text in ['отмена', 'cancel', 'стоп', 'отменить']:
        await state.finish()
        await message.answer("❌ Поиск отменен", reply_markup=get_main_keyboard())
        return
    
    if text == '-':
        min_cost = None
    else:
        try:
            min_cost = float(text.replace(',', '.'))
        except ValueError:
            await message.answer("❌ Неверный формат суммы. Введите число или '-'")
            return
    
    await state.update_data(min_cost=min_cost)
    await SearchPurchaseStates.waiting_for_max_cost.set()
    await message.answer("💰 Введите максимальную стоимость (или '-' для пропуска):")

@dp.message_handler(state=SearchPurchaseStates.waiting_for_max_cost)
async def search_purchases_by_max_cost(message: types.Message, state: FSMContext):
    """Поиск покупок по максимальной стоимости"""
    text = message.text.lower()
    if text in ['отмена', 'cancel', 'стоп', 'отменить']:
        await state.finish()
        await message.answer("❌ Поиск отменен", reply_markup=get_main_keyboard())
        return
    
    data = await state.get_data()
    min_cost = data.get('min_cost')
    
    if text == '-':
        max_cost = None
    else:
        try:
            max_cost = float(text.replace(',', '.'))
        except ValueError:
            await message.answer("❌ Неверный формат суммы. Введите число или '-'")
            return
    
    results = search_purchases(
        user_id=message.from_user.id,
        min_cost=min_cost,
        max_cost=max_cost
    )
    
    range_text = ""
    if min_cost is not None:
        range_text += f"от {min_cost} руб. "
    if max_cost is not None:
        range_text += f"до {max_cost} руб."
    
    await show_purchase_search_results(message.from_user.id, results, f"результатов в диапазоне {range_text}")
    await state.finish()

# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ ПОИСКА ==========

async def show_search_results(message_or_chat_id, results, description, trans_type):
    """Показать результаты поиска транзакций"""
    if isinstance(message_or_chat_id, types.Message):
        chat_id = message_or_chat_id.from_user.id
    else:
        chat_id = message_or_chat_id
    
    if not results:
        await bot.send_message(chat_id, f"🔍 <b>Нет {description}</b>", parse_mode='HTML')
        return
    
    type_text = "расходов" if trans_type == 'expense' else "доходов"
    response = f"🔍 <b>Найдено {len(results)} {type_text} {description}:</b>\n\n"
    
    for trans in results:
        if len(trans) >= 6:
            trans_id, trans_type_db, amount, category, description_text, trans_date, time = trans[:7]
            time_str = f" ({time})" if time else ""
            
            response += f"💰 <b>{amount:.2f} руб.</b> - {category}\n"
            response += f"   📅 {trans_date}{time_str}\n"
            if description_text:
                response += f"   📝 {html.escape(description_text)}\n"
            response += f"   🆔 ID: {trans_id}\n\n"
    
    if len(response) > 4000:
        # Разделяем на части если сообщение слишком длинное
        parts = [response[i:i+4000] for i in range(0, len(response), 4000)]
        for part in parts:
            await bot.send_message(chat_id, part, parse_mode='HTML')
    else:
        await bot.send_message(chat_id, response, parse_mode='HTML')

async def show_search_results_chat(chat_id, results, description, trans_type):
    """Алиас для show_search_results с chat_id"""
    await show_search_results(chat_id, results, description, trans_type)

async def show_plan_search_results(chat_id, results, description):
    """Показать результаты поиска планов"""
    if not results:
        await bot.send_message(chat_id, f"🔍 <b>Нет {description}</b>", parse_mode='HTML')
        return
    
    response = f"🔍 <b>Найдено {len(results)} планов {description}:</b>\n\n"
    
    for plan in results:
        if len(plan) >= 7:
            plan_id, title, description_text, plan_date, time, category, is_shared = plan[:7]
            time_str = f" в {time}" if time else ""
            shared_icon = " 👥" if is_shared else ""
            
            response += f"📅 <b>{html.escape(title)}</b>{shared_icon}\n"
            response += f"   📅 Дата: {plan_date}{time_str}\n"
            response += f"   🏷️ Категория: {html.escape(category)}\n"
            if description_text:
                response += f"   📋 Описание: {html.escape(description_text)}\n"
            response += f"   🆔 ID: {plan_id}\n\n"
    
    if len(response) > 4000:
        parts = [response[i:i+4000] for i in range(0, len(response), 4000)]
        for part in parts:
            await bot.send_message(chat_id, part, parse_mode='HTML')
    else:
        await bot.send_message(chat_id, response, parse_mode='HTML')

async def show_plan_search_results_chat(chat_id, results, description):
    """Алиас для show_plan_search_results"""
    await show_plan_search_results(chat_id, results, description)

async def show_purchase_search_results(chat_id, results, description):
    """Показать результаты поиска покупок"""
    if not results:
        await bot.send_message(chat_id, f"🔍 <b>Нет {description}</b>", parse_mode='HTML')
        return
    
    response = f"🔍 <b>Найдено {len(results)} покупок {description}:</b>\n\n"
    
    for purchase in results:
        if len(purchase) >= 7:
            purchase_id, item_name, cost, priority, target_date, notes, status = purchase[:7]
            emoji = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}[priority]
            date_str = f"до {target_date}" if target_date else ""
            status_emoji = "✅" if status == 'bought' else "📋"
            
            response += f"{emoji} <b>{html.escape(item_name)}</b> {status_emoji}\n"
            response += f"   💰 Стоимость: {cost:.2f} руб.\n"
            if date_str:
                response += f"   📅 {date_str}\n"
            if notes:
                response += f"   📝 Заметки: {html.escape(notes)}\n"
            response += f"   🆔 ID: {purchase_id}\n\n"
    
    if len(response) > 4000:
        parts = [response[i:i+4000] for i in range(0, len(response), 4000)]
        for part in parts:
            await bot.send_message(chat_id, part, parse_mode='HTML')
    else:
        await bot.send_message(chat_id, response, parse_mode='HTML')

async def show_purchase_search_results_chat(chat_id, results, description):
    """Алиас для show_purchase_search_results"""
    await show_purchase_search_results(chat_id, results, description)

# ========== ОБРАБОТЧИКИ СОСТОЯНИЙ РЕДАКТИРОВАНИЯ ==========

# Редактирование расходов
@dp.message_handler(state=EditExpense.waiting_for_amount)
async def edit_expense_amount(message: types.Message, state: FSMContext):
    """Редактирование суммы расхода"""
    text = message.text.lower()
    if text in ['отмена', 'cancel', 'стоп', 'отменить']:
        await state.finish()
        await message.answer("❌ Редактирование отменено", reply_markup=get_main_keyboard())
        return
    
    try:
        amount = float(text.replace(',', '.'))
        if amount <= 0:
            await message.answer("❌ Сумма должна быть больше 0")
            return
        
        data = await state.get_data()
        trans_id = data.get('trans_id')
        
        update_transaction(trans_id, amount=amount)
        
        transaction = get_transaction(trans_id)
        await message.answer(f"✅ Сумма расхода обновлена!\n\n"
                           f"{format_transaction(transaction, include_id=True)}",
                           parse_mode='HTML',
                           reply_markup=get_edit_transaction_keyboard(trans_id, 'expense'))
        await state.finish()
    
    except ValueError:
        await message.answer("❌ Пожалуйста, введите корректную сумму")

@dp.callback_query_handler(lambda c: c.data.startswith('expense_cat_'), state=EditExpense.waiting_for_category)
async def edit_expense_category(callback_query: types.CallbackQuery, state: FSMContext):
    """Редактирование категории расхода"""
    category = callback_query.data[11:]  # Убираем 'expense_cat_'
    
    data = await state.get_data()
    trans_id = data.get('trans_id')
    
    update_transaction(trans_id, category=category)
    
    transaction = get_transaction(trans_id)
    await bot.send_message(callback_query.from_user.id,
                          f"✅ Категория расхода обновлена!\n\n"
                          f"{format_transaction(transaction, include_id=True)}",
                          parse_mode='HTML',
                          reply_markup=get_edit_transaction_keyboard(trans_id, 'expense'))
    await state.finish()
    await callback_query.answer()

@dp.message_handler(state=EditExpense.waiting_for_category)
async def cancel_edit_expense_category(message: types.Message, state: FSMContext):
    """Отмена выбора категории при редактировании расхода"""
    text = message.text.lower()
    if text in ['отмена', 'cancel', 'стоп', 'отменить']:
        await state.finish()
        await message.answer("❌ Редактирование отменено", reply_markup=get_main_keyboard())
    else:
        await message.answer("Пожалуйста, выберите категорию из предложенных кнопок.")

@dp.message_handler(state=EditExpense.waiting_for_description)
async def edit_expense_description(message: types.Message, state: FSMContext):
    """Редактирование описания расхода"""
    text = message.text.lower()
    if text in ['отмена', 'cancel', 'стоп', 'отменить']:
        await state.finish()
        await message.answer("❌ Редактирование отменено", reply_markup=get_main_keyboard())
        return
    
    data = await state.get_data()
    trans_id = data.get('trans_id')
    
    description = message.text if message.text != '-' else None
    update_transaction(trans_id, description=description)
    
    transaction = get_transaction(trans_id)
    await message.answer(f"✅ Описание расхода обновлено!\n\n"
                       f"{format_transaction(transaction, include_id=True)}",
                       parse_mode='HTML',
                       reply_markup=get_edit_transaction_keyboard(trans_id, 'expense'))
    await state.finish()

# Редактирование доходов
@dp.message_handler(state=EditIncome.waiting_for_amount)
async def edit_income_amount(message: types.Message, state: FSMContext):
    """Редактирование суммы дохода"""
    text = message.text.lower()
    if text in ['отмена', 'cancel', 'стоп', 'отменить']:
        await state.finish()
        await message.answer("❌ Редактирование отменено", reply_markup=get_main_keyboard())
        return
    
    try:
        amount = float(text.replace(',', '.'))
        if amount <= 0:
            await message.answer("❌ Сумма должна быть больше 0")
            return
        
        data = await state.get_data()
        trans_id = data.get('trans_id')
        
        update_transaction(trans_id, amount=amount)
        
        transaction = get_transaction(trans_id)
        await message.answer(f"✅ Сумма дохода обновлена!\n\n"
                           f"{format_transaction(transaction, include_id=True)}",
                           parse_mode='HTML',
                           reply_markup=get_edit_transaction_keyboard(trans_id, 'income'))
        await state.finish()
    
    except ValueError:
        await message.answer("❌ Пожалуйста, введите корректную сумму")

@dp.callback_query_handler(lambda c: c.data.startswith('income_cat_'), state=EditIncome.waiting_for_category)
async def edit_income_category(callback_query: types.CallbackQuery, state: FSMContext):
    """Редактирование категории дохода"""
    category = callback_query.data[10:]  # Убираем 'income_cat_'
    
    data = await state.get_data()
    trans_id = data.get('trans_id')
    
    update_transaction(trans_id, category=category)
    
    transaction = get_transaction(trans_id)
    await bot.send_message(callback_query.from_user.id,
                          f"✅ Категория дохода обновлена!\n\n"
                          f"{format_transaction(transaction, include_id=True)}",
                          parse_mode='HTML',
                          reply_markup=get_edit_transaction_keyboard(trans_id, 'income'))
    await state.finish()
    await callback_query.answer()

@dp.message_handler(state=EditIncome.waiting_for_category)
async def cancel_edit_income_category(message: types.Message, state: FSMContext):
    """Отмена выбора категории при редактировании дохода"""
    text = message.text.lower()
    if text in ['отмена', 'cancel', 'стоп', 'отменить']:
        await state.finish()
        await message.answer("❌ Редактирование отменено", reply_markup=get_main_keyboard())
    else:
        await message.answer("Пожалуйста, выберите категорию из предложенных кнопок.")

@dp.message_handler(state=EditIncome.waiting_for_description)
async def edit_income_description(message: types.Message, state: FSMContext):
    """Редактирование описания дохода"""
    text = message.text.lower()
    if text in ['отмена', 'cancel', 'стоп', 'отменить']:
        await state.finish()
        await message.answer("❌ Редактирование отменено", reply_markup=get_main_keyboard())
        return
    
    data = await state.get_data()
    trans_id = data.get('trans_id')
    
    description = message.text if message.text != '-' else None
    update_transaction(trans_id, description=description)
    
    transaction = get_transaction(trans_id)
    await message.answer(f"✅ Описание дохода обновлено!\n\n"
                       f"{format_transaction(transaction, include_id=True)}",
                       parse_mode='HTML',
                       reply_markup=get_edit_transaction_keyboard(trans_id, 'income'))
    await state.finish()

# Редактирование планов
@dp.message_handler(state=EditPlan.waiting_for_title)
async def edit_plan_title(message: types.Message, state: FSMContext):
    """Редактирование названия плана"""
    text = message.text.lower()
    if text in ['отмена', 'cancel', 'стоп', 'отменить']:
        await state.finish()
        await message.answer("❌ Редактирование отменено", reply_markup=get_main_keyboard())
        return
    
    data = await state.get_data()
    plan_id = data.get('plan_id')
    
    update_plan(plan_id, title=message.text)
    
    plan = get_plan(plan_id)
    await message.answer(f"✅ Название плана обновлено!\n\n"
                       f"{format_plan(plan, include_id=True)}",
                       parse_mode='HTML',
                       reply_markup=get_edit_plan_keyboard(plan_id))
    await state.finish()

@dp.message_handler(state=EditPlan.waiting_for_description)
async def edit_plan_description(message: types.Message, state: FSMContext):
    """Редактирование описания плана"""
    text = message.text.lower()
    if text in ['отмена', 'cancel', 'стоп', 'отменить']:
        await state.finish()
        await message.answer("❌ Редактирование отменено", reply_markup=get_main_keyboard())
        return
    
    data = await state.get_data()
    plan_id = data.get('plan_id')
    
    description = message.text if message.text != '-' else None
    update_plan(plan_id, description=description)
    
    plan = get_plan(plan_id)
    await message.answer(f"✅ Описание плана обновлено!\n\n"
                       f"{format_plan(plan, include_id=True)}",
                       parse_mode='HTML',
                       reply_markup=get_edit_plan_keyboard(plan_id))
    await state.finish()

@dp.message_handler(state=EditPlan.waiting_for_date)
async def edit_plan_date(message: types.Message, state: FSMContext):
    """Редактирование даты плана"""
    text = message.text.lower()
    if text in ['отмена', 'cancel', 'стоп', 'отменить']:
        await state.finish()
        await message.answer("❌ Редактирование отменено", reply_markup=get_main_keyboard())
        return
    
    data = await state.get_data()
    plan_id = data.get('plan_id')
    
    date_str = text
    
    if date_str == 'сегодня':
        new_date = date.today().isoformat()
    elif date_str == 'завтра':
        new_date = (date.today() + timedelta(days=1)).isoformat()
    else:
        try:
            datetime.strptime(date_str, '%Y-%m-%d')
            new_date = date_str
        except ValueError:
            await message.answer("❌ Неверный формат даты. Используйте ГГГГ-ММ-ДД")
            return
    
    update_plan(plan_id, date=new_date)
    
    plan = get_plan(plan_id)
    await message.answer(f"✅ Дата плана обновлена!\n\n"
                       f"{format_plan(plan, include_id=True)}",
                       parse_mode='HTML',
                       reply_markup=get_edit_plan_keyboard(plan_id))
    await state.finish()

@dp.message_handler(state=EditPlan.waiting_for_time)
async def edit_plan_time(message: types.Message, state: FSMContext):
    """Редактирование времени плана"""
    text = message.text.lower()
    if text in ['отмена', 'cancel', 'стоп', 'отменить']:
        await state.finish()
        await message.answer("❌ Редактирование отменено", reply_markup=get_main_keyboard())
        return
    
    data = await state.get_data()
    plan_id = data.get('plan_id')
    
    time_str = message.text if message.text != '-' else None
    
    if time_str and time_str != '-':
        try:
            datetime.strptime(time_str, '%H:%M')
        except ValueError:
            await message.answer("❌ Неверный формат времени. Используйте ЧЧ:ММ")
            return
    
    update_plan(plan_id, time=time_str)
    
    plan = get_plan(plan_id)
    await message.answer(f"✅ Время плана обновлено!\n\n"
                       f"{format_plan(plan, include_id=True)}",
                       parse_mode='HTML',
                       reply_markup=get_edit_plan_keyboard(plan_id))
    await state.finish()

@dp.callback_query_handler(lambda c: c.data.startswith('plan_cat_'), state=EditPlan.waiting_for_category)
async def edit_plan_category(callback_query: types.CallbackQuery, state: FSMContext):
    """Редактирование категории плана"""
    category = callback_query.data[9:]  # Убираем 'plan_cat_'
    
    data = await state.get_data()
    plan_id = data.get('plan_id')
    
    update_plan(plan_id, category=category)
    
    plan = get_plan(plan_id)
    await bot.send_message(callback_query.from_user.id,
                          f"✅ Категория плана обновлена!\n\n"
                          f"{format_plan(plan, include_id=True)}",
                          parse_mode='HTML',
                          reply_markup=get_edit_plan_keyboard(plan_id))
    await state.finish()
    await callback_query.answer()

@dp.message_handler(state=EditPlan.waiting_for_category)
async def cancel_edit_plan_category(message: types.Message, state: FSMContext):
    """Отмена выбора категории при редактировании плана"""
    text = message.text.lower()
    if text in ['отмена', 'cancel', 'стоп', 'отменить']:
        await state.finish()
        await message.answer("❌ Редактирование отменено", reply_markup=get_main_keyboard())
    else:
        await message.answer("Пожалуйста, выберите категорию из предложенных кнопок.")

# Редактирование покупок
@dp.message_handler(state=EditPurchase.waiting_for_name)
async def edit_purchase_name(message: types.Message, state: FSMContext):
    """Редактирование названия покупки"""
    text = message.text.lower()
    if text in ['отмена', 'cancel', 'стоп', 'отменить']:
        await state.finish()
        await message.answer("❌ Редактирование отменено", reply_markup=get_main_keyboard())
        return
    
    data = await state.get_data()
    purchase_id = data.get('purchase_id')
    
    update_purchase(purchase_id, item_name=message.text)
    
    purchase = get_purchase(purchase_id)
    await message.answer(f"✅ Название покупки обновлено!\n\n"
                       f"{format_purchase(purchase, include_id=True)}",
                       parse_mode='HTML',
                       reply_markup=get_edit_purchase_keyboard(purchase_id))
    await state.finish()

@dp.message_handler(state=EditPurchase.waiting_for_cost)
async def edit_purchase_cost(message: types.Message, state: FSMContext):
    """Редактирование стоимости покупки"""
    text = message.text.lower()
    if text in ['отмена', 'cancel', 'стоп', 'отменить']:
        await state.finish()
        await message.answer("❌ Редактирование отменено", reply_markup=get_main_keyboard())
        return
    
    try:
        cost = float(text.replace(',', '.'))
        if cost <= 0:
            await message.answer("❌ Стоимость должна быть больше 0")
            return
        
        data = await state.get_data()
        purchase_id = data.get('purchase_id')
        
        update_purchase(purchase_id, estimated_cost=cost)
        
        purchase = get_purchase(purchase_id)
        await message.answer(f"✅ Стоимость покупки обновлена!\n\n"
                           f"{format_purchase(purchase, include_id=True)}",
                           parse_mode='HTML',
                           reply_markup=get_edit_purchase_keyboard(purchase_id))
        await state.finish()
    
    except ValueError:
        await message.answer("❌ Пожалуйста, введите корректную сумму")

@dp.callback_query_handler(lambda c: c.data.startswith('priority_'), state=EditPurchase.waiting_for_priority)
async def edit_purchase_priority(callback_query: types.CallbackQuery, state: FSMContext):
    """Редактирование приоритета покупки"""
    priority = callback_query.data[9:]  # Убираем 'priority_'
    
    data = await state.get_data()
    purchase_id = data.get('purchase_id')
    
    update_purchase(purchase_id, priority=priority)
    
    purchase = get_purchase(purchase_id)
    await bot.send_message(callback_query.from_user.id,
                          f"✅ Приоритет покупки обновлен!\n\n"
                          f"{format_purchase(purchase, include_id=True)}",
                          parse_mode='HTML',
                          reply_markup=get_edit_purchase_keyboard(purchase_id))
    await state.finish()
    await callback_query.answer()

@dp.message_handler(state=EditPurchase.waiting_for_priority)
async def cancel_edit_purchase_priority(message: types.Message, state: FSMContext):
    """Отмена выбора приоритета при редактировании покупки"""
    text = message.text.lower()
    if text in ['отмена', 'cancel', 'стоп', 'отменить']:
        await state.finish()
        await message.answer("❌ Редактирование отменено", reply_markup=get_main_keyboard())
    else:
        await message.answer("Пожалуйста, выберите приоритет из предложенных кнопок.")

@dp.message_handler(state=EditPurchase.waiting_for_date)
async def edit_purchase_date(message: types.Message, state: FSMContext):
    """Редактирование даты покупки"""
    text = message.text.lower()
    if text in ['отмена', 'cancel', 'стоп', 'отменить']:
        await state.finish()
        await message.answer("❌ Редактирование отменено", reply_markup=get_main_keyboard())
        return
    
    data = await state.get_data()
    purchase_id = data.get('purchase_id')
    
    date_str = message.text if message.text != '-' else None
    
    if date_str and date_str != '-':
        try:
            datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError:
            await message.answer("❌ Неверный формат даты. Используйте ГГГГ-ММ-ДД")
            return
    
    update_purchase(purchase_id, target_date=date_str)
    
    purchase = get_purchase(purchase_id)
    await message.answer(f"✅ Дата покупки обновлена!\n\n"
                       f"{format_purchase(purchase, include_id=True)}",
                       parse_mode='HTML',
                       reply_markup=get_edit_purchase_keyboard(purchase_id))
    await state.finish()

@dp.message_handler(state=EditPurchase.waiting_for_notes)
async def edit_purchase_notes(message: types.Message, state: FSMContext):
    """Редактирование заметок покупки"""
    text = message.text.lower()
    if text in ['отмена', 'cancel', 'стоп', 'отменить']:
        await state.finish()
        await message.answer("❌ Редактирование отменено", reply_markup=get_main_keyboard())
        return
    
    data = await state.get_data()
    purchase_id = data.get('purchase_id')
    
    notes = message.text if message.text != '-' else None
    update_purchase(purchase_id, notes=notes)
    
    purchase = get_purchase(purchase_id)
    await message.answer(f"✅ Заметки покупки обновлены!\n\n"
                       f"{format_purchase(purchase, include_id=True)}",
                       parse_mode='HTML',
                       reply_markup=get_edit_purchase_keyboard(purchase_id))
    await state.finish()

# ========== ОБРАБОТЧИКИ ОБЩИХ ПЛАНОВ ==========

@dp.callback_query_handler(lambda c: c.data == 'shared_plans')
async def show_shared_plans_menu(callback_query: types.CallbackQuery):
    """Меню общих планов"""
    await bot.send_message(callback_query.from_user.id,
                          "👥 <b>Общие планы:</b>\n\n"
                          "Выберите действие:",
                          parse_mode='HTML',
                          reply_markup=get_shared_plans_keyboard())
    await callback_query.answer()

@dp.callback_query_handler(lambda c: c.data == 'show_shared_plans')
async def show_all_shared_plans(callback_query: types.CallbackQuery):
    """Показать все общие планы"""
    shared_plans = get_shared_plans()
    
    if not shared_plans:
        await bot.send_message(callback_query.from_user.id,
                              "📅 Нет общих планов",
                              reply_markup=get_shared_plans_keyboard())
        return
    
    response = "👥 <b>Все общие планы:</b>\n\n"
    current_date = None
    
    for plan in shared_plans:
        if len(plan) >= 14:
            plan_date = plan[4]  # date
            title = plan[2]      # title
            description = plan[3] # description
            time = plan[5]       # time
            category = plan[6]   # category
            username = plan[13] or plan[12]  # full_name или username
            
            if plan_date != current_date:
                current_date = plan_date
                response += f"\n<b>📅 {plan_date}:</b>\n"
            
            time_str = f" в {time}" if time else ""
            response += f"  • <b>{html.escape(title)}</b>{time_str}\n"
            response += f"    👤 {username} | 🏷️ {html.escape(category)}\n"
            
            if description:
                desc_short = description[:50] + "..." if len(description) > 50 else description
                response += f"    📝 {html.escape(desc_short)}\n"
            
            response += "\n"
    
    await bot.send_message(callback_query.from_user.id, response, parse_mode='HTML')
    await callback_query.answer()

@dp.callback_query_handler(lambda c: c.data == 'create_shared_plan')
async def create_shared_plan_start(callback_query: types.CallbackQuery):
    """Создание общего плана"""
    await AddPlan.waiting_for_title.set()
    await bot.send_message(callback_query.from_user.id,
                          "📝 Введите название общего плана:\n\n"
                          "Для отмены отправьте 'отмена' или 'cancel'")
    await callback_query.answer()

@dp.callback_query_handler(lambda c: c.data == 'show_personal_plans')
async def show_personal_plans(callback_query: types.CallbackQuery):
    """Показать личные планы"""
    plans = get_user_plans(callback_query.from_user.id)
    
    if not plans:
        await bot.send_message(callback_query.from_user.id,
                              "📅 У вас нет личных планов",
                              reply_markup=get_shared_plans_keyboard())
        return
    
    response = "📅 <b>Ваши личные планы:</b>\n\n"
    
    for plan in plans:
        response += format_plan(plan, include_id=True) + "\n"
    
    await bot.send_message(callback_query.from_user.id, response, parse_mode='HTML')
    await callback_query.answer()

# ========== ДОПОЛНИТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ ПОИСКА ==========

def search_transactions(user_id, trans_type=None, description=None, category=None, 
                       min_amount=None, max_amount=None, date_filter=None):
    """Поиск транзакций по фильтрам"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    query = '''
        SELECT id, type, amount, category, description, date,
               strftime('%H:%M', created_at) as time
        FROM transactions 
        WHERE user_id = ? AND is_deleted = 0
    '''
    params = [user_id]
    
    if trans_type:
        query += " AND type = ?"
        params.append(trans_type)
    
    if description:
        query += " AND description LIKE ?"
        params.append(f'%{description}%')
    
    if category:
        query += " AND category = ?"
        params.append(category)
    
    if min_amount is not None:
        query += " AND amount >= ?"
        params.append(min_amount)
    
    if max_amount is not None:
        query += " AND amount <= ?"
        params.append(max_amount)
    
    if date_filter:
        if date_filter == 'сегодня':
            query += " AND date = DATE('now')"
        elif date_filter == 'неделя':
            query += " AND date >= DATE('now', '-7 days')"
        elif date_filter == 'месяц':
            query += " AND strftime('%Y-%m', date) = strftime('%Y-%m', 'now')"
        else:
            try:
                datetime.strptime(date_filter, '%Y-%m-%d')
                query += " AND date = ?"
                params.append(date_filter)
            except ValueError:
                pass
    
    query += " ORDER BY date DESC, created_at DESC"
    
    cursor.execute(query, params)
    results = cursor.fetchall()
    conn.close()
    
    return results

def search_plans(user_id, search_text=None, category=None, date_from=None, 
                date_to=None, is_shared=None):
    """Поиск планов по фильтрам"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    query = '''
        SELECT id, title, description, date, time, category, is_shared
        FROM plans 
        WHERE user_id = ? AND is_deleted = 0
    '''
    params = [user_id]
    
    if search_text:
        query += " AND (title LIKE ? OR description LIKE ?)"
        params.append(f'%{search_text}%')
        params.append(f'%{search_text}%')
    
    if category:
        query += " AND category = ?"
        params.append(category)
    
    if date_from:
        query += " AND date >= ?"
        params.append(date_from)
    
    if date_to:
        query += " AND date <= ?"
        params.append(date_to)
    
    if is_shared is not None:
        query += " AND is_shared = ?"
        params.append(int(is_shared))
    
    query += " ORDER BY date, time NULLS FIRST"
    
    cursor.execute(query, params)
    results = cursor.fetchall()
    conn.close()
    
    return results

def search_purchases(user_id, search_text=None, priority=None, status=None,
                    min_cost=None, max_cost=None):
    """Поиск покупок по фильтрам"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    query = '''
        SELECT id, item_name, estimated_cost, priority, target_date, notes, status
        FROM planned_purchases 
        WHERE user_id = ? AND is_deleted = 0
    '''
    params = [user_id]
    
    if search_text:
        query += " AND (item_name LIKE ? OR notes LIKE ?)"
        params.append(f'%{search_text}%')
        params.append(f'%{search_text}%')
    
    if priority:
        query += " AND priority = ?"
        params.append(priority)
    
    if status:
        query += " AND status = ?"
        params.append(status)
    
    if min_cost is not None:
        query += " AND estimated_cost >= ?"
        params.append(min_cost)
    
    if max_cost is not None:
        query += " AND estimated_cost <= ?"
        params.append(max_cost)
    
    query += " ORDER BY "
    query += '''
        CASE priority 
            WHEN 'high' THEN 1
            WHEN 'medium' THEN 2
            WHEN 'low' THEN 3
        END,
        target_date NULLS LAST
    '''
    
    cursor.execute(query, params)
    results = cursor.fetchall()
    conn.close()
    
    return results

# ========== ЗАПУСК БОТА ==========

async def on_startup(dp):
    """Действия при запуске бота"""
    try:
        await schedule_reminders(bot)
        logger.info("✅ Бот запущен!")
        logger.info("✅ Напоминания запланированы")
    except Exception as e:
        logger.error(f"❌ Ошибка при запуске планировщика: {e}")

if __name__ == '__main__':
    # Запускаем миграцию базы данных
    try:
        import migration
        migration.migrate_database()
    except Exception as e:
        logger.warning(f"⚠️ Ошибка при миграции базы данных: {e}")
    
    # Запускаем бота
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)