"""Generate a recommendation PDF: best GST provider for the Credit Signal Report project."""
from fpdf import FPDF

OUT = "GST_Provider_Recommendation.pdf"

NAVY = (28, 42, 74)
GREEN = (22, 130, 75)
GREENBG = (224, 242, 231)
GREY = (90, 90, 90)
LIGHT = (236, 240, 248)
WHITE = (255, 255, 255)
AMBER = (170, 110, 10)


class PDF(FPDF):
    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 8, "Credit Signal Report  -  GST Provider Recommendation", align="C")


pdf = PDF(orientation="P", unit="mm", format="A4")
pdf.set_auto_page_break(auto=True, margin=15)
pdf.add_page()
LM = pdf.l_margin
FULL = pdf.w - 2 * LM

# ---- Title
pdf.set_font("Helvetica", "B", 20)
pdf.set_text_color(*NAVY)
pdf.cell(0, 11, "Which GST Provider for My Project?", new_x="LMARGIN", new_y="NEXT")
pdf.set_font("Helvetica", "", 10)
pdf.set_text_color(*GREY)
pdf.multi_cell(0, 5,
    "Project: Credit Signal Report - look up a buyer's GSTIN and read their filing history, "
    "compliance and turnover signals to judge credit risk.", new_x="LMARGIN", new_y="NEXT")
pdf.ln(4)

# ---- Verdict banner
pdf.set_fill_color(*GREEN)
pdf.set_text_color(*WHITE)
pdf.set_font("Helvetica", "B", 14)
pdf.multi_cell(0, 9, "  RECOMMENDED:  Karza  (now part of Perfios)", fill=True,
               new_x="LMARGIN", new_y="NEXT")
pdf.set_fill_color(*GREENBG)
pdf.set_text_color(20, 80, 45)
pdf.set_font("Helvetica", "", 10)
pdf.multi_cell(0, 5.5,
    "  Karza's GST stack was purpose-built for lending and underwriting. It returns exactly the "
    "signals our risk model needs - filing history (GSTR-1 / GSTR-3B), compliance gaps, "
    "cancellation/suspension and derived turnover - not just \"is this GSTIN valid\". "
    "It is the closest fit to a credit-signal product.",
    fill=True, new_x="LMARGIN", new_y="NEXT")
pdf.ln(5)

# ---- Why it fits (bullets)
pdf.set_font("Helvetica", "B", 12)
pdf.set_text_color(*NAVY)
pdf.cell(0, 7, "Why it fits this project", new_x="LMARGIN", new_y="NEXT")
pdf.set_font("Helvetica", "", 10)
pdf.set_text_color(40, 40, 40)
bullets = [
    "Built for credit decisions - used widely by lenders/NBFCs for automated underwriting.",
    "Deep data: filing-history depth + compliance scoring + turnover estimation feed our weighted score.",
    "Strong reputation for data intelligence and fraud signals (useful for red flags).",
    "Handles the GSTN tunnel for us - no GSP licence or government contract needed.",
]
for b in bullets:
    pdf.set_x(LM)
    pdf.set_text_color(*GREEN)
    pdf.cell(6, 5.5, chr(149))  # bullet
    pdf.set_text_color(40, 40, 40)
    pdf.multi_cell(FULL - 6, 5.5, b, new_x="LMARGIN", new_y="NEXT")
pdf.ln(3)

# ---- Decision table (rank)
pdf.set_font("Helvetica", "B", 12)
pdf.set_text_color(*NAVY)
pdf.cell(0, 7, "Ranked for our use case", new_x="LMARGIN", new_y="NEXT")

rows = [
    ("1", "Karza (Perfios)", "PRIMARY", "Deepest credit/filing-history signals; built for underwriting.", GREEN),
    ("2", "Clear (ClearTax)", "ALTERNATIVE", "A real GSP with mature GST APIs; more compliance-native.", NAVY),
    ("3", "Surepass", "CHEAP PILOT", "Affordable, fast to integrate; start here, upgrade for depth.", AMBER),
    ("-", "Govt GST portal (GSTN)", "NOT FOR MVP", "Needs GSP licence: Rs 2-5 cr capital + GSTN contract.", (150, 60, 60)),
]
c_rank, c_name, c_tag, c_note = 12, 46, 30, FULL - 12 - 46 - 30
# header
pdf.set_font("Helvetica", "B", 9.5)
pdf.set_fill_color(*NAVY)
pdf.set_text_color(*WHITE)
pdf.cell(c_rank, 8, " #", fill=True)
pdf.cell(c_name, 8, " Provider", fill=True)
pdf.cell(c_tag, 8, " Role", fill=True)
pdf.cell(c_note, 8, " Why", fill=True, new_x="LMARGIN", new_y="NEXT")

