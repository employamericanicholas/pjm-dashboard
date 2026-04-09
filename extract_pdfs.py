import sys
import os

def extract_pdf(pdf_path, output_path):
    try:
        import pdfplumber
        print(f"Using pdfplumber for: {pdf_path}")
        with pdfplumber.open(pdf_path) as pdf:
            total = len(pdf.pages)
            print(f"  Total pages: {total}")
            with open(output_path, "w", encoding="utf-8") as f:
                for i, page in enumerate(pdf.pages):
                    text = page.extract_text() or ""
                    f.write(f"\n\n--- PAGE {i+1} ---\n\n")
                    f.write(text)
                    if (i + 1) % 50 == 0:
                        print(f"  Processed {i+1}/{total} pages...")
        print(f"  Done -> {output_path}")
    except ImportError:
        try:
            import pypdf
            print(f"Using pypdf for: {pdf_path}")
            reader = pypdf.PdfReader(pdf_path)
            total = len(reader.pages)
            print(f"  Total pages: {total}")
            with open(output_path, "w", encoding="utf-8") as f:
                for i, page in enumerate(reader.pages):
                    text = page.extract_text() or ""
                    f.write(f"\n\n--- PAGE {i+1} ---\n\n")
                    f.write(text)
                    if (i + 1) % 50 == 0:
                        print(f"  Processed {i+1}/{total} pages...")
            print(f"  Done -> {output_path}")
        except ImportError:
            print("ERROR: Neither pdfplumber nor pypdf is installed.")
            print("Run: pip install pdfplumber")
            sys.exit(1)

pdfs = [
    ("Monitoring Analytics 2025 PJM State of the Market Report 2025 Vol 1.pdf", "pjm_vol1.txt"),
    ("Monitoring Analytics 2025 PJM State of the Market Report 2025 Vol 2.pdf", "pjm_vol2.txt"),
]

base_dir = os.path.dirname(os.path.abspath(__file__))

for pdf_name, txt_name in pdfs:
    pdf_path = os.path.join(base_dir, pdf_name)
    txt_path = os.path.join(base_dir, txt_name)
    if not os.path.exists(pdf_path):
        print(f"SKIPPING (not found): {pdf_path}")
        continue
    extract_pdf(pdf_path, txt_path)

print("\nAll done!")
