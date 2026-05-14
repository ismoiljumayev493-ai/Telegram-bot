import logging
import os
import requests
from datetime import datetime
import pytz
from telegram import Update, ChatPermissions
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ChatMemberHandler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TASHKENT = pytz.timezone('Asia/Tashkent')
TOKEN = os.environ.get('MODERATOR_BOT_TOKEN', '8453410881:AAGrN42Vstfoh1uNrUTlmMnIbdDfv-KkMeI')
GROQ_KEY = os.environ.get('GROQ_API_KEY', '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')

# Ma'lumotlar bazasi
users = {}
warnings = {}
banned = {}
admin_ids = set()

SPAM_WORDS = ['spam', 'reklama', 'click here', 'subscribe', 't.me/', 'http://', 'https://']
BAD_WORDS = ['haqorat1', 'haqorat2']  # O'zingiz qo'shing

def now():
    return datetime.now(TASHKENT).strftime('%d.%m.%Y %H:%M')

def is_admin(uid):
    return uid in admin_ids

async def check_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admins = await context.bot.get_chat_administrators(update.effective_chat.id)
    admin_ids.clear()
    for admin in admins:
        admin_ids.add(admin.user.id)

async def new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        uid = member.id
        name = member.first_name
        username = member.username or name
        
        if uid not in users:
            users[uid] = {
                'name': name,
                'username': username,
                'qoshilgan': now(),
                'xabarlar': 0,
                'oxirgi_xabar': None,
                'ogohlantirishlar': 0,
                'ban_tarixi': [],
                'faol': True
            }
        
        await update.message.reply_text(
            f"👋 Xush kelibsiz, {name}!\n\n"
            f"📋 Guruh qoidalari:\n"
            f"1. Spam va reklama taqiqlangan\n"
            f"2. Haqorat taqiqlangan\n"
            f"3. Begona linklar taqiqlangan\n\n"
            f"Qoidalarni buzgan holda ⚠️ ogohlantirish beriladi.\n"
            f"3 ta ogohlantirish = 🚫 Ban!"
        )

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_user:
        return
    
    await check_admin(update, context)
    
    user = update.effective_user
    uid = user.id
    text = update.message.text or ''
    
    # Foydalanuvchi ma'lumotini yangilash
    if uid not in users:
        users[uid] = {
            'name': user.first_name,
            'username': user.username or user.first_name,
            'qoshilgan': now(),
            'xabarlar': 0,
            'oxirgi_xabar': None,
            'ogohlantirishlar': 0,
            'ban_tarixi': [],
            'faol': True
        }
    
    users[uid]['xabarlar'] += 1
    users[uid]['oxirgi_xabar'] = now()
    users[uid]['faol'] = True
    
    # Admin xabarlarini tekshirmaymiz
    if is_admin(uid):
        return
    
    # Spam tekshiruvi
    text_lower = text.lower()
    spam_topildi = any(word in text_lower for word in SPAM_WORDS)
    haqorat_topildi = any(word in text_lower for word in BAD_WORDS)
    
    if spam_topildi or haqorat_topildi:
        try:
            await update.message.delete()
            sabab = "spam/reklama" if spam_topildi else "haqorat"
            
            if uid not in warnings:
                warnings[uid] = 0
            warnings[uid] += 1
            users[uid]['ogohlantirishlar'] += 1
            
            qolgan = 3 - warnings[uid]
            
            if warnings[uid] >= 3:
                await context.bot.ban_chat_member(update.effective_chat.id, uid)
                banned[uid] = {'vaqt': now(), 'sabab': sabab}
                users[uid]['ban_tarixi'].append({'vaqt': now(), 'sabab': sabab})
                await update.effective_chat.send_message(
                    f"🚫 {user.first_name} guruhdan ban qilindi!\n"
                    f"Sabab: {sabab}\n"
                    f"3/3 ogohlantirish to'ldi."
                )
            else:
                await update.effective_chat.send_message(
                    f"⚠️ {user.first_name}, {sabab} taqiqlangan!\n"
                    f"Ogohlantirish: {warnings[uid]}/3\n"
                    f"Yana {qolgan} ta ogohlantirish = Ban!"
                )
        except Exception as e:
            logger.error(f"Xato: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 *Moderator Bot ishga tushdi!*\n\n"
        "📋 *Admin buyruqlari:*\n"
        "/kim @username — A'zo haqida ma'lumot\n"
        "/ban @username — Banlaish\n"
        "/unban @username — Bandan chiqarish\n"
        "/ogohlantir @username — Ogohlantirish\n"
        "/top — Eng faol a'zolar\n"
        "/sust — Faol bo'lmagan a'zolar\n"
        "/statistika — Guruh statistikasi\n"
        "/qoidalar — Guruh qoidalari\n"
        "/yordam — Yordam",
        parse_mode='Markdown'
    )

