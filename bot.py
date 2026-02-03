import asyncio
import logging
import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.utils import executor
from datetime import datetime, date, timedelta

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
    
    result = f"{emoji} *{type_text}:* {amount:.2f} руб.\n"
    result += f"   📂 Категория: {category}\n"
    result += f"   📅 Дата: {date_str}{time_str}\n"
    
    if description:
        result += f"   📝 Описание: {description}\n"
    
    if include_id:
        result += f"   🆔 ID: {trans_id}\n"
    
    return result

def format_plan(plan, include_id=False):
    """Форматирование плана для отображения"""
    plan_id, title, description, plan_date, time, category, is_shared = plan[:7]
    
    shared_icon = " 👥" if is_shared else ""
    time_str = f" в {time}" if time else ""
    
    result = f"📅 *{title}*{shared_icon}\n"
    result += f"   📅 Дата: {plan_date}{time_str}\n"
    result += f"   🏷️ Категория: {category}\n"
    
    if description:
        result += f"   📋 Описание: {description}\n"
    
    if include_id:
        result += f"   🆔 ID: {plan_id}\n"
    
    return result

def format_purchase(purchase, include_id=False):
    """Форматирование покупки для отображения"""
    purchase_id, item_name, cost, priority, target_date, notes, status = purchase[:7]
    
    emoji = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}[priority]
    date_str = f"до {target_date}" if target_date else ""
    status_emoji = "✅" if status == 'bought' else "📋"
    
    result = f"{emoji} *{item_name}* {status_emoji}\n"
    result += f"   💰 Стоимость: {cost:.2f} руб.\n"
    
    if date_str:
        result += f"   📅 {date_str}\n"
    
    if notes:
        result += f"   📝 Заметки: {notes}\n"
    
    if include_id:
        result += f"   🆔 ID: {purchase_id}\n"
    
    return result

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

📌 **Основные возможности:**
• 💰 Учет расходов и доходов
• 📊 Статистика и аналитика
• 👥 Общие финансы и сравнение
• 📅 Планировщик с напоминаниями
• 🛒 Список желаемых покупок

🆕 **Новые функции:**
• ✏️ Редактирование записей
• 🗑️ Удаление с подтверждением
• 🔍 Расширенный поиск
• 👥 Общие планы

Используй кнопки ниже или команды:
/edit - редактирование записей
/search - поиск записей
/shared - общие расходы сегодня
/last - последние транзакции
/help - справка по командам
"""
    
    await message.answer(welcome_text, reply_markup=get_main_keyboard())

@dp.message_handler(commands=['help'])
async def cmd_help(message: types.Message):
    """Обработчик команды /help"""
    help_text = """
📚 **Справка по командам:**

**Основные команды:**
/start - запустить бота
/help - эта справка
/edit - редактирование записей
/search - поиск записей
/shared - общие расходы сегодня
/last - последние 10 транзакций
/weekly - недельная сводка

**Управление записями:**
✏️ Редактировать - изменить запись
🗑️ Удалить - удалить запись (с подтверждением)

**Общие планы:**
👥 Общие планы - просмотр и создание

