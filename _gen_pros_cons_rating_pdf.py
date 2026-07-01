"""GST provider Pros/Cons + Star-rating verdict PDF for the Credit Signal Report project."""
import math
from fpdf import FPDF

OUT = "GST_Provider_ProsCons_Rating.pdf"

NAVY = (28, 42, 74)
LIGHT = (236, 240, 248)
GREEN = (224, 242, 231)
RED = (250, 232, 232)
WHITE = (255, 255, 255)
GOLD = (240, 176, 32)
GREY = (205, 205, 205)

# Provider, Pros, Cons, rating(0-5), verdict
ROWS = [
    ("Karza (Perfios)",
     "Built for lending/underwriting; deep filing history, compliance & turnover signals; trusted by NBFCs",
     "Enterprise sales motion; pricing opaque; can be pricier",
     5.0,
     "MOST RECOMMENDED - returns exactly the credit signals our risk model needs."),
    ("Clear (ClearTax)",
     "A real GSP; mature GST APIs; good docs; strong GST domain depth",
     "More filing/compliance-oriented than credit-signal-oriented",
     4.0,
     "Strong alternative / backup provider."),
    ("Perfios",
     "Enterprise-grade, 99.9% uptime SLA; large client base; owns Karza stack",
     "Geared to bigger clients; pricing on request",
     4.0,
     "Good - same group as Karza; use its credit stack."),
    ("Surepass",
     "Cheap, fast plug-and-play; batch processing; 3000+ clients",
     "Thin on filing-history / compliance depth",
     3.5,
     "Best for a cheap pilot; upgrade later for depth."),
    ("Signzy",
     "Customisable end-to-end KYB onboarding flows",
     "Heavier than plug-and-play; overkill for simple GSTIN lookups",
     3.0,
     "Only if we want full KYB orchestration."),
    ("Others (HyperVerge, Cashfree,\nAttestr, IDfy, BeFiSc)",
     "Easy, cheap, instant integration",
     "Mostly identity verification; little filing-history depth",
     2.5,
     "Not recommended - too shallow for credit scoring."),
    ("Govt GST Portal (GSTN, direct)",
     "Authoritative first-party data; no reseller markup",
     "Needs GSP licence: Rs 2-5 cr capital + GSTN contract; built for filing; months of effort",
     1.0,
     "NOT recommended for MVP - huge barrier, kills launch speed."),
]


class PDF(FPDF):
    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 8, f"Credit Signal Report - GST Provider Pros/Cons & Rating  |  Page {self.page_no()}",
                  align="C")


def star_points(cx, cy, R):
    r = R * 0.40
    pts = []
    for i in range(10):
        ang = math.radians(-90 + i * 36)
        rad = R if i % 2 == 0 else r
        pts.append((cx + rad * math.cos(ang), cy + rad * math.sin(ang)))
    return pts


def draw_stars(pdf, x, y, rating, size=2.4, gap=1.2):
    """Draw 5 stars; filled per rating (supports .5 via narrower half)."""
    full = int(rating)
    half = (rating - full) >= 0.5
    step = 2 * size + gap
    for i in range(5):
        cx = x + size + i * step
        cy = y + size
        # background (empty) star
        pdf.set_fill_color(*GREY)
        pdf.polygon(star_points(cx, cy, size), style="F")
        if i < full:
            pdf.set_fill_color(*GOLD)
            pdf.polygon(star_points(cx, cy, size), style="F")
        elif i == full and half:
            # draw a clipped half star (left half) gold
            with pdf.rect_clip(cx - size, cy - size, size, 2 * size):
                pdf.set_fill_color(*GOLD)
                pdf.polygon(star_points(cx, cy, size), style="F")
    return 5 * step


pdf = PDF(orientation="L", unit="mm", format="A4")
pdf.set_auto_page_break(auto=True, margin=15)
pdf.add_page()
LM = pdf.l_margin

# Title
pdf.set_font("Helvetica", "B", 19)
pdf.set_text_color(*NAVY)
pdf.cell(0, 11, "GST Provider - Pros, Cons & Recommendation", new_x="LMARGIN", new_y="NEXT")
pdf.set_font("Helvetica", "", 9.5)
pdf.set_text_color(90, 90, 90)
pdf.multi_cell(0, 5,
    "For the Credit Signal Report (look up a buyer's GSTIN -> filing history, compliance & turnover). "
    "Star rating = fit for this project (5 = most recommended).", new_x="LMARGIN", new_y="NEXT")
pdf.ln(2)

# Column widths (landscape usable ~277)
W_NAME, W_PROS, W_CONS, W_VERD = 46, 74, 64, 93
PAD = 1.5
LINE_H = 4.3


def header_row():
    pdf.set_font("Helvetica", "B", 9.5)
    pdf.set_fill_color(*NAVY)
    pdf.set_text_color(*WHITE)
    pdf.cell(W_NAME, 9, "  Provider", fill=True)
    pdf.cell(W_PROS, 9, "  Pros", fill=True)
    pdf.cell(W_CONS, 9, "  Cons", fill=True)
    pdf.cell(W_VERD, 9, "  Rating & Verdict", fill=True, new_x="LMARGIN", new_y="NEXT")


