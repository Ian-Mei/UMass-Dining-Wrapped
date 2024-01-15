import tabula
import fitz
def has_activity(pdf_path,page_num):
    doc = fitz.open(pdf_path)

    page = doc[page_num]
    print(page.get_text())
    if "No Activity" in page.get_text():
        
        return False
    return True

print(has_activity("info.pdf",3))
