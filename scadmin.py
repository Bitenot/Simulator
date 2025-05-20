# -*- coding: utf-8 -*-

import sqlite3
import telebot
import time

def get_resource(section: str, line_index: int = None, path: str = "resources.txt") -> str | list[str]:
    section = section.strip().upper()
    start_marker = f"==== {section} ===="
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    inside_section = False
    section_lines = []

    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith("====") and section in line:
            inside_section = True
            continue
        elif line.startswith("====") and inside_section:
            break
        elif inside_section:
            section_lines.append(line)

    if not section_lines:
        raise ValueError(f"Раздел '{section}' не найден или пуст в {path}")

    if line_index is not None:
        if line_index >= len(section_lines):
            raise IndexError(f"В разделе '{section}' нет строки с индексом {line_index}")
        return section_lines[line_index]

ADMIN_ID = 1766101476
TOKEN = get_resource("TOKENS", 1)
DB_PATH = get_resource("PATHS", 0)
ADMINS_DB_PATH = get_resource("PATHS", 1)
BANNED_USERS_DB_PATH= get_resource("PATHS", 2)

bot = telebot.TeleBot(TOKEN)

def init_admins_db():
    conn = sqlite3.connect(ADMINS_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            user_id INTEGER PRIMARY KEY,
            username TEXT
        )
    """)
    # Добавляем главного админа, если его нет
    cursor.execute("INSERT OR IGNORE INTO admins (user_id, username) VALUES (?, ?)", (ADMIN_ID, ""))
    conn.commit()
    conn.close()

init_admins_db()

def create_table(group_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS '{group_id}' (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            points INTEGER DEFAULT 0,
            last_play INTEGER DEFAULT 0,
            character_level INTEGER DEFAULT 1,
            farm_level INTEGER DEFAULT 1,
            vampirism INTEGER DEFAULT 0,
            clprice INTEGER DEFAULT 70,
            farmprice INTEGER DEFAULT 120,
            vamprice INTEGER DEFAULT 100,
            chronos BOOLEAN DEFAULT 0,
            ares BOOLEAN DEFAULT 0,
            fortuna INTEGER DEFAULT 0,
            fortuna_price INTEGER DEFAULT 1500,
            rebirth_level INTEGER DEFAULT 1
        )
    """)
    conn.commit()
    conn.close()

def get_time_word(value: int, word_type: str) -> str:
    forms = {
        'секунда': ('секунда', 'секунды', 'секунд'),
        'минута': ('минута', 'минуты', 'минут'),
        'час': ('час', 'часа', 'часов'),
    }

    if word_type not in forms:
        raise ValueError("Неверный тип времени. Используй: 'секунда', 'минута', 'час'.")

    n = abs(value)
    last_two = n % 100
    last_digit = n % 10

    # Определение формы слова
    if 11 <= last_two <= 14:
        form = forms[word_type][2]
    elif last_digit == 1:
        form = forms[word_type][0]
    elif 2 <= last_digit <= 4:
        form = forms[word_type][1]
    else:
        form = forms[word_type][2]

    return f"{value} {form}"

user_locks = {}