def cell_h(text, w):
    lines = pdf.multi_cell(w - 2 * PAD, LINE_H, text, dry_run=True, output="LINES")
    return max(len(lines), 1) * LINE_H


header_row()
for i, (name, pros, cons, rating, verdict) in enumerate(ROWS):
    pdf.set_font("Helvetica", "", 8.3)
    h_name = cell_h(name, W_NAME)
    h_pros = cell_h(pros, W_PROS)
    h_cons = cell_h(cons, W_CONS)
    h_verd = cell_h(verdict, W_VERD) + 8  # room for stars row
    row_h = max(h_name, h_pros, h_cons, h_verd) + 2 * PAD

    if pdf.get_y() + row_h > pdf.h - 15:
        pdf.add_page()
        header_row()

    x0, y0 = pdf.get_x(), pdf.get_y()
    base = LIGHT if i % 2 else WHITE

    # Provider
    pdf.set_fill_color(*base)
    pdf.rect(x0, y0, W_NAME, row_h, style="F")
    pdf.set_xy(x0 + PAD, y0 + PAD)
    pdf.set_font("Helvetica", "B", 8.5)
    pdf.set_text_color(*NAVY)
    pdf.multi_cell(W_NAME - 2 * PAD, LINE_H, name)

    # Pros
    px = x0 + W_NAME
    pdf.set_fill_color(*GREEN)
    pdf.rect(px, y0, W_PROS, row_h, style="F")
    pdf.set_xy(px + PAD, y0 + PAD)
    pdf.set_font("Helvetica", "", 8.3)
    pdf.set_text_color(20, 90, 50)
    pdf.multi_cell(W_PROS - 2 * PAD, LINE_H, pros)

    # Cons
    cx = px + W_PROS
    pdf.set_fill_color(*RED)
    pdf.rect(cx, y0, W_CONS, row_h, style="F")
    pdf.set_xy(cx + PAD, y0 + PAD)
    pdf.set_text_color(140, 30, 30)
    pdf.multi_cell(W_CONS - 2 * PAD, LINE_H, cons)

    # Verdict + stars
    vx = cx + W_CONS
    pdf.set_fill_color(*base)
    pdf.rect(vx, y0, W_VERD, row_h, style="F")
    draw_stars(pdf, vx + PAD, y0 + PAD, rating)
    pdf.set_xy(vx + PAD + 35, y0 + PAD - 0.5)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(*NAVY)
    pdf.cell(0, 5.5, f"{rating:.1f} / 5")
    pdf.set_xy(vx + PAD, y0 + PAD + 7)
    pdf.set_font("Helvetica", "", 8.3)
    pdf.set_text_color(45, 45, 45)
    pdf.multi_cell(W_VERD - 2 * PAD, LINE_H, verdict)

    pdf.set_xy(x0, y0 + row_h)

# ---- Best & Preferred conclusion box
pdf.ln(5)
if pdf.get_y() > pdf.h - 50:
    pdf.add_page()
FULL = pdf.w - 2 * LM
y0 = pdf.get_y()
pdf.set_fill_color(*GREEN)
pdf.rect(LM, y0, FULL, 8, style="F")
pdf.set_xy(LM + 2, y0 + 1)
pdf.set_font("Helvetica", "B", 12)
pdf.set_text_color(20, 90, 50)
# gold stars beside the title
draw_stars(pdf, LM + 2, y0 + 1.6, 5.0, size=2.2)
pdf.set_xy(LM + 40, y0 + 1)
pdf.cell(0, 6, "BEST & PREFERRED:  Karza (now part of Perfios)")
pdf.set_xy(LM, y0 + 9)
pdf.set_font("Helvetica", "", 9.3)
pdf.set_text_color(40, 40, 40)
pdf.multi_cell(FULL, 4.8,
    "Karza (Perfios) is the best and preferred choice for the Credit Signal Report because its GST "
    "stack is purpose-built for lending and underwriting. Unlike the commodity verifiers that only "
    "confirm a GSTIN is valid, Karza returns the exact signals our risk model scores on: filing "
    "history (GSTR-1 / GSTR-3B), compliance gaps, cancellation/suspension status and derived "
    "turnover. It is widely trusted by NBFCs and lenders, handles the GSTN tunnel for us (no GSP "
    "licence or government contract), and gives the deepest credit-relevant data of any option - "
    "earning it the full 5/5 fit rating.",
    new_x="LMARGIN", new_y="NEXT")
pdf.ln(1)
pdf.set_x(LM)
pdf.set_font("Helvetica", "B", 9)
pdf.set_text_color(*NAVY)
pdf.multi_cell(FULL, 4.8,
    "Preferred rollout: pilot on Surepass (cheap, fast) to launch quickly, then switch to Karza "
    "(Perfios) via a swappable GstProvider interface for production-grade credit signals. Keep Clear "
    "(ClearTax) as the backup provider.", new_x="LMARGIN", new_y="NEXT")

pdf.output(OUT)
print("WROTE", OUT)
