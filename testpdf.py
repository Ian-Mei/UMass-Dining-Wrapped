# extract_doc_info.py
import json
from PyPDF2 import PdfFileReader
import fitz
import requests
import tabula
from datetime import date

with open(r"UMass-Dining-Wrapped\cookies.json", "r") as file:
    cookies_list = json.load(file)

# Convert the list of cookies to a CookieJar
cookies = requests.utils.cookiejar_from_dict(
    {cookie["name"]: cookie["value"] for cookie in cookies_list}
)

# Create a session and set the loaded cookies
session = requests.Session()
session.cookies = cookies


def download_pdf(url, save_path):
    response = session.get(url)
    with open(save_path, "wb") as pdf_file:
        pdf_file.write(response.content)


import shutil

def addpage(url, save_path):
    response = session.get(url)

    # Open the existing PDF
    existing_pdf = fitz.open(save_path)

    # Open the new page PDF
    new_pdf = fitz.open("pdf", response.content)

    # Add new pages to the existing PDF
    existing_pdf.insert_pdf(new_pdf)

    # Save the modified PDF to a temporary file
    temp_save_path = save_path + ".temp"
    existing_pdf.save(temp_save_path)

    # Close the PDF files
    existing_pdf.close()
    new_pdf.close()

    # Replace the original file with the temporary one
    shutil.move(temp_save_path, save_path)





if __name__ == "__main__":
    today = date.today()
    year = today.year
    month = today.month
    day = today.day
    path = f"https://get.cbord.com/umass/full/historyPDF.php?dateS={year}-{month}-{day-14}&dateE={year}-{month}-{day}"
    save_path = "UMass-Dining-Wrapped\info.pdf"
    download_pdf(path, save_path)

    day = day - 12
    path = f"https://get.cbord.com/umass/full/historyPDF.php?dateS={year}-{month}-{day-14}&dateE={year}-{month}-{day}"
    addpage(path, save_path)

    tables = tabula.read_pdf("UMass-Dining-Wrapped\info.pdf", pages="all")
    print(tables)

