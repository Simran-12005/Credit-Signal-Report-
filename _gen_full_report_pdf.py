"""One combined PDF: pros/cons + star ratings + best pick + why-not-others + free testing."""
import math
from fpdf import FPDF

OUT = "GST_Provider_Report.pdf"

NAVY = (28, 42, 74)
LIGHT = (236, 240, 248)
GREEN = (224, 242, 231)
GREEN_S = (22, 130, 75)
RED = (250, 232, 232)
REDTXT = (150, 45, 45)
WHITE = (255, 255, 255)
GOLD = (240, 176, 32)
GREY = (205, 205, 205)
AMBER = (170, 110, 10)

# --- comparison rows: name, pros, cons, rating, verdict
ROWS = [
    ("Karza (Perfios)",
     "Built for lending/underwriting; deep filing history, compliance & turnover signals; trusted by NBFCs",
     "Enterprise sales motion; pricing opaque; can be pricier",
     5.0, "MOST RECOMMENDED - returns exactly the credit signals our risk model needs."),
    ("Clear (ClearTax)",
     "A real GSP; mature GST APIs; good docs; strong GST domain depth",
     "More filing/compliance-oriented than credit-signal-oriented",
     4.0, "Strong alternative / backup provider."),
    ("Perfios",
     "Enterprise-grade, 99.9% uptime SLA; large client base; owns Karza stack",
     "Geared to bigger clients; pricing on request",
     4.0, "Good - same group as Karza; use its credit stack."),
    ("Surepass",
     "Cheap, fast plug-and-play; batch processing; 3000+ clients",
     "Thin on filing-history / compliance depth",
     3.5, "Best for a cheap pilot; upgrade later for depth."),
    ("Signzy",
     "Customisable end-to-end KYB onboarding flows",
     "Heavier than plug-and-play; overkill for simple GSTIN lookups",
     3.0, "Only if we want full KYB orchestration."),
    ("Others (HyperVerge, Cashfree,\nAttestr, IDfy, BeFiSc)",
     "Easy, cheap, instant integration",
     "Mostly identity verification; little filing-history depth",
     2.5, "Not recommended - too shallow for credit scoring."),
    ("Govt GST Portal (GSTN, direct)",
     "Authoritative first-party data; no reseller markup",
     "Needs GSP licence: Rs 2-5 cr capital + GSTN contract; built for filing; months of effort",
     1.0, "NOT recommended for MVP - huge barrier, kills launch speed."),
]

NOT_OTHERS = [
    ("Clear (ClearTax)", "More built for filing/compliance than credit signals - keep only as a backup."),
    ("Perfios (plain verification)", "Use the Karza credit stack inside Perfios, not just plain verification."),
    ("Surepass", "Thin on filing-history/compliance depth - okay for a cheap pilot, not the real score."),
    ("Signzy", "A heavy end-to-end KYB flow - overkill for simple GSTIN credit lookups."),
    ("Others (HyperVerge, Cashfree, Attestr, IDfy, BeFiSc)", "Only confirm a GSTIN is valid - too shallow for credit scoring."),
    ("Govt GST Portal (direct)", "Needs a GSP licence (Rs 2-5 cr capital + GSTN contract) - kills launch speed."),
]

TEST_ROWS = [
    ("Perfios", "10,000+ free sandbox credits", "BEST - same stack as Karza; test real signals free", GREEN_S),
    ("Sandbox.co.in (Quicko)", "Free to start; good docs + test cases", "Search GSTIN + return-status (compliance) APIs", NAVY),
    ("AppyFlow", "50 free requests", "Basic verification only - too shallow for scoring", AMBER),
    ("GSTINCheck", "20 free requests (email)", "Quick smoke test only", AMBER),
    ("Govt GST Developer Portal", "Sandbox + sample test keys", "Production GSP-gated; sandbox fine for trials", NAVY),
]


