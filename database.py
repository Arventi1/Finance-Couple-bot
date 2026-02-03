import sqlite3
from datetime import datetime, date, timedelta
from config import DB_PATH, MY_USER_ID, GIRLFRIEND_USER_ID

def init_db():
    """Инициализация базы данных с ВСЕМИ полями"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Таблица пользователей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Таблица транзакций (расходы/доходы) - ВСЕ поля сразу
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            type TEXT CHECK(type IN ('income', 'expense')),
            amount REAL,
            category TEXT,
            description TEXT,
            date DATE DEFAULT CURRENT_DATE,
            is_deleted BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Таблица планов - ВСЕ поля сразу
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            title TEXT NOT NULL,
            description TEXT,
            date DATE NOT NULL,
            time TEXT,
            category TEXT DEFAULT 'личные',
            is_shared BOOLEAN DEFAULT 0,
            notification_enabled BOOLEAN DEFAULT 1,
            notification_time TEXT,
            is_deleted BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Таблица планируемых покупок - ВСЕ поля сразу
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS planned_purchases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            item_name TEXT NOT NULL,
            estimated_cost REAL,
            priority TEXT CHECK(priority IN ('low', 'medium', 'high')),
            target_date DATE,
            notes TEXT,
            status TEXT DEFAULT 'planned',
            is_deleted BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ База данных создана/инициализирована")

# ========== ФУНКЦИИ ДЛЯ ПОЛЬЗОВАТЕЛЕЙ ==========

def add_user(user_id, username, full_name):
    """Добавить пользователя"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        'INSERT OR IGNORE INTO users (id, username, full_name) VALUES (?, ?, ?)',
        (user_id, username, full_name)
    )
    conn.commit()
    conn.close()

# ========== ФУНКЦИИ ДЛЯ ТРАНЗАКЦИЙ ==========

def add_transaction(user_id, trans_type, amount, category, description=None):
    """Добавить транзакцию (расход/доход)"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO transactions (user_id, type, amount, category, description, date)
        VALUES (?, ?, ?, ?, ?, DATE('now'))
    ''', (user_id, trans_type, amount, category, description))
    transaction_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return transaction_id

def get_transaction(transaction_id):
    """Получить конкретную транзакцию"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM transactions WHERE id = ? AND is_deleted = 0', (transaction_id,))
    result = cursor.fetchone()
    conn.close()
    return result

def update_transaction(transaction_id, amount=None, category=None, description=None):
    """Обновить транзакцию"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    updates = []
    params = []
    
    if amount is not None:
        updates.append("amount = ?")
        params.append(amount)
    
    if category is not None:
        updates.append("category = ?")
        params.append(category)
    
    if description is not None:
        updates.append("description = ?")
        params.append(description)
    
    if updates:
        updates.append("updated_at = CURRENT_TIMESTAMP")
        query = f"UPDATE transactions SET {', '.join(updates)} WHERE id = ?"
        params.append(transaction_id)
        cursor.execute(query, params)
    
    conn.commit()
    conn.close()

def delete_transaction(transaction_id):
    """Удалить транзакцию"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('UPDATE transactions SET is_deleted = 1 WHERE id = ?', (transaction_id,))
    conn.commit()
    conn.close()

def soft_delete_transaction(transaction_id):
    """Мягкое удаление транзакции (алиас для delete_transaction)"""
    delete_transaction(transaction_id)