async def kim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await check_admin(update, context)
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Bu buyruq faqat adminlar uchun!")
        return
    
    if not context.args:
        await update.message.reply_text("📝 Foydalanish: /kim @username")
        return
    
    username = context.args[0].replace('@', '').lower()
    topildi = None
    
    for uid, data in users.items():
        if data['username'].lower() == username:
            topildi = (uid, data)
            break
    
    if not topildi:
        await update.message.reply_text(f"❌ @{username} topilmadi!")
        return
    
    uid, data = topildi
    warn_count = warnings.get(uid, 0)
    faollik = "🟢 Faol" if data['faol'] else "🔴 Faol emas"
    ban_count = len(data.get('ban_tarixi', []))
    
    msg = (
        f"👤 *A'zo haqida ma'lumot:*\n\n"
        f"📛 Ismi: {data['name']}\n"
        f"🔗 Username: @{data['username']}\n"
        f"📅 Qo'shilgan: {data['qoshilgan']}\n"
        f"💬 Xabarlar soni: {data['xabarlar']}\n"
        f"⏰ Oxirgi xabar: {data['oxirgi_xabar'] or 'Noma\\'lum'}\n"
        f"⚠️ Ogohlantirishlar: {warn_count}/3\n"
        f"🚫 Ban tarixi: {ban_count} marta\n"
        f"📊 Holat: {faollik}\n"
    )
    
    if data.get('ban_tarixi'):
        msg += "\n🚫 *Ban tarixi:*\n"
        for b in data['ban_tarixi']:
            msg += f"  • {b['vaqt']} — {b['sabab']}\n"
    
    await update.message.reply_text(msg, parse_mode='Markdown')

async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await check_admin(update, context)
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Bu buyruq faqat adminlar uchun!")
        return
    if not context.args:
        await update.message.reply_text("📝 Foydalanish: /ban @username")
        return
    username = context.args[0].replace('@', '').lower()
    for uid, data in users.items():
        if data['username'].lower() == username:
            try:
                await context.bot.ban_chat_member(update.effective_chat.id, uid)
                users[uid]['ban_tarixi'].append({'vaqt': now(), 'sabab': 'Admin qarori'})
                await update.message.reply_text(f"🚫 @{username} ban qilindi!")
            except:
                await update.message.reply_text("❌ Ban qilishda xatolik!")
            return
    await update.message.reply_text(f"❌ @{username} topilmadi!")

async def unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await check_admin(update, context)
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Bu buyruq faqat adminlar uchun!")
        return
    if not context.args:
        await update.message.reply_text("📝 Foydalanish: /unban @username")
        return
    username = context.args[0].replace('@', '').lower()
    for uid, data in users.items():
        if data['username'].lower() == username:
            try:
                await context.bot.unban_chat_member(update.effective_chat.id, uid)
                await update.message.reply_text(f"✅ @{username} bandan chiqarildi!")
            except:
                await update.message.reply_text("❌ Xatolik!")
            return
    await update.message.reply_text(f"❌ @{username} topilmadi!")

