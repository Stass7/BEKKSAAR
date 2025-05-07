import os, re, logging, requests
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove, Contact, constants
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, ContextTypes, filters
)

# ---------- переменные окружения ----------
BOT_TOKEN       = os.getenv("BOT_TOKEN")
APPS_SCRIPT_URL = os.getenv("APPS_SCRIPT_URL")
if not BOT_TOKEN or not APPS_SCRIPT_URL:
    raise RuntimeError("Нужно задать BOT_TOKEN и APPS_SCRIPT_URL в переменных Railway")

# ---------- состояния ----------
LANG, FNAME, LNAME, EMAIL, PHONE, PROJECT, SERVICES, EXTRA, REVIEW = range(9)

# ---------- константы ----------
PROJECT_TYPES = {
    "Apartment":  "🏢 Apartment",
    "House":      "🏠 House",
    "Commercial": "🏭 Commercial",
    "Other":      "🛠 Other",
}

SERVICES = [
    "Concept design",
    "Space replanning",
    "3D visualization",
    "Material & Finishes Selection",
    "Technical Documentation",
    "Custom Furniture Design",
    "Interior Styling & Décor",
    "Turn-key Project Realisation & Management",
]

EMAIL_RE  = re.compile(r"^[^@\\s]+@[^@\\s]+\\.[A-Za-z]{2,}$")
PHONE_RE  = re.compile(r"^[0-9+\\-()\\s]{6,20}$")

# ---------- переводы ----------
T = {
 "en": {  # English texts
   "welcome":      "Welcome to BEKKSAAR! We create spaces that empower you.",
   "first":        "Please enter your *First Name*:",
   "last":         "Enter Last Name (or send '-' to skip):",
   "email":        "Enter your *Email*:",
   "email_bad":    "❌ Looks wrong, try again:",
   "phone":        "Send your *Phone* (or tap *Share contact*):",
   "phone_bad":    "❌ Looks wrong, try again:",
   "project":      "Which *Project Type* are you interested in?",
   "services":     "Select *Services* (toggle ✅). Tap *Done* when finished:",
   "done":         "Done",
   "extra":        "Anything else? (text or '-' to skip)",
   "resume":       ("📋 *Your request:*\\n\\n"
                    "👤 *Name:* {first} {last}\\n"
                    "✉️ *Email:* {email}\\n"
                    "📞 *Phone:* {phone}\\n"
                    "🏗 *Project:* {proj}\\n"
                    "🛠 *Services:* {serv}\\n"
                    "📝 *Extra:* {extra}"),
   "send":         "Send ✅",
   "edit":         "Edit ✏️",
   "thanks":       "Thank you! We’ll contact you soon.",
   "privacy":      "We collect your name, phone and email only to discuss your order. "
                   "We never share data with third parties and delete it on request.",
   "share":        "Share contact",
 },
 "ru": {  # Russian texts
   "welcome":      "Добро пожаловать в BEKKSAAR! Мы создаём пространства, которые вдохновляют.",
   "first":        "Введите *Имя*:",
   "last":         "Введите Фамилию (или '-' чтобы пропустить):",
   "email":        "Введите *Email*:",
   "email_bad":    "❌ Похоже на ошибочный email, попробуйте ещё раз:",
   "phone":        "Отправьте *Телефон* (или «Поделиться контактом»):",
   "phone_bad":    "❌ Похоже на неправильный номер, попробуйте ещё раз:",
   "project":      "Какой *тип проекта* интересует?",
   "services":     "Выберите *услуги* (переключается ✅). Когда всё, нажмите *Готово*:",
   "done":         "Готово",
   "extra":        "Что-нибудь ещё? (текст или '-' чтобы пропустить)",
   "resume":       ("📋 *Заявка:*\\n\\n"
                    "👤 *Имя:* {first} {last}\\n"
                    "✉️ *Email:* {email}\\n"
                    "📞 *Телефон:* {phone}\\n"
                    "🏗 *Проект:* {proj}\\n"
                    "🛠 *Услуги:* {serv}\\n"
                    "📝 *Доп:* {extra}"),
   "send":         "Отправить ✅",
   "edit":         "Изменить ✏️",
   "thanks":       "Спасибо за запрос! Мы свяжемся с вами в ближайшее время.",
   "privacy":      "Мы сохраняем имя, телефон и email только для связи по заказу. "
                   "Данные не передаются третьим лицам и удаляются по запросу.",
   "share":        "Поделиться контактом",
 },
 "ar": {  # Arabic texts
   "welcome":      "مرحباً بكم في BEKKSAAR! نصمم مساحات تمنحك القوة.",
   "first":        "أدخل *الاسم الأول*:",
   "last":         "أدخل اسم العائلة (أو '-' للتخطي):",
   "email":        "أدخل *البريد الإلكتروني*:",
   "email_bad":    "❌ البريد غير صالح، حاول مرة أخرى:",
   "phone":        "أرسل *رقم الهاتف* (أو اضغط مشاركة جهة الاتصال):",
   "phone_bad":    "❌ الرقم غير صالح، حاول مرة أخرى:",
   "project":      "ما نوع المشروع الذي تهتم به؟",
   "services":     "اختر الخدمات المطلوبة (تبديل ✅). عند الانتهاء اضغط *تم*:",
   "done":         "تم",
   "extra":        "أي تفاصيل إضافية؟ (نص أو '-' لتخطي)",
   "resume":       ("📋 *طلبك:*\\n\\n"
                    "👤 *الاسم:* {first} {last}\\n"
                    "✉️ *الإيميل:* {email}\\n"
                    "📞 *الهاتف:* {phone}\\n"
                    "🏗 *المشروع:* {proj}\\n"
                    "🛠 *الخدمات:* {serv}\\n"
                    "📝 *ملاحظات:* {extra}"),
   "send":         "إرسال ✅",
   "edit":         "تعديل ✏️",
   "thanks":       "شكراً لطلبك! سنتواصل معك قريباً.",
   "privacy":      "نحن نجمع اسمك ورقمك وبريدك فقط لمناقشة طلبك. "
                   "لن نشارك بياناتك مع أي طرف ثالث وسيتم حذفها عند الطلب.",
   "share":        "مشاركة جهة الاتصال",
 }
}

