import smtplib
import vk_api
import json
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import re
import time
from dotenv import load_dotenv
import os

# Загружаем переменные окружения
load_dotenv()
TOKEN = os.getenv("VK_TOKEN")
SMTP_EMAIL = os.getenv("SMTP_EMAIL")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")

# 🔹 Инициализация бота
vk_session = vk_api.VkApi(token=TOKEN)
vk = vk_session.get_api()
longpoll = VkBotLongPoll(vk_session, 218569753)  # ID группы

# 🔹 Хранилище данных пользователей
user_data = {}

# 🔹 Функции отправки сообщений
def send_message(user_id, message):
    try:
        vk.messages.send(user_id=user_id, message=message, random_id=int(time.time() * 1000))
    except vk_api.exceptions.ApiError as e:
        print(f"Ошибка VK API при отправке сообщения: {e}")

def send_keyboard(user_id, message, buttons):
    keyboard = {
        "one_time": True,
        "buttons": [[{"action": {"type": "text", "label": btn}, "color": "primary"}] for btn in buttons]
    }
    vk.messages.send(user_id=user_id, message=message, random_id=int(time.time() * 1000),
                     keyboard=json.dumps(keyboard, ensure_ascii=False))

def remove_keyboard(user_id, message):
    keyboard = {"buttons": [], "one_time": True}
    vk.messages.send(user_id=user_id, message=message, random_id=int(time.time() * 1000), keyboard=json.dumps(keyboard))

def send_email(subject, body):
    try:
        msg = MIMEMultipart()
        msg["From"] = SMTP_EMAIL
        msg["To"] = ADMIN_EMAIL
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        server = smtplib.SMTP_SSL("smtp.yandex.ru", 465)
        server.login(SMTP_EMAIL, SMTP_PASSWORD)
        server.sendmail(SMTP_EMAIL, ADMIN_EMAIL, msg.as_string())
        server.quit()
    except Exception as e:
        print(f"Ошибка отправки email: {e}")

# 🔹 Обработка сообщений
def process_message(user_id, message):
    if user_id not in user_data:
        user_data[user_id] = {}
        send_keyboard(user_id, "Выберите категорию:", ["Пациент 18+", "Родитель", "Ребенок"])
        return

    data = user_data[user_id]

    if "category" not in data:
        data["category"] = message
        remove_keyboard(user_id, "Введите ваше ФИО:")
        return

    if "fio" not in data:
        data["fio"] = message
        send_message(user_id, "Введите ваш телефон:")
        return

    if "phone" not in data:
        if re.match(r"^\+?\d{10,15}$", message):
            data["phone"] = message
            send_message(user_id, "Введите ваш email:")
        else:
            send_message(user_id, "❌ Введите корректный номер телефона.")
        return

    if "email" not in data:
        if re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", message):
            data["email"] = message
            if data["category"] == "Родитель":
                send_message(user_id, "Введите ФИО ребенка:")
            elif data["category"] == "Ребенок":
                send_message(user_id, "Введите ФИО родителя:")
            else:
                send_keyboard(user_id, "Выберите тип диабета:", ["Тип 1", "Тип 2"])
        else:
            send_message(user_id, "❌ Введите корректный email.")
        return

    if data["category"] == "Родитель" and "child_fio" not in data:
        data["child_fio"] = message
        send_message(user_id, "Введите дату рождения ребенка (ДД.ММ.ГГГГ):")
        return

    if data["category"] == "Родитель" and "child_dob" not in data:
        if re.match(r"\d{2}.\d{2}.\d{4}", message):
            data["child_dob"] = message
            send_keyboard(user_id, "Выберите тип диабета у ребенка:", ["Тип 1", "Тип 2"])
        else:
            send_message(user_id, "❌ Неверный формат даты. Введите в формате ДД.ММ.ГГГГ.")
        return

    if data["category"] == "Ребенок" and "parent_fio" not in data:
        data["parent_fio"] = message
        send_message(user_id, "Введите телефон родителя:")
        return

    if data["category"] == "Ребенок" and "parent_phone" not in data:
        if re.match(r"^\+?\d{10,15}$", message):
            data["parent_phone"] = message
            send_keyboard(user_id, "Выберите тип диабета:", ["Тип 1", "Тип 2", "Другой"])
        else:
            send_message(user_id, "❌ Введите корректный номер телефона.")
        return

    if "diabetes" not in data:
        data["diabetes"] = message
        send_keyboard(user_id, "Есть инвалидность?", ["Да", "Нет", "Прохожу МСЭ"])
        return

    if "disability" not in data:
        data["disability"] = message
        send_message(user_id, "Введите название населённого пункта:")
        return

    if "city" not in data:
        data["city"] = message
        send_message(user_id, "Введите название поликлиники:")
        return

    if "clinic" not in data:
        data["clinic"] = message
        send_message(user_id, "Опишите суть обращения:")
        return

    if "request" not in data:
        data["request"] = message

        application_text = f"""
        📄 Новая заявка:
        🔹 ФИО: {data["fio"]}
        🔹 Телефон: {data["phone"]}
        🔹 Email: {data["email"]}
        🔹 Категория: {data["category"]}
        🔹 ФИО родителя: {data.get("parent_fio", "-")}
        🔹 Телефон родителя: {data.get("parent_phone", "-")}
        🔹 ФИО ребенка: {data.get("child_fio", "-")}
        🔹 Дата рождения ребенка: {data.get("child_dob", "-")}
        🔹 Тип диабета: {data.get("diabetes", "-")}
        🔹 Инвалидность: {data["disability"]}
        🔹 Населенный пункт: {data["city"]}
        🔹 Поликлиника: {data["clinic"]}
        🔹 Суть обращения: {data["request"]}
        """

        send_email("Новая медицинская заявка", application_text)
        send_message(user_id, "✅ Ваша заявка отправлена!")

        del user_data[user_id]

# 🔹 Запуск бота
print("🚀 Бот запущен!")
for event in longpoll.listen():
    if event.type == VkBotEventType.MESSAGE_NEW and event.from_user:
        process_message(event.message.peer_id, event.message.text.strip())