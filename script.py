#######################################################################################################################################################################################

import requests
import time
import json
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException, NoSuchElementException, TimeoutException
import datetime
from PIL import Image
from anticaptchaofficial.imagecaptcha import imagecaptcha

import docker
import os

chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument("--headless")  # Run Chrome in headless mode

driver = webdriver.Remote(
    command_executor='http://selenium-hub:4444/wd/hub',
    options=chrome_options
)

all_tracking_data = {}

# Initialize lists for successful and failed consignment numbers
successful_numbers = []
failed_numbers = []

# Set up the list of consignment numbers
consignment_numbers = ['EW354806654IN', 'EW354806668IN', 'EW354806671IN']  # Add your consignment numbers here

# Function to solve the captcha using OCR
def solve_captcha(captcha_url):
    # Download the captcha image and save it to a file
    captcha_image_path = "captcha.jpg"
    response = requests.get(captcha_url)
    with open(captcha_image_path, "wb") as file:
        file.write(response.content)

    # Solve the captcha with retry mechanism
    solver = imagecaptcha()
    solver.set_verbose(1)
    solver.set_key("0db318322bf75f1455409a012c44a8c9")

    max_retries = 3  # Set the maximum number of retries
    retry_count = 0

    while retry_count < max_retries:
        try:
            captcha_text = solver.solve_and_return_solution(captcha_image_path)
            print(captcha_text)
            return captcha_text
        except Exception as e:
            print(f"Error solving captcha: {str(e)}. Retrying...")
            retry_count += 1
            time.sleep(2)  # Wait for a few seconds before retrying

    print("Max retries exceeded. Captcha solving failed.")
    return None

# Function to check if the captcha image element is present
def is_captcha_image_present():
    try:
        captcha_image = driver.find_element(By.ID, 'ctl00_PlaceHolderMain_ucNewLegacyControl_ucCaptcha1_imgCaptcha')
        return captcha_image
    except:
        return False

# Find and refresh the captcha image
def refresh_captcha():
    while True:
        try:
            refresh_button = driver.find_element(By.ID, 'ctl00_PlaceHolderMain_ucNewLegacyControl_ucCaptcha1_imgbtnCaptcha')
            refresh_button.click()
            time.sleep(3)  # Wait for 10 seconds after refresh
            break
        except StaleElementReferenceException:
            continue


def get_tracking_data(consignment_number):
    # Open the tracking page
    driver.get('https://www.indiapost.gov.in/_layouts/15/DOP.Portal.Tracking/TrackConsignment.aspx')

    # Find the input field and fill it with the consignment number
    input_field = WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.ID, 'ctl00_PlaceHolderMain_ucNewLegacyControl_txtOrignlPgTranNo')))
    input_field.clear()
    input_field.send_keys(consignment_number)

    # Loop until the desired captcha image element is found
    while True:
        # Check if the captcha image element is present
        captcha_image = is_captcha_image_present()
        if captcha_image:
            # If the desired captcha image element is found, break the loop
            if captcha_image.get_attribute('id') == 'ctl00_PlaceHolderMain_ucNewLegacyControl_ucCaptcha1_imgCaptcha':
                break
        # Refresh the captcha
        refresh_captcha()

    # Solve the captcha using OCR
    captcha_image_url = captcha_image.get_attribute('src')
    captcha_solution = solve_captcha(captcha_image_url)

    # Fill the captcha field
    captcha_field = WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.ID, 'ctl00_PlaceHolderMain_ucNewLegacyControl_ucCaptcha1_txtCaptcha')))
    captcha_field.clear()
    captcha_field.send_keys(captcha_solution)

    # Submit the form
    submit_button = WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.ID, 'ctl00_PlaceHolderMain_ucNewLegacyControl_btnSearch')))
    submit_button.click()

    # Wait for 10 seconds to allow the data to load
    time.sleep(3)


    # Wait for the response, timeout after 30 seconds
    try:
        WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.ID, 'ctl00_PlaceHolderMain_ucNewLegacyControl_divTrckMailArticleOER')))
    except TimeoutException:
        print("Server error. Process timed out.")
        driver.quit()
        return None

    # Check if the captcha message element is present
    try:
        captcha_message = driver.find_element(By.ID, 'ctl00_PlaceHolderMain_ucNewLegacyControl_ucCaptcha1_lblCaptchamessage')
        captcha_message_style = captcha_message.get_attribute('style')

        # If the captcha message style is 'block', refresh the captcha
        if captcha_message_style == 'display: block;':
            print("Invalid captcha. Refreshing...")
            refresh_captcha()
            return None

    except NoSuchElementException:
        pass

        
    # Loop until the target element with ID 'ctl00_PlaceHolderMain_ucNewLegacyControl_divTrckMailArticleOER' is found
    while True:
        try:
            element1 = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, 'ctl00_PlaceHolderMain_ucNewLegacyControl_divTrckMailArticleOER'))).get_attribute('innerHTML')
            break
        except:
            # If the target element is not found, refresh the captcha and try again
            refresh_captcha()

            # Check if the captcha image element is present after refreshing
            captcha_image = is_captcha_image_present()
            if captcha_image:
                # If the desired captcha image element is found, break the loop
                if captcha_image.get_attribute('id') == 'ctl00_PlaceHolderMain_ucNewLegacyControl_ucCaptcha1_imgCaptcha':
                    break

    # Create BeautifulSoup object from the target div HTML
    soup = BeautifulSoup(element1, 'html.parser')

    # Extracting shipment details
    details_table = soup.find('table', {'class': 'responsivetable MailArticleOER'})
    details_rows = details_table.find_all('tr')
    details = {}
    for row in details_rows[1:]:
        cells = row.find_all('td')
        details['Booked At'] = cells[0].text.strip()
        details['Booked On'] = cells[1].text.strip()
        details['Destination Pincode'] = cells[2].text.strip()
        details['Tariff'] = cells[3].text.strip()
        details['Article Type'] = cells[4].text.strip()
        details['Delivery Location'] = cells[5].text.strip()

    # Extracting event details
    event_table = soup.find('table', {'class': 'responsivetable MailArticleEvntOER'})
    event_rows = event_table.find_all('tr')[1:]
    events = []
    for row in event_rows:
        cells = row.find_all('td')
        event = {
            'Date': cells[0].text.strip(),
            'Time': cells[1].text.strip(),
            'Office': cells[2].text.strip(),
            'Event': cells[3].text.strip()
        }
        events.append(event)

    # Creating JSON object
    data = {
        'Details': details,
        'Events': events
    }

    # Converting to JSON string
    json_string = json.dumps(data, indent=4)

    # Return the data
    return json_string

for consignment_number in consignment_numbers:
    tracking_data = get_tracking_data(consignment_number)
    if tracking_data is not None:
        # Store the tracking data for the consignment number
        all_tracking_data[consignment_number] = json.loads(tracking_data)
    time.sleep(2)

# Save all tracking data to a JSON file
current_datetime = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
file_name = f"track_data_{current_datetime}.json"
folder_name = "track_data"  # Folder name where you want to save the file

# Create the folder if it doesn't exist
if not os.path.exists(folder_name):
    os.makedirs(folder_name)

# Combine the folder name and file name to get the full file path
file_path = os.path.join(os.getcwd(), folder_name, file_name)

# Copy the track_data.json file from the container to the host machine using os.system
os.system(f"docker cp web-scrape-web-scrape-app-1:/app/{file_name} ./track_data/")


# Print the successful and failed consignment numbers
print("Successful Consignment Numbers:")
print(list(all_tracking_data.keys()))
print("Failed Consignment Numbers:")
print(failed_numbers)

