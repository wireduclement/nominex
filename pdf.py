from fpdf import FPDF

class PDFGenerator:
    def __init__(self, title="Voting Codes"):
        self.title = title
        self.pdf = FPDF()
        self.pdf.set_auto_page_break(auto=True, margin=5)

    def header(self):
            self.pdf.set_font("Arial", "B", 16)
            self.pdf.cell(0, 10, self.title, ln=True, align="C")
            self.pdf.ln(10)

    def add_codes(self, codes):
        self.pdf.add_page()
        self.header()

        self.pdf.set_font("Arial", size=12)
        col_width = self.pdf.w / 3.5  # Three columns
        row_height = 10

        for idx, code in enumerate(codes):
            self.pdf.cell(col_width, row_height, code[1], border=1)
            if (idx + 1) % 3 == 0:
                self.pdf.ln(row_height)

    def output(self, filepath):
        self.pdf.output(filepath)