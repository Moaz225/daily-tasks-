import logging
import asyncio
import os
from datetime import datetime
from pytz import timezone
from flask import Flask, request, redirect

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import Application, CallbackQueryHandler, ContextTypes

# ----------------------------------------------------
# 1. الإعدادات الأساسية
# ----------------------------------------------------
TOKEN = os.environ.get("TELEGRAM_TOKEN", "7587071583:AAFN8TC9Od89D_nhe7scVholgT9NUenJBnY")
GROUP_CHAT_ID = -4960478787
# هذا مفتاح سري لحماية روابطك. اختر أي نص عشوائي طويل
SECRET_KEY = os.environ.get("SECRET_KEY", "YOUR_LONG_RANDOM_SECRET_KEY_HERE_12345")

logging.basicConfig(level=logging.INFO)

# ----------------------------------------------------
# 2. إعداد تطبيق البوت وتطبيق الويب
# ----------------------------------------------------
app_flask = Flask(__name__)
app_telegram = Application.builder().token(TOKEN).build()

# ----------------------------------------------------
# 3. بيانات البوت (المهام والمتغيرات) - لا تغيير هنا
# ----------------------------------------------------
current_keyboard = []
current_message_id = None
user_task_log = {}

daily_tasks = {
    0: ["Чистка кофемолки", "Протереть верхние полки в баре", "Протереть подоконники", "Проверить чистоту в туалетах", "Поливка цветов", "Протереть перила"],
    1: ["Протереть стены в баре", "Попросить мойщицу оттереть стыки", "Помыть раковину", "Проверить чистоту в туалетах"],
    2: ["Протереть стойки самообслуживания", "Протереть подоконники", "Порядок на полках под баром", "Проверить чистоту в туалетах"],
    3: ["Протереть плафоны на 1 и 2 этажах", "Порядок на складе", "Протереть книжный стеллаж", "Протереть подоконники", "Проверить чистоту в туалетах", "Поливка цветов", "Протереть перила"],
    4: ["Помыть барные холодильники", "Протереть подоконники", "Помыть обе витрины", "Проверить чистоту в туалетах"],
    5: ["Помыть и прибрать зону выдачи на кухне", "Протереть подоконники", "Проверить чистоту в туалетах"],
    6: ["Протереть книжный стеллаж", "Протереть подоконники", "Проверить чистоту в туалетах", "Проверить и пополнить все схранилища и антисептики", "Поливка цветов", "Протереть перила"]
}

# ----------------------------------------------------
# 4. وظيفة إرسال المهام (تم تعديلها قليلاً)
# ----------------------------------------------------
async def send_daily_task(application: Application):
    """
    يرسل قائمة المهام. يتم استدعاؤه الآن بواسطة المنبه الخارجي.
    """
    global current_keyboard, current_message_id, user_task_log
    time_now = datetime.now(timezone("Asia/Yekaterinburg"))
    day = time_now.weekday()
    date_str = time_now.strftime("%d.%m.%Y")
    tasks = daily_tasks.get(day, [])

    user_task_log.clear()

    if not tasks:
        await application.bot.send_message(chat_id=GROUP_CHAT_ID, text="📭 Сегодня заданий нет")
        return

    day_names = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
    header = f"🧼 *{day_names[day]} – {date_str}*\nВыберите выполненные задачи:"

    current_keyboard = []
    for i, task in enumerate(tasks):
        current_keyboard.append([InlineKeyboardButton(f"☑ {task}", callback_data=f"task_{i}")])
    current_keyboard.append([InlineKeyboardButton("✅ Я всё выполнил!", callback_data="all_done")])

    try:
        sent_message = await application.bot.send_message(
            chat_id=GROUP_CHAT_ID,
            text=header,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(current_keyboard)
        )
        current_message_id = sent_message.message_id
    except Exception as e:
        logging.error(f"Failed to send message: {e}")

# ----------------------------------------------------
# 5. معالج الأزرار (لا تغيير هنا)
# ----------------------------------------------------
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global current_keyboard, current_message_id
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user_name = query.from_user.first_name
    time_now = datetime.now(timezone("Asia/Yekaterinburg"))
    day = time_now.weekday()
    tasks = daily_tasks.get(day, [])

    if user_id not in user_task_log:
        user_task_log[user_id] = set()

    data = query.data

    if data == "all_done":
        await context.bot.send_message(chat_id=GROUP_CHAT_ID, text=f"✅ {user_name} выполнил(а) *все* задачи!", parse_mode="Markdown")
        return

    if data.startswith("task_"):
        try:
            index = int(data.split("_")[1])
            if 0 <= index < len(tasks):
                task_text = tasks[index]
                if index in user_task_log[user_id]:
                    await query.message.reply_text(f"⚠️ {user_name}, вы уже отметили задачу: *{task_text}*", parse_mode="Markdown")
                else:
                    user_task_log[user_id].add(index)
                    await query.message.reply_text(f"✅ {user_name} выполнил(а) задачу: *{task_text}*", parse_mode="Markdown")
                    
                    # حذف الزر
                    new_keyboard = [row for row in current_keyboard if not (len(row) == 1 and row[0].callback_data == data)]
                    current_keyboard = new_keyboard

                    await context.bot.edit_message_reply_markup(
                        chat_id=GROUP_CHAT_ID,
                        message_id=current_message_id,
                        reply_markup=InlineKeyboardMarkup(current_keyboard)
                    )
        except Exception as e:
            logging.error(f"Error processing button click: {e}")

# ----------------------------------------------------
# 6. مسارات (Routes) خادم الويب
# ----------------------------------------------------

@app_flask.route("/")
def index():
    # صفحة رئيسية بسيطة للتأكد أن الخادم يعمل
    return "Bot is alive!"

@app_flask.route(f"/webhook", methods=['POST'])
def webhook_handler():
    """هذا المسار يستقبل التحديثات من تيليجرام"""
    async def process_update():
        update = Update.de_json(request.get_json(force=True), app_telegram.bot)
        await app_telegram.process_update(update)
    
    asyncio.run(process_update())
    return 'ok', 200

@app_flask.route(f"/trigger_daily_task/{SECRET_KEY}", methods=['GET'])
def trigger_task():
    """
    هذا هو المسار السري الذي سيزوره المنبه الخارجي.
    """
    async def run_task():
        await send_daily_task(app_telegram)
    
    asyncio.run(run_task())
    return "Daily task triggered", 200

@app_flask.route(f"/set_webhook/{SECRET_KEY}", methods=['GET'])
def set_webhook():
    """
    قم بزيارة هذا الرابط مرة واحدة فقط بعد النشر لربط البوت.
    """
    RENDER_URL = os.environ.get('RENDER_EXTERNAL_URL')
    if not RENDER_URL:
        return "Error: RENDER_EXTERNAL_URL not set"
        
    webhook_url = f"{RENDER_URL}/webhook"
    
    async def run_set_webhook():
        await app_telegram.bot.set_webhook(webhook_url)
        return f"Webhook set successfully to {webhook_url}"
    
    return asyncio.run(run_set_webhook())

# ----------------------------------------------------
# 7. نقطة البدء
# ----------------------------------------------------
if __name__ == "__main__":
    # تسجيل معالج الأزرار
    app_telegram.add_handler(CallbackQueryHandler(button_handler))
    
    # لا تقم بتشغيل app_flask.run() هنا
    # Render سيستخدم gunicorn لتشغيله
    pass