**Для восстановления удаленных записей**
обратитесь к администратору базы данных.
"""
    
    await message.answer(help_text, parse_mode='Markdown')

@dp.message_handler(commands=['last'])
async def cmd_last(message: types.Message):
    """Последние транзакции"""
    if not is_authorized_user(message.from_user.id):
        return
    
    transactions = get_recent_transactions(message.from_user.id, 10)
    
    if not transactions:
        await message.answer("📭 У вас еще нет транзакций")
        return
    
    response = "📊 *Последние 10 транзакций:*\n\n"
    
    for trans in transactions:
        trans_type, amount, category, description, datetime_str = trans
        
        emoji = "💵" if trans_type == 'income' else "💸"
        type_text = "Доход" if trans_type == 'income' else "Расход"
        
        response += f"{emoji} *{type_text}: {amount:.2f} руб.*\n"
        response += f"   📂 Категория: {category}\n"
        response += f"   📅 Дата: {datetime_str}\n"
        if description:
            response += f"   📝 Описание: {description}\n"
        response += "\n"
    
    await message.answer(response, parse_mode='Markdown')

@dp.message_handler(commands=['weekly'])
async def cmd_weekly(message: types.Message):
    """Недельная сводка"""
    if not is_authorized_user(message.from_user.id):
        return
    
    weekly_data = get_weekly_summary()
    
    if not weekly_data:
        await message.answer("📊 Нет данных за последние 4 недели")
        return
    
    response = "📊 *Еженедельная сводка (последние 4 недели):*\n\n"
    
    current_week = None
    for data in weekly_data:
        username, week_start, income, expense = data
        
        if week_start != current_week:
            current_week = week_start
            response += f"\n*📅 Неделя с {week_start}:*\n"
        
        balance = income - expense
        response += f"  👤 {username}:\n"
        response += f"    💵 Доходы: {income:.2f} руб.\n"
        response += f"    💸 Расходы: {expense:.2f} руб.\n"
        response += f"    ⚖️ Баланс: {balance:.2f} руб.\n"
    
    await message.answer(response, parse_mode='Markdown')

@dp.message_handler(commands=['shared'])
async def cmd_shared(message: types.Message):
    """Общие расходы сегодня"""
    if not is_authorized_user(message.from_user.id):
        return
    
    today_expenses = get_daily_combined_expenses()
    
    if not today_expenses:
        await message.answer("💸 *Сегодня еще не было общих расходов*", parse_mode='Markdown')
        return
    
    response = "👫 *Общие расходы сегодня:*\n\n"
    user_totals = {}
    overall_total = 0
    
    for expense in today_expenses:
        username, category, amount, description, created_at = expense
        
        if username not in user_totals:
            user_totals[username] = 0
        
        user_totals[username] += amount
        overall_total += amount
    
    for username, total in user_totals.items():
        response += f"*{username}:* {total:.2f} руб.\n"
    
    response += f"\n💰 *Всего: {overall_total:.2f} руб.*"
    
    await message.answer(response, parse_mode='Markdown')

# ========== ОБРАБОТЧИКИ ДОБАВЛЕНИЯ РАСХОДОВ ==========

@dp.message_handler(lambda message: message.text == '💰 Добавить расход')
async def add_expense_start(message: types.Message):
    """Начало добавления расхода"""
    if not is_authorized_user(message.from_user.id):
        return
    
    await AddExpense.waiting_for_amount.set()
    await message.answer("💸 Введите сумму расхода:")

@dp.message_handler(state=AddExpense.waiting_for_amount)
async def process_expense_amount(message: types.Message, state: FSMContext):
    """Обработка суммы расхода"""
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
                          "📝 Добавьте описание (или отправьте '-' если не нужно):")
    await callback_query.answer()

@dp.message_handler(state=AddExpense.waiting_for_description)
async def process_expense_description(message: types.Message, state: FSMContext):
    """Обработка описания расхода"""
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
✅ *Расход добавлен!*

💰 Сумма: {data['amount']:.2f} руб.
📂 Категория: {data['category']}
"""
    if description:
        response += f"📝 Описание: {description}\n"
    
    response += f"🆔 ID: {transaction_id}"
    
    await message.answer(response, parse_mode='Markdown', reply_markup=get_main_keyboard())

# ========== ОБРАБОТЧИКИ ДОБАВЛЕНИЯ ДОХОДОВ ==========

@dp.message_handler(lambda message: message.text == '💵 Добавить доход')
async def add_income_start(message: types.Message):
    """Начало добавления дохода"""
    if not is_authorized_user(message.from_user.id):
        return
    
    await AddIncome.waiting_for_amount.set()
    await message.answer("💰 Введите сумму дохода:")

@dp.message_handler(state=AddIncome.waiting_for_amount)
async def process_income_amount(message: types.Message, state: FSMContext):
    """Обработка суммы дохода"""
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
                          "📝 Добавьте описание (или отправьте '-' если не нужно):")
    await callback_query.answer()

@dp.message_handler(state=AddIncome.waiting_for_description)
async def process_income_description(message: types.Message, state: FSMContext):
    """Обработка описания дохода"""
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
✅ *Доход добавлен!*

