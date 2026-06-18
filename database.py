import sqlite3
import os

DB_FILE = "stock_app.db"

def get_connection():
    return sqlite3.connect(DB_FILE)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Watchlist Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS watchlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT UNIQUE NOT NULL,
            name TEXT
        )
    ''')
    
    # Portfolio Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS portfolio (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT UNIQUE NOT NULL,
            name TEXT,
            quantity REAL NOT NULL,
            average_cost REAL NOT NULL
        )
    ''')
    
    # Settings Table (for API key etc)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

# --- Watchlist Functions ---

def get_watchlist():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT symbol, name FROM watchlist')
    rows = cursor.fetchall()
    conn.close()
    return [{"symbol": r[0], "name": r[1]} for r in rows]

def add_to_watchlist(symbol, name=""):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO watchlist (symbol, name) VALUES (?, ?)', (symbol, name))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False # Already exists

def remove_from_watchlist(symbol):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM watchlist WHERE symbol = ?', (symbol,))
    conn.commit()
    conn.close()

# --- Portfolio Functions ---

def get_portfolio():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT symbol, name, quantity, average_cost FROM portfolio')
    rows = cursor.fetchall()
    conn.close()
    return [{"symbol": r[0], "name": r[1], "quantity": r[2], "average_cost": r[3]} for r in rows]

def add_to_portfolio(symbol, name, quantity, average_cost):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT quantity, average_cost FROM portfolio WHERE symbol = ?', (symbol,))
        row = cursor.fetchone()
        
        if row:
            old_qty = row[0]
            old_cost = row[1]
            
            new_qty = old_qty + quantity
            
            if new_qty <= 0:
                cursor.execute('DELETE FROM portfolio WHERE symbol = ?', (symbol,))
            else:
                if quantity > 0:
                    # 買い増しの場合、加重平均で取得単価を計算
                    new_cost = (old_qty * old_cost + quantity * average_cost) / new_qty
                else:
                    # 売りの場合、取得単価は変わらない
                    new_cost = old_cost
                    
                cursor.execute('''
                    UPDATE portfolio 
                    SET name = ?, quantity = ?, average_cost = ?
                    WHERE symbol = ?
                ''', (name, new_qty, new_cost, symbol))
        else:
            if quantity > 0:
                cursor.execute('''
                    INSERT INTO portfolio (symbol, name, quantity, average_cost) 
                    VALUES (?, ?, ?, ?)
                ''', (symbol, name, quantity, average_cost))
            
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error adding to portfolio: {e}")
        return False

def remove_from_portfolio(symbol):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM portfolio WHERE symbol = ?', (symbol,))
    conn.commit()
    conn.close()

# --- Settings Functions ---

def get_setting(key, default=""):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else default

def set_setting(key, value):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO settings (key, value) VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value=excluded.value
    ''', (key, value))
    conn.commit()
    conn.close()

# Initialize DB on import
init_db()