async def ogohlantir(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await check_admin(update, context)
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Bu buyruq faqat adminlar uchun!")
        return
    if not context.args:
        await update.message.reply_text("📝 Foydalanish: /ogohlantir @username")
        return
    username = context.args[0].replace('@', '').lower()
    for uid, data in users.items():
        if data['username'].lower() == username:
            if uid not in warnings:
                warnings[uid] = 0
            warnings[uid] += 1
            users[uid]['ogohlantirishlar'] += 1
            qolgan = 3 - warnings[uid]
            if warnings[uid] >= 3:
                await context.bot.ban_chat_member(update.effective_chat.id, uid)
                await update.message.reply_text(f"🚫 @{username} 3 ta ogohlantirish — ban qilindi!")
            else:
                await update.message.reply_text(f"⚠️ @{username} ogohlantirildi! {warnings[uid]}/3\nYana {qolgan} ta = Ban!")
            return
    await update.message.reply_text(f"❌ @{username} topilmadi!")

async def top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await check_admin(update, context)
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Bu buyruq faqat adminlar uchun!")
        return
    if not users:
        await update.message.reply_text("📊 Hozircha ma'lumot yo'q.")
        return
    sorted_users = sorted(users.items(), key=lambda x: x[1]['xabarlar'], reverse=True)[:10]
    msg = "🏆 *Eng faol a'zolar:*\n\n"
    for i, (uid, data) in enumerate(sorted_users, 1):
        msg += f"{i}. {data['name']} — {data['xabarlar']} xabar\n"
    await update.message.reply_text(msg, parse_mode='Markdown')

async def sust(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await check_admin(update, context)
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Bu buyruq faqat adminlar uchun!")
        return
    sust_users = [(uid, data) for uid, data in users.items() if data['xabarlar'] == 0]
    if not sust_users:
        await update.message.reply_text("✅ Hamma faol!")
        return
    msg = "😴 *Faol bo'lmagan a'zolar:*\n\n"
    for uid, data in sust_users[:10]:
        msg += f"• {data['name']} (@{data['username']}) — {data['qoshilgan']} dan beri\n"
    await update.message.reply_text(msg, parse_mode='Markdown')

async def statistika(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await check_admin(update, context)
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Bu buyruq faqat adminlar uchun!")
        return
    jami_xabar = sum(d['xabarlar'] for d in users.values())
    jami_ban = sum(len(d.get('ban_tarixi', [])) for d in users.values())
    jami_warn = sum(warnings.values())
    msg = (
        f"📊 *Guruh statistikasi:*\n\n"
        f"👥 Jami a'zolar: {len(users)}\n"
        f"💬 Jami xabarlar: {jami_xabar}\n"
        f"⚠️ Jami ogohlantirishlar: {jami_warn}\n"
        f"🚫 Jami banlar: {jami_ban}\n"
        f"🕐 Vaqt: {now()}"
    )
    await update.message.reply_text(msg, parse_mode='Markdown')

async def qoidalar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📋 *Guruh qoidalari:*\n\n"
        "1️⃣ Spam va reklama taqiqlangan\n"
        "2️⃣ Haqorat taqiqlangan\n"
        "3️⃣ Begona linklar taqiqlangan\n"
        "4️⃣ Bir-biringizga hurmat bilan munosabatda bo'ling\n\n"
        "⚠️ 3 ta ogohlantirish = 🚫 Ban!",
        parse_mode='Markdown'
    )

async def yordam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 *Moderator Bot buyruqlari:*\n\n"
        "👤 *A'zo boshqaruvi:*\n"
        "/kim @username — A'zo haqida ma'lumot\n"
        "/ban @username — Ban qilish\n"
        "/unban @username — Bandan chiqarish\n"
        "/ogohlantir @username — Ogohlantirish\n\n"
        "📊 *Statistika:*\n"
        "/top — Eng faol a'zolar\n"
        "/sust — Faol bo'lmagan a'zolar\n"
        "/statistika — Guruh statistikasi\n\n"
        "📋 *Boshqa:*\n"
        "/qoidalar — Guruh qoidalari\n"
        "/yordam — Ushbu yordam",
        parse_mode='Markdown'
    )

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("kim", kim))
    app.add_handler(CommandHandler("ban", ban))
    app.add_handler(CommandHandler("unban", unban))
    app.add_handler(CommandHandler("ogohlantir", ogohlantir))
    app.add_handler(CommandHandler("top", top))
    app.add_handler(CommandHandler("sust", sust))
    app.add_handler(CommandHandler("statistika", statistika))
    app.add_handler(CommandHandler("qoidalar", qoidalar))
    app.add_handler(CommandHandler("yordam", yordam))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, new_member))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    logger.info("Moderator bot ishga tushdi!")
    app.run_polling()

if __name__ == '__main__':
    main()