def star_points(cx, cy, R):
    r = R * 0.40
    return [(cx + (R if i % 2 == 0 else r) * math.cos(math.radians(-90 + i * 36)),
             cy + (R if i % 2 == 0 else r) * math.sin(math.radians(-90 + i * 36))) for i in range(10)]


def draw_stars(pdf, x, y, rating, size=2.4, gap=1.2):
    full = int(rating)
    half = (rating - full) >= 0.5
    step = 2 * size + gap
    for i in range(5):
        cx, cy = x + size + i * step, y + size
        pdf.set_fill_color(*GREY)
        pdf.polygon(star_points(cx, cy, size), style="F")
        if i < full:
            pdf.set_fill_color(*GOLD)
            pdf.polygon(star_points(cx, cy, size), style="F")
        elif i == full and half:
            with pdf.rect_clip(cx - size, cy - size, size, 2 * size):
                pdf.set_fill_color(*GOLD)
                pdf.polygon(star_points(cx, cy, size), style="F")


class PDF(FPDF):
    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 8, f"Credit Signal Report - GST Provider Report  |  Page {self.page_no()}", align="C")


pdf = PDF(orientation="L", unit="mm", format="A4")
pdf.set_auto_page_break(auto=True, margin=15)
pdf.add_page()
LM = pdf.l_margin
FULL = pdf.w - 2 * LM


def section_title(txt):
    pdf.set_x(LM)
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(*NAVY)
    pdf.cell(0, 8, txt, new_x="LMARGIN", new_y="NEXT")


def line_h_for(text, w, lh):
    return max(len(pdf.multi_cell(w, lh, text, dry_run=True, output="LINES")), 1) * lh


# ===== Title
pdf.set_font("Helvetica", "B", 20)
pdf.set_text_color(*NAVY)
pdf.cell(0, 12, "GST Provider - Full Recommendation Report", new_x="LMARGIN", new_y="NEXT")
pdf.set_font("Helvetica", "", 10)
pdf.set_text_color(90, 90, 90)
pdf.multi_cell(0, 5,
    "For the Credit Signal Report: look up a buyer's GSTIN -> filing history, compliance & turnover. "
    "Star rating = fit for this project (5 = most recommended).", new_x="LMARGIN", new_y="NEXT")
pdf.ln(3)

# ===== 1. Comparison table
section_title("1.  Pros, Cons & Rating")
W_NAME, W_PROS, W_CONS, W_VERD = 46, 74, 64, 93
PAD, LINE_H = 1.5, 4.3


def comp_header():
    pdf.set_font("Helvetica", "B", 9.5)
    pdf.set_fill_color(*NAVY)
    pdf.set_text_color(*WHITE)
    pdf.cell(W_NAME, 9, "  Provider", fill=True)
    pdf.cell(W_PROS, 9, "  Pros", fill=True)
    pdf.cell(W_CONS, 9, "  Cons", fill=True)
    pdf.cell(W_VERD, 9, "  Rating & Verdict", fill=True, new_x="LMARGIN", new_y="NEXT")