💰 Сумма: {data['amount']:.2f} руб.
📂 Категория: {data['category']}
"""
    if description:
        response += f"📝 Описание: {description}\n"
    
    response += f"🆔 ID: {transaction_id}"
    
    await message.answer(response, parse_mode='Markdown', reply_markup=get_main_keyboard())

# ========== ОБРАБОТЧИКИ ДОБАВЛЕНИЯ ПЛАНОВ ==========

@dp.message_handler(lambda message: message.text == '📅 Добавить план')
async def add_plan_start(message: types.Message):
    """Начало добавления плана"""
    if not is_authorized_user(message.from_user.id):
        return
    
    await AddPlan.waiting_for_title.set()
    await message.answer("📝 Введите название плана:")

@dp.message_handler(state=AddPlan.waiting_for_title)
async def process_plan_title(message: types.Message, state: FSMContext):
    """Обработка названия плана"""
    await state.update_data(title=message.text)
    await AddPlan.next()
    await message.answer("📋 Введите описание плана (или '-' если не нужно):")

@dp.message_handler(state=AddPlan.waiting_for_description)
async def process_plan_description(message: types.Message, state: FSMContext):
    """Обработка описания плана"""
    description = message.text if message.text != '-' else None
    await state.update_data(description=description)
    await AddPlan.next()
    await message.answer("📅 Введите дату (в формате ГГГГ-ММ-ДД, или 'сегодня', 'завтра'):")

@dp.message_handler(state=AddPlan.waiting_for_date)
async def process_plan_date(message: types.Message, state: FSMContext):
    """Обработка даты плана"""
    date_str = message.text.lower()
    
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
    await message.answer("⏰ Введите время (в формате ЧЧ:ММ, или '-' если не нужно):")

@dp.message_handler(state=AddPlan.waiting_for_time)
async def process_plan_time(message: types.Message, state: FSMContext):
    """Обработка времени плана"""
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
                          "Отправьте 'да' или 'нет':")
    await callback_query.answer()

@dp.message_handler(state=AddPlan.waiting_for_shared)
async def process_plan_shared(message: types.Message, state: FSMContext):
    """Обработка общего статуса плана"""
    is_shared = message.text.lower() in ['да', 'yes', 'y', 'д']
    
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
    
    shared_text = "общим" if is_shared else "личным"
    time_text = f" в {data['time']}" if data['time'] else ""
    
    response = f"""
✅ *План добавлен!*

📝 Название: {data['title']}
📅 Дата: {data['date']}{time_text}
🏷️ Категория: {data['category']}
👥 Статус: {shared_text}
"""
    if data['description']:
        response += f"📋 Описание: {data['description']}\n"
    
    response += f"🆔 ID: {plan_id}"
    
    await message.answer(response, parse_mode='Markdown', reply_markup=get_main_keyboard())

# ========== ОБРАБОТЧИКИ ДОБАВЛЕНИЯ ПОКУПОК ==========

@dp.message_handler(lambda message: message.text == '🛒 Добавить покупку')
async def add_purchase_start(message: types.Message):
    """Начало добавления покупки"""
    if not is_authorized_user(message.from_user.id):
        return
    
    await AddPurchase.waiting_for_name.set()
    await message.answer("🛍️ Введите название покупки:")

@dp.message_handler(state=AddPurchase.waiting_for_name)
async def process_purchase_name(message: types.Message, state: FSMContext):
    """Обработка названия покупки"""
    await state.update_data(name=message.text)
    await AddPurchase.next()
    await message.answer("💰 Введите примерную стоимость:")

@dp.message_handler(state=AddPurchase.waiting_for_cost)
async def process_purchase_cost(message: types.Message, state: FSMContext):
    """Обработка стоимости покупки"""
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
                          "📅 Введите дату, к которой нужна покупка (ГГГГ-ММ-ДД или '-'):")
    await callback_query.answer()

@dp.message_handler(state=AddPurchase.waiting_for_date)
async def process_purchase_date(message: types.Message, state: FSMContext):
    """Обработка даты покупки"""
    date_str = message.text if message.text != '-' else None
    
    if date_str and date_str != '-':
        try:
            datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError:
            await message.answer("❌ Неверный формат даты. Используйте ГГГГ-ММ-ДД")
            return
    
    await state.update_data(date=date_str)
    await AddPurchase.next()
    await message.answer("📝 Добавьте заметки (или отправьте '-' если не нужно):")

@dp.message_handler(state=AddPurchase.waiting_for_notes)
async def process_purchase_notes(message: types.Message, state: FSMContext):
    """Обработка заметок покупки"""
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
✅ *Покупка добавлена!*

🛍️ Название: {data['name']}
💰 Стоимость: {data['cost']:.2f} руб.
🎯 Приоритет: {data['priority']}
"""
    if date_text:
        response += f"📅 {date_text}\n"
    
    if notes:
        response += f"📝 Заметки: {notes}\n"
    
    response += f"🆔 ID: {purchase_id}"
    
    await message.answer(response, parse_mode='Markdown', reply_markup=get_main_keyboard())

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
    
    response = "📅 *Ваши планы на сегодня:*\n\n"
    
    for plan in plans:
        response += format_plan(plan, include_id=True) + "\n"
    
    await message.answer(response, parse_mode='Markdown')

