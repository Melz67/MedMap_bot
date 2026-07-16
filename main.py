import logging
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from datetime import datetime
import os
import json
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

MAIN_MENU, VISIT_TYPE, DOCTOR_NAME, LOCATION, SPECIALTY, PRODUCTS, COMMENT = range(7)
PHARMACY_NAME, PHARMACY_ADDRESS, PHARMACY_PRODUCTS, PHARMACY_COMMENT = range(7, 11)
FIRST_NAME_INPUT, LAST_NAME_INPUT = 11, 12

REPORTS_DIR = "reports"
if not os.path.exists(REPORTS_DIR):
    os.makedirs(REPORTS_DIR)

USERS_DATA_FILE = "users_data.json"

def load_users_data():
    """تحميل بيانات المستخدمين من الملف"""
    if os.path.exists(USERS_DATA_FILE):
        with open(USERS_DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_user_data(user_id, first_name, full_name):
    """حفظ بيانات مستخدم جديد"""
    users_data = load_users_data()
    users_data[str(user_id)] = {
        'first_name': first_name,
        'full_name': full_name,
        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    with open(USERS_DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(users_data, f, ensure_ascii=False, indent=2)

def get_user_data(user_id):
    """جلب بيانات مستخدم محدد"""
    users_data = load_users_data()
    return users_data.get(str(user_id))

class ExcelHandler:
    @staticmethod
    def get_today_filename(user_id, first_name):
        """إنشاء اسم الملف بناءً على الاسم الأول و user_id"""
        today = datetime.now()
        day_name = today.strftime("%a")
        date_str = today.strftime("%d-%b")
        username = f"{first_name}{user_id}"
        return f"{username}_Report_{day_name}_{date_str}.xlsx"
    
    @staticmethod
    def create_new_report(user_id, first_name, full_name):
        """إنشاء تقرير جديد مع الاسم الكامل في الداخل"""
        filename = ExcelHandler.get_today_filename(user_id, first_name)
        filepath = os.path.join(REPORTS_DIR, filename)
        
        wb = Workbook()
        ws = wb.active
        ws.title = "Daily Report"
        
        header_fill = PatternFill("solid", fgColor="FFFF00")
        blue_fill = PatternFill("solid", fgColor="31859B")
        orange_fill = PatternFill("solid", fgColor="FABF8F")
        section_fill = PatternFill("solid", fgColor="C6E0B4")
        center = Alignment(horizontal="center", vertical="center")
        left_align = Alignment(horizontal="left", vertical="center")
        bold = Font(bold=True)
        border = Border(
            left=Side(style="thin"),
            right=Side(style="thin"),
            top=Side(style="thin"),
            bottom=Side(style="thin")
        )
        
        ws.merge_cells("A2:F2")
        ws["A2"].value = "Daily Report"
        ws["A2"].font = Font(bold=True, size=14)
        ws["A2"].alignment = center
        ws["A2"].fill = header_fill
        
        ws["A4"].value = "Name:"
        ws["A5"].value = "Date:"
        ws["A4"].font = ws["A5"].font = bold
        
        ws.merge_cells("B4:F4")
        ws.merge_cells("B5:F5")
        ws["B4"].value = full_name  
        ws["B5"].value = datetime.now().strftime("%d/%m/%Y")
        ws["B5"].alignment = left_align
        
        for col in ["A", "B"]:
            ws[f"{col}4"].fill = blue_fill
            ws[f"{col}5"].fill = orange_fill
        
        headers = ["A.M / P.M", "Doctor Name", "Hospital", "Specialist", "Product", "Comment"]
        header_row = 7
        for col, h in enumerate(headers, start=1):
            cell = ws.cell(row=header_row, column=col, value=h)
            cell.font = bold
            cell.fill = header_fill
            cell.alignment = center
            cell.border = border
        
        ws.merge_cells("A8:A14")
        ws["A8"].value = "A.M"
        ws["A8"].alignment = center
        ws["A8"].font = bold
        ws["A8"].fill = section_fill
        
        for r in range(8, 15):
            for c in range(2, 7):
                ws.cell(row=r, column=c).border = border
        
        for c in range(1, 7):
            ws.cell(row=15, column=c).fill = orange_fill
        
        ws.merge_cells("A16:A28")
        ws["A16"].value = "P.M"
        ws["A16"].alignment = center
        ws["A16"].font = bold
        ws["A16"].fill = section_fill
        
        for r in range(16, 29):
            for c in range(2, 7):
                ws.cell(row=r, column=c).border = border
        
        for c in range(1, 7):
            ws.cell(row=29, column=c).fill = orange_fill
        
        ws.merge_cells("A30:A37")
        ws["A30"].value = "PHARMACY"
        ws["A30"].alignment = center
        ws["A30"].font = bold
        ws["A30"].fill = header_fill
        
        ph_headers = ["Pharmacy Name", "Address", "Products", "Comments"]
        ph_cols = [2, 3, 4, 6]
        for col, h in zip(ph_cols, ph_headers):
            cell = ws.cell(row=30, column=col, value=h)
            cell.font = bold
            cell.fill = header_fill
            cell.border = border
            cell.alignment = center
        
        for r in range(30, 38):
            ws.merge_cells(f"D{r}:E{r}")
        
        for r in range(31, 38):
            for c in range(2, 7):
                ws.cell(row=r, column=c).border = border
        
        widths = [15, 25, 20, 20, 20, 30]
        for i, w in enumerate(widths, start=1):
            ws.column_dimensions[chr(64 + i)].width = w
        
        wb.save(filepath)
        return filepath, True
    
    @staticmethod
    def add_visit(user_id, first_name, visit_type, data):
        """إضافة زيارة للتقرير"""
        filename = ExcelHandler.get_today_filename(user_id, first_name)
        filepath = os.path.join(REPORTS_DIR, filename)
        
        if not os.path.exists(filepath):
            return None 
        
        wb = load_workbook(filepath)
        ws = wb.active
        border = Border(
            left=Side(style="thin"),
            right=Side(style="thin"),
            top=Side(style="thin"),
            bottom=Side(style="thin")
        )
        
        if visit_type == "AM":
            for row in range(8, 15):
                if not ws.cell(row=row, column=2).value:
                    ws.cell(row=row, column=2).value = data.get("Dr", "")
                    ws.cell(row=row, column=3).value = data.get("Hospital", "")
                    ws.cell(row=row, column=4).value = data.get("Specialty", "")
                    ws.cell(row=row, column=5).value = data.get("Products", "")
                    ws.cell(row=row, column=6).value = data.get("Comment", "")
                    for c in range(2, 7):
                        ws.cell(row=row, column=c).border = border
                    break
        
        elif visit_type == "PM":
            for row in range(16, 29):
                if not ws.cell(row=row, column=2).value:
                    ws.cell(row=row, column=2).value = data.get("Dr", "")
                    ws.cell(row=row, column=3).value = data.get("Area", "")
                    ws.cell(row=row, column=4).value = data.get("Specialty", "")
                    ws.cell(row=row, column=5).value = data.get("Products", "")
                    ws.cell(row=row, column=6).value = data.get("Comment", "")
                    for c in range(2, 7):
                        ws.cell(row=row, column=c).border = border
                    break
        
        elif visit_type == "PHARMACY":
            for row in range(31, 38):
                if not ws.cell(row=row, column=2).value:
                    ws.cell(row=row, column=2).value = data.get("Pharmacy", "")
                    ws.cell(row=row, column=3).value = data.get("Address", "")
                    ws.merge_cells(f"D{row}:E{row}")
                    ws.cell(row=row, column=4).value = data.get("Products", "")
                    ws.cell(row=row, column=6).value = data.get("Comment", "")
                    for c in range(2, 7):
                        ws.cell(row=row, column=c).border = border
                    break
        
        wb.save(filepath)
        return filepath

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ["📊 إنشاء تقرير جديد"],
        ["✅ تسجيل زيارة جديدة"],
        ["📤 إرسال التقرير"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "🤖 *Medical Rep Bot*\n\nمرحباً! اختر من القائمة:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    return MAIN_MENU

async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    choice = update.message.text
    
    if choice == "📊 إنشاء تقرير جديد":
        await update.message.reply_text(
            "👤 أدخل الاسم الأول:",
            reply_markup=ReplyKeyboardRemove()
        )
        return FIRST_NAME_INPUT
    
    elif choice == "✅ تسجيل زيارة جديدة":
        keyboard = [
            ["🌅 A.M Visit"],
            ["🌆 P.M Visit"],
            ["💊 Pharmacy Visit"],
            ["🔙 رجوع"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text("اختر نوع الزيارة:", reply_markup=reply_markup)
        return VISIT_TYPE
    
    elif choice == "📤 إرسال التقرير":
        return await send_report(update, context)

async def first_name_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """استقبال الاسم الأول"""
    context.user_data['first_name'] = update.message.text.strip()
    await update.message.reply_text("👤 أدخل باقي الاسم:")
    return LAST_NAME_INPUT

async def last_name_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """استقبال باقي الاسم وإنشاء التقرير"""
    last_name = update.message.text.strip()
    first_name = context.user_data['first_name']
    full_name = f"{first_name} {last_name}"
    user_id = update.effective_user.id
    

    context.user_data['full_name'] = full_name
    context.user_data['user_id'] = user_id
    

    save_user_data(user_id, first_name, full_name)
    
    filepath, is_new = ExcelHandler.create_new_report(user_id, first_name, full_name)
    filename = os.path.basename(filepath)
    
    if is_new:
        await update.message.reply_text(
            f"✅ *تم إنشاء التقرير بنجاح!*\n\n"
            f"📄 اسم الملف: `{filename}`\n"
            f"👤 الاسم: {full_name}\n"
            f"🆔 User ID: {user_id}",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            f"ℹ️ *التقرير موجود بالفعل*\n\n📄 اسم الملف: `{filename}`",
            parse_mode='Markdown'
        )
    
    return await start(update, context)

async def visit_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    choice = update.message.text
    
    if choice == "🔙 رجوع":
        return await start(update, context)
    
    if choice == "🌅 A.M Visit":
        context.user_data['visit_type'] = "AM"
        context.user_data['location_label'] = "المستشفى"
    elif choice == "🌆 P.M Visit":
        context.user_data['visit_type'] = "PM"
        context.user_data['location_label'] = "المنطقة"
    elif choice == "💊 Pharmacy Visit":
        context.user_data['visit_type'] = "PHARMACY"
        await update.message.reply_text(
            "🏪 أدخل اسم الصيدلية:",
            reply_markup=ReplyKeyboardRemove()
        )
        return PHARMACY_NAME
    
    await update.message.reply_text(
        "👤 أدخل اسم الدكتور:",
        reply_markup=ReplyKeyboardRemove()
    )
    return DOCTOR_NAME

async def doctor_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['doctor_name'] = update.message.text
    location_label = context.user_data['location_label']
    await update.message.reply_text(f"🏥 أدخل {location_label}:")
    return LOCATION

async def location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['location'] = update.message.text
    await update.message.reply_text("🩺 أدخل تخصص الدكتور:")
    return SPECIALTY

async def specialty(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['specialty'] = update.message.text
    await update.message.reply_text("💊 أدخل أسماء المنتجات (افصل بينها بفاصلة):")
    return PRODUCTS

async def products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['products'] = update.message.text
    keyboard = [["⏭️ تخطي"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "💬 أدخل التعليق (أو اضغط تخطي):",
        reply_markup=reply_markup
    )
    return COMMENT

async def comment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    comment_text = update.message.text
    context.user_data['comment'] = comment_text if comment_text != "⏭️ تخطي" else ""
    
    visit_type = context.user_data['visit_type']
    location_label = "Hospital" if visit_type == "AM" else "Area"
    
    data = {
        "Dr": context.user_data['doctor_name'],
        location_label: context.user_data['location'],
        "Specialty": context.user_data['specialty'],
        "Products": context.user_data['products'],
        "Comment": context.user_data.get('comment', '')
    }
    
    user_id = update.effective_user.id
    user_data = get_user_data(user_id)
    
    if not user_data:
        await update.message.reply_text(
            "⚠️ *لم يتم العثور على بياناتك!*\n\n"
            "الرجاء إنشاء تقرير جديد أولاً من القائمة الرئيسية.",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode='Markdown'
        )
        return await start(update, context)
    
    first_name = user_data['first_name']
    
    filepath = ExcelHandler.add_visit(user_id, first_name, visit_type, data)
    
    if filepath:
        await update.message.reply_text(
            f"✅ *تم تسجيل الزيارة بنجاح!*\n\n"
            f"📄 تم الحفظ في: `{os.path.basename(filepath)}`",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            "⚠️ *خطأ: لم يتم العثور على التقرير!*\n\n"
            "قم بإنشاء تقرير جديد أولاً.",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode='Markdown'
        )
    
    return await start(update, context)

async def pharmacy_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['pharmacy_name'] = update.message.text
    await update.message.reply_text("📍 أدخل عنوان الصيدلية:")
    return PHARMACY_ADDRESS

async def pharmacy_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['pharmacy_address'] = update.message.text
    await update.message.reply_text("💊 أدخل أسماء المنتجات:")
    return PHARMACY_PRODUCTS

async def pharmacy_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['pharmacy_products'] = update.message.text
    keyboard = [["⏭️ تخطي"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "💬 أدخل التعليق (أو اضغط تخطي):",
        reply_markup=reply_markup
    )
    return PHARMACY_COMMENT

async def pharmacy_comment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    comment_text = update.message.text
    context.user_data['pharmacy_comment'] = comment_text if comment_text != "⏭️ تخطي" else ""
    
    data = {
        "Pharmacy": context.user_data['pharmacy_name'],
        "Address": context.user_data['pharmacy_address'],
        "Products": context.user_data['pharmacy_products'],
        "Comment": context.user_data.get('pharmacy_comment', '')
    }
    
    user_id = update.effective_user.id
    user_data = get_user_data(user_id)
    
    if not user_data:
        await update.message.reply_text(
            "⚠️ *لم يتم العثور على بياناتك!*\n\n"
            "الرجاء إنشاء تقرير جديد أولاً من القائمة الرئيسية.",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode='Markdown'
        )
        return await start(update, context)
    
    first_name = user_data['first_name']
    
    filepath = ExcelHandler.add_visit(user_id, first_name, "PHARMACY", data)
    
    if filepath:
        await update.message.reply_text(
            f"✅ *تم تسجيل زيارة الصيدلية بنجاح!*\n\n"
            f"📄 تم الحفظ في: `{os.path.basename(filepath)}`",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            "⚠️ *خطأ: لم يتم العثور على التقرير!*\n\n"
            "قم بإنشاء تقرير جديد أولاً.",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode='Markdown'
        )
    
    return await start(update, context)

async def send_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    
    user_data = get_user_data(user_id)
    
    if not user_data:
        await update.message.reply_text(
            "⚠️ *لم يتم العثور على بياناتك!*\n\n"
            "الرجاء إنشاء تقرير جديد أولاً من القائمة الرئيسية.",
            parse_mode='Markdown'
        )
        return await start(update, context)
    
    first_name = user_data['first_name']
    
    filename = ExcelHandler.get_today_filename(user_id, first_name)
    filepath = os.path.join(REPORTS_DIR, filename)
    
    if not os.path.exists(filepath):
        await update.message.reply_text(
            "⚠️ *لا يوجد تقرير لليوم!*\n\nقم بإنشاء تقرير جديد أولاً.",
            parse_mode='Markdown'
        )
        return await start(update, context)
    
    waiting_msg = await update.message.reply_text("⏳ جاري إرسال التقرير...")
    
    try:
        with open(filepath, 'rb') as file:
            await update.message.reply_document(
                document=file,
                filename=filename,
                caption=f"📊 *تقرير اليوم*\n\n📅 {datetime.now().strftime('%d %B %Y')}",
                parse_mode='Markdown'
            )
        await waiting_msg.delete()
        await update.message.reply_text("✅ تم إرسال التقرير بنجاح!")
    except Exception as e:
        await waiting_msg.delete()
        await update.message.reply_text(f"❌ خطأ: {str(e)}")
    
    return await start(update, context)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "تم الإلغاء. استخدم /start للبدء مجدداً.",
        reply_markup=ReplyKeyboardRemove()
    )
    context.user_data.clear()
    return ConversationHandler.END

async def reset_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إعادة تعيين المحادثة في حالة حدوث خطأ"""
    context.user_data.clear()
    return await start(update, context)

def main():
    """تشغيل البوت باستخدام التوكن من متغيرات البيئة"""
    
    if not BOT_TOKEN:
        print("❌ خطأ: لم يتم العثور على BOT_TOKEN في متغيرات البيئة!")
        return
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MAIN_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, main_menu)],
            FIRST_NAME_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, first_name_input)],
            LAST_NAME_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, last_name_input)],
            VISIT_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, visit_type)],
            DOCTOR_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, doctor_name)],
            LOCATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, location)],
            SPECIALTY: [MessageHandler(filters.TEXT & ~filters.COMMAND, specialty)],
            PRODUCTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, products)],
            COMMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, comment)],
            PHARMACY_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, pharmacy_name)],
            PHARMACY_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, pharmacy_address)],
            PHARMACY_PRODUCTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, pharmacy_products)],
            PHARMACY_COMMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, pharmacy_comment)],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CommandHandler("start", start),  
        ],
        allow_reentry=True,  
    )
    
    application.add_handler(conv_handler)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reset_conversation))
    
    print("🤖 البوت يعمل الآن...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
