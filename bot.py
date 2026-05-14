import logging
import os
from datetime import datetime
import pytz
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from groq import Groq

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TASHKENT = pytz.timezone('Asia/Tashkent')
TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', 'SIZNING_TELEGRAM_TOKENINGIZ')
GROQ_KEY = os.environ.get('GROQ_API_KEY', 'SIZNING_GROQ_KALITINGIZ')
TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '8830711295:AAFKBbfKHU649R0dAUHA_tG2KviVo062W-4')
GROQ_KEY = os.environ.get('GROQ_API_KEY', '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')
groq_client = Groq(api_key=GROQ_KEY)
managers = {}
tasks = {}
task_counter = [0]

def now_tashkent():
    return datetime.now(TASHKENT).strftime('%d.%m.%Y %H:%M')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("👔 Menejer", callback_data='role_manager'),
         InlineKeyboardButton("👤 Jamoa a'zosi", callback_data='role_member')]
    ]
    await update.message.reply_text(
        f"Salom, {update.effective_user.first_name}! 👋\n\nRolingizni tanlang:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    uid = user.id
    name = user.first_name

    if query.data == 'role_manager':
        managers[uid] = {'name': name, 'username': user.username or name}
        if uid in members:
            del members[uid]
        await query.edit_message_text(
            f"✅ Siz *Menejer* sifatida ro'yxatdan o'tdingiz!\n\n"
            f"📋 *Buyruqlar:*\n"
            f"/vazifa — Hammaga vazifa yuborish\n"
            f"/shaxsiy — Biriga shaxsiy vazifa\n"
            f"/hammaga — Hammaga xabar\n"
            f"/vazifalar — Barcha vazifalar\n"
            f"/azolar — Jamoa ro'yxati\n"
            f"/hisobot — Kunlik hisobot\n"
            f"/sora — AI yordamchi\n"
            f"/yordam — Yordam",
            parse_mode='Markdown'
        )
    elif query.data == 'role_member':
        members[uid] = {'name': name, 'username': user.username or name}
        if uid in managers:
            del managers[uid]
        await query.edit_message_text(
            f"✅ Siz *Jamoa a'zosi* sifatida ro'yxatdan o'tdingiz!\n\n"
            f"📋 *Buyruqlar:*\n"
            f"/menvazifalar — Mening vazifalarim\n"
            f"/sora — AI yordamchi\n"
            f"/yordam — Yordam",
            parse_mode='Markdown'
        )
    elif query.data.startswith('status_'):
        parts = query.data.split('_')
        task_id = int(parts[1])
        status = parts[2]
        if task_id in tasks:
            tasks[task_id]['status'] = status
            status_text = {'done': '✅ Bajarildi', 'progress': '🔄 Jarayonda', 'notdone': '❌ Bajarilmadi'}
            tasks[task_id]['updated'] = now_tashkent()
            await query.edit_message_text(f"Vazifa holati: {status_text.get(status)}")
            for mid in managers:
                try:
                    await context.bot.send_message(
                        mid,
                        f"📊 *Vazifa holati yangilandi*\n"
                        f"Vazifa: {tasks[task_id]['text']}\n"
                        f"Holat: {status_text.get(status)}\n"
                        f"Kim: {query.from_user.first_name}\n"
                        f"Vaqt: {now_tashkent()}",
                        parse_mode='Markdown'
                    )
                except:
                    pass

async def vazifa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in managers:
        await update.message.reply_text("❌ Bu buyruq faqat menejerlar uchun!")
        return
    if not context.args:
        await update.message.reply_text("📝 Foydalanish: /vazifa <matn>")
        return
    text = ' '.join(context.args)
    deadline = None
    if 'muddat:' in text:
        parts = text.split('muddat:')
        text = parts[0].strip()
        deadline = parts[1].strip()
    task_counter[0] += 1
    task_id = task_counter[0]
    tasks[task_id] = {'text': text, 'deadline': deadline, 'status': 'notdone', 'created': now_tashkent(), 'by': managers[uid]['name']}
    keyboard = [[
        InlineKeyboardButton("✅ Bajarildi", callback_data=f'status_{task_id}_done'),
        InlineKeyboardButton("🔄 Jarayonda", callback_data=f'status_{task_id}_progress'),
        InlineKeyboardButton("❌ Bajarilmadi", callback_data=f'status_{task_id}_notdone')
    ]]
    sent = 0
    for mid in members:
        try:
            msg = f"📌 *Yangi vazifa #{task_id}*\n\n{text}"
            if deadline:
                msg += f"\n\n⏰ *Muddat:* {deadline}"
            msg += f"\n\n👔 *Menejer:* {managers[uid]['name']}\n🕐 *Vaqt:* {now_tashkent()}"
            await context.bot.send_message(mid, msg, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
            sent += 1
        except:
            pass
    await update.message.reply_text(f"✅ Vazifa {sent} ta a'zoga yuborildi!\n📌 Vazifa #{task_id}: {text}")

async def shaxsiy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in managers:
        await update.message.reply_text("❌ Bu buyruq faqat menejerlar uchun!")
        return
    if len(context.args) < 2:
        await update.message.reply_text("📝 Foydalanish: /shaxsiy @username <xabar>")
        return
    username = context.args[0].replace('@', '')
    text = ' '.join(context.args[1:])
    sent = False
    for mid, mdata in members.items():
        if mdata['username'].lower() == username.lower():
            try:
                task_counter[0] += 1
                task_id = task_counter[0]
                tasks[task_id] = {'text': text, 'status': 'notdone', 'created': now_tashkent(), 'by': managers[uid]['name'], 'assigned_to': username}
                keyboard = [[
                    InlineKeyboardButton("✅ Bajarildi", callback_data=f'status_{task_id}_done'),
                    InlineKeyboardButton("🔄 Jarayonda", callback_data=f'status_{task_id}_progress'),
                    InlineKeyboardButton("❌ Bajarilmadi", callback_data=f'status_{task_id}_notdone')
                ]]
                await context.bot.send_message(mid, f"📌 *Shaxsiy vazifa #{task_id}*\n\n{text}\n\n👔 *Menejer:* {managers[uid]['name']}\n🕐 *Vaqt:* {now_tashkent()}", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
                sent = True
            except:
                pass
    if sent:
        await update.message.reply_text(f"✅ Shaxsiy vazifa @{username} ga yuborildi!")
    else:
        await update.message.reply_text(f"❌ @{username} topilmadi!")

async def hammaga(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in managers:
        await update.message.reply_text("❌ Bu buyruq faqat menejerlar uchun!")
        return
    if not context.args:
        await update.message.reply_text("📝 Foydalanish: /hammaga <xabar>")
        return
    text = ' '.join(context.args)
    sent = 0
    for mid in members:
        try:
            await context.bot.send_message(mid, f"📢 *Menejerdan xabar*\n\n{text}\n\n🕐 {now_tashkent()}", parse_mode='Markdown')
            sent += 1
        except:
            pass
    await update.message.reply_text(f"✅ Xabar {sent} ta a'zoga yuborildi!")

async def vazifalar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not tasks:
        await update.message.reply_text("📋 Hozircha vazifalar yo'q.")
        return
    status_map = {'done': '✅', 'progress': '🔄', 'notdone': '❌'}
    msg = "📋 *Barcha vazifalar:*\n\n"
    for tid, t in tasks.items():
        msg += f"{status_map.get(t['status'], '❓')} *#{tid}* {t['text']}\n"
        if t.get('deadline'):
            msg += f"   ⏰ Muddat: {t['deadline']}\n"
        msg += f"   🕐 {t['created']}\n\n"
    await update.message.reply_text(msg, parse_mode='Markdown')

async def azolar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = "👥 *Jamoa ro'yxati:*\n\n"
    if managers:
        msg += "👔 *Menejerlar:*\n"
        for uid, d in managers.items():
            msg += f"  • {d['name']} (@{d['username']})\n"
    if members:
        msg += "\n👤 *A'zolar:*\n"
        for uid, d in members.items():
            msg += f"  • {d['name']} (@{d['username']})\n"
    if not managers and not members:
        msg = "Hozircha hech kim yo'q."
    await update.message.reply_text(msg, parse_mode='Markdown')

async def hisobot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in managers:
        await update.message.reply_text("❌ Bu buyruq faqat menejerlar uchun!")
        return
    done = sum(1 for t in tasks.values() if t['status'] == 'done')
    progress = sum(1 for t in tasks.values() if t['status'] == 'progress')
    notdone = sum(1 for t in tasks.values() if t['status'] == 'notdone')
    await update.message.reply_text(
        f"📊 *Kunlik hisobot*\n🕐 {now_tashkent()}\n\n"
        f"✅ Bajarildi: {done}\n🔄 Jarayonda: {progress}\n❌ Bajarilmadi: {notdone}\n📌 Jami: {len(tasks)}\n\n"
        f"👥 Menejerlar: {len(managers)}\n👤 A'zolar: {len(members)}",
        parse_mode='Markdown'
    )

async def sora(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("📝 Foydalanish: /sora <savol>")
        return
    question = ' '.join(context.args)
    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": f"Sen O'zbek va Rus tillarida javob beradigan aqlli yordamchisan. Hozirgi vaqt Toshkent bo'yicha: {now_tashkent()}. Qisqa va aniq javob ber."},
                {"role": "user", "content": question}
            ],
            max_tokens=500
        )
        await update.message.reply_text(f"🤖 {response.choices[0].message.content}")
    except Exception as e:
        await update.message.reply_text(f"❌ Xatolik: {str(e)}")

async def voice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in managers:
        await update.message.reply_text("❌ Ovozli xabar faqat menejerlar yuborishi mumkin!")
        return
    sent = 0
    for mid in members:
        try:
            await context.bot.forward_message(mid, update.effective_chat.id, update.message.message_id)
            sent += 1
        except:
            pass
    await update.message.reply_text(f"✅ Ovozli xabar {sent} ta a'zoga yuborildi!")

async def free_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": f"Sen jamoa boshqaruv botining AI yordamchisissan. Hozirgi vaqt (Toshkent): {now_tashkent()}. O'zbek yoki Rus tilida javob ber."},
                {"role": "user", "content": text}
            ],
            max_tokens=500
        )
        await update.message.reply_text(f"🤖 {response.choices[0].message.content}")
    except:
        await update.message.reply_text("❌ Xatolik yuz berdi.")

async def yordam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid in managers:
        msg = ("👔 *Menejer buyruqlari:*\n\n"
               "/vazifa <matn> — Hammaga vazifa\n"
               "/vazifa <matn> muddat: KK.OO — Muddatli vazifa\n"
               "/shaxsiy @username <matn> — Shaxsiy vazifa\n"
               "/hammaga <xabar> — Hammaga xabar\n"
               "/vazifalar — Barcha vazifalar\n"
               "/azolar — Jamoa ro'yxati\n"
               "/hisobot — Hisobot\n"
               "/sora <savol> — AI yordamchi\n")
    else:
        msg = ("👤 *A'zo buyruqlari:*\n\n"
               "/menvazifalar — Mening vazifalarim\n"
               "/sora <savol> — AI yordamchi\n"
               "/yordam — Yordam\n")
    await update.message.reply_text(msg, parse_mode='Markdown')

async def menvazifalar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user_tasks = {tid: t for tid, t in tasks.items()}
    if not user_tasks:
        await update.message.reply_text("📋 Sizga vazifa yuklanmagan.")
        return
    status_map = {'done': '✅', 'progress': '🔄', 'notdone': '❌'}
    msg = "📋 *Sizning vazifalaringiz:*\n\n"
    for tid, t in user_tasks.items():
        msg += f"{status_map.get(t['status'])} *#{tid}* {t['text']}\n\n"
    await update.message.reply_text(msg, parse_mode='Markdown')

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("vazifa", vazifa))
    app.add_handler(CommandHandler("shaxsiy", shaxsiy))
    app.add_handler(CommandHandler("hammaga", hammaga))
    app.add_handler(CommandHandler("vazifalar", vazifalar))
    app.add_handler(CommandHandler("azolar", azolar))
    app.add_handler(CommandHandler("hisobot", hisobot))
    app.add_handler(CommandHandler("sora", sora))
    app.add_handler(CommandHandler("yordam", yordam))
    app.add_handler(CommandHandler("menvazifalar", menvazifalar))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.VOICE, voice_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, free_text))
    logger.info("Bot ishga tushdi!")
    app.run_polling()

if __name__ == '__main__':
    main()