@dp.message_handler(lambda message: message.text == '📋 Мои покупки')
async def show_purchases(message: types.Message):
    """Показать планируемые покупки"""
    if not is_authorized_user(message.from_user.id):
        return
    
    purchases = get_user_purchases(message.from_user.id)
    
    if not purchases:
        await message.answer("🛍️ Список планируемых покупок пуст!")
        return
    
    response = "📋 *Ваши планируемые покупки:*\n\n"
    total = 0
    
    for purchase in purchases:
        response += format_purchase(purchase, include_id=True) + "\n"
        total += purchase[2]  # estimated_cost
    
    response += f"\n💰 *Общая сумма: {total:.2f} руб.*"
    
    await message.answer(response, parse_mode='Markdown')

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
                              "👤 *Данные партнера:*", 
                              parse_mode='Markdown', 
                              reply_markup=get_partner_view_keyboard())
    
    elif action == 'combined':
        await bot.send_message(user_id, 
                              "👫 *Общая статистика:*", 
                              parse_mode='Markdown', 
                              reply_markup=get_combined_stats_keyboard())
    
    elif action == 'comparison':
        comparison = get_monthly_comparison()
        
        if comparison:
            response = "📊 *Сравнение за месяц:*\n\n"
            total_combined_income = 0
            total_combined_expense = 0
            
            for user_data in comparison:
                username = user_data[0]
                income = user_data[1] or 0
                expense = user_data[2] or 0
                balance = user_data[3] or 0
                
                response += f"*{username}:*\n"
                response += f"  💵 Доходы: {income:.2f} руб.\n"
                response += f"  💸 Расходы: {expense:.2f} руб.\n"
                response += f"  ⚖️ Баланс: {balance:.2f} руб.\n\n"
                
                total_combined_income += income
                total_combined_expense += expense
            
            total_balance = total_combined_income - total_combined_expense
            response += f"*Общие итоги:*\n"
            response += f"  📈 Общий доход: {total_combined_income:.2f} руб.\n"
            response += f"  📉 Общий расход: {total_combined_expense:.2f} руб.\n"
            response += f"  ⚖️ Общий баланс: {total_balance:.2f} руб."
        
        else:
            response = "📊 Данных для сравнения нет"
        
        await bot.send_message(user_id, response, parse_mode='Markdown')
    
    elif action == 'categories':
        categories_stats = get_common_categories_statistics()
        
        if categories_stats:
            response = "📂 *Топ категорий по расходам за месяц:*\n\n"
            total_expenses = 0
            
            for i, (category, expense, count) in enumerate(categories_stats, 1):
                if expense > 0:
                    total_expenses += expense
                    response += f"{i}. *{category}:* {expense:.2f} руб. ({count} записей)\n"
            
            response += f"\n💸 *Всего расходов:* {total_expenses:.2f} руб."
        
        else:
            response = "📊 Данных по категориям нет"
        
        await bot.send_message(user_id, response, parse_mode='Markdown')
    
    elif action == 'today':
        today_expenses = get_daily_combined_expenses()
        
        if today_expenses:
            response = "📅 *Расходы за сегодня:*\n\n"
            current_user = None
            user_total = 0
            overall_total = 0
            
            for expense in today_expenses:
                username, category, amount, description, created_at = expense
                
                if username != current_user:
                    if current_user:
                        response += f"*Итого: {user_total:.2f} руб.*\n\n"
                        user_total = 0
                    
                    current_user = username
                    response += f"*👤 {username}:*\n"
                
                user_total += amount
                overall_total += amount
                
                desc = f" - {description}" if description else ""
                response += f"  • {category}: {amount:.2f} руб.{desc}\n"
            
            if current_user:
                response += f"\n*Итого: {user_total:.2f} руб.*"
            
            response += f"\n\n💰 *Общая сумма: {overall_total:.2f} руб.*"
        
        else:
            response = "💸 *Сегодня еще не было расходов*"
        
        await bot.send_message(user_id, response, parse_mode='Markdown')
    
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
📊 *Статистика за {period_text}:*

