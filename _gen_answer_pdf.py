"""Focused answer PDF: which GST provider to use, and why not the others."""
import math
from fpdf import FPDF

OUT = "GST_Provider_Answer.pdf"

NAVY = (28, 42, 74)
GREEN = (22, 130, 75)
GREENBG = (224, 242, 231)
WHITE = (255, 255, 255)
GOLD = (240, 176, 32)
GREY = (205, 205, 205)
REDTXT = (150, 45, 45)
LIGHT = (242, 244, 249)

# why NOT the others
NOT_OTHERS = [
    ("Clear (ClearTax)", "More built for filing/compliance than credit signals - keep only as a backup."),
    ("Perfios (verification API)", "Fine, but use the Karza credit stack inside Perfios, not just plain verification."),
    ("Surepass", "Thin on filing-history/compliance depth - okay for a cheap pilot, not for the real score."),
    ("Signzy", "A heavy end-to-end KYB flow - overkill for simple GSTIN credit lookups."),
    ("Others (HyperVerge, Cashfree,\nAttestr, IDfy, BeFiSc)", "Only confirm a GSTIN is valid - too shallow for credit scoring."),
    ("Govt GST Portal (direct)", "Needs a GSP licence (Rs 2-5 cr capital + GSTN contract) - kills launch speed."),
]


def star_points(cx, cy, R):
    r = R * 0.40
    pts = []
    for i in range(10):
        ang = math.radians(-90 + i * 36)
        rad = R if i % 2 == 0 else r
        pts.append((cx + rad * math.cos(ang), cy + rad * math.sin(ang)))
    return pts


def draw_stars(pdf, x, y, n, size=2.6, gap=1.4):
    step = 2 * size + gap
    for i in range(n):
        cx = x + size + i * step
        pdf.set_fill_color(*GOLD)
        pdf.polygon(star_points(cx, y + size, size), style="F")


class PDF(FPDF):
    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 8, "Credit Signal Report - GST Provider: which one to use", align="C")


pdf = PDF(orientation="P", unit="mm", format="A4")
pdf.set_auto_page_break(auto=True, margin=15)
pdf.add_page()
LM = pdf.l_margin
FULL = pdf.w - 2 * LM

# Question
pdf.set_font("Helvetica", "B", 18)
pdf.set_text_color(*NAVY)
pdf.cell(0, 11, "Which GST provider should I use?", new_x="LMARGIN", new_y="NEXT")
pdf.ln(3)

# Answer banner
y0 = pdf.get_y()
pdf.set_fill_color(*GREEN)
pdf.rect(LM, y0, FULL, 22, style="F")
draw_stars(pdf, LM + 4, y0 + 4, 5)
pdf.set_xy(LM + 4, y0 + 10)
pdf.set_font("Helvetica", "B", 16)
pdf.set_text_color(*WHITE)
pdf.cell(0, 9, "Use  Karza  (now part of Perfios)")
pdf.set_y(y0 + 25)

# Why this one
pdf.set_font("Helvetica", "B", 12)
pdf.set_text_color(*NAVY)
pdf.set_x(LM)
pdf.cell(0, 7, "Why Karza is suitable", new_x="LMARGIN", new_y="NEXT")
pdf.set_font("Helvetica", "", 10.5)
pdf.set_text_color(40, 40, 40)
reasons = [
    "Its GST stack is purpose-built for lending and credit underwriting.",
    "Returns the exact signals the risk model needs: filing history (GSTR-1 / GSTR-3B), "
    "compliance gaps, cancellation/suspension and derived turnover - not just \"is this GSTIN valid\".",
    "Trusted by NBFCs and lenders, and handles the GSTN connection for us "
    "(no GSP licence or government contract).",
]
for r in reasons:
    pdf.set_x(LM)
    pdf.set_text_color(*GREEN)
    pdf.cell(6, 5.6, chr(149))
    pdf.set_text_color(40, 40, 40)
    pdf.multi_cell(FULL - 6, 5.6, r, new_x="LMARGIN", new_y="NEXT")
pdf.ln(4)

# Why not the others
pdf.set_font("Helvetica", "B", 12)
pdf.set_text_color(*NAVY)
pdf.set_x(LM)
pdf.cell(0, 7, "Why not the others", new_x="LMARGIN", new_y="NEXT")
pdf.ln(1)

n_w = 56
note_w = FULL - n_w
for i, (name, why) in enumerate(NOT_OTHERS):
    pdf.set_font("Helvetica", "", 9.5)
    nlines = pdf.multi_cell(note_w - 3, 5, why, dry_run=True, output="LINES")
    namelines = pdf.multi_cell(n_w - 3, 5, name, dry_run=True, output="LINES")
    h = max(len(nlines), len(namelines), 1) * 5 + 3
    x0, yy = LM, pdf.get_y()
    if i % 2 == 0:
        pdf.set_fill_color(*LIGHT)
        pdf.rect(x0, yy, FULL, h, style="F")
    pdf.set_xy(x0 + 2, yy + 1.5)
    pdf.set_font("Helvetica", "B", 9.5)
    pdf.set_text_color(*REDTXT)
    pdf.multi_cell(n_w - 3, 5, name)
    pdf.set_xy(x0 + n_w + 1, yy + 1.5)
    pdf.set_font("Helvetica", "", 9.5)
    pdf.set_text_color(45, 45, 45)
    pdf.multi_cell(note_w - 3, 5, why)
    pdf.set_xy(x0, yy + h)
pdf.ln(4)

# Bottom line
pdf.set_x(LM)
pdf.set_fill_color(*NAVY)
pdf.set_text_color(*WHITE)
pdf.set_font("Helvetica", "B", 10)
pdf.multi_cell(0, 6,
    "  Bottom line: Karza (Perfios) is the only option that gives deep, credit-relevant GST data "
    "without a GSP licence. Build a swappable GstProvider interface so the others can be added later "
    "if needed.", fill=True, new_x="LMARGIN", new_y="NEXT")

pdf.output(OUT)
print("WROTE", OUT)
