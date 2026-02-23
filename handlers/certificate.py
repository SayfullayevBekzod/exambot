"""PDF Certificate — test natijasi uchun sertifikat"""
import os
import tempfile
from datetime import datetime

from fpdf import FPDF
from telegram import Update
from telegram.ext import ContextTypes

from database import get_session, UserResult, Subject
from sqlalchemy import desc


class CertificatePDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 28)
        self.set_text_color(44, 62, 80)
        self.cell(0, 20, "IELTS Preparation Bot", align="C", new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "", 14)
        self.set_text_color(127, 140, 141)
        self.cell(0, 10, "Certificate of Achievement", align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(5)
        # Chiziq
        self.set_draw_color(52, 152, 219)
        self.set_line_width(1)
        self.line(30, self.get_y(), 180, self.get_y())
        self.ln(10)


def generate_certificate(full_name, subject_name, score, total, percentage, band, date_str):
    """PDF sertifikat yaratish"""
    pdf = CertificatePDF()
    pdf.add_page()

    # Asosiy matn
    pdf.set_font("Helvetica", "", 16)
    pdf.set_text_color(44, 62, 80)
    pdf.cell(0, 15, "This is to certify that", align="C", new_x="LMARGIN", new_y="NEXT")

    # Ism
    pdf.set_font("Helvetica", "B", 24)
    pdf.set_text_color(41, 128, 185)
    pdf.cell(0, 20, full_name, align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    # Natija
    pdf.set_font("Helvetica", "", 14)
    pdf.set_text_color(44, 62, 80)
    pdf.cell(0, 10, "has successfully completed the", align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 12, f"IELTS {subject_name} Test", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(10)

    # Band score
    pdf.set_font("Helvetica", "B", 36)
    pdf.set_text_color(39, 174, 96)
    pdf.cell(0, 25, f"Band {band}", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    # Natija tafsilotlari
    pdf.set_font("Helvetica", "", 14)
    pdf.set_text_color(44, 62, 80)
    pdf.cell(0, 10, f"Score: {score}/{total} ({percentage:.0f}%)", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(15)

    # Sana
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(127, 140, 141)
    pdf.cell(0, 8, f"Date: {date_str}", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, "Issued by IELTS Preparation Bot", align="C", new_x="LMARGIN", new_y="NEXT")

    # Pastki chiziq
    pdf.ln(10)
    pdf.set_draw_color(52, 152, 219)
    pdf.set_line_width(0.5)
    pdf.line(30, pdf.get_y(), 180, pdf.get_y())

    # Faylga saqlash
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        pdf.output(f.name)
        return f.name


async def certificate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/sertifikat buyrug'i"""
    from handlers.payment import require_premium
    if not await require_premium(update, "📊 PDF Sertifikat"):
        return
    user_id = update.effective_user.id
    session = get_session()
    try:
        # Oxirgi natijani olish
        result = (
            session.query(UserResult)
            .filter_by(user_id=user_id)
            .order_by(desc(UserResult.completed_at))
            .first()
        )

        if not result:
            await update.message.reply_text(
                "❌ Hali test natijangiz yo'q!\n\n"
                "Avval test yeching, keyin sertifikat oling."
            )
            return

        subject = session.query(Subject).get(result.subject_id)
        s_name = subject.name if subject else "Unknown"

        # Band hisoblash
        pct = result.percentage
        if pct >= 90:
            band = "8.0-9.0"
        elif pct >= 75:
            band = "6.5-7.5"
        elif pct >= 60:
            band = "5.5-6.0"
        elif pct >= 40:
            band = "4.5-5.0"
        else:
            band = "3.0-4.0"

        date_str = result.completed_at.strftime("%d %B %Y") if result.completed_at else datetime.now().strftime("%d %B %Y")
        full_name = update.effective_user.full_name or "Student"

        await update.message.reply_text("📊 Sertifikat tayyorlanmoqda...")

        pdf_path = generate_certificate(
            full_name, s_name, result.score, result.total, pct, band, date_str
        )

        with open(pdf_path, "rb") as pdf_file:
            await update.message.reply_document(
                document=pdf_file,
                filename=f"IELTS_Certificate_{s_name}_{full_name}.pdf",
                caption=f"🎓 <b>IELTS Sertifikat</b>\n\n"
                        f"👤 {full_name}\n"
                        f"📚 {s_name}\n"
                        f"📊 Band {band} ({pct:.0f}%)\n"
                        f"📅 {date_str}",
                parse_mode="HTML",
            )

        os.unlink(pdf_path)
    except Exception as e:
        await update.message.reply_text(f"❌ Xatolik: {str(e)[:100]}")
    finally:
        session.close()