pdf.set_font("Helvetica", "", 9)
for i, (rank, name, tag, note, col) in enumerate(rows):
    bg = LIGHT if i % 2 else WHITE
    line_h = 4.6
    note_lines = pdf.multi_cell(c_note - 2, line_h, note, dry_run=True, output="LINES")
    h = max(len(note_lines), 1) * line_h + 3
    if pdf.get_y() + h > pdf.h - 15:
        pdf.add_page()
    x0, y0 = pdf.get_x(), pdf.get_y()
    pdf.set_fill_color(*bg)
    pdf.rect(x0, y0, FULL, h, style="F")
    pdf.set_xy(x0 + 1, y0 + 1.5)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(*GREY)
    pdf.cell(c_rank - 1, h - 3, rank)
    pdf.set_xy(x0 + c_rank + 1, y0 + 1.5)
    pdf.set_text_color(*NAVY)
    pdf.cell(c_name - 1, h - 3, name)
    pdf.set_xy(x0 + c_rank + c_name + 1, y0 + 1.5)
    pdf.set_text_color(*col)
    pdf.set_font("Helvetica", "B", 8)
    pdf.cell(c_tag - 1, h - 3, tag)
    pdf.set_xy(x0 + c_rank + c_name + c_tag + 1, y0 + 1.5)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(40, 40, 40)
    pdf.multi_cell(c_note - 2, line_h, note)
    pdf.set_xy(x0, y0 + h)
pdf.ln(5)

# ---- Free testing / sandbox section
if pdf.get_y() > pdf.h - 70:
    pdf.add_page()
pdf.set_x(LM)
pdf.set_font("Helvetica", "B", 12)
pdf.set_text_color(*NAVY)
pdf.cell(0, 7, "Testing without paying", new_x="LMARGIN", new_y="NEXT")
pdf.set_font("Helvetica", "", 9.5)
pdf.set_text_color(40, 40, 40)
pdf.set_x(LM)
pdf.multi_cell(0, 5,
    "Layer 1 - Build a MockGstProvider that returns fake but realistic filing/compliance data. "
    "Test the whole scoring + report flow offline: no API keys, no rate limits, no payment.",
    new_x="LMARGIN", new_y="NEXT")
pdf.ln(1)

test_rows = [
    ("Perfios", "10,000+ free sandbox credits", "BEST - same stack as Karza; test real signals free", GREEN),
    ("Sandbox.co.in (Quicko)", "Free to start; good docs + test cases", "Search GSTIN + return-status (compliance) APIs", NAVY),
    ("AppyFlow", "50 free requests", "Basic verification only - too shallow for scoring", AMBER),
    ("GSTINCheck", "20 free requests (email)", "Quick smoke test only", AMBER),
    ("Govt GST Developer Portal", "Sandbox + sample test keys", "Production GSP-gated; sandbox fine for trials", NAVY),
]
t_name, t_free = 52, 56
t_note = FULL - t_name - t_free
pdf.set_font("Helvetica", "B", 9)
pdf.set_fill_color(*NAVY)
pdf.set_text_color(*WHITE)
pdf.set_x(LM)
pdf.cell(t_name, 8, " Provider", fill=True)
pdf.cell(t_free, 8, " Free testing", fill=True)
pdf.cell(t_note, 8, " Notes for us", fill=True, new_x="LMARGIN", new_y="NEXT")
pdf.set_font("Helvetica", "", 8.7)
for i, (nm, free, note, col) in enumerate(test_rows):
    bg = LIGHT if i % 2 else WHITE
    lh = 4.6
    nlines = pdf.multi_cell(t_note - 2, lh, note, dry_run=True, output="LINES")
    h = max(len(nlines), 1) * lh + 3
    x0, y0 = LM, pdf.get_y()
    pdf.set_fill_color(*bg)
    pdf.rect(x0, y0, FULL, h, style="F")
    pdf.set_xy(x0 + 1, y0 + 1.5)
    pdf.set_font("Helvetica", "B", 8.7)
    pdf.set_text_color(*NAVY)
    pdf.cell(t_name - 1, h - 3, nm)
    pdf.set_xy(x0 + t_name + 1, y0 + 1.5)
    pdf.set_font("Helvetica", "", 8.7)
    pdf.set_text_color(40, 40, 40)
    pdf.cell(t_free - 1, h - 3, free)
    pdf.set_xy(x0 + t_name + t_free + 1, y0 + 1.5)
    pdf.set_text_color(*col)
    pdf.multi_cell(t_note - 2, lh, note)
    pdf.set_xy(x0, y0 + h)
pdf.ln(4)

# ---- Action box
if pdf.get_y() > pdf.h - 30:
    pdf.add_page()
pdf.set_x(LM)
pdf.set_fill_color(*NAVY)
pdf.set_text_color(*WHITE)
pdf.set_font("Helvetica", "B", 10.5)
pdf.multi_cell(0, 6.5,
    "  Plan: Develop against MockGstProvider (free, offline) -> validate on Perfios sandbox "
    "(10k free credits) -> go live on Karza (Perfios). One swappable GstProvider interface; "
    "cache + cost-log every call.",
    fill=True, new_x="LMARGIN", new_y="NEXT")

pdf.output(OUT)
print("WROTE", OUT)