def get_recent_transactions(user_id, limit=5, trans_type=None):
    """Получить последние транзакции"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    type_filter = f"AND type = '{trans_type}'" if trans_type else ""
    
    cursor.execute(f'''
        SELECT id, type, amount, category, description, date,
               strftime('%H:%M', created_at) as time
        FROM transactions 
        WHERE user_id = ? AND is_deleted = 0 {type_filter}
        ORDER BY created_at DESC
        LIMIT ?
    ''', (user_id, limit))
    
    results = cursor.fetchall()
    conn.close()
    return results

def get_user_transactions(user_id, period='month', trans_type=None):
    """Получить транзакции пользователя за период"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    type_filter = f"AND type = '{trans_type}'" if trans_type else ""
    
    if period == 'today':
        cursor.execute(f'''
            SELECT id, type, amount, category, description,
                   strftime('%H:%M', created_at) as time
            FROM transactions 
            WHERE user_id = ? AND date = DATE('now') 
            AND is_deleted = 0 {type_filter}
            ORDER BY created_at DESC
        ''', (user_id,))
    elif period == 'month':
        cursor.execute(f'''
            SELECT id, type, amount, category, description, date,
                   strftime('%H:%M', created_at) as time
            FROM transactions 
            WHERE user_id = ? AND strftime('%Y-%m', date) = strftime('%Y-%m', 'now')
            AND is_deleted = 0 {type_filter}
            ORDER BY date DESC, created_at DESC
        ''', (user_id,))
    else:
        cursor.execute(f'''
            SELECT id, type, amount, category, description, date,
                   strftime('%Y-%m-%d %H:%M', created_at) as datetime
            FROM transactions 
            WHERE user_id = ? AND is_deleted = 0 {type_filter}
            ORDER BY date DESC, created_at DESC
            LIMIT 50
        ''', (user_id,))
    
    results = cursor.fetchall()
    conn.close()
    return results

# ========== ФУНКЦИИ ДЛЯ ПЛАНОВ ==========

def add_plan(user_id, title, description, plan_date, time=None, category='личные', is_shared=False):
    """Добавить план"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO plans (user_id, title, description, date, time, category, is_shared)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, title, description, plan_date, time, category, int(is_shared)))
    plan_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return plan_id

def get_plan(plan_id):
    """Получить конкретный план"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM plans WHERE id = ? AND is_deleted = 0', (plan_id,))
    result = cursor.fetchone()
    conn.close()
    return result

def update_plan(plan_id, title=None, description=None, date=None, time=None, category=None, is_shared=None):
    """Обновить план"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    updates = []
    params = []
    
    if title is not None:
        updates.append("title = ?")
        params.append(title)
    
    if description is not None:
        updates.append("description = ?")
        params.append(description)
    
    if date is not None:
        updates.append("date = ?")
        params.append(date)
    
    if time is not None:
        updates.append("time = ?")
        params.append(time)
    
    if category is not None:
        updates.append("category = ?")
        params.append(category)
    
    if is_shared is not None:
        updates.append("is_shared = ?")
        params.append(int(is_shared))
    
    if updates:
        updates.append("updated_at = CURRENT_TIMESTAMP")
        query = f"UPDATE plans SET {', '.join(updates)} WHERE id = ?"
        params.append(plan_id)
        cursor.execute(query, params)
    
    conn.commit()
    conn.close()

def delete_plan(plan_id):
    """Удалить план"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('UPDATE plans SET is_deleted = 1 WHERE id = ?', (plan_id,))
    conn.commit()
    conn.close()

def get_user_plans(user_id, target_date=None):
    """Получить планы пользователя"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    if not target_date:
        target_date = date.today().isoformat()
    
    cursor.execute('''
        SELECT id, title, description, date, time, category, is_shared
        FROM plans 
        WHERE (user_id = ? OR is_shared = 1)
        AND date = ? 
        AND is_deleted = 0
        ORDER BY time NULLS FIRST, created_at
    ''', (user_id, target_date))
    
    results = cursor.fetchall()
    conn.close()
    return results

def get_recent_plans(user_id, limit=5):
    """Получить последние планы"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, title, date, time, category, is_shared
        FROM plans 
        WHERE user_id = ? AND is_deleted = 0
        ORDER BY date DESC, created_at DESC
        LIMIT ?
    ''', (user_id, limit))
    
    results = cursor.fetchall()
    conn.close()
    return results

def get_shared_plans():
    """Получить общие планы"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT p.*, u.username, u.full_name 
        FROM plans p
        JOIN users u ON p.user_id = u.id
        WHERE p.is_shared = 1
        AND p.is_deleted = 0
        AND p.date >= DATE('now')
        ORDER BY p.date, p.time NULLS FIRST
    ''')
    
    results = cursor.fetchall()
    conn.close()
    return results

# ========== ФУНКЦИИ ДЛЯ ПОКУПОК ==========

def add_planned_purchase(user_id, item_name, estimated_cost, priority, target_date=None, notes=None):
    """Добавить планируемую покупку"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO planned_purchases (user_id, item_name, estimated_cost, priority, target_date, notes)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (user_id, item_name, estimated_cost, priority, target_date, notes))
    purchase_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return purchase_id

def get_purchase(purchase_id):
    """Получить конкретную покупку"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM planned_purchases WHERE id = ? AND is_deleted = 0', (purchase_id,))
    result = cursor.fetchone()
    conn.close()
    return result