comp_header()
for i, (name, pros, cons, rating, verdict) in enumerate(ROWS):
    pdf.set_font("Helvetica", "", 8.3)
    h = max(line_h_for(name, W_NAME - 2 * PAD, LINE_H),
            line_h_for(pros, W_PROS - 2 * PAD, LINE_H),
            line_h_for(cons, W_CONS - 2 * PAD, LINE_H),
            line_h_for(verdict, W_VERD - 2 * PAD, LINE_H) + 8) + 2 * PAD
    if pdf.get_y() + h > pdf.h - 15:
        pdf.add_page()
        comp_header()
    x0, y0 = pdf.get_x(), pdf.get_y()
    base = LIGHT if i % 2 else WHITE
    pdf.set_fill_color(*base); pdf.rect(x0, y0, W_NAME, h, style="F")
    pdf.set_xy(x0 + PAD, y0 + PAD); pdf.set_font("Helvetica", "B", 8.5); pdf.set_text_color(*NAVY)
    pdf.multi_cell(W_NAME - 2 * PAD, LINE_H, name)
    px = x0 + W_NAME
    pdf.set_fill_color(*GREEN); pdf.rect(px, y0, W_PROS, h, style="F")
    pdf.set_xy(px + PAD, y0 + PAD); pdf.set_font("Helvetica", "", 8.3); pdf.set_text_color(20, 90, 50)
    pdf.multi_cell(W_PROS - 2 * PAD, LINE_H, pros)
    cx = px + W_PROS
    pdf.set_fill_color(*RED); pdf.rect(cx, y0, W_CONS, h, style="F")
    pdf.set_xy(cx + PAD, y0 + PAD); pdf.set_text_color(140, 30, 30)
    pdf.multi_cell(W_CONS - 2 * PAD, LINE_H, cons)
    vx = cx + W_CONS
    pdf.set_fill_color(*base); pdf.rect(vx, y0, W_VERD, h, style="F")
    draw_stars(pdf, vx + PAD, y0 + PAD, rating)
    pdf.set_xy(vx + PAD + 35, y0 + PAD - 0.5); pdf.set_font("Helvetica", "B", 9); pdf.set_text_color(*NAVY)
    pdf.cell(0, 5.5, f"{rating:.1f} / 5")
    pdf.set_xy(vx + PAD, y0 + PAD + 7); pdf.set_font("Helvetica", "", 8.3); pdf.set_text_color(45, 45, 45)
    pdf.multi_cell(W_VERD - 2 * PAD, LINE_H, verdict)
    pdf.set_xy(x0, y0 + h)
pdf.ln(5)

# ===== 2. Best & preferred
if pdf.get_y() > pdf.h - 55:
    pdf.add_page()
y0 = pdf.get_y()
pdf.set_fill_color(*GREEN); pdf.rect(LM, y0, FULL, 8, style="F")
draw_stars(pdf, LM + 2, y0 + 1.6, 5.0, size=2.2)
pdf.set_xy(LM + 40, y0 + 1); pdf.set_font("Helvetica", "B", 12); pdf.set_text_color(20, 90, 50)
pdf.cell(0, 6, "2.  BEST & PREFERRED:  Karza (now part of Perfios)")
pdf.set_xy(LM, y0 + 9); pdf.set_font("Helvetica", "", 9.3); pdf.set_text_color(40, 40, 40)
pdf.multi_cell(FULL, 4.8,
    "Karza (Perfios) is the best and preferred choice because its GST stack is purpose-built for "
    "lending and underwriting. Unlike commodity verifiers that only confirm a GSTIN is valid, Karza "
    "returns the exact signals our risk model scores on: filing history (GSTR-1 / GSTR-3B), compliance "
    "gaps, cancellation/suspension status and derived turnover. It is trusted by NBFCs, handles the "
    "GSTN tunnel for us (no GSP licence or government contract), and gives the deepest credit-relevant "
    "data of any option - earning the full 5/5 fit rating.", new_x="LMARGIN", new_y="NEXT")
pdf.ln(1)
pdf.set_x(LM); pdf.set_font("Helvetica", "B", 9); pdf.set_text_color(*NAVY)
pdf.multi_cell(FULL, 4.8,
    "Preferred rollout: pilot on Surepass (cheap, fast) to launch quickly, then switch to Karza "
    "(Perfios) via a swappable GstProvider interface. Keep Clear (ClearTax) as the backup provider.",
    new_x="LMARGIN", new_y="NEXT")
pdf.ln(5)

# ===== 3. Why not the others
if pdf.get_y() > pdf.h - 60:
    pdf.add_page()
