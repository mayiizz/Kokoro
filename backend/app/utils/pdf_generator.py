from fpdf import FPDF

def generate_pdf(text: str, filename="resume.pdf"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=11)

    for line in text.split("\n"):
        pdf.multi_cell(0, 8, line)

    pdf.output(filename)
    return filename
