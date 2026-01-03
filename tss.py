import telebot
import sqlite3
import random
import time
import string
from datetime import datetime
import threading
import os

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "ВАШ_ТОКЕН")
bot = telebot.TeleBot(TOKEN)

# База данных
def init_db():
    conn = sqlite3.connect('game.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT, balance INTEGER DEFAULT 0, btc REAL DEFAULT 0)')
    c.execute('CREATE TABLE IF NOT EXISTS projects (user_id INTEGER, name TEXT, online INTEGER DEFAULT 0, hosting TEXT DEFAULT "Game Free")')
    conn.commit()
    conn.close()

init_db()

# Мини-игра
current_game = {"active": False, "question": "", "answer": 0, "winner": None}
game_lock = threading.Lock()

def auto_game():
    while True:
        time.sleep(300)  # 5 минут
        with game_lock:
            if not current_game["active"]:
                a = random.randint(10, 50)
                b = random.randint(10, 50)
                op = random.choice(['+', '-', '*'])
                if op == '+':
                    ans = a + b
                    q = f"{a} + {b}"
                elif op == '-':
                    ans = a - b
                    q = f"{a} - {b}"
                else:
                    ans = a * b
                    q = f"{a} × {b}"
                
                current_game["active"] = True
                current_game["question"] = q
                current_game["answer"] = ans
                current_game["winner"] = None
                
                # Убери или замени на свою группу
                # bot.send_message("@ваша_группа", f"🎯 КОНКУРС!\nРешите: {q}\n💰 Приз: 100,000$\nВведите ответ!")

threading.Thread(target=auto_game, daemon=True).start()

# Команды
@bot.message_handler(commands=['start'])
def start(m):
    bot.send_message(m.chat.id, "🎮 YANG TRAPPA\n\nКоманды:\n/crmp название - создать проект\n/my - мой проект\n/balance - баланс\n/bonus - бонус\n/game - текущая игра\n/top - топ")

@bot.message_handler(commands=['crmp'])
def create_project_cmd(m):
    user_id = m.from_user.id
    username = m.from_user.username or m.from_user.first_name
    args = m.text.split()
    if len(args) < 2:
        bot.reply_to(m, "Нужно: /crmp Название")
        return
    
    name = args[1]
    conn = sqlite3.connect('game.db')
    c = conn.cursor()
    
    c.execute('SELECT * FROM projects WHERE user_id = ?', (user_id,))
    if c.fetchone():
        bot.reply_to(m, "❌ Уже есть проект")
        return
    
    c.execute('INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)', (user_id, username))
    c.execute('INSERT INTO projects (user_id, name) VALUES (?, ?)', (user_id, name))
    c.execute('UPDATE users SET balance = balance + 300000, btc = btc + 2 WHERE user_id = ?', (user_id,))
    
    conn.commit()
    conn.close()
    
    bot.reply_to(m, f"✅ Проект '{name}' создан!\n💰 +300,000$ и 2 BTC")

@bot.message_handler(commands=['my'])
def my_project(m):
    user_id = m.from_user.id
    conn = sqlite3.connect('game.db')
    c = conn.cursor()
    c.execute('SELECT * FROM projects WHERE user_id = ?', (user_id,))
    proj = c.fetchone()
    c.execute('SELECT balance, btc FROM users WHERE user_id = ?', (user_id,))
    user = c.fetchone()
    conn.close()
    
    if not proj:
        bot.reply_to(m, "❌ Нет проекта")
        return
    
    bot.reply_to(m, f"📊 {proj[1]}\n💰 ${user[0]:,}\n₿ {user[1]:.1f}\n👥 {proj[2]}\n🖥️ {proj[3]}")

@bot.message_handler(commands=['balance'])
def balance(m):
    user_id = m.from_user.id
    conn = sqlite3.connect('game.db')
    c = conn.cursor()
    c.execute('SELECT balance, btc FROM users WHERE user_id = ?', (user_id,))
    user = c.fetchone()
    conn.close()
    
    if user:
        bot.reply_to(m, f"💰 ${user[0]:,}\n₿ {user[1]:.1f}")
    else:
        bot.reply_to(m, "❌ Нет аккаунта")

@bot.message_handler(commands=['bonus'])
def bonus(m):
    user_id = m.from_user.id
    amount = random.randint(55000, 150000)
    conn = sqlite3.connect('game.db')
    c = conn.cursor()
    c.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (amount, user_id))
    conn.commit()
    conn.close()
    bot.reply_to(m, f"🎁 +${amount:,}")

@bot.message_handler(commands=['game'])
def game_info(m):
    with game_lock:
        if current_game["active"] and not current_game["winner"]:
            bot.reply_to(m, f"🎯 Текущая игра:\n{current_game['question']}\n💰 Приз: 100,000$")
        else:
            bot.reply_to(m, "🎮 Следующая игра через 5 минут")

@bot.message_handler(commands=['top'])
def top(m):
    conn = sqlite3.connect('game.db')
    c = conn.cursor()
    c.execute('SELECT username, balance FROM users ORDER BY balance DESC LIMIT 10')
    top_users = c.fetchall()
    conn.close()
    
    text = "🏆 ТОП 10:\n"
    for i, (name, bal) in enumerate(top_users, 1):
        text += f"{i}. {name}: ${bal:,}\n"
    
    bot.reply_to(m, text)

# Проверка ответов на игру
@bot.message_handler(func=lambda m: True)
def check_answer(m):
    if m.text.isdigit():
        with game_lock:
            if current_game["active"] and not current_game["winner"]:
                if int(m.text) == current_game["answer"]:
                    user_id = m.from_user.id
                    username = m.from_user.username or m.from_user.first_name
                    
                    conn = sqlite3.connect('game.db')
                    c = conn.cursor()
                    c.execute('UPDATE users SET balance = balance + 100000 WHERE user_id = ?', (user_id,))
                    conn.commit()
                    conn.close()
                    
                    current_game["winner"] = username
                    current_game["active"] = False
                    
                    bot.reply_to(m, f"🏆 {username} выиграл 100,000$!")
                    bot.send_message(m.chat.id, f"✅ Ответ: {current_game['question']} = {current_game['answer']}")

print("✅ Бот запускается...")
bot.polling(none_stop=True)