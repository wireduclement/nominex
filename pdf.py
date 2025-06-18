from fpdf import FPDF
from datetime import datetime

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


class ResultPDFGenerator:
    def __init__(self, results):
        self.results = results

    def generate(self, filename="election_winners.pdf"):
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()

        # Title
        pdf.set_font("Arial", "B", 20)
        pdf.cell(0, 10, f"{datetime.now().year} Final Election Results", ln=True, align="C")
        pdf.ln(10)

        # Style settings
        pdf.set_font("Arial", "", 12)
        pdf.set_fill_color(230, 230, 230)

        current_position = None
        for result in self.results:
            (
                full_name,
                class_name,
                gender,
                photo_url,
                position_name,
                total_votes,
                rank
            ) = result

            if position_name != current_position:
                pdf.ln(5)
                pdf.set_font("Arial", "B", 14)
                pdf.set_text_color(0)
                pdf.cell(0, 10, f"Position: {position_name}", ln=True)
                pdf.set_font("Arial", "B", 12)
                pdf.set_fill_color(200, 220, 255)
                pdf.cell(60, 8, "Role", 1, 0, "C", fill=True)
                pdf.cell(70, 8, "Candidates", 1, 0, "C", fill=True)
                pdf.cell(30, 8, "Class", 1, 0, "C", fill=True)
                pdf.cell(30, 8, "Votes", 1, 1, "C", fill=True)
                current_position = position_name

            label = "Main" if rank == 1 else "Assistant"
            pdf.set_font("Arial", "", 12)
            pdf.set_fill_color(255, 255, 255)
            pdf.cell(60, 8, label, 1)
            pdf.cell(70, 8, full_name, 1)
            pdf.cell(30, 8, class_name, 1)
            pdf.cell(30, 8, str(total_votes), 1, ln=True)

        pdf.output(filename)