def tr(lang, key, **kw): return T[lang][key].format(**kw)

# ---------- клавиатуры ----------
def kb_lang():
    return InlineKeyboardMarkup([[InlineKeyboardButton("English 🇬🇧", callback_data="l_en"),
                                  InlineKeyboardButton("Русский 🇷🇺", callback_data="l_ru"),
                                  InlineKeyboardButton("العربية 🇸🇦", callback_data="l_ar")]])

def kb_project():
    return InlineKeyboardMarkup([[InlineKeyboardButton(txt, callback_data=f"p_{k}")]
                                 for k, txt in PROJECT_TYPES.items()])

def kb_services(lang, chosen):
    rows=[[InlineKeyboardButton(("✅ " if s in chosen else "")+s, callback_data=f"s_{i}")]
          for i,s in enumerate(SERVICES)]
    rows.append([InlineKeyboardButton(tr(lang,"done"), callback_data="s_done")])
    return InlineKeyboardMarkup(rows)

# ---------- валидаторы ----------
def good_email(e):  return EMAIL_RE.match(e)
def good_phone(p):  return PHONE_RE.match(p)

# ---------- хэндлеры ----------
async def start(u:Update, c:ContextTypes.DEFAULT_TYPE):
    c.user_data.clear(); c.user_data["lang"]="en"
    await u.message.reply_text(tr("en","welcome"), reply_markup=kb_lang())
    return LANG

async def set_lang(q, c):
    lang=q.data[2:]; c.user_data["lang"]=lang
    await q.message.reply_text(tr(lang,"first"), parse_mode=constants.ParseMode.MARKDOWN)
    return FNAME

async def first(u, c):
    c.user_data["first"]=u.message.text.strip()
    await u.message.reply_text(tr(c.user_data["lang"],"last"), parse_mode=constants.ParseMode.MARKDOWN)
    return LNAME

async def last(u,c):
    txt=u.message.text.strip(); c.user_data["last"]=("" if txt=="-" else txt)
    await u.message.reply_text(tr(c.user_data["lang"],"email"), parse_mode=constants.ParseMode.MARKDOWN)
    return EMAIL

async def email(u,c):
    lang=c.user_data["lang"]; em=u.message.text.strip()
    if not good_email(em):
        await u.message.reply_text(tr(lang,"email_bad"), parse_mode=constants.ParseMode.MARKDOWN)
        return EMAIL
    c.user_data["email"]=em
    kb=ReplyKeyboardMarkup([[KeyboardButton(tr(lang,"share"), request_contact=True)]],
                           resize_keyboard=True, one_time_keyboard=True)
    await u.message.reply_text(tr(lang,"phone"), reply_markup=kb, parse_mode=constants.ParseMode.MARKDOWN)
    return PHONE