section_title("3.  Why not the others")
n_w = 70
note_w = FULL - n_w
for i, (name, why) in enumerate(NOT_OTHERS):
    pdf.set_font("Helvetica", "", 9.3)
    h = max(line_h_for(why, note_w - 3, 4.8), line_h_for(name, n_w - 3, 4.8), 1 * 4.8) + 3
    if pdf.get_y() + h > pdf.h - 15:
        pdf.add_page()
    x0, yy = LM, pdf.get_y()
    if i % 2 == 0:
        pdf.set_fill_color(*LIGHT); pdf.rect(x0, yy, FULL, h, style="F")
    pdf.set_xy(x0 + 2, yy + 1.5); pdf.set_font("Helvetica", "B", 9.3); pdf.set_text_color(*REDTXT)
    pdf.multi_cell(n_w - 3, 4.8, name)
    pdf.set_xy(x0 + n_w + 1, yy + 1.5); pdf.set_font("Helvetica", "", 9.3); pdf.set_text_color(45, 45, 45)
    pdf.multi_cell(note_w - 3, 4.8, why)
    pdf.set_xy(x0, yy + h)
pdf.ln(5)

# ===== 4. Free testing
if pdf.get_y() > pdf.h - 70:
    pdf.add_page()
section_title("4.  Testing without paying")
pdf.set_font("Helvetica", "", 9.5); pdf.set_text_color(40, 40, 40); pdf.set_x(LM)
pdf.multi_cell(0, 5,
    "Layer 1 - Build a MockGstProvider returning fake but realistic data: test the whole scoring + "
    "report flow offline with no API keys, no rate limits, no payment. Layer 2 - free sandboxes below.",
    new_x="LMARGIN", new_y="NEXT")
pdf.ln(1)
t_name, t_free = 56, 60
t_note = FULL - t_name - t_free
pdf.set_font("Helvetica", "B", 9); pdf.set_fill_color(*NAVY); pdf.set_text_color(*WHITE); pdf.set_x(LM)
pdf.cell(t_name, 8, " Provider", fill=True)
pdf.cell(t_free, 8, " Free testing", fill=True)
pdf.cell(t_note, 8, " Notes for us", fill=True, new_x="LMARGIN", new_y="NEXT")
pdf.set_font("Helvetica", "", 8.7)
for i, (nm, free, note, col) in enumerate(TEST_ROWS):
    bg = LIGHT if i % 2 else WHITE
    h = max(line_h_for(note, t_note - 2, 4.6), 1 * 4.6) + 3
    x0, yy = LM, pdf.get_y()
    pdf.set_fill_color(*bg); pdf.rect(x0, yy, FULL, h, style="F")
    pdf.set_xy(x0 + 1, yy + 1.5); pdf.set_font("Helvetica", "B", 8.7); pdf.set_text_color(*NAVY)
    pdf.cell(t_name - 1, h - 3, nm)
    pdf.set_xy(x0 + t_name + 1, yy + 1.5); pdf.set_font("Helvetica", "", 8.7); pdf.set_text_color(40, 40, 40)
    pdf.cell(t_free - 1, h - 3, free)
    pdf.set_xy(x0 + t_name + t_free + 1, yy + 1.5); pdf.set_text_color(*col)
    pdf.multi_cell(t_note - 2, 4.6, note)
    pdf.set_xy(x0, yy + h)
pdf.ln(5)

# ===== Bottom line
if pdf.get_y() > pdf.h - 25:
    pdf.add_page()
pdf.set_x(LM); pdf.set_fill_color(*NAVY); pdf.set_text_color(*WHITE); pdf.set_font("Helvetica", "B", 10)
pdf.multi_cell(0, 6.5,
    "  Bottom line: Develop against MockGstProvider (free, offline) -> validate on Perfios sandbox "
    "(10k free credits) -> go live on Karza (Perfios). One swappable GstProvider interface; "
    "cache + cost-log every call. Karza is the only option giving deep, credit-relevant GST data "
    "without a GSP licence.", fill=True, new_x="LMARGIN", new_y="NEXT")

pdf.output(OUT)
print("WROTE", OUT)
