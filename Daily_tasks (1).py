import logging
import asyncio
import nest_asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CallbackQueryHandler, ContextTypes
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
from pytz import timezone

nest_asyncio.apply()
TOKEN = "7587071583:AAFN8TC9Od89D_nhe7scVholgT9NUenJBnY"
GROUP_CHAT_ID = -4960478787
logging.basicConfig(level=logging.INFO)

# تخزين البيانات الديناميكية للوحة الأزرار
current_keyboard = []
current_message_id = None
user_task_log = {}

daily_tasks = {
    0: [  # Понедельник
        "Чистка кофемолки",
        "Протереть верхние полки в баре",
        "Протереть подоконники",
        "Проверить чистоту в туалетах",
        "Поливка цветов",
        "Протереть перила"
    ],
    1: [  # Вторник
        "Протереть стены в баре",
        "Попросить мойщицу оттереть стыки",
        "Помыть раковину",
        "Проверить чистоту в туалетах"
    ],
    2: [  # Среда
        "Протереть стойки самообслуживания",
        "Протереть подоконники",
        "Порядок на полках под баром",
        "Проверить чистоту в туалетах"
    ],
    3: [  # Четверг
        "Протереть плафоны на 1 и 2 этажах",
        "Порядок на складе",
        "Протереть книжный стеллаж",
        "Протереть подоконники",
        "Проверить чистоту в туалетах",
        "Поливка цветов",
        "Протереть перила"
    ],
    4: [  # Пятница
        "Помыть барные холодильники",
        "Протереть подоконники",
        "Помыть обе витрины",
        "Проверить чистоту в туалетах"
    ],
    5: [  # Суббота
        "Помыть и прибрать зону выдачи на кухне",
        "Протереть подоконники",
        "Проверить чистоту в туалетах"
    ],
    6: [  # Воскресенье
        "Протереть книжный стеллаж",
        "Протереть подоконники",
        "Проверить чистоту в туалетах",
        "Проверить и пополнить все схранилища и антисептики",
        "Поливка цветов",
        "Протереть перила"
    ]
}

async def send_daily_task(context: ContextTypes.DEFAULT_TYPE):
    global current_keyboard, current_message_id, user_task_log
    time_now = datetime.now(timezone("Asia/Yekaterinburg"))
    day = time_now.weekday()
    date_str = time_now.strftime("%d.%m.%Y")
    tasks = daily_tasks.get(day, [])

    user_task_log.clear()

    if not tasks:
        await context.bot.send_message(chat_id=GROUP_CHAT_ID, text="📭 Сегодня заданий нет")
        return

    day_names = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
    header = f"🧼 *{day_names[day]} – {date_str}*\nВыберите выполненные задачи:"

    current_keyboard = []
    for i, task in enumerate(tasks):
        current_keyboard.append([InlineKeyboardButton(f"☑ {task}", callback_data=f"task_{i}")])
    current_keyboard.append([InlineKeyboardButton("✅ Я всё выполнил!", callback_data="all_done")])

    sent_message = await context.bot.send_message(
        chat_id=GROUP_CHAT_ID,
        text=header,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(current_keyboard)
    )

    current_message_id = sent_message.message_id

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
        index = int(data.split("_")[1])
        if 0 <= index < len(tasks):
            if index in user_task_log[user_id]:
                await context.bot.send_message(chat_id=GROUP_CHAT_ID, text=f"⚠️ {user_name}, вы уже отметили задачу: *{tasks[index]}*", parse_mode="Markdown")
            else:
                user_task_log[user_id].add(index)
                await context.bot.send_message(chat_id=GROUP_CHAT_ID, text=f"✅ {user_name} выполнил(а) задачу: *{tasks[index]}*", parse_mode="Markdown")

                # 🧠 حذف الزر من اللوحة
                new_keyboard = []
                for row in current_keyboard:
                    new_row = [btn for btn in row if btn.callback_data != data]
                    if new_row:
                        new_keyboard.append(new_row)
                current_keyboard = new_keyboard

                # تحديث الرسالة بالأزرار الجديدة
                await context.bot.edit_message_reply_markup(
                    chat_id=GROUP_CHAT_ID,
                    message_id=current_message_id,
                    reply_markup=InlineKeyboardMarkup(current_keyboard)
                )

async def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CallbackQueryHandler(button_handler))

    class DummyContext:
        bot = app.bot

    await send_daily_task(DummyContext())

    scheduler = BackgroundScheduler(timezone="Asia/Yekaterinburg")
    scheduler.add_job(lambda: asyncio.create_task(send_daily_task(DummyContext())), "cron", hour=13, minute=0)
    scheduler.start()

    print("🤖 Бот запущен и работает...")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())