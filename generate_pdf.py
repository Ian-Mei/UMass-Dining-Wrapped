import updatecookies

from datetime import timedelta
import json
import fitz
import requests

from datetime import date
import shutil

session = requests.Session()
def loadcookies():
    cookies = updatecookies.updatecookies()
    session.cookies.update({cookie['name']: cookie['value'] for cookie in cookies})

    


def download_pdf(url, save_path):
    response = session.get(url)
    with open(save_path, "wb") as pdf_file:
        pdf_file.write(response.content)



def addpage(url, save_path):
    response = session.get(url)

    # Open the existing PDF
    existing_pdf = fitz.open(save_path)

    # Open the new page PDF
    new_pdf = fitz.open("pdf", response.content)

    if "No Activity" not in new_pdf[0].get_text():
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
    else:
        # Close the PDF files
        existing_pdf.close()
        new_pdf.close()



def generate_pdf():
    loadcookies()
    today = date(2023,12,16)
    year = today.year
    month = today.month
    day = today.day
    current_date = date(year, month, day)
    start_date = current_date - timedelta(days=5)
    end_date = current_date + timedelta(days=1)
    path = f"https://get.cbord.com/umass/full/historyPDF.php?dateS={start_date.year}-{start_date.month}-{start_date.day}&dateE={end_date.year}-{end_date.month}-{end_date.day}"
        
    save_path = "info.pdf"
    download_pdf(path, save_path)
    while True:
        start_date = current_date - timedelta(days=3)
        end_date = current_date + timedelta(days=2)
        
        path = f"https://get.cbord.com/umass/full/historyPDF.php?dateS={start_date.year}-{start_date.month}-{start_date.day}&dateE={end_date.year}-{end_date.month}-{end_date.day}"
        
        addpage(path, save_path)

        if month == 8 and day < 25:
            break

        current_date -= timedelta(days=3)
        year, month, day = current_date.year, current_date.month, current_date.day