def check_admin(user_id):
    global user_locks

    # Если пользователь уже обрабатывается
    if user_locks.get(user_id):
        return False  # не даём второй вызов

    # Блокируем
    user_locks[user_id] = True

    try:
        conn = sqlite3.connect(ADMINS_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM admins WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        conn.close()

        return result is not None or user_id == ADMIN_ID or user_id == 1781529906 or user_id == 5375127224 or user_id == 1178628743

    finally:
        # Снимаем блокировку в любом случае
        user_locks.pop(user_id, None)

def load_rebirth_data(file_path="/home/bitnami/schoolar/rebirth_data.txt"):
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()

    multiplier_section = []
    price_section = []

    current_section = None
    for line in lines:
        if line.strip() == "====multiplier====":
            current_section = "multiplier"
            continue
        elif line.strip() == "====prices====":
            current_section = "prices"
            continue

        if current_section == "multiplier" and line.strip():
            multiplier_section.append(float(line.strip()))
        elif current_section == "prices" and line.strip():
            price_section.append(int(line.strip()))

    return multiplier_section, price_section


def get_rebirth_multiplier(rebirth_level, file_path="/home/bitnami/schoolar/rebirth_data.txt"):
    multipliers, _ = load_rebirth_data(file_path)
    index = max(0, rebirth_level - 1)  # чтобы при rebirth_level = 1 брать индекс 0
    if index < len(multipliers):
        return multipliers[index]
    return 1.0


def get_rebirth_price(rebirth_level, file_path="/home/bitnami/schoolar/rebirth_data.txt"):
    _, prices = load_rebirth_data(file_path)
    index = rebirth_level - 1  # цена следующего ребитха
    if 0 <= index < len(prices):
        return prices[index]
    return None

def get_rebirth_names(rebirth_level):
    name = "Костыль"
    if rebirth_level == 2:
        name = "Сэнку Исигами"
    elif rebirth_level == 3:
        name = "Тодзи Фусигуро"
    elif rebirth_level == 4:
        name = "Рейхардт Ван Астрея"
    elif rebirth_level == 5:
        name = "Чёрный Мечник"
    elif rebirth_level == 6:
        name = "Луфасу Мафаалу"
    elif rebirth_level == 7:
        name = "Ван Лин"
    elif rebirth_level == 7:
        name = "Римуру Темпест"
    elif rebirth_level == 8:
        name = "Анос Вольдигоад"
    elif rebirth_level == 9:
        name = "Ева"
    elif rebirth_level == 10:
        name = "Йогири Такато"
    elif rebirth_level == 11:
        name = "Фезарин"
    elif rebirth_level == 12:
        name = "Cat"
    elif rebirth_level == 13:
        name = "Анафабаула"
    elif rebirth_level == 14:
        name = "Алый король"
    elif rebirth_level == 15:
        name = "SCP 303 GOD"
    elif rebirth_level == 16:
        name = "Azatoth"
    elif rebirth_level == 17:
        name = "Writer"
    elif rebirth_level == 18:
        name = "SCP 3018"
    elif rebirth_level == 19:
        name = "ABSS"
    elif rebirth_level == 20:
        name = "I AM THAT I AM"
    elif rebirth_level > 20:
        name = "I AM THAT I AM"
    else:
        name = "Костыль"
    return name

@bot.message_handler(commands=['support'])
def handle_support(message):
    # Удаляем команду и оставляем только сообщение
    user_msg = message.text[len('/support'):].strip()
    
    if not user_msg:
        bot.reply_to(message, "Пожалуйста, напиши сообщение после команды /support.")
        return

    # Отправка сообщения владельцу бота
    support_text = f"📩 Сообщение от @{message.from_user.username or 'без username'} (ID: {message.from_user.id}):\n\n{user_msg}"
    bot.send_message(ADMIN_ID, support_text)
    bot.reply_to(message, "Сообщение отправлено в поддержку. Спасибо!")

@bot.message_handler(commands=['admin'])
def admin_command(message):
    if not message.from_user.id == ADMIN_ID:
        bot.reply_to(message, "❌ У вас нет прав для выполнения этой команды.")
        return

    try:
        _, identifier = message.text.split()
    except ValueError:
        bot.reply_to(message, "✅ Использование: /admin id/username")
        return

    conn = sqlite3.connect(ADMINS_DB_PATH)
    cursor = conn.cursor()

    # Проверяем, является ли identifier числом (ID)
    if identifier.isdigit():
        user_id = int(identifier)
        cursor.execute("INSERT OR IGNORE INTO admins (user_id, username) VALUES (?, ?)", (user_id, ""))
        bot.reply_to(message, f"✅ Пользователь с ID {user_id} добавлен в администраторы.")
    else:
        # Удаляем @ если он есть
        username = identifier[1:] if identifier.startswith('@') else identifier
        cursor.execute("INSERT OR IGNORE INTO admins (user_id, username) VALUES (NULL, ?)", (username,))
        bot.reply_to(message, f"✅ Пользователь @{username} добавлен в администраторы.")

    conn.commit()
    conn.close()

@bot.message_handler(commands=['admins'])
def admin_list(message):
    if not check_admin(message.from_user.id):
        bot.reply_to(message, "❌ У вас нет прав для выполнения этой команды.")
        return

    bot.reply_to(message, f"🛡️ Действующие администраторы:\n\n"
                               f"👑 @Thermobyte - Owner:\n\tУровень доступа: o5.\n\tРоль: разработчик\n\tСрок: Навсегда\n"
                               f"⚜️ @lllapas - Heiress:\n\tУровень доступа: o4\n\tРоль: наследник владельца\n\tСрок: Навсегда\n"
                               f"🤖 @AC_EvelineBot - Admin-bot.\n\tУровень доступа: o3.5\n\tРоль: админ панель\n\tСрок: Навсегда")

@bot.message_handler(commands=['limit'])
def ban_user(message):
    if not check_admin(message.from_user.id):
        bot.reply_to(message, "❌ У вас нет прав для выполнения этой команды.")
        return

    try:
        _, target_username, ban_time = message.text.split()
        if not target_username.startswith('@'):
            raise ValueError("Неправильный формат имени пользователя.")
        ban_time = int(ban_time)
    except ValueError:
        bot.reply_to(message, "✅ Использование: /ban @username time (минуты)")
        return

    group_id = message.chat.id

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(f"SELECT user_id FROM '{group_id}' WHERE username = ?", (target_username[1:],))
    target_user_id = cursor.fetchone()
    
    if not target_user_id:
        bot.reply_to(message, f"❌ Пользователь {target_username} не найден в этой группе.")
        conn.close()
        return

    target_user_id = target_user_id[0]
    ban_until = int(time.time()) + (ban_time * 60)
    cursor.execute(f"UPDATE '{group_id}' SET last_play = ? WHERE user_id = ?", (ban_until, target_user_id))
    conn.commit()
    conn.close()
    bot.reply_to(message, f"✅ Пользователь {target_username} забанен на {ban_time} минут.")

@bot.message_handler(commands=['reset'])
def reset_data(message):
    if not check_admin(message.from_user.id):
        bot.reply_to(message, "❌ У вас нет прав для выполнения этой команды.")
        return

    try:
        _, subcommand, target_username = message.text.split()
        if not target_username.startswith('@'):
            raise ValueError("Неправильный формат имени пользователя.")
    except ValueError:
        bot.reply_to(message, "✅ Использование: /reset time/stats @username")
        return

    group_id = message.chat.id

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(f"SELECT user_id FROM '{group_id}' WHERE username = ?", (target_username[1:],))
    target_user_id = cursor.fetchone()
    
    if not target_user_id:
        bot.reply_to(message, f"❌ Пользователь {target_username} не найден в этой группе.")
        conn.close()
        return

    target_user_id = target_user_id[0]

    if subcommand == 'time':
        cursor.execute(f"UPDATE '{group_id}' SET last_play = 0 WHERE user_id = ?", (target_user_id,))
        bot.reply_to(message, f"✅ Время перезарядки для {target_username} сброшено.")
    elif subcommand == 'stats':
        cursor.execute(f"UPDATE '{group_id}' SET points = 0, last_play = 0, character_level = 1, farm_level = 1, vampirism = 0, clprice = 70, farmprice = 120, vamprice = 120, chronos = 0, ares = 0, fortuna = 0, fortuna_price = 1500, rebirth_level = 1 WHERE user_id = ?", (target_user_id,))
        bot.reply_to(message, f"✅ Статистика {target_username} сброшена.")
    else:
        bot.reply_to(message, "Использование: /reset time/stats @username")
        return

    conn.commit()
    conn.close()

@bot.message_handler(commands=['add'])
def add_points(message):
    if not check_admin(message.from_user.id):
        bot.reply_to(message, "❌ У вас нет прав для выполнения этой команды.")
        return

    try:
        _, subcommand, target_username, points = message.text.split()
        if not target_username.startswith('@') or subcommand != 'points':
            raise ValueError("Неправильный формат команды.")
        points = int(points)
    except ValueError:
        bot.reply_to(message, "✅ Использование: /add points @username количество")
        return

    group_id = message.chat.id

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(f"SELECT user_id FROM '{group_id}' WHERE username = ?", (target_username[1:],))
    target_user_id = cursor.fetchone()
    
    if not target_user_id:
        bot.reply_to(message, f"❌ Пользователь {target_username} не найден в этой группе.")
        conn.close()
        return

    target_user_id = target_user_id[0]
    cursor.execute(f"UPDATE '{group_id}' SET points = points + ? WHERE user_id = ?", (points, target_user_id))
    conn.commit()
    conn.close()
    bot.reply_to(message, f"✅ Пользователю {target_username} добавлено {points} очков.")

@bot.message_handler(commands=['set'])
def set_skill(message):
    if not check_admin(message.from_user.id):
        bot.reply_to(message, "❌ У вас нет прав для выполнения этой команды.")
        return

    try:
        _, subcommand, skill_name, level = message.text.split()
        level = int(level)
    except ValueError:
        bot.reply_to(message, "✅ Использование: /set skill название уровень")
        return

    group_id = message.chat.id
    skill_column = {
        'character': 'character_level',
        'farm': 'farm_level',
        'vampirism': 'vampirism',
        'ares': 'ares',
        'chronos': 'chronos',
        'fortuna': 'fortuna',
        'rebirth': 'rebirth_level'
    }.get(skill_name.lower())

    if not skill_column:
        bot.reply_to(message, "❌ Недопустимое название способности. Используйте character, farm, vampirism, ares или chronos.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(f"UPDATE '{group_id}' SET {skill_column} = ? WHERE user_id = ?", (level, message.from_user.id))
    conn.commit()
    conn.close()
    bot.reply_to(message, f"✅ Уровень способности {skill_name} установлен на {level}.")

@bot.message_handler(commands=['getdata'])
def user_info(message):
    if not check_admin(message.from_user.id):
        bot.reply_to(message, "❌ У вас нет прав для выполнения этой команды.")
        return

    try:
        _, target_username = message.text.split()
        if not target_username.startswith('@'):
            raise ValueError("Неправильный формат имени пользователя.")
    except ValueError:
        bot.reply_to(message, "✅ Использование: /info @username")
        return

    group_id = message.chat.id

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM '{group_id}' WHERE username = ?", (target_username[1:],))
    user_data = cursor.fetchone()
    conn.close()

    if not user_data:
        bot.reply_to(message, f"❌ Пользователь {target_username} не найден.")
        return

    rebirth_level = user_data[14]  # Индекс 14 соответствует rebirth_level

    response = (f"📜 Информация о {target_username}:\n"
                f"👨🏿‍🦲 Очки: {user_data[2]}\n"
                f"🕐 Время последней игры: {user_data[3]}\n"
                f"🧑🏻‍🌾 Уровень персонажа: {user_data[4]}\n"
                f"🏡 Уровень фермы: {user_data[5]}\n"
                f"🧛🏻‍♀️ Вампиризм: {user_data[6]}\n"
                f"💵 Цена повышения уровня персонажа: {user_data[7]}\n"
                f"💵 Цена повышения вампиризма: {user_data[9]}\n"
                f"⌛️ Часы кроноса: {'Да' if user_data[10] else 'Нет'}\n"
                f"➖ Минусофобия: {'Да' if user_data[11] else 'Нет'}\n"
                f"🍀 Метка Фортуны: {user_data[12] if user_data[12]>0 else 'Нет'}\n"
                f"\n🟢 Ребитх: {rebirth_level} - 👑{get_rebirth_names(rebirth_level)}👑. Множитель: x{get_rebirth_multiplier(rebirth_level)}")
    bot.reply_to(message, response)

@bot.message_handler(commands=['stop'])
def stop_bot(message):
    if not check_admin(message.from_user.id):
        bot.reply_to(message, "❌ У вас нет прав для выполнения этой команды.")
        return
    bot.reply_to(message, "✅ Бот остановлен.")
    bot.stop_polling()

@bot.message_handler(commands=['permanent'])
def ban_user(message):
    if not check_admin(message.from_user.id):
        bot.reply_to(message, "❌ У вас нет прав для выполнения этой команды.")
        return

    try:
        banned_id = int(message.text.split()[1])
    except (IndexError, ValueError):
        bot.reply_to(message, "⚠️ Использование: /permanent <user_id>")
        return

    conn = sqlite3.connect(BANNED_USERS_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO banned_users (user_id) VALUES (?)", (banned_id,))
    conn.commit()
    conn.close()

    bot.reply_to(message, f"🔒 Пользователь {banned_id} забанен.")

@bot.message_handler(commands=['pardon'])
def unban_user(message):
    if not check_admin(message.from_user.id):
        bot.reply_to(message, "❌ У вас нет прав для выполнения этой команды.")
        return

    try:
        unbanned_id = int(message.text.split()[1])
    except (IndexError, ValueError):
        bot.reply_to(message, "⚠️ Использование: /unban <user_id>")
        return

    conn = sqlite3.connect(BANNED_USERS_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM banned_users WHERE user_id = ?", (unbanned_id,))
    conn.commit()
    conn.close()

    bot.reply_to(message, f"✅ Пользователь {unbanned_id} разбанен.")

bot.polling(none_stop=True)
