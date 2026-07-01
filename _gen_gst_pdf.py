"""Generate a table-format PDF of GST provider pros & cons."""
from fpdf import FPDF

OUT = "GST_Provider_Pros_Cons.pdf"

# (Provider, Best for, Pros, Cons)
PROVIDERS = [
    ("Karza (now Perfios)",
     "Credit / underwriting GST stack",
     "Built for lenders/NBFCs; rich filing history, compliance & turnover signals (not just verification); strong data-intelligence reputation",
     "Enterprise sales motion; pricing opaque; can be pricier"),
    ("Perfios",
     "Reliable financial-data platform",
     "Enterprise-grade, 99.9% uptime SLA; large client base; now owns Karza's stack",
     "Geared to larger clients; pricing on request"),
    ("Clear (ClearTax)",
     "Compliance-native (is a GSP)",
     "First-party GSP access; mature GST APIs; good documentation",
     "More filing/compliance-oriented than credit-signal-oriented"),
    ("Signzy",
     "Customisable KYB onboarding flows",
     "End-to-end orchestrated KYB journeys; good for banks/enterprises",
     "Heavier than plug-and-play; overkill for simple GSTIN lookups"),
    ("Surepass",
     "Cheap, quick-start verification",
     "Affordable; batch processing; 3000+ clients; fast integration",
     "Thin on filing-history / compliance depth"),
    ("Others (HyperVerge, Cashfree,\nAttestr, IDfy, Gridlines, BeFiSc)",
     "Commodity GSTIN verification",
     "Easy, cheap, instant integration",
     "Mostly identity verification; little filing-history depth"),
]

GOVT = (
    "Direct Govt GST Portal (GSTN, via GSP licence)",
    "Authoritative first-party data; no reseller markup; full API surface",
    "Needs India IT/BFSI company with Rs 2-5 cr capital + Rs 5-10 cr turnover; "
    "GSTN contract + security audits; built for filing, not third-party lookups; "
    "months of effort - kills the launch-in-weeks goal",
)

# Theme colors
NAVY = (28, 42, 74)
LIGHT = (236, 240, 248)
GREEN = (224, 242, 231)
RED = (250, 232, 232)
WHITE = (255, 255, 255)


class PDF(FPDF):
    def header(self):
        if self.page_no() == 1:
            return

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(140, 140, 140)
        self.cell(0, 8, f"Credit Signal Report  -  GST Provider Comparison   |   Page {self.page_no()}",
                  align="C")


pdf = PDF(orientation="L", unit="mm", format="A4")
pdf.set_auto_page_break(auto=True, margin=15)
pdf.add_page()

# Title
pdf.set_font("Helvetica", "B", 20)
pdf.set_text_color(*NAVY)
pdf.cell(0, 12, "GST Data Provider - Pros & Cons", new_x="LMARGIN", new_y="NEXT")
pdf.set_font("Helvetica", "", 10)
pdf.set_text_color(90, 90, 90)
pdf.multi_cell(0, 5,
    "For the Credit Signal Report we look up a third-party buyer's GSTIN to read identity + "
    "filing/compliance history. Recommended path: a third-party API provider behind a swappable "
    "interface. Recommended pick: Karza (Perfios); alternative: Clear; cheap pilot: Surepass.")
pdf.ln(3)

# Column layout (landscape A4 usable width ~ 277mm)
W_NAME = 52
W_BEST = 55
W_PROS = 85
W_CONS = 85
ROW_H = 6
PAD = 1.5


def header_row():
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_fill_color(*NAVY)
    pdf.set_text_color(*WHITE)
    pdf.cell(W_NAME, 9, "  Provider", border=0, fill=True)
    pdf.cell(W_BEST, 9, "  Best for", border=0, fill=True)
    pdf.cell(W_PROS, 9, "  Pros", border=0, fill=True)
    pdf.cell(W_CONS, 9, "  Cons", border=0, fill=True, new_x="LMARGIN", new_y="NEXT")


def wrapped_height(text, w, line_h):
    # estimate number of lines using split_only
    lines = pdf.multi_cell(w - 2 * PAD, line_h, text, dry_run=True, output="LINES")
    return max(len(lines), 1) * line_h