def update_purchase(purchase_id, item_name=None, estimated_cost=None, priority=None, 
                   target_date=None, notes=None, status=None):
    """Обновить покупку"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    updates = []
    params = []
    
    if item_name is not None:
        updates.append("item_name = ?")
        params.append(item_name)
    
    if estimated_cost is not None:
        updates.append("estimated_cost = ?")
        params.append(estimated_cost)
    
    if priority is not None:
        updates.append("priority = ?")
        params.append(priority)
    
    if target_date is not None:
        updates.append("target_date = ?")
        params.append(target_date)
    
    if notes is not None:
        updates.append("notes = ?")
        params.append(notes)
    
    if status is not None:
        updates.append("status = ?")
        params.append(status)
    
    if updates:
        updates.append("updated_at = CURRENT_TIMESTAMP")
        query = f"UPDATE planned_purchases SET {', '.join(updates)} WHERE id = ?"
        params.append(purchase_id)
        cursor.execute(query, params)
    
    conn.commit()
    conn.close()

def delete_purchase(purchase_id):
    """Удалить покупку"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('UPDATE planned_purchases SET is_deleted = 1 WHERE id = ?', (purchase_id,))
    conn.commit()
    conn.close()

def get_user_purchases(user_id, status='planned'):
    """Получить покупки пользователя"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, item_name, estimated_cost, priority, target_date, notes, status
        FROM planned_purchases 
        WHERE user_id = ? AND status = ? AND is_deleted = 0
        ORDER BY 
            CASE priority 
                WHEN 'high' THEN 1
                WHEN 'medium' THEN 2
                WHEN 'low' THEN 3
            END,
            target_date NULLS LAST
    ''', (user_id, status))
    
    results = cursor.fetchall()
    conn.close()
    return results

def get_recent_purchases(user_id, limit=5):
    """Получить последние покупки"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, item_name, estimated_cost, priority, target_date, notes
        FROM planned_purchases 
        WHERE user_id = ? AND is_deleted = 0
        ORDER BY created_at DESC
        LIMIT ?
    ''', (user_id, limit))
    
    results = cursor.fetchall()
    conn.close()
    return results

# ========== СТАТИСТИКА ==========

def get_period_statistics(user_id, period='month'):
    """Получить статистику за период"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    if period == 'today':
        cursor.execute('''
            SELECT 
                SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END) as total_income,
                SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END) as total_expense,
                COUNT(*) as count
            FROM transactions 
            WHERE user_id = ? AND date = DATE('now') AND is_deleted = 0
        ''', (user_id,))
    elif period == 'week':
        cursor.execute('''
            SELECT 
                SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END) as total_income,
                SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END) as total_expense,
                COUNT(*) as count
            FROM transactions 
            WHERE user_id = ? AND date >= DATE('now', '-7 days') AND is_deleted = 0
        ''', (user_id,))
    elif period == 'month':
        cursor.execute('''
            SELECT 
                SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END) as total_income,
                SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END) as total_expense,
                COUNT(*) as count
            FROM transactions 
            WHERE user_id = ? AND strftime('%Y-%m', date) = strftime('%Y-%m', 'now') AND is_deleted = 0
        ''', (user_id,))
    elif period == 'all':
        cursor.execute('''
            SELECT 
                SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END) as total_income,
                SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END) as total_expense,
                COUNT(*) as count
            FROM transactions 
            WHERE user_id = ? AND is_deleted = 0
        ''', (user_id,))
    
    result = cursor.fetchone()
    conn.close()
    return result

def get_daily_combined_expenses():
    """Получить ежедневные расходы обоих пользователей"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            u.full_name,
            t.category,
            t.amount,
            t.description
        FROM transactions t
        JOIN users u ON t.user_id = u.id
        WHERE t.date = DATE('now') 
        AND t.type = 'expense'
        AND t.user_id IN (?, ?)
        AND t.is_deleted = 0
        ORDER BY u.full_name, t.created_at DESC
    ''', (MY_USER_ID, GIRLFRIEND_USER_ID))
    
    results = cursor.fetchall()
    conn.close()
    return results