📈 *Доходы:* {total_income:.2f} руб.
📉 *Расходы:* {total_expense:.2f} руб.
💰 *Баланс:* {balance:.2f} руб.
📋 *Количество операций:* {count}
        """
        
        transactions = get_user_transactions(user_id, action)
        
        if transactions:
            response += "\n\n📝 *Детали операций:*\n\n"
            
            if action == 'today':
                for trans in transactions:
                    response += format_transaction(trans) + "\n"
            
            else:
                current_date = None
                for trans in transactions:
                    trans_date = trans[5] if len(trans) > 5 else "Сегодня"
                    
                    if trans_date != current_date:
                        current_date = trans_date
                        response += f"\n📅 *{trans_date}:*\n"
                    
                    response += "  " + format_transaction(trans)
    
    else:
        response = f"📊 *Нет данных за {period_text}*"
    
    await bot.send_message(user_id, response, parse_mode='Markdown')
    await callback_query.answer()

# ========== ОБРАБОТЧИКИ УПРАВЛЕНИЯ ЗАПИСЯМИ ==========

@dp.message_handler(lambda message: message.text == '🔧 Управление')
async def show_management(message: types.Message):
    """Показать меню управления"""
    if not is_authorized_user(message.from_user.id):
        return
    
    await message.answer("🔧 **Управление записями:**\n\n"
                        "Выберите действие:", 
                        parse_mode='Markdown',
                        reply_markup=get_management_keyboard())

# УПРАВЛЕНИЕ РАСХОДАМИ
@dp.callback_query_handler(lambda c: c.data == 'manage_expense')
async def manage_expense_start(callback_query: types.CallbackQuery):
    """Начало управления расходами"""
    user_id = callback_query.from_user.id
    
    expenses = get_user_transactions(user_id, 'month', 'expense')
    
    if not expenses:
        await bot.send_message(user_id, "📭 У вас нет расходов для редактирования")
        return
    
    await bot.send_message(user_id,
                          "💰 **Ваши расходы за месяц:**\n\n"
                          "Выберите расход для редактирования:",
                          parse_mode='Markdown',
                          reply_markup=create_transactions_keyboard(expenses, 'expense'))
    
    await callback_query.answer()

@dp.callback_query_handler(lambda c: c.data.startswith('select_expense_'))
async def select_expense_for_edit(callback_query: types.CallbackQuery):
    """Выбор расхода для редактирования"""
    expense_id = int(callback_query.data[15:])
    expense = get_transaction(expense_id)
    
    if not expense:
        await bot.send_message(callback_query.from_user.id, "❌ Расход не найден")
        await callback_query.answer()
        return
    
    response = format_transaction((expense_id, *expense[2:7]), include_id=True)
    response = "✏️ **Редактирование расхода:**\n\n" + response
    
    await bot.send_message(callback_query.from_user.id,
                          response,
                          parse_mode='Markdown',
                          reply_markup=get_edit_transaction_keyboard(expense_id, 'expense'))
    
    await callback_query.answer()

# РЕДАКТИРОВАНИЕ СУММЫ РАСХОДА
@dp.callback_query_handler(lambda c: c.data.startswith('edit_amount_expense_'))
async def edit_expense_amount(callback_query: types.CallbackQuery, state: FSMContext):
    """Редактирование суммы расхода"""
    expense_id = int(callback_query.data[20:])
    await EditExpense.waiting_for_amount.set()
    await state.update_data(expense_id=expense_id)
    await bot.send_message(callback_query.from_user.id, "💵 Введите новую сумму расхода:")
    await callback_query.answer()

@dp.message_handler(state=EditExpense.waiting_for_amount)
async def process_edit_expense_amount(message: types.Message, state: FSMContext):
    """Обработка новой суммы расхода"""
    try:
        amount = float(message.text.replace(',', '.'))
        if amount <= 0:
            await message.answer("❌ Сумма должна быть больше 0")
            return
        
        data = await state.get_data()
        expense_id = data['expense_id']
        
        update_transaction(expense_id, amount=amount)
        
        await state.finish()
        await message.answer(f"✅ Сумма расхода обновлена: {amount} руб.", 
                           reply_markup=get_main_keyboard())
    
    except ValueError:
        await message.answer("❌ Пожалуйста, введите корректную сумму")

# РЕДАКТИРОВАНИЕ КАТЕГОРИИ РАСХОДА
@dp.callback_query_handler(lambda c: c.data.startswith('edit_category_expense_'))
async def edit_expense_category(callback_query: types.CallbackQuery, state: FSMContext):
    """Редактирование категории расхода"""
    expense_id = int(callback_query.data[23:])
    await EditExpense.waiting_for_category.set()
    await state.update_data(expense_id=expense_id)
    await bot.send_message(callback_query.from_user.id,
                         "📂 Выберите новую категорию:",
                         reply_markup=get_expense_categories_keyboard())
    await callback_query.answer()

@dp.callback_query_handler(lambda c: c.data.startswith('expense_cat_'), state=EditExpense.waiting_for_category)
async def process_edit_expense_category(callback_query: types.CallbackQuery, state: FSMContext):
    """Обработка новой категории расхода"""
    category = callback_query.data[11:]
    data = await state.get_data()
    expense_id = data['expense_id']
    
    update_transaction(expense_id, category=category)
    
    await state.finish()
    await bot.send_message(callback_query.from_user.id,
                          f"✅ Категория расхода обновлена: {category}",
                          reply_markup=get_main_keyboard())
    await callback_query.answer()

# РЕДАКТИРОВАНИЕ ОПИСАНИЯ РАСХОДА
@dp.callback_query_handler(lambda c: c.data.startswith('edit_desc_expense_'))
async def edit_expense_description(callback_query: types.CallbackQuery, state: FSMContext):
    """Редактирование описания расхода"""
    expense_id = int(callback_query.data[20:])
    await EditExpense.waiting_for_description.set()
    await state.update_data(expense_id=expense_id)
    await bot.send_message(callback_query.from_user.id,
                          "📝 Введите новое описание (или '-' чтобы удалить описание):")
    await callback_query.answer()

@dp.message_handler(state=EditExpense.waiting_for_description)
async def process_edit_expense_description(message: types.Message, state: FSMContext):
    """Обработка нового описания расхода"""
    data = await state.get_data()
    expense_id = data['expense_id']
    description = message.text if message.text != '-' else None
    
    update_transaction(expense_id, description=description)
    
    await state.finish()
    response = "✅ Описание расхода удалено" if description is None else f"✅ Описание расхода обновлено: {description}"
    await message.answer(response, reply_markup=get_main_keyboard())

# УДАЛЕНИЕ РАСХОДА С ПОДТВЕРЖДЕНИЕМ
@dp.callback_query_handler(lambda c: c.data.startswith('delete_confirm_expense_'))
async def confirm_delete_expense(callback_query: types.CallbackQuery):
    """Подтверждение удаления расхода"""
    expense_id = int(callback_query.data[24:])
    expense = get_transaction(expense_id)
    
    if not expense:
        await bot.send_message(callback_query.from_user.id, "❌ Расход не найден")
        await callback_query.answer()
        return
    
    response = format_transaction((expense_id, *expense[2:7]), include_id=True)
    response = "🗑️ **Подтверждение удаления расхода:**\n\n" + response + "\n\n❓ Вы уверены, что хотите удалить этот расход?"
    
    await bot.send_message(callback_query.from_user.id,
                          response,
                          parse_mode='Markdown',
                          reply_markup=get_delete_confirmation_keyboard('expense', expense_id))
    await callback_query.answer()

@dp.callback_query_handler(lambda c: c.data.startswith('delete_expense_yes_'))
async def delete_expense_yes(callback_query: types.CallbackQuery):
    """Подтверждение удаления расхода"""
    expense_id = int(callback_query.data[20:])
    soft_delete_transaction(expense_id)
    await bot.send_message(callback_query.from_user.id,
                          "✅ Расход успешно удален",
                          reply_markup=get_main_keyboard())
    await callback_query.answer()

@dp.callback_query_handler(lambda c: c.data.startswith('delete_expense_no_'))
async def delete_expense_no(callback_query: types.CallbackQuery):
    """Отмена удаления расхода"""
    await bot.send_message(callback_query.from_user.id,
                          "❌ Удаление отменено",
                          reply_markup=get_main_keyboard())
    await callback_query.answer()

# ========== АНАЛОГИЧНЫЕ ОБРАБОТЧИКИ ДЛЯ ДОХОДОВ, ПЛАНОВ И ПОКУПОК ==========
# (код аналогичный, меняются только названия функций и типы данных)

# ========== ОБРАБОТЧИКИ ОБЩИХ ПЛАНОВ ==========

@dp.callback_query_handler(lambda c: c.data == 'shared_plans')
async def show_shared_plans_menu(callback_query: types.CallbackQuery):
    """Меню общих планов"""
    await bot.send_message(callback_query.from_user.id,
                          "👥 **Управление общими планами:**",
                          parse_mode='Markdown',
                          reply_markup=get_shared_plans_keyboard())
    await callback_query.answer()

@dp.callback_query_handler(lambda c: c.data == 'show_shared_plans')
async def show_shared_plans(callback_query: types.CallbackQuery):
    """Показать общие планы"""
    shared_plans = get_shared_plans()
    
    if not shared_plans:
        await bot.send_message(callback_query.from_user.id,
                              "📭 Нет общих планов")
        return
    
    response = "👥 **Общие планы:**\n\n"
    
    for plan in shared_plans:
        plan_id, user_id, title, description, plan_date, time, category, is_shared, *_ = plan[:9]
        username = plan[12]  # full_name из join
        time_str = f" в {time}" if time else ""
        
        response += f"📅 **{title}** ({username})\n"
        response += f"   📅 {plan_date}{time_str}\n"
        response += f"   🏷️ {category}\n"
        
        if description:
            response += f"   📋 {description}\n"
        
        response += f"   🆔 ID: {plan_id}\n\n"
    
    await bot.send_message(callback_query.from_user.id,
                          response,
                          parse_mode='Markdown')
    await callback_query.answer()

# ========== ОБРАБОТЧИКИ ПОИСКА ==========

@dp.message_handler(lambda message: message.text == '🔍 Поиск')
async def show_search_menu(message: types.Message):
    """Показать меню поиска"""
    if not is_authorized_user(message.from_user.id):
        return
    
    await message.answer("🔍 **Поиск записей:**\n\n"
                        "Выберите тип поиска:",
                        parse_mode='Markdown',
                        reply_markup=get_search_keyboard())

@dp.callback_query_handler(lambda c: c.data == 'search_expenses')
async def search_expenses_start(callback_query: types.CallbackQuery):
    """Начало поиска расходов"""
    await bot.send_message(callback_query.from_user.id,
                          "🔍 **Поиск расходов:**\n\n"
                          "Выберите критерий поиска:",
                          parse_mode='Markdown',
                          reply_markup=get_search_filters_keyboard('expenses'))
    await callback_query.answer()

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
                          "🔧 **Управление записями:**",
                          parse_mode='Markdown',
                          reply_markup=get_management_keyboard())
    await callback_query.answer()

@dp.callback_query_handler(lambda c: c.data == 'back_to_search')
async def back_to_search(callback_query: types.CallbackQuery):
    """Возврат в меню поиска"""
    await bot.send_message(callback_query.from_user.id,
                          "🔍 **Поиск записей:**",
                          parse_mode='Markdown',
                          reply_markup=get_search_keyboard())
    await callback_query.answer()

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