def data_row(name, best, pros, cons, zebra):
    pdf.set_font("Helvetica", "", 8.5)
    line_h = 4.4
    h_name = wrapped_height(name, W_NAME, line_h)
    h_best = wrapped_height(best, W_BEST, line_h)
    h_pros = wrapped_height(pros, W_PROS, line_h)
    h_cons = wrapped_height(cons, W_CONS, line_h)
    row_h = max(h_name, h_best, h_pros, h_cons) + 2 * PAD

    if pdf.get_y() + row_h > pdf.h - 15:
        pdf.add_page()
        header_row()

    x0 = pdf.get_x()
    y0 = pdf.get_y()

    base = LIGHT if zebra else WHITE
    # Name cell
    pdf.set_fill_color(*base)
    pdf.rect(x0, y0, W_NAME, row_h, style="F")
    pdf.set_xy(x0 + PAD, y0 + PAD)
    pdf.set_font("Helvetica", "B", 8.5)
    pdf.set_text_color(*NAVY)
    pdf.multi_cell(W_NAME - 2 * PAD, line_h, name)

    # Best for
    pdf.set_fill_color(*base)
    pdf.rect(x0 + W_NAME, y0, W_BEST, row_h, style="F")
    pdf.set_xy(x0 + W_NAME + PAD, y0 + PAD)
    pdf.set_font("Helvetica", "", 8.5)
    pdf.set_text_color(50, 50, 50)
    pdf.multi_cell(W_BEST - 2 * PAD, line_h, best)

    # Pros (green tint)
    pdf.set_fill_color(*GREEN)
    pdf.rect(x0 + W_NAME + W_BEST, y0, W_PROS, row_h, style="F")
    pdf.set_xy(x0 + W_NAME + W_BEST + PAD, y0 + PAD)
    pdf.set_text_color(20, 90, 50)
    pdf.multi_cell(W_PROS - 2 * PAD, line_h, pros)

    # Cons (red tint)
    pdf.set_fill_color(*RED)
    pdf.rect(x0 + W_NAME + W_BEST + W_PROS, y0, W_CONS, row_h, style="F")
    pdf.set_xy(x0 + W_NAME + W_BEST + W_PROS + PAD, y0 + PAD)
    pdf.set_text_color(140, 30, 30)
    pdf.multi_cell(W_CONS - 2 * PAD, line_h, cons)

    pdf.set_xy(x0, y0 + row_h)


header_row()
for i, (name, best, pros, cons) in enumerate(PROVIDERS):
    data_row(name, best, pros, cons, zebra=(i % 2 == 1))

# Govt option as a highlighted full-width-ish block
pdf.ln(4)
pdf.set_x(pdf.l_margin)
pdf.set_font("Helvetica", "B", 11)
pdf.set_text_color(*NAVY)
pdf.cell(0, 7, "Alternative considered: Direct Govt GST Portal (GSTN) - not for MVP",
         new_x="LMARGIN", new_y="NEXT")
pdf.set_font("Helvetica", "", 8.5)
pdf.set_x(pdf.l_margin)
pdf.set_text_color(20, 90, 50)
pdf.multi_cell(0, 4.4, "Pros: " + GOVT[1], new_x="LMARGIN", new_y="NEXT")
pdf.set_x(pdf.l_margin)
pdf.set_text_color(140, 30, 30)
pdf.multi_cell(0, 4.4, "Cons: " + GOVT[2], new_x="LMARGIN", new_y="NEXT")

# Recommendation footer
pdf.ln(3)
pdf.set_x(pdf.l_margin)
pdf.set_fill_color(*NAVY)
pdf.set_text_color(*WHITE)
pdf.set_font("Helvetica", "B", 9.5)
pdf.multi_cell(0, 6,
    "  Recommendation: Use a third-party provider behind a swappable GstProvider interface. "
    "Primary = Karza (Perfios) for filing-history depth; alternative = Clear (a GSP); "
    "cheap pilot = Surepass. Cache + cost-log every call.",
    fill=True)

pdf.output(OUT)
print("WROTE", OUT)