async def phone(u,c):
    lang=c.user_data["lang"]
    p=u.message.contact.phone_number if u.message.contact else u.message.text.strip()
    if not good_phone(p):
        await u.message.reply_text(tr(lang,"phone_bad"), parse_mode=constants.ParseMode.MARKDOWN)
        return PHONE
    c.user_data["phone"]=p
    await u.message.reply_text(tr(lang,"project"), reply_markup=kb_project(), parse_mode=constants.ParseMode.MARKDOWN,
                               reply_markup_remove=ReplyKeyboardRemove())
    return PROJECT

async def choose_project(q,c):
    c.user_data["project"]=PROJECT_TYPES[q.data[2:]]
    c.user_data["services"]=[]
    await q.message.reply_text(tr(c.user_data["lang"],"services"),
                               reply_markup=kb_services(c.user_data["lang"],[]),
                               parse_mode=constants.ParseMode.MARKDOWN)
    return SERVICES

async def toggle_service(q,c):
    lang=c.user_data["lang"]; data=q.data
    if data=="s_done":
        await q.message.reply_text(tr(lang,"extra"), parse_mode=constants.ParseMode.MARKDOWN)
        return EXTRA
    idx=int(data[2:]); s=SERVICES[idx]
    lst=c.user_data["services"]
    lst.remove(s) if s in lst else lst.append(s)
    await q.edit_message_reply_markup(reply_markup=kb_services(lang,lst))
    return SERVICES

async def extra(u,c):
    c.user_data["extra"]=("" if u.message.text.strip()=="-" else u.message.text.strip())
    lang=c.user_data["lang"]; d=c.user_data
    resume=tr(lang,"resume",
              first=d["first"], last=d["last"], email=d["email"], phone=d["phone"],
              proj=d["project"], serv=", ".join(d["services"]) or "—", extra=d["extra"] or "—")
    kb=InlineKeyboardMarkup([[InlineKeyboardButton(tr(lang,"send"), callback_data="ok"),
                              InlineKeyboardButton(tr(lang,"edit"), callback_data="edit")]])
    await u.message.reply_text(resume, reply_markup=kb, parse_mode=constants.ParseMode.MARKDOWN)
    return REVIEW

async def review(q,c):
    lang=c.user_data["lang"]
    if q.data=="edit":
        await q.message.reply_text(tr(lang,"first"), parse_mode=constants.ParseMode.MARKDOWN)
        return FNAME
    # отправляем в Google Apps Script
    try:
        requests.post(APPS_SCRIPT_URL, json={
            "first_name": c.user_data["first"],
            "last_name":  c.user_data["last"],
            "email":      c.user_data["email"],
            "phone":      c.user_data["phone"],
            "project_type": c.user_data["project"],
            "services":     c.user_data["services"],
            "extra":        c.user_data["extra"],
        }, timeout=10)
    except Exception as e:
        logging.error("POST to script failed: %s", e)
    await q.message.reply_text(tr(lang,"thanks"))
    await q.message.reply_text(tr(lang,"privacy"))
    return ConversationHandler.END

async def cancel(u,c):
    await u.message.reply_text("Cancelled."); return ConversationHandler.END

def main():
    app=ApplicationBuilder().token(BOT_TOKEN).build()
    conv=ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            LANG:     [CallbackQueryHandler(set_lang, pattern="^l_")],
            FNAME:    [MessageHandler(filters.TEXT & ~filters.COMMAND, first)],
            LNAME:    [MessageHandler(filters.TEXT & ~filters.COMMAND, last)],
            EMAIL:    [MessageHandler(filters.TEXT & ~filters.COMMAND, email)],
            PHONE:    [MessageHandler(filters.CONTACT, phone),
                       MessageHandler(filters.TEXT & ~filters.COMMAND, phone)],
            PROJECT:  [CallbackQueryHandler(choose_project, pattern="^p_")],
            SERVICES: [CallbackQueryHandler(toggle_service, pattern="^s_")],
            EXTRA:    [MessageHandler(filters.TEXT & ~filters.COMMAND, extra)],
            REVIEW:   [CallbackQueryHandler(review, pattern="^(ok|edit)$")],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True)
    app.add_handler(conv)
    logging.info("Bot started."); app.run_polling()

if __name__=="__main__":
    main()
