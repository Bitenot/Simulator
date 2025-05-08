# -*- coding: utf-8 -*-
import sqlite3
import telebot
import random
import time
from functools import wraps
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import sentry_sdk

sentry_sdk.init(
    dsn="https://179dc616054924dab0480879f689dd7b@o4509259448320000.ingest.de.sentry.io/4509259455004752",
    # Add data like request headers and IP for users,
    # see https://docs.sentry.io/platforms/python/data-management/data-collected/ for more info
    send_default_pii=True,
)

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
TOKEN = get_resource("TOKENS", 0)
DB_PATH = get_resource("PATHS", 0)
ADMINS_DB_PATH = get_resource("PATHS", 1)
BANNED_USERS_DB_PATH= get_resource("PATHS", 2)

bot = telebot.TeleBot(TOKEN)

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
            clprice INTEGER DEFAULT 60,
            farmprice INTEGER DEFAULT 85,
            vamprice INTEGER DEFAULT 170,
            chronos BOOLEAN DEFAULT 0,
            ares BOOLEAN DEFAULT 0,
            fortuna INTEGER DEFAULT 0,
            fortuna_price INTEGER DEFAULT 1500
        )
    """)

    columns = {
        "character_level": "INTEGER DEFAULT 1",
        "farm_level": "INTEGER DEFAULT 1",
        "vampirism": "INTEGER DEFAULT 0",
        "clprice": "INTEGER DEFAULT 60",
        "farmprice": "INTEGER DEFAULT 85",
        "vamprice": "INTEGER DEFAULT 170",
        "chronos": "BOOLEAN DEFAULT 0",
        "ares": "BOOLEAN DEFAULT 0",
        "fortuna": "INTEGER DEFAULT 0" ,
        "fortuna_price": "INTEGER DEFAULT 1500"
    }
    for column, column_type in columns.items():
        cursor.execute(f"PRAGMA table_info('{group_id}')")
        existing_columns = [info[1] for info in cursor.fetchall()]
        if column not in existing_columns:
            cursor.execute(f"ALTER TABLE '{group_id}' ADD COLUMN {column} {column_type}")
    conn.commit()
    conn.close()
    
user_locks = {}

def safe_command(func):
    @wraps(func)
    def wrapper(message, *args, **kwargs):
        global conn
        user_id = message.from_user.id
        if user_locks.get(user_id):
            bot.reply_to(message, "⏳ Подождите, предыдущая команда ещё не завершилась. Не спамьте, пожалуйста.")
            return

        user_locks[user_id] = True

        try:
            # Проверка на бан
            conn = sqlite3.connect(BANNED_USERS_DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM banned_users WHERE user_id = ?", (user_id,))
            if cursor.fetchone():
                bot.reply_to(message, "🚫 Вы забанены пермачем и не можете играть.\nОбращайтесь в поддержку если уверены что забанены ошибочно: @Thermobyte")
                return

            return func(message, *args, **kwargs)

        except Exception as e:
            bot.reply_to(message, f"⚠️ Произошла ошибка: {e}")
            raise  # можно убрать, если не хочешь логировать в консоль

        finally:
            conn.close()
            user_locks.pop(user_id, None)

    return wrapper

def safe_callback(func):
    @wraps(func)
    def wrapper(call, *args, **kwargs):
        user_id = call.from_user.id
        if user_locks.get(user_id):
            bot.answer_callback_query(call.id, "⏳ Подождите, предыдущая операция ещё не завершена.")
            return

        user_locks[user_id] = True

        try:
            conn = sqlite3.connect(BANNED_USERS_DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM banned_users WHERE user_id = ?", (user_id,))
            if cursor.fetchone():
                bot.answer_callback_query(call.id, "🚫 Вы забанены. Обратитесь в поддержку.")
                return

            return func(call, *args, **kwargs)

        except Exception as e:
            bot.answer_callback_query(call.id, f"⚠️ Ошибка: {e}", show_alert=True)
            raise

        finally:
            conn.close()
            user_locks.pop(user_id, None)

    return wrapper

def get_time_word(value: int, word_type: str) -> str:
    forms = {
        'секунда': ('секунду ', 'секунды ', 'секунд '),
        'минута': ('минуту ', 'минуты ', 'минут '),
        'час': ('час ', 'часа ', 'часов '),
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

def check_achievement(points, character_level, vampirism, fortuna, farm_level):
    achievements = []

    # Очки (points)
    if points >= 10_000_000_000:
        achievements.append("⭐️ Величайший")
    elif points >= 1_000_000_000:
        achievements.append("🏆 Мультимиллиардер")
    elif points >= 100_000_000:
        achievements.append("🌐 Миллиардер")
    elif points >= 10_000_000:
        achievements.append("🧐 Мультимиллионер")
    elif points >= 1_000_000:
        achievements.append("🕶 Миллионер")
    elif points >= 100_000:
        achievements.append("👑 Король")
    elif points >= 50_000:
        achievements.append("💍 Аристократ")
    elif points >= 10_000:
        achievements.append("💵 Магнат")
    elif points >= 1_000:
        achievements.append("💵 Богатый")

    # Уровень персонажа
    if character_level >= 6:
        achievements.append("🧑‍💻 CEO")

    # Вампиризм
    if vampirism >= 6:
        achievements.append("🧛🏻‍♀️ Дракула")

    # Уровень фермы
    if 1 <= farm_level <= 5:
        achievements.append("📉 Начинающий")
    elif 5 < farm_level <= 10:
        achievements.append("📈 Ученик")
    elif 10 < farm_level <= 15:
        achievements.append("💳 Стартапер")
    elif 15 < farm_level <= 20:
        achievements.append("📊 Бизнесмен")
    elif 20 < farm_level <= 30:
        achievements.append("💎 Предприниматель")
    elif 30 < farm_level <= 50:
        achievements.append("💳 Конкурент")
    elif 50 < farm_level <= 70:
        achievements.append("🌐 Международный делец")
    elif 70 < farm_level <= 100:
        achievements.append("🔈 В 10-ке New York Times")
    elif farm_level > 100:
        achievements.append("😈 Манипулятор рынка")

    # Удача (fortuna)
    if fortuna == 1:
        achievements.append("🍀 Везунчик")
    elif fortuna == 2:
        achievements.append("🎰 Избранник Фортуны")
    elif fortuna >= 3:
        achievements.append("🍀❤️ Любовник Фортуны")

    # Вернём строку, как нужно для телеграм-бота
    return ", ".join(achievements) if achievements else "Нет достижений"
    
def calculate_farm_price(farm_level, character_level):
    if 1 <= farm_level < 3:
        base_price = 100
    elif 3 <= farm_level < 5:
        base_price = 170
    elif 5 <= farm_level < 7:
        base_price = 230
    elif 7 <= farm_level < 10:
        base_price = 270
    elif 10 <= farm_level < 15:
        base_price = 350
    elif 15 <= farm_level < 30:
        base_price = 420
    elif 30 <= farm_level < 50:
        base_price = 670
    elif 50 <= farm_level < 70:
        base_price = 1000
    elif 70 <= farm_level <= 100:
        base_price = 1500
    else:
        base_price = 2500

    level_bonus = 5 * (farm_level - 1)
    boost_map = {
        2: 0.075,
        3: 0.113,
        4: 0.137,
        5: 0.16
    }
    character_boost = boost_map.get(character_level, 0)
    return round((base_price + level_bonus) * (1 + character_boost))

def get_rankings():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT user_id, SUM(points) FROM (" +
                   " UNION ALL ".join(
                       [f"SELECT user_id, points FROM '{table[0]}'"
                        for table in cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")]
                   ) +
                   ") GROUP BY user_id ORDER BY SUM(points) DESC"
                   )
    global_ranks = {row[0]: idx + 1 for idx, row in enumerate(cursor.fetchall())}

    conn.close()
    return global_ranks

@bot.message_handler(commands=['message'])
@safe_command
def send_custom_message(message):
    try:
        args = message.text.split(' ', 2)
        if len(args) < 3:
            bot.reply_to(message, "❌ Неправильный формат. Используй:\n/message <chat_id> <текст или photo:путь>")
            return

        chat_id = args[1]
        content = args[2]

        if content.startswith("photo:"):
            photo_path = content[6:].strip()
            with open(photo_path, 'rb') as photo:
                bot.send_photo(chat_id, photo, caption=f"📷 Фото от админа")
                bot.reply_to(message, f"✅ Фото отправлено в {chat_id}")
        else:
            bot.send_message(chat_id, content)
            bot.reply_to(message, f"✅ Сообщение отправлено в {chat_id}")

    except Exception as e:
        bot.reply_to(message, f"⚠️ Ошибка: {str(e)}")

def get_user_message(user_id: int) -> str | None:
    user_messages = {
        1766101476: "Доброго вам дня, Господин.",
        1866831769: "Привет, Ебалдуй хуев блять крч иди нахуй ну привет крч епта генерал Шварц мега накраузен биг гластер ибб хуевнамбас басбас некукашка.",
        1831570922: "Добро пожаловать, Паля хуй в анале .",
        1384347872: "Привет, Кама.",
        1078150755: "Здарова, Даня",
        1781529906: "Куку, Дяк",
        6113547946: "Давно не виделись, Хливнюк",
        5375127224: "Привет, администратор Настя",
        1883638589: "Сложней всего быть вратарём... Бущан",
        1963483010: "Хули ты тут забыл, Чура?",
        1178628743: "Ну типо привет, Ева",
        1280324225: "О май гад кто заставил тебя сюда зайти, Verаніка",
        1612850413: "Даже ты сюда зашел, Любчик. Я в ахуе",
        1423167585: "Нет, серьёзно! Кто заставил вас сюда заходить?",
        5259346309: "Ни за что бы не подумал что ты сюда зайдешь, Шуст",
        2022289714: "КАКОГО ХУЯ? КАТЯ??? ЧТО ТЫ ЗДЕСЬ МАТЬ ЕГО ДЕЛАЕШЬ???",
        1579674787: "Даже не думай в это играть",
        1347702394: "Арина, ты как сюда попала?",
        6837339007: "Школьный, пиздуй на ферму работать!"
    }

    return user_messages.get(user_id)

@bot.message_handler(commands=['start'])
@safe_command
def message_start(message):
    user_id = message.from_user.id
    msg = get_user_message(user_id)
    if msg:
        bot.reply_to(message, msg)

@bot.message_handler(commands=['sponsors'])
@safe_command
def sponsors_list(message):
    bot.reply_to(message, f"⭐️ Наши спонсоры:\n\n🏅@GoshaRubchinskiyyyyy - 3€(120грн)💶\n🥈@Dq_Dq_Dq - 11грн\n🥉@W_m_m_v_m_v - 11грн")

@bot.message_handler(commands=['admins'])
def admin_list(message):
    bot.reply_to(message, "🛡️ Действующие администраторы:\n\n👑 @Thermobyte - Owner\n⚜️ @lllapas - Heiress\n🤖 @AC_EvelineBot - Admin-bot")

@bot.message_handler(commands=['play'])
@safe_command
def play_game(message):
    user_id = message.from_user.id
    username = message.from_user.username or f"user_{user_id}"
    group_id = message.chat.id
    create_table(group_id)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        f"SELECT points, last_play, character_level, farm_level, vampirism, chronos, ares, fortuna FROM '{group_id}' WHERE user_id = ?",
        (user_id,))
    row = cursor.fetchone()

    now = int(time.time())
    if row:
        points, last_play, character_level, farm_level, vampirism, chronos, ares, fortuna = row
        cooldown_time = 13680 if chronos else 19800
        if now - last_play < cooldown_time:
            remaining_time = cooldown_time - (now - last_play)
            hours, remainder = divmod(remaining_time, 3600)
            minutes, seconds = divmod(remainder, 60)
            bot.reply_to(message,
                         f"Не запрягайте своих рабов, подождите {get_time_word(hours, 'час') if hours > 0 else ''}{get_time_word(minutes, 'минута') if minutes > 0 else ''}{get_time_word(seconds, 'секунда')}. У нас 21 век!")
            return
    else:
        points, last_play, character_level, farm_level, vampirism, chronos, ares, fortuna = 0, 0, 1, 1, 0, 0, 0, 0
        cursor.execute(
            f"INSERT INTO '{group_id}' (user_id, username, points, last_play, character_level, farm_level, vampirism, chronos, ares, fortuna) VALUES (?, ?, 0, 0, 1, 1, 0, 0, 0, 0)",
            (user_id, username))



    jackpot_chance = 0.085 if fortuna <= 0 else 0.05+(0.04*fortuna)
    max_points = (10 + (farm_level - 1) * 5) * 2
    jackpot_boots = True if farm_level < 6 else False
    jackpot = max_points * 2 * 1.7 * (1.15 if jackpot_boots else 1)

    if ares:
        if random.random() <= jackpot_chance:
            if fortuna >= 3 and random.random < 0.35:
                delta = jackpot*2
            elif fortuna >= 2:
                delta = jackpot * 1.2
            else:
                delta = jackpot
                bot.reply_to(message, f"🎉 Джекпот! Вы выиграли {int(delta)} очков! 🎉")
        else:
            delta = random.randint(1, 10 + (farm_level - 1) * 5)
    else:
        if random.random() <= jackpot_chance:
            if fortuna >= 3 and random.random < 0.5:
                delta = max_points * 2 * 1.7 * (1.15 if jackpot_boots else 1)
                delta = delta*2
            else:
                delta = max_points * 2 * 1.7 * (1.15 if jackpot_boots else 1)
            bot.reply_to(message, f"🎉 Джекпот! Вы выиграли {int(delta)} очков! 🎉")
        elif random.random() < 0.55:
            delta = random.randint(1, 10 + (farm_level - 1) * 5)
        else:
            delta = -random.randint(1, 10 + (farm_level - 1) * 5)

    if (character_level > 1 and random.random() < 0.1 + 0.15 * (character_level - 1 + (fortuna*0.05))) or (character_level >= 6):
        delta += random.randint(1, 10 + (farm_level - 1) * 5)
        
    if vampirism > 0 and random.random() <= (0.25+(vampirism*0.03)):
        cursor.execute(f"SELECT user_id, username, farm_level, points, fortuna FROM '{group_id}' WHERE user_id != ?", (user_id,))
        other_users = cursor.fetchall()
        if other_users:
            victim_id, victim_username, victim_farm_level, victim_points, victim_fortuna = random.choice(other_users)

            if victim_points <= 0:
                # Жертва без очков
                bot.reply_to(message, f"@{victim_username} слишком бомжара, у него нет школьных 😞")
            else:
                is_crit = random.random() < (0.20+(vampirism*0.01))   
                if is_crit:
                    base_steal = 10 + (vampirism * 3)
                    max_possible_steal = min(victim_points, victim_farm_level * vampirism + base_steal)
                    stolen_points = random.randint(1, base_steal)
                    stolen_points += round(victim_points * (0.10+(0.0125*vampirism)))  # 10% при крите
                else:
                    base_steal = 7 + (vampirism * 3)
                    max_possible_steal = min(victim_points, victim_farm_level * vampirism + base_steal)
                    percentage_steal = victim_points * (0.05+(0.0125*vampirism))
                    stolen_points = random.randint(1, base_steal)
                    stolen_points += round(percentage_steal)

                # Минусуем жертву и добавляем очки игроку
                if victim_fortuna >= 1 and random.random() <= 30+(victim_fortuna*0.065):
                    if vampirism >= 6 and random.random() <= 0.5:
                        cursor.execute(f"UPDATE '{group_id}' SET points = points - ? WHERE user_id = ?", (stolen_points, victim_id))
                        cursor.execute(f"UPDATE '{group_id}' SET points = points + ? WHERE user_id = ?", (stolen_points, user_id))
                        if stolen_points > 0:
                            crit_text = " (КРИТ! 💥)" if is_crit else ""
                            bot.reply_to(message, f"{crit_text}\n\nВы спиздили {stolen_points} Школьных у @{victim_username}")
                        else:
                            bot.reply_to(message, f"@{victim_username} оказался бомжарой — вы ничего не получили.")
                    else:
                        stolen_points = stolen_points*0.5
                        cursor.execute(f"UPDATE '{group_id}' SET points = points - ? WHERE user_id = ?", (stolen_points, user_id))
                        cursor.execute(f"UPDATE '{group_id}' SET points = points + ? WHERE user_id = ?", (stolen_points, victim_id))
                        if stolen_points > 0:
                            crit_text = " (КРИТ! 💥)" if is_crit else ""
                            bot.reply_to(message, f"{crit_text}\n\nФортуна благославила {victim_username}!\nУ вас отобрали {stolen_points} Школьных.")
                        else:
                            bot.reply_to(message, f"@{victim_username} оказался бомжарой — вы ничего не получили.")
                else:
                    cursor.execute(f"UPDATE '{group_id}' SET points = points - ? WHERE user_id = ?", (stolen_points, victim_id))
                    cursor.execute(f"UPDATE '{group_id}' SET points = points + ? WHERE user_id = ?", (stolen_points, user_id))
                    if stolen_points > 0:
                        crit_text = " (КРИТ! 💥)" if is_crit else ""
                        bot.reply_to(message, f"{crit_text}\n\nВы спиздили {stolen_points} Школьных у @{victim_username}")
                    else:
                         bot.reply_to(message, f"@{victim_username} оказался бомжарой — вы ничего не получили.")

    points += delta

    cursor.execute(f"UPDATE '{group_id}' SET points = ?, last_play = ? WHERE user_id = ?", (points, now, user_id))
    conn.commit()

    cursor.execute(f"SELECT user_id, points FROM '{group_id}' ORDER BY points DESC")
    local_ranks = {row[0]: idx + 1 for idx, row in enumerate(cursor.fetchall())}
    global_ranks = get_rankings()

    local_place = local_ranks.get(user_id, "N/A")
    global_place = global_ranks.get(user_id, "N/A")

    def check_delta(points):
        if points > 0:
            text = "появилось"
        else:
            text = "умерло"
        return text

    bot.reply_to(message, f"💵 @{username} на вашей ферме {check_delta(delta)} {abs(delta)} Школьных.\n"
                          f"👨🏿‍🦲 Теперь на ферме {points} Школьных.\n"
                          f"🏆 Вы занимаете {local_place} место в локальном топе.")

    conn.close()

@bot.message_handler(commands=['statistic'])
@safe_command
def show_stats(message):
    group_id = message.chat.id
    user_id = message.from_user.id
    create_table(group_id)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        f"SELECT username, points, character_level, farm_level, vampirism, chronos, ares, fortuna FROM '{group_id}' WHERE user_id = ?",
        (user_id,))
    stats = cursor.fetchone()
    conn.close()

    if not stats:
        bot.reply_to(message, "😰 Вы ещё не играли!")
        return

    username, points, character_level, farm_level, vampirism, chronos, ares, fortuna = stats
    achievement_text = check_achievement(points, character_level, vampirism, fortuna, farm_level)
    

    response = f"📜 Ваша статистика:\n\n"\
               f"👨🏿‍🦲 @{username}, у вас {points} Школьных.\n" \
               f"🧑🏻‍🌾 Уровень персонажа: {character_level}\n" \
               f"🏡 Уровень фермы: {farm_level}\n" \
               f"🧛🏻‍♀️ Вампиризм: {vampirism}\n" \
               f"➖ Минусофобия: {'Есть' if ares else 'Нету'}\n" \
               f"⌛️ Часы Кроноса: {'Есть' if chronos else 'Нету'}\n"\
               f"🍀 Метка Фортуны: {fortuna if fortuna > 0 else 'Нету'}\n\n"\
               f"🟡 Достижения: \n{achievement_text}"
    bot.reply_to(message, response)

@bot.message_handler(commands=['localtop'])
@safe_command
def show_stats(message):
    group_id = message.chat.id
    create_table(group_id)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(f"SELECT username, points FROM '{group_id}' ORDER BY points DESC")
    stats = cursor.fetchall()
    conn.close()

    if not stats:
        bot.reply_to(message, "👿 Пока никто не играл!")
        return

    medals = ["🥇", "🥈", "🥉"]
    response = "🏆 Локальный рейтинг:\n\n"

    for idx, row in enumerate(stats):
        medal = medals[idx] if idx < 3 else f"{idx + 1}."
        response += f"{medal} @{row[0]} - {row[1]} Школьных\n"

    bot.reply_to(message, response)


@bot.message_handler(commands=['top'])
@safe_command
def global_top(message):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()

    users = {}
    for table in tables:
        table_name = table[0]
        cursor.execute(f"SELECT user_id, username, points FROM '{table_name}'")
        for user_id, username, points in cursor.fetchall():
            if user_id not in users or users[user_id][1] < points:
                users[user_id] = (username, points)

    # Exclude user with ID 6837339007
    users = {k: v for k, v in users.items() if k != 6837339007}

    sorted_users = sorted(users.items(), key=lambda x: x[1][1], reverse=True)

    medals = ["🥇", "🥈", "🥉"]
    top_list = ""

    for i, (uid, (uname, pts)) in enumerate(sorted_users[:10]):
        prefix = medals[i] if i < 3 else f"{i + 1}."
        if uid == 5375127224:
            top_list += f"{prefix} @{uname} - ♾️ рабов\n"
        else:
            top_list += f"{prefix} @{uname} - {pts} рабов\n"

    conn.close()
    response = "🏆 Глобальный рейтинг:\n\n" + (top_list if top_list else "🤬 Пока никто не играет.")
    bot.reply_to(message, response)


@bot.message_handler(commands=['help'])
@safe_command
def help_command(message):
    bot.reply_to(message,
                 "🏡 Прокачать ферму Школьных - /play.\n🧐 Просмотреть статистику - /statistic.\n🏆 Глобальный топ фермеров - /top.\n"
                 "📖 Список команд: /commands.\n"
                 "⚔️ Бросить вызов другому игроку - /battlez @username.\n"
                 "⬆️ Прокачать уровни - /upgrade")


@bot.message_handler(commands=['events'])
@safe_command
def events_command(message):
    bot.reply_to(message, "📜 Информация о текущих событиях:\n"
                          "❌ Финальная стадия разработки. Конец сезона!\n\n Игрок который по окончанию сезона наберёт больше всего SPS - 84грн в звёздах телеграм")

@bot.message_handler(commands=['battlez'])
@safe_command
def battlez_command(message):
    try:
        _, target_username = message.text.split()
        if not target_username.startswith('@'):
            raise ValueError("❌ Неправильный формат имени пользователя.")
    except ValueError:
        bot.reply_to(message, "✅ Использование: /battlez @username")
        return

    user_id = message.from_user.id
    username = message.from_user.username or f"user_{user_id}"
    group_id = message.chat.id

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(f"SELECT user_id, points FROM '{group_id}' WHERE username = ?", (target_username[1:],))
    target_user = cursor.fetchone()

    if not target_user:
        bot.reply_to(message, f"❌ Пользователь {target_username} не найден в этой группе.")
        conn.close()
        return

    target_user_id, target_points = target_user
    if target_points <= 0:
        bot.reply_to(message, f"❌ Пользователя @{target_username} нельзя вызвать на дуэль, так как у него недостаточно очков.")
        conn.close()
        return

    if user_id == 6113547946:
        handle_battle(user_id, target_user_id, group_id, auto_accept=True)
    else:
        markup = InlineKeyboardMarkup()
        accept_button = InlineKeyboardButton("✅",
                                             callback_data=f"accept_battle|{user_id}|{target_user_id}|{group_id}")
        markup.add(accept_button)
        sent_message = bot.reply_to(message, f"⚔️ @{username} бросил вызов {target_username}", reply_markup=markup)
    conn.close()

@safe_command
def handle_battle_callback(call):
    if not call.data.startswith("accept_battle"):
        return

    _, challenger_id, target_id, group_id = call.data.split('|')
    challenger_id = int(challenger_id)
    target_id = int(target_id)
    group_id = int(group_id)

    if call.from_user.id != target_id:
        bot.answer_callback_query(call.id, "❌Вы не можете принять этот вызов.")
        return

    handle_battle(challenger_id, target_id, group_id, call=call)
    
@safe_command
def handle_battle(challenger_id, target_id, group_id, call=None, auto_accept=False):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(f"SELECT points FROM '{group_id}' WHERE user_id = ?", (challenger_id,))
    challenger_points = cursor.fetchone()[0]

    cursor.execute(f"SELECT points FROM '{group_id}' WHERE user_id = ?", (target_id,))
    target_points = cursor.fetchone()[0]

    if challenger_id == 1766101476:
        win_chance = 0.5
        max_points = 25
    else:
        win_chance = 0.5
        max_points = 25

    if random.random() < win_chance:
        delta = random.randint(1, max_points)
        winner_id, loser_id, points = challenger_id, target_id, delta
    else:
        delta = random.randint(1, max_points)
        winner_id, loser_id, points = target_id, challenger_id, delta

    cursor.execute(f"UPDATE '{group_id}' SET points = points + ? WHERE user_id = ?", (points, winner_id))
    cursor.execute(f"UPDATE '{group_id}' SET points = points - ? WHERE user_id = ?", (points, loser_id))
    conn.commit()

    cursor.execute(f"SELECT username, points FROM '{group_id}' WHERE user_id = ?", (winner_id,))
    winner_username, winner_points = cursor.fetchone()

    cursor.execute(f"SELECT username, points FROM '{group_id}' WHERE user_id = ?", (loser_id,))
    loser_username, loser_points = cursor.fetchone()

    conn.close()

    if call:
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                              text=f"⚔️ Битва завершена! @{winner_username} победил @{loser_username} и получил {points} очков.\n\n"
                                   f"👨🏿‍🦲 Баланс @{winner_username}: {winner_points} Школьных.\n"
                                   f"👨🏿‍🦲 Баланс @{loser_username}: {loser_points} Школьных.")
    else:
        bot.send_message(group_id,
                         text=f"⚔️ Битва завершена! @{winner_username} победил @{loser_username} и получил {points} очков.\n\n"
                              f"👨🏿‍🦲 Баланс @{winner_username}: {winner_points} Школьных.\n"
                              f"👨🏿‍🦲 Баланс @{loser_username}: {loser_points} Школьных.")


@bot.message_handler(commands=['upgradeinfo'])
@safe_command
def help_command(message):
    bot.reply_to(message,
                 "💵\n\nПрокачка рабовладельца даёт вам +15% шанса к получению дополнительных рабов на свою ферму за каждый уровень от 1 до 10 + очки от уровня фермы. Максимум: 5.\n\nПрокачка фермы повышает максимально возможное число получения и уменьшения рабов за 1 игру на 5 за каждый уровень.\n\nСпособность вампиризм даёт 25% шанс выкачать из рандомного игрока рандомно от 1 очков + ? за каждый уровень и уровень фермы +3.75% баланса жертвы, шанс 15% на крит - 10% от баланса жертвы. Максимум: 5\n\nЧасы кроноса снижают время перезарядки /play на 38%\n\n")

@bot.message_handler(commands=['superskills'])
@safe_command
def help_command(message):
    bot.reply_to(message,
                 f"💵\n\nМетка Фортуны:\nПервый уровень: повышает шанс на джекпот в зависимости от уровня способности (Максимум до 18%),  ")

@bot.message_handler(commands=['upgrade'])
@safe_command
@safe_callback
def upgrade_command(message):
    user_id = message.from_user.id
    group_id = message.chat.id
    create_table(group_id)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        f"SELECT points, character_level, clprice, farm_level, farmprice, vampirism, vamprice, chronos, fortuna, fortuna_price FROM '{group_id}' WHERE user_id = ?",
        (user_id,))
    points, character_level, clprice, farm_level, farmprice, vampirism, vamprice, chronos, fortuna, fortuna_price = cursor.fetchone()

    farmprice = calculate_farm_price(farm_level, character_level)

    # === Кнопки ===
    markup = InlineKeyboardMarkup()
    level_button = InlineKeyboardButton(f"👨🏿‍🦲 - {clprice}", callback_data=f"upgrade_character|{user_id}|{group_id}")
    farm_button = InlineKeyboardButton(f"🏡 - {farmprice}", callback_data=f"upgrade_farm|{user_id}|{group_id}")
    vamp_button = InlineKeyboardButton(f"🧛🏻‍♀️ - {vamprice}", callback_data=f"upgrade_vampirism|{user_id}|{group_id}")
    chronos_button = InlineKeyboardButton(f"⏳ - 330", callback_data=f"buy_chronos|{user_id}|{group_id}")
    fortuna_love = InlineKeyboardButton(f"🍀 - {fortuna_price}", callback_data=f"upgrade_fortuna|{user_id}|{group_id}")
    markup.add(level_button, farm_button, vamp_button, chronos_button, fortuna_love)

    bot.reply_to(message, f"🟢 Ваши очки: {points}\n❓ Выберите, что вы хотите улучшить:", reply_markup=markup)

@safe_callback
def handle_upgrade_callback(call):
    if call.data.startswith("upgrade_character"):
        _, user_id, group_id = call.data.split('|')
        user_id = int(user_id)
        group_id = int(group_id)

        if call.from_user.id != user_id:
            bot.answer_callback_query(call.id, "❌ Это не ваша кнопка")
            return

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            f"SELECT points, character_level, clprice, farm_level, farmprice, vampirism, vamprice, chronos, fortuna, fortuna_price FROM '{group_id}' WHERE user_id = ?",
            (user_id,))
        points, character_level, clprice, farm_level, farmprice, vampirism, vamprice, chronos, fortuna, fortuna_price = cursor.fetchone()

        if points >= clprice and character_level < 6:
            if character_level == 5:
                clprice = 1500
            elif character_level < 5:
                points -= clprice
                character_level += 1
                clprice = int(clprice * 1.25)
            cursor.execute(f"UPDATE '{group_id}' SET points = ?, character_level = ?, clprice = ? WHERE user_id = ?",
                           (points, character_level, clprice, user_id))
            conn.commit()
            bot.answer_callback_query(call.id, f"👨🏿‍🦲 Уровень персонажа повышен до {character_level}!")
        else:
            bot.answer_callback_query(call.id,
                                      "❌ Недостаточно очков для повышения уровня или достигнут максимальный уровень.")

        markup = InlineKeyboardMarkup()
        level_button = InlineKeyboardButton(f"👨🏿‍🦲 - {clprice}",callback_data=f"upgrade_character|{user_id}|{group_id}")
        farm_button = InlineKeyboardButton(f"🏡 - {farmprice}", callback_data=f"upgrade_farm|{user_id}|{group_id}")
        vamp_button = InlineKeyboardButton(f"🧛🏻‍♀️ - {vamprice}", callback_data=f"upgrade_vampirism|{user_id}|{group_id}")
        chronos_button = InlineKeyboardButton(f"⏳ - 330", callback_data=f"buy_chronos|{user_id}|{group_id}")
        fortuna_love = InlineKeyboardButton(f"🍀 - {fortuna_price}", callback_data=f"upgrade_fortuna|{user_id}|{group_id}")
        markup.add(level_button, farm_button, vamp_button, chronos_button, fortuna_love)

        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"🟢 Ваши очки: {points}\n❓ Выберите, что вы хотите улучшить:",
            reply_markup=markup
        )
        conn.close()

    elif call.data.startswith("upgrade_farm"):
        _, user_id, group_id = call.data.split('|')
        user_id = int(user_id)
        group_id = int(group_id)

        if call.from_user.id != user_id:
            bot.answer_callback_query(call.id, "❌ Не ваша кнопка", show_alert=True)
            return

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            f"SELECT points, character_level, clprice, farm_level, farmprice, vampirism, vamprice, chronos, fortuna, fortuna_price FROM '{group_id}' WHERE user_id = ?",
            (user_id,))
        points, character_level, clprice, farm_level, farmprice, vampirism, vamprice, chronos, fortuna, fortuna_price = cursor.fetchone()

        new_farmprice = calculate_farm_price(farm_level, character_level)

        if points >= new_farmprice:
            points -= new_farmprice
            farm_level += 1
            farmprice = new_farmprice
            cursor.execute(f"UPDATE '{group_id}' SET points = ?, farm_level = ?, farmprice = ? WHERE user_id = ?",
                           (points, farm_level, farmprice, user_id))
            conn.commit()
            bot.answer_callback_query(call.id, f"🏡 Ферма улучшена до уровня {farm_level}!")
        else:
            bot.answer_callback_query(call.id, "❌ Недостаточно очков для улучшения фермы.")

        markup = InlineKeyboardMarkup()
        level_button = InlineKeyboardButton(f"👨🏿‍🦲 - {clprice}",callback_data=f"upgrade_character|{user_id}|{group_id}")
        farm_button = InlineKeyboardButton(f"🏡 - {farmprice}", callback_data=f"upgrade_farm|{user_id}|{group_id}")
        vamp_button = InlineKeyboardButton(f"🧛🏻‍♀️ - {vamprice}",callback_data=f"upgrade_vampirism|{user_id}|{group_id}")
        chronos_button = InlineKeyboardButton(f"⏳ - 330", callback_data=f"buy_chronos|{user_id}|{group_id}")
        fortuna_love = InlineKeyboardButton(f"🍀 - {fortuna_price}",callback_data=f"upgrade_fortuna|{user_id}|{group_id}")
        markup.add(level_button, farm_button, vamp_button, chronos_button, fortuna_love)

        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"🟢 Ваши очки: {points}\n❓ Выберите, что вы хотите улучшить:",
            reply_markup=markup
        )
        conn.close()

    elif call.data.startswith("upgrade_vampirism"):
        _, user_id, group_id = call.data.split('|')
        user_id = int(user_id)
        group_id = int(group_id)

        if call.from_user.id != user_id:
            bot.answer_callback_query(call.id, "❌ Не ваша кнопка", show_alert=True)
            return

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            f"SELECT points, character_level, clprice, farm_level, farmprice, vampirism, vamprice, chronos, fortuna, fortuna_price FROM '{group_id}' WHERE user_id = ?",
            (user_id,))
        points, character_level, clprice, farm_level, farmprice, vampirism, vamprice, chronos, fortuna, fortuna_price = cursor.fetchone()

        if points >= vamprice and vampirism < 6:
                if vampirism < 5:
                    points -= vamprice
                    vampirism += 1
                    vamprice = int(vamprice * 1.825)
                    vamprice += 5*(farm_level - 1)
                elif vampirism == 5:
                    points -= vamprice
                    vampirism += 1
                    vamprice = 3000
                    vamprice += 7*(farm_level - 1)

                    cursor.execute(f"UPDATE '{group_id}' SET points = ?, vampirism = ?, vamprice = ? WHERE user_id = ?",
                                   (points, vampirism, vamprice, user_id))
                    conn.commit()
                    bot.answer_callback_query(call.id, f"✅ Вампиризм прокачан до {vampirism}!")

                else:
                    bot.answer_callback_query(call.id,
                                              "❌ Недостаточно очков для прокачки вампиризма или достигнут максимальный уровень.")

                markup = InlineKeyboardMarkup()
                level_button = InlineKeyboardButton(f"👨🏿‍🦲 - {clprice}",callback_data=f"upgrade_character|{user_id}|{group_id}")
                farm_button = InlineKeyboardButton(f"🏡 - {farmprice}", callback_data=f"upgrade_farm|{user_id}|{group_id}")
                vamp_button = InlineKeyboardButton(f"🧛🏻‍♀️ - {vamprice}",callback_data=f"upgrade_vampirism|{user_id}|{group_id}")
                chronos_button = InlineKeyboardButton(f"⏳ - 330", callback_data=f"buy_chronos|{user_id}|{group_id}")
                fortuna_love = InlineKeyboardButton(f"🍀 - {fortuna_price}",callback_data=f"upgrade_fortuna|{user_id}|{group_id}")
                markup.add(level_button, farm_button, vamp_button, chronos_button, fortuna_love)

                bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text=f"🟢 Ваши очки: {points}\n❓ Выберите, что вы хотите улучшить:",
                    reply_markup=markup
                )
        conn.close()

    elif call.data.startswith("buy_chronos"):
        _, user_id, group_id = call.data.split('|')
        user_id = int(user_id)
        group_id = int(group_id)

        if call.from_user.id != user_id:
            bot.answer_callback_query(call.id, "❌ Не ваша кнопка", show_alert=True)
            return

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            f"SELECT points, character_level, clprice, farm_level, farmprice, vampirism, vamprice, chronos, fortuna, fortuna_price FROM '{group_id}' WHERE user_id = ?",
            (user_id,))
        points, character_level, clprice, farm_level, farmprice, vampirism, vamprice, chronos, fortuna, fortuna_price = cursor.fetchone()

        if points >= 330 and not chronos:
            points -= 330
            chronos = 1
            cursor.execute(f"UPDATE '{group_id}' SET points = ?, chronos = ? WHERE user_id = ?",
                           (points, chronos, user_id))
            conn.commit()
            bot.answer_callback_query(call.id, "✅ Часы Кроноса куплены!")
        else:
            bot.answer_callback_query(call.id, "❌ Недостаточно очков для покупки Chronos или он уже куплен.")

        markup = InlineKeyboardMarkup()
        level_button = InlineKeyboardButton(f"👨🏿‍🦲 - {clprice}", callback_data=f"upgrade_character|{user_id}|{group_id}")
        farm_button = InlineKeyboardButton(f"🏡 - {farmprice}", callback_data=f"upgrade_farm|{user_id}|{group_id}")
        vamp_button = InlineKeyboardButton(f"🧛🏻‍♀️ - {vamprice}",callback_data=f"upgrade_vampirism|{user_id}|{group_id}")
        chronos_button = InlineKeyboardButton(f"⏳ - 330", callback_data=f"buy_chronos|{user_id}|{group_id}")
        fortuna_love = InlineKeyboardButton(f"🍀 - {fortuna_price}",callback_data=f"upgrade_fortuna|{user_id}|{group_id}")
        markup.add(level_button, farm_button, vamp_button, chronos_button, fortuna_love)

        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"🟢 Ваши очки: {points}\n❓ Выберите, что вы хотите улучшить:",
            reply_markup=markup
        )
        conn.close()

    elif call.data.startswith("upgrade_fortuna"):
            _, user_id, group_id = call.data.split('|')
            user_id = int(user_id)
            group_id = int(group_id)

            if call.from_user.id != user_id:
                bot.answer_callback_query(call.id, "❌ Не ваша кнопка", show_alert=True)
                return

            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute(
                f"SELECT points, character_level, clprice, farm_level, farmprice, vampirism, vamprice, chronos, fortuna, fortuna_price FROM '{group_id}' WHERE user_id = ?",
                (user_id,))
            points, character_level, clprice, farm_level, farmprice, vampirism, vamprice, chronos, fortuna, fortuna_price = cursor.fetchone()
            
            if points > fortuna_price and fortuna < 3:
                if fortuna == 0:
                    points -= fortuna_price
                    fortuna += 1
                    fortuna_price = 3300
                elif fortuna == 1:
                    points -= fortuna_price
                    fortuna += 1
                    fortuna_price = 7000
                    fortuna_price += 23*(farm_level-1)
                    
                cursor.execute(f"UPDATE '{group_id}' SET points = ?, fortuna = ?, fortuna_price = ? WHERE user_id = ?",
                           (points, fortuna, fortuna_price, user_id))
                conn.commit()
                bot.answer_callback_query(call.id, f"✅ Метка фортуны прокачана до {fortuna}!")
            else:
                bot.answer_callback_query(call.id,
                                          "❌ Недостаточно очков для удовлетворения Фортуны или достигнут максимальный уровень.")
            markup = InlineKeyboardMarkup()
            level_button = InlineKeyboardButton(f"👨🏿‍🦲 - {clprice}",
                                                callback_data=f"upgrade_character|{user_id}|{group_id}")
            farm_button = InlineKeyboardButton(f"🏡 - {farmprice}", callback_data=f"upgrade_farm|{user_id}|{group_id}")
            vamp_button = InlineKeyboardButton(f"🧛🏻‍♀️ - {vamprice}",
                                               callback_data=f"upgrade_vampirism|{user_id}|{group_id}")
            chronos_button = InlineKeyboardButton(f"⏳ - 330", callback_data=f"buy_chronos|{user_id}|{group_id}")
            fortuna_love = InlineKeyboardButton(f"🍀 - {fortuna_price}",
                                                callback_data=f"upgrade_fortuna|{user_id}|{group_id}")
            markup.add(level_button, farm_button, vamp_button, chronos_button, fortuna_love)

            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=f"🟢 Ваши очки: {points}\n❓ Выберите, что вы хотите улучшить:",
                reply_markup=markup
            )

            conn.close()

bot.register_callback_query_handler(handle_upgrade_callback, func=lambda call: call.data.startswith(("upgrade", "buy_chronos")))
bot.register_callback_query_handler(handle_battle_callback, func=lambda call: call.data.startswith("accept_battle"))

bot.polling(none_stop=True)
