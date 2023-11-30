import json
import requests
from bs4 import BeautifulSoup



def download_pdf(url, save_path):
    response = session.get(url)
    with open(save_path, 'wb') as pdf_file:
        pdf_file.write(response.content)


# URL to scrape after logging in
url = 'https://get.cbord.com/umass/full/history.php'

# Load cookies from a JSON file
with open('cookies.json', 'r') as file:
    cookies_list = json.load(file)

# Convert the list of cookies to a CookieJar
cookies = requests.utils.cookiejar_from_dict({cookie['name']: cookie['value'] for cookie in cookies_list})

# Create a session and set the loaded cookies
session = requests.Session()
session.cookies = cookies

# Now, you can use the session to send requests with the loaded cookies
response = session.get(url)

# Check if the request was successful (status code 200)
if response.status_code == 200:
    # Parse the HTML content of the page
    soup = BeautifulSoup(response.text, 'html.parser')
    # Assuming you want to extract information from a specific section with a class
    section_class = 'history_table table-responsive'
    section = soup.find('div', class_=section_class)

    #print(soup.get_text())
    
    for link in soup.find_all('a'):
        if(link.get('href')[:6]=="histor"):
            pdf = "https://get.cbord.com/umass/full/" + link.get('href')
        
    download_pdf(pdf,"info.pdf")
    # Check if the section is found


    # if section:
    #     # Extract specific information within the section
    #     specific_info = section.find('span', class_='info-class').text
    #     print(f"Specific Information: {specific_info}")
    # else:
    #     print("Section not found on the page.")


else:
    print(f"Failed to retrieve the page. Status code: {response.status_code}")



