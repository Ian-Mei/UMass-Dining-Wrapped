import requests
import json
from bs4 import BeautifulSoup
from selenium import webdriver
import time

# Create a new instance of the Firefox WebDriver (you can use other drivers like Chrome, etc.)
driver = webdriver.Chrome()

# Open the website
driver.get("https://login.microsoftonline.com/7bd08b0b-3395-4dc1-94bb-d0b2e56a497f/saml2?SAMLRequest=fZJLj9sgFIX3%2FRUWe%2FyMExvFHqWNRo3Uh9Vxu%2BimwnCZINngcvG0%2FfclzkSaLjobFnD5zuEc9ne%2FpzF6AofamoZkcUoiMMJKbR4b8rW%2FpxW5a9%2FskU9jPrPD4s%2FmC%2FxcAH10DIs23K83z97PyJJktI%2FaxJMWzqJV3ppRG4iFnZLdINNqSAdaFHVJN1JktN4MA5XpkEO55Zt6p5JVh0T31glYxRri3QIkOh0b8nD4%2BOFHqYQaCqipqGXAZCWngwqsKlei2u6kKnMVxrHjiPoJGqL4iBcA4gIng54b35A8zQuaZTTf9WnBNjVL63hbpd9J1DnrrbDjW22uISzOMMtRIzN8AmResIsRlscpG65DyN73fUe7zw89ib7dwswvYYZ4DbJrfK%2Bz5mdh0l7TZqtj95LwOiA8GNylDdLe2sBZO4iXKRzFIJdkRpGcIShJvk9eqrS3hj8F7OnY2VGLP9FhHO2vdw64h1sPoZmJ%2B%2F8byeJs3dGSqnWULQZnEFppkCRpn2X%2F%2FUrtXw%3D%3D")

while(True):
    if(driver.current_url == "https://www.spire.umass.edu/psc/heproda/EMPLOYEE/SA/c/NUI_FRAMEWORK.PT_LANDINGPAGE.GBL?"):
        cookies_list = driver.get_cookies()
        driver.quit()
        break


# URL to scrape after logging in
url = 'https://www.spire.umass.edu/psc/heproda/EMPLOYEE/SA/c/NUI_FRAMEWORK.PT_LANDINGPAGE.GBL'

# # Load cookies from a JSON file
# with open('cookies.json', 'r') as file:
#     cookies_list = json.load(file)

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

    # Example: Extracting href and text content of all the links
    links = soup.find_all('a')
    for link in links:
        href = link.get('href')
        text_content = link.text.strip()  # Get the text content, stripping leading/trailing whitespaces
        print(f"Link: {href}, Text Content: {text_content}")
else:
    print(f"Failed to retrieve the page. Status code: {response.status_code}")
