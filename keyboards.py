from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# ========== ОСНОВНЫЕ КЛАВИАТУРЫ ==========

def get_main_keyboard():
    """Главное меню"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.add(
        KeyboardButton('💰 Добавить расход'),
        KeyboardButton('💵 Добавить доход')
    )
    keyboard.add(
        KeyboardButton('📊 Статистика'),
        KeyboardButton('👫 Общие финансы')
    )
    keyboard.add(
        KeyboardButton('📅 Добавить план'),
        KeyboardButton('🛒 Добавить покупку')
    )
    keyboard.add(
        KeyboardButton('📝 Мои планы'),
        KeyboardButton('📋 Мои покупки')
    )
    keyboard.add(
        KeyboardButton('🔧 Управление'),
        KeyboardButton('🔍 Поиск')
    )
    return keyboard

def get_back_keyboard():
    """Клавиатура с кнопкой назад"""
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton('🔙 Назад', callback_data='back_to_main'))
    return keyboard

# ========== КЛАВИАТУРЫ ДЛЯ КАТЕГОРИЙ ==========

def get_expense_categories_keyboard():
    """Категории для расходов"""
    keyboard = InlineKeyboardMarkup(row_width=2)
    categories = ['Еда', 'Транспорт', 'Развлечения', 'Одежда', 'Жилье', 'Здоровье', 'Подарки', 'Другое']
    for cat in categories:
        keyboard.insert(InlineKeyboardButton(cat, callback_data=f'expense_cat_{cat}'))
    return keyboard

def get_income_categories_keyboard():
    """Категории для доходов"""
    keyboard = InlineKeyboardMarkup(row_width=2)
    categories = ['Зарплата', 'Подработка', 'Инвестиции', 'Подарок', 'Возврат долга', 'Прочее']
    for cat in categories:
        keyboard.insert(InlineKeyboardButton(cat, callback_data=f'income_cat_{cat}'))
    return keyboard

def get_plan_categories_keyboard():
    """Категории для планов"""
    keyboard = InlineKeyboardMarkup(row_width=2)
    categories = ['личные', 'работа', 'семья', 'отдых', 'здоровье', 'другое']
    for cat in categories:
        keyboard.insert(InlineKeyboardButton(cat, callback_data=f'plan_cat_{cat}'))
    return keyboard

def get_priority_keyboard():
    """Приоритеты для покупок"""
    keyboard = InlineKeyboardMarkup(row_width=3)
    keyboard.add(
        InlineKeyboardButton('🔴 Высокий', callback_data='priority_high'),
        InlineKeyboardButton('🟡 Средний', callback_data='priority_medium'),
        InlineKeyboardButton('🟢 Низкий', callback_data='priority_low')
    )
    return keyboard

# ========== КЛАВИАТУРЫ ДЛЯ СТАТИСТИКИ ==========

def get_statistics_menu_keyboard():
    """Меню статистики"""
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton('📊 Моя статистика', callback_data='stats_my'),
        InlineKeyboardButton('👫 Общая статистика', callback_data='stats_combined')
    )
    keyboard.add(
        InlineKeyboardButton('👤 Статистика партнера', callback_data='stats_partner'),
        InlineKeyboardButton('📈 Сравнение', callback_data='stats_comparison')
    )
    keyboard.add(
        InlineKeyboardButton('📂 По категориям', callback_data='stats_categories'),
        InlineKeyboardButton('📅 Расходы сегодня', callback_data='stats_today')
    )
    keyboard.add(InlineKeyboardButton('🔙 Назад', callback_data='back_to_main'))
    return keyboard

def get_period_selection_keyboard():
    """Выбор периода для статистики"""
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton('📅 Сегодня', callback_data='period_today'),
        InlineKeyboardButton('📆 Неделя', callback_data='period_week'),
        InlineKeyboardButton('📊 Месяц', callback_data='period_month'),
        InlineKeyboardButton('📈 Все время', callback_data='period_all')
    )
    keyboard.add(InlineKeyboardButton('🔙 Назад', callback_data='back_to_stats'))
    return keyboard

def get_partner_view_keyboard():
    """Просмотр данных партнера"""
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton('💸 Расходы партнера', callback_data='partner_expenses'),
        InlineKeyboardButton('💵 Доходы партнера', callback_data='partner_incomes')
    )
    keyboard.add(
        InlineKeyboardButton('📅 Планы партнера', callback_data='partner_plans'),
        InlineKeyboardButton('🛒 Покупки партнера', callback_data='partner_purchases')
    )
    keyboard.add(
        InlineKeyboardButton('📊 Полная статистика', callback_data='partner_full_stats'),
        InlineKeyboardButton('🔙 Назад', callback_data='back_to_stats')
    )
    return keyboard

def get_combined_stats_keyboard():
    """Общая статистика"""
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton('📈 Общие расходы', callback_data='combined_expenses'),
        InlineKeyboardButton('💰 Общие доходы', callback_data='combined_incomes')
    )
    keyboard.add(
        InlineKeyboardButton('📊 Сравнение по категориям', callback_data='combined_categories'),
        InlineKeyboardButton('📋 Итоги за месяц', callback_data='combined_monthly')
    )
    keyboard.add(
        InlineKeyboardButton('📅 Совместные планы', callback_data='combined_plans'),
        InlineKeyboardButton('🔙 Назад', callback_data='back_to_stats')
    )
    return keyboard

# ========== КЛАВИАТУРЫ ДЛЯ УПРАВЛЕНИЯ ==========

def get_management_keyboard():
    """Меню управления записями"""
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton('✏️ Редактировать расход', callback_data='manage_expense'),
        InlineKeyboardButton('✏️ Редактировать доход', callback_data='manage_income')
    )
    keyboard.add(
        InlineKeyboardButton('🗑️ Удалить расход', callback_data='delete_expense'),
        InlineKeyboardButton('🗑️ Удалить доход', callback_data='delete_income')
    )
    keyboard.add(
        InlineKeyboardButton('✏️ Редактировать план', callback_data='manage_plan'),
        InlineKeyboardButton('🗑️ Удалить план', callback_data='delete_plan')
    )
    keyboard.add(
        InlineKeyboardButton('✏️ Редактировать покупку', callback_data='manage_purchase'),
        InlineKeyboardButton('🗑️ Удалить покупку', callback_data='delete_purchase')
    )
    keyboard.add(
        InlineKeyboardButton('👥 Общие планы', callback_data='shared_plans'),
        InlineKeyboardButton('🔙 Назад', callback_data='back_to_main')
    )
    return keyboard

def get_edit_transaction_keyboard(transaction_id, trans_type):
    """Редактирование транзакции"""
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton('💵 Изменить сумму', callback_data=f'edit_amount_{trans_type}_{transaction_id}'),
        InlineKeyboardButton('📂 Изменить категорию', callback_data=f'edit_category_{trans_type}_{transaction_id}')
    )
    keyboard.add(
        InlineKeyboardButton('📝 Изменить описание', callback_data=f'edit_desc_{trans_type}_{transaction_id}'),
        InlineKeyboardButton('🗑️ Удалить', callback_data=f'delete_confirm_{trans_type}_{transaction_id}')
    )
    keyboard.add(InlineKeyboardButton('🔙 Отмена', callback_data='cancel_edit'))
    return keyboard

def get_edit_plan_keyboard(plan_id):
    """Редактирование плана"""
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton('📝 Изменить название', callback_data=f'edit_plan_title_{plan_id}'),
        InlineKeyboardButton('📋 Изменить описание', callback_data=f'edit_plan_desc_{plan_id}')
    )
    keyboard.add(
        InlineKeyboardButton('📅 Изменить дату', callback_data=f'edit_plan_date_{plan_id}'),
        InlineKeyboardButton('⏰ Изменить время', callback_data=f'edit_plan_time_{plan_id}')
    )
    keyboard.add(
        InlineKeyboardButton('🏷️ Изменить категорию', callback_data=f'edit_plan_cat_{plan_id}'),
        InlineKeyboardButton('👥 Общий/Личный', callback_data=f'toggle_shared_{plan_id}')
    )
    keyboard.add(
        InlineKeyboardButton('🗑️ Удалить', callback_data=f'delete_plan_confirm_{plan_id}'),
        InlineKeyboardButton('🔙 Отмена', callback_data='cancel_edit')
    )
    return keyboard

def get_edit_purchase_keyboard(purchase_id):
    """Редактирование покупки"""
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton('🛍️ Изменить название', callback_data=f'edit_purchase_name_{purchase_id}'),
        InlineKeyboardButton('💰 Изменить стоимость', callback_data=f'edit_purchase_cost_{purchase_id}')
    )
    keyboard.add(
        InlineKeyboardButton('🎯 Изменить приоритет', callback_data=f'edit_purchase_priority_{purchase_id}'),
        InlineKeyboardButton('📅 Изменить дату', callback_data=f'edit_purchase_date_{purchase_id}')
    )
    keyboard.add(
        InlineKeyboardButton('📝 Изменить заметки', callback_data=f'edit_purchase_notes_{purchase_id}'),
        InlineKeyboardButton('✅ Отметить купленным', callback_data=f'purchase_done_{purchase_id}')
    )
    keyboard.add(
        InlineKeyboardButton('🗑️ Удалить', callback_data=f'delete_purchase_confirm_{purchase_id}'),
        InlineKeyboardButton('🔙 Отмена', callback_data='cancel_edit')
    )
    return keyboard

def get_delete_confirmation_keyboard(item_type, item_id):
    """Подтверждение удаления"""
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton('✅ Да, удалить', callback_data=f'delete_{item_type}_yes_{item_id}'),
        InlineKeyboardButton('❌ Нет, отмена', callback_data=f'delete_{item_type}_no_{item_id}')
    )
    return keyboard

# ========== КЛАВИАТУРЫ ДЛЯ ОБЩИХ ПЛАНОВ ==========

def get_shared_plans_keyboard():
    """Общие планы"""
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton('📅 Показать общие планы', callback_data='show_shared_plans'),
        InlineKeyboardButton('➕ Создать общий план', callback_data='create_shared_plan')
    )
    keyboard.add(
        InlineKeyboardButton('👀 Мои личные планы', callback_data='show_personal_plans'),
        InlineKeyboardButton('🔙 Назад', callback_data='back_to_management')
    )
    return keyboard

# ========== КЛАВИАТУРЫ ДЛЯ ПОИСКА ==========

def get_search_keyboard():
    """Поиск записей"""
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton('🔍 Поиск расходов', callback_data='search_expenses'),
        InlineKeyboardButton('🔍 Поиск доходов', callback_data='search_incomes')
    )
    keyboard.add(
        InlineKeyboardButton('📅 Поиск планов', callback_data='search_plans'),
        InlineKeyboardButton('🛒 Поиск покупок', callback_data='search_purchases')
    )
    keyboard.add(
        InlineKeyboardButton('📋 Последние записи', callback_data='show_recent'),
        InlineKeyboardButton('🔙 Назад', callback_data='back_to_main')
    )
    return keyboard

def get_search_filters_keyboard(search_type):
    """Фильтры поиска"""
    keyboard = InlineKeyboardMarkup(row_width=2)
    
    if search_type in ['expenses', 'incomes']:
        keyboard.add(
            InlineKeyboardButton('🔍 По описанию', callback_data=f'search_{search_type}_by_desc'),
            InlineKeyboardButton('📂 По категории', callback_data=f'search_{search_type}_by_cat')
        )
        keyboard.add(
            InlineKeyboardButton('💰 По сумме', callback_data=f'search_{search_type}_by_amount'),
            InlineKeyboardButton('📅 По дате', callback_data=f'search_{search_type}_by_date')
        )
    
    elif search_type == 'plans':
        keyboard.add(
            InlineKeyboardButton('🔍 По названию', callback_data='search_plans_by_text'),
            InlineKeyboardButton('🏷️ По категории', callback_data='search_plans_by_cat')
        )
        keyboard.add(
            InlineKeyboardButton('📅 По дате', callback_data='search_plans_by_date'),
            InlineKeyboardButton('👥 Только общие', callback_data='search_plans_shared')
        )
    
    elif search_type == 'purchases':
        keyboard.add(
            InlineKeyboardButton('🔍 По названию', callback_data='search_purchases_by_text'),
            InlineKeyboardButton('🎯 По приоритету', callback_data='search_purchases_by_priority')
        )
        keyboard.add(
            InlineKeyboardButton('💰 По стоимости', callback_data='search_purchases_by_cost'),
            InlineKeyboardButton('✅/📋 По статусу', callback_data='search_purchases_by_status')
        )
    
    keyboard.add(InlineKeyboardButton('🔙 Назад', callback_data='back_to_search'))
    return keyboard

# ========== КЛАВИАТУРЫ ДЛЯ ВЫБОРА ЗАПИСЕЙ ==========

def create_transactions_keyboard(transactions, trans_type):
    """Клавиатура с транзакциями для выбора"""
    keyboard = InlineKeyboardMarkup(row_width=1)
    
    for trans in transactions:
        trans_id, amount, category, description, trans_date, time = trans[:6]
        desc_short = (description[:20] + "...") if description and len(description) > 20 else (description or "")
        date_str = trans_date if len(trans) > 5 else "сегодня"
        time_str = f" ({time})" if time else ""
        
        text = f"{amount} руб. - {category} - {date_str}{time_str}"
        if desc_short:
            text += f" | {desc_short}"
        
        callback_data = f'select_{trans_type}_{trans_id}'
        keyboard.add(InlineKeyboardButton(text, callback_data=callback_data))
    
    keyboard.add(InlineKeyboardButton('🔙 Назад', callback_data='back_to_management'))
    return keyboard

def create_plans_keyboard(plans):
    """Клавиатура с планами для выбора"""
    keyboard = InlineKeyboardMarkup(row_width=1)
    
    for plan in plans:
        plan_id, title, description, plan_date, time, category, is_shared = plan[:7]
        shared_icon = " 👥" if is_shared else ""
        time_str = f" в {time}" if time else ""
        desc_short = (description[:20] + "...") if description and len(description) > 20 else (description or "")
        
        text = f"{title}{shared_icon} - {plan_date}{time_str}"
        if desc_short:
            text += f" | {desc_short}"
        
        keyboard.add(InlineKeyboardButton(text, callback_data=f'select_plan_{plan_id}'))
    
    keyboard.add(InlineKeyboardButton('🔙 Назад', callback_data='back_to_management'))
    return keyboard

def create_purchases_keyboard(purchases):
    """Клавиатура с покупками для выбора"""
    keyboard = InlineKeyboardMarkup(row_width=1)
    
    for purchase in purchases:
        purchase_id, item_name, cost, priority, target_date, notes, status = purchase[:7]
        emoji = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}[priority]
        date_str = f"до {target_date}" if target_date else ""
        notes_short = (notes[:20] + "...") if notes and len(notes) > 20 else (notes or "")
        
        text = f"{emoji} {item_name} - {cost} руб. {date_str}"
        if notes_short:
            text += f" | {notes_short}"
        
        keyboard.add(InlineKeyboardButton(text, callback_data=f'select_purchase_{purchase_id}'))
    
    keyboard.add(InlineKeyboardButton('🔙 Назад', callback_data='back_to_management'))
    return keyboard