def get_common_categories_statistics():
    """Статистика по общим категориям"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            category,
            SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END) as total_expense,
            COUNT(*) as transaction_count
        FROM transactions 
        WHERE strftime('%Y-%m', date) = strftime('%Y-%m', 'now')
        AND user_id IN (?, ?) AND is_deleted = 0
        GROUP BY category
        ORDER BY total_expense DESC
        LIMIT 10
    ''', (MY_USER_ID, GIRLFRIEND_USER_ID))
    
    results = cursor.fetchall()
    conn.close()
    return results

def get_monthly_comparison():
    """Сравнение месячных расходов обоих пользователей"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            u.full_name,
            SUM(CASE WHEN t.type = 'income' THEN t.amount ELSE 0 END) as total_income,
            SUM(CASE WHEN t.type = 'expense' THEN t.amount ELSE 0 END) as total_expense,
            (SUM(CASE WHEN t.type = 'income' THEN t.amount ELSE 0 END) - 
             SUM(CASE WHEN t.type = 'expense' THEN t.amount ELSE 0 END)) as balance
        FROM transactions t
        JOIN users u ON t.user_id = u.id
        WHERE strftime('%Y-%m', t.date) = strftime('%Y-%m', 'now')
        AND t.user_id IN (?, ?) AND t.is_deleted = 0
        GROUP BY u.full_name
    ''', (MY_USER_ID, GIRLFRIEND_USER_ID))
    
    results = cursor.fetchall()
    conn.close()
    return results

def get_shared_expenses_by_category():
    """Получить расходы по категориям для обоих пользователей"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            t.category,
            SUM(CASE WHEN t.user_id = ? THEN t.amount ELSE 0 END) as user1_expenses,
            SUM(CASE WHEN t.user_id = ? THEN t.amount ELSE 0 END) as user2_expenses,
            SUM(t.amount) as total
        FROM transactions t
        WHERE strftime('%Y-%m', t.date) = strftime('%Y-%m', 'now')
        AND t.type = 'expense' AND t.is_deleted = 0
        GROUP BY t.category
        ORDER BY total DESC
    ''', (MY_USER_ID, GIRLFRIEND_USER_ID))
    
    results = cursor.fetchall()
    conn.close()
    return results

def get_combined_statistics(period='month'):
    """Получить объединенную статистику"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    if period == 'month':
        cursor.execute('''
            SELECT 
                SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END) as total_income,
                SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END) as total_expense,
                user_id
            FROM transactions 
            WHERE strftime('%Y-%m', date) = strftime('%Y-%m', 'now') AND is_deleted = 0
            GROUP BY user_id
        ''')
    
    results = cursor.fetchall()
    conn.close()
    return results

def get_recent_transactions_all(user_id, limit=10):
    """Получить последние транзакции"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT type, amount, category, description, 
               strftime('%Y-%m-%d %H:%M', created_at) as datetime
        FROM transactions 
        WHERE user_id = ? AND is_deleted = 0
        ORDER BY created_at DESC
        LIMIT ?
    ''', (user_id, limit))
    
    results = cursor.fetchall()
    conn.close()
    return results

def get_weekly_summary():
    """Еженедельная сводка"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            u.full_name,
            DATE(t.date, 'weekday 0', '-6 days') as week_start,
            SUM(CASE WHEN t.type = 'income' THEN t.amount ELSE 0 END) as weekly_income,
            SUM(CASE WHEN t.type = 'expense' THEN t.amount ELSE 0 END) as weekly_expense
        FROM transactions t
        JOIN users u ON t.user_id = u.id
        WHERE t.date >= DATE('now', '-30 days')
        AND u.id IN (?, ?) AND t.is_deleted = 0
        GROUP BY u.full_name, week_start
        ORDER BY week_start DESC
        LIMIT 4
    ''', (MY_USER_ID, GIRLFRIEND_USER_ID))
    
    results = cursor.fetchall()
    conn.close()
    return results

def get_today_reminders():
    """Получить сегодняшние напоминания"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT p.*, u.username 
        FROM plans p
        JOIN users u ON p.user_id = u.id
        WHERE p.date = DATE('now') 
        AND p.notification_enabled = 1
        AND p.is_deleted = 0
        AND p.notification_time IS NOT NULL
    ''')
    
    results = cursor.fetchall()
    conn.close()
    return results