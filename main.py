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
from config import BOT_TOKEN

# تفعيل اللوجينج
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# المراحل المختلفة للمحادثة
MAIN_MENU, VISIT_TYPE, DOCTOR_NAME, LOCATION, SPECIALTY, PRODUCTS, COMMENT = range(7)
PHARMACY_NAME, PHARMACY_ADDRESS, PHARMACY_PRODUCTS, PHARMACY_COMMENT = range(7, 11)
NAME_INPUT = 11

# مجلد حفظ التقارير
REPORTS_DIR = "reports"
if not os.path.exists(REPORTS_DIR):
    os.makedirs(REPORTS_DIR)


class ExcelHandler:
    """إدارة ملفات Excel بالتصميم المخصص"""
    
    @staticmethod
    def get_today_filename():
        """إنشاء اسم الملف لليوم الحالي"""
        today = datetime.now()
        day_name = today.strftime("%a")
        date_str = today.strftime("%d-%b")
        return f"Report_{day_name}_{date_str}.xlsx"
    
    @staticmethod
    def create_new_report(user_name=""):
        """إنشاء تقرير جديد بالتصميم المخصص"""
        filename = ExcelHandler.get_today_filename()
        filepath = os.path.join(REPORTS_DIR, filename)
        
        # if os.path.exists(filepath):
        #     return filepath, False
        
        # إنشاء workbook جديد
        wb = Workbook()
        ws = wb.active
        ws.title = "Daily Report"
        
        # ===== تعريف الأنماط =====
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
        
        # ===== Title Section =====
        ws.merge_cells("A2:F2")
        ws["A2"].value = "Daily Report"
        ws["A2"].font = Font(bold=True, size=14)
        ws["A2"].alignment = center
        ws["A2"].fill = header_fill
        
        # ===== Name & Date Section =====
        ws["A4"].value = "Name:"
        ws["A5"].value = "Date:"
        ws["A4"].font = ws["A5"].font = bold
        
        ws.merge_cells("B4:F4")
        ws.merge_cells("B5:F5")
        
        # وضع الاسم والتاريخ
        ws["B4"].value = user_name
        ws["B5"].value = datetime.now().strftime("%d/%m/%Y")
        ws["B5"].alignment = left_align
        
        for col in ["A", "B"]:
            ws[f"{col}4"].fill = blue_fill
            ws[f"{col}5"].fill = orange_fill
        
        # ===== Table Header =====
        headers = ["A.M / P.M", "Doctor Name", "Hospital", "Specialist", "Product", "Comment"]
        header_row = 7
        for col, h in enumerate(headers, start=1):
            cell = ws.cell(row=header_row, column=col, value=h)
            cell.font = bold
            cell.fill = header_fill
            cell.alignment = center
            cell.border = border
        
        # ===== A.M Section =====
        ws.merge_cells("A8:A14")
        ws["A8"].value = "A.M"
        ws["A8"].alignment = center
        ws["A8"].font = bold
        ws["A8"].fill = section_fill
        
        for r in range(8, 15):
            for c in range(2, 7):
                ws.cell(row=r, column=c).border = border
        
        # Separator after A.M
        for c in range(1, 7):
            ws.cell(row=15, column=c).fill = orange_fill
        
        # ===== P.M Section =====
        ws.merge_cells("A16:A28")
        ws["A16"].value = "P.M"
        ws["A16"].alignment = center
        ws["A16"].font = bold
        ws["A16"].fill = section_fill
        
        for r in range(16, 29):
            for c in range(2, 7):
                ws.cell(row=r, column=c).border = border
        
        # Separator after P.M
        for c in range(1, 7):
            ws.cell(row=29, column=c).fill = orange_fill
        
        # ===== Pharmacy Section =====
        ws.merge_cells("A30:A37")
        ws["A30"].value = "PHARMACY"
        ws["A30"].alignment = center
        ws["A30"].font = bold
        ws["A30"].fill = header_fill
        
        ph_headers = ["Pharmacy Name", "Address", "Products", "Comments"]
        ph_cols = [2, 3, 4, 6]  # B, C, D, F
        
        for col, h in zip(ph_cols, ph_headers):
            cell = ws.cell(row=30, column=col, value=h)
            cell.font = bold
            cell.fill = header_fill
            cell.border = border
            cell.alignment = center
        
        # Merge Products column (D30:E37)
        for r in range(30, 38):
            ws.merge_cells(f"D{r}:E{r}")
        
        # Add borders to pharmacy rows
        for r in range(31, 38):
            for c in range(2, 7):
                ws.cell(row=r, column=c).border = border
        
        # ===== Column Widths =====
        widths = [15, 25, 20, 20, 20, 30]
        for i, w in enumerate(widths, start=1):
            ws.column_dimensions[chr(64 + i)].width = w
        
        wb.save(filepath)
        return filepath, True
    
    @staticmethod
    def add_visit(visit_type, data):
        """إضافة زيارة جديدة للتقرير"""
        filename = ExcelHandler.get_today_filename()
        filepath = os.path.join(REPORTS_DIR, filename)
        
        if not os.path.exists(filepath):
            ExcelHandler.create_new_report()
        
        wb = load_workbook(filepath)
        ws = wb.active
        
        border = Border(
            left=Side(style="thin"),
            right=Side(style="thin"),
            top=Side(style="thin"),
            bottom=Side(style="thin")
        )
        
        if visit_type == "AM":
            # A.M: rows 8-14
            for row in range(8, 15):
                if not ws.cell(row=row, column=2).value:  # إذا الصف فاضي
                    ws.cell(row=row, column=2).value = data.get("Dr", "")
                    ws.cell(row=row, column=3).value = data.get("Hospital", "")
                    ws.cell(row=row, column=4).value = data.get("Specialty", "")
                    ws.cell(row=row, column=5).value = data.get("Products", "")
                    ws.cell(row=row, column=6).value = data.get("Comment", "")
                    
                    for c in range(2, 7):
                        ws.cell(row=row, column=c).border = border
                    break
        
        elif visit_type == "PM":
            # P.M: rows 16-28
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
            # Pharmacy: rows 31-37
            for row in range(31, 38):
                if not ws.cell(row=row, column=2).value:
                    ws.cell(row=row, column=2).value = data.get("Pharmacy", "")
                    ws.cell(row=row, column=3).value = data.get("Address", "")
                    
                    # Products in merged cells D:E
                    ws.merge_cells(f"D{row}:E{row}")
                    ws.cell(row=row, column=4).value = data.get("Products", "")
                    
                    ws.cell(row=row, column=6).value = data.get("Comment", "")
                    
                    for c in range(2, 7):
                        ws.cell(row=row, column=c).border = border
                    break
        
        wb.save(filepath)
        return filepath


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بداية المحادثة"""
    keyboard = [
        ["📊 إنشاء تقرير جديد"],
        ["✅ تسجيل زيارة جديدة"],
        ["📤 إرسال التقرير"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "🤖 *Medical Rep Bot*\n\n"
        "مرحباً! اختر من القائمة:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    return MAIN_MENU


async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة القائمة الرئيسية"""
    choice = update.message.text
    
    if choice == "📊 إنشاء تقرير جديد":
        await update.message.reply_text(
            "👤 أدخل اسمك (سيظهر في التقرير):",
            reply_markup=ReplyKeyboardRemove()
        )
        return NAME_INPUT
    
    elif choice == "✅ تسجيل زيارة جديدة":
        keyboard = [
            ["🌅 A.M Visit"],
            ["🌆 P.M Visit"],
            ["💊 Pharmacy Visit"],
            ["🔙 رجوع"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(
            "اختر نوع الزيارة:",
            reply_markup=reply_markup
        )
        return VISIT_TYPE
    
    elif choice == "📤 إرسال التقرير":
        return await send_report(update, context)


async def name_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """استلام اسم المستخدم وإنشاء التقرير"""
    user_name = update.message.text
    
    filepath, is_new = ExcelHandler.create_new_report(user_name)
    filename = os.path.basename(filepath)
    
    if is_new:
        await update.message.reply_text(
            f"✅ *تم إنشاء التقرير بنجاح!*\n\n"
            f"📄 اسم الملف: `{filename}`\n"
            f"👤 الاسم: {user_name}",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            f"ℹ️ *التقرير موجود بالفعل*\n\n"
            f"📄 اسم الملف: `{filename}`",
            parse_mode='Markdown'
        )
    
    return await start(update, context)


async def visit_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """اختيار نوع الزيارة"""
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
    """حفظ اسم الدكتور"""
    context.user_data['doctor_name'] = update.message.text
    location_label = context.user_data['location_label']
    
    await update.message.reply_text(f"🏥 أدخل {location_label}:")
    return LOCATION


async def location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """حفظ الموقع"""
    context.user_data['location'] = update.message.text
    await update.message.reply_text("🩺 أدخل تخصص الدكتور:")
    return SPECIALTY


async def specialty(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """حفظ التخصص"""
    context.user_data['specialty'] = update.message.text
    await update.message.reply_text("💊 أدخل أسماء المنتجات (افصل بينها بفاصلة):")
    return PRODUCTS


async def products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """حفظ المنتجات"""
    context.user_data['products'] = update.message.text
    
    keyboard = [["⏭️ تخطي"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "💬 أدخل التعليق (أو اضغط تخطي):",
        reply_markup=reply_markup
    )
    return COMMENT


async def comment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """حفظ التعليق وإتمام الزيارة"""
    comment_text = update.message.text
    
    if comment_text != "⏭️ تخطي":
        context.user_data['comment'] = comment_text
    else:
        context.user_data['comment'] = ""
    
    visit_type = context.user_data['visit_type']
    location_label = "Hospital" if visit_type == "AM" else "Area"
    
    data = {
        "Dr": context.user_data['doctor_name'],
        location_label: context.user_data['location'],
        "Specialty": context.user_data['specialty'],
        "Products": context.user_data['products'],
        "Comment": context.user_data.get('comment', '')
    }
    
    filepath = ExcelHandler.add_visit(visit_type, data)
    
    await update.message.reply_text(
        "✅ *تم تسجيل الزيارة بنجاح!*\n\n"
        f"📄 تم الحفظ في: `{os.path.basename(filepath)}`",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode='Markdown'
    )
    
    context.user_data.clear()
    return await start(update, context)


async def pharmacy_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """حفظ اسم الصيدلية"""
    context.user_data['pharmacy_name'] = update.message.text
    await update.message.reply_text("📍 أدخل عنوان الصيدلية:")
    return PHARMACY_ADDRESS


async def pharmacy_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """حفظ عنوان الصيدلية"""
    context.user_data['pharmacy_address'] = update.message.text
    await update.message.reply_text("💊 أدخل أسماء المنتجات:")
    return PHARMACY_PRODUCTS


async def pharmacy_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """حفظ منتجات الصيدلية"""
    context.user_data['pharmacy_products'] = update.message.text
    
    keyboard = [["⏭️ تخطي"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "💬 أدخل التعليق (أو اضغط تخطي):",
        reply_markup=reply_markup
    )
    return PHARMACY_COMMENT


async def pharmacy_comment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """حفظ تعليق الصيدلية وإتمام الزيارة"""
    comment_text = update.message.text
    
    if comment_text != "⏭️ تخطي":
        context.user_data['pharmacy_comment'] = comment_text
    else:
        context.user_data['pharmacy_comment'] = ""
    
    data = {
        "Pharmacy": context.user_data['pharmacy_name'],
        "Address": context.user_data['pharmacy_address'],
        "Products": context.user_data['pharmacy_products'],
        "Comment": context.user_data.get('pharmacy_comment', '')
    }
    
    filepath = ExcelHandler.add_visit("PHARMACY", data)
    
    await update.message.reply_text(
        "✅ *تم تسجيل زيارة الصيدلية بنجاح!*\n\n"
        f"📄 تم الحفظ في: `{os.path.basename(filepath)}`",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode='Markdown'
    )
    
    context.user_data.clear()
    return await start(update, context)


async def send_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إرسال التقرير للمستخدم"""
    filename = ExcelHandler.get_today_filename()
    filepath = os.path.join(REPORTS_DIR, filename)
    
    if not os.path.exists(filepath):
        await update.message.reply_text(
            "⚠️ *لا يوجد تقرير لليوم!*\n\n"
            "قم بإنشاء تقرير جديد أولاً من القائمة الرئيسية.",
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
        await update.message.reply_text(f"❌ حدث خطأ أثناء إرسال التقرير:\n{str(e)}")
    
    return await start(update, context)


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إلغاء المحادثة"""
    await update.message.reply_text(
        "تم الإلغاء. استخدم /start للبدء من جديد.",
        reply_markup=ReplyKeyboardRemove()
    )
    context.user_data.clear()
    return ConversationHandler.END



def main():
    """تشغيل البوت"""
    TOKEN = BOT_TOKEN
    

    
    application = Application.builder().token(TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MAIN_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, main_menu)],
            NAME_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, name_input)],
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
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    application.add_handler(conv_handler)
    
    print("🤖 البوت يعمل الآن...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
