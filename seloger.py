# Copyright (c) 2022 Amine Daoud.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import time
import json
import csv
import os
from os import path
import random
import re
import yaml
import requests
from bs4 import BeautifulSoup
import browser_cookie3
from email_sender import send_email

print("starting seloger scraping")

# pylint: disable=invalid-name,line-too-long
base_url = "https://www.seloger.com"

# Load the config file
with open("config.yaml", "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

insee_codes = config['insee_codes']
insee_key = "inseeCodes"

projects = ",".join(str(x) for x in config['projects'])
types = ",".join(str(x) for x in config['types'])
min_price = config['min_price']
max_price = config['max_price']
min_surface = config['min_surface']
max_surface = config['max_surface']
sort = config['sort']
mandatorycommodities = config['mandatorycommodities']
furnished = config['furnished']
enterprise = config['enterprise']
qs_version = config['qsVersion']
m = config['m']
min_timeout_between_requests = config['min_timeout_between_requests']
max_timeout_between_requests = config['max_timeout_between_requests']
MAX_RETRIES = config['max_request_retries_when_connection_error']
prohibited_words = config['filter']
headers = config['headers']
csv_header = ['titre', 'prix', 'city', 'surface', 'code postal', 'rue/quartier', 'description', 'nombre de pieces', 'reference', 'electricite',
              'gas', 'number of Photos', 'hasVisite3D', 'type', 'latitude', 'longitude', 'lien', 'annee de construction', 'carcteristiques', 'transport']

places = f'[{{%22{insee_key}%22:[{",".join(str(x) for x in insee_codes)}]}}]'

add_furnished = f"&furnished={int(furnished)}" if projects == "1" else ""
natures = ",".join(str(x) for x in config['natures'])
add_nature = f"&natures={natures}" if projects == "2" else ""
href = f"/list.htm?projects={projects}&types={types}{add_nature}&places={places}&price={min_price}/{max_price}&surface={min_surface}/{max_surface}&sort={sort}&mandatorycommodities={mandatorycommodities}{add_furnished}&enterprise={enterprise}&qsVersion={qs_version}&m={m}"


print(places)
url = base_url + href
print(url)
first_url = url
cj = browser_cookie3.chrome()

with open('temp_apparts.csv', 'w', newline='', encoding="utf-8") as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(csv_header)

with open('temp_rejected_apparts.csv', 'w', newline='', encoding="utf-8") as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(['rejection reason'] + csv_header)


def get_page(request_url, request_headers):
    retries = MAX_RETRIES
    page = None
    global cj
    while retries:
        try:
            # TODO remove verify=False
            page = requests.get(
                request_url, cookies=cj, headers=request_headers, verify=False, timeout=10)
            break
        except (requests.ConnectionError, requests.exceptions.ReadTimeout) as e1:
            requests.session().close()
            cj = browser_cookie3.chrome()
            print("Connection problem...")
            print("sleep for few seconds")
            timeout = random.randint(
                min_timeout_between_requests, max_timeout_between_requests)
            time.sleep(timeout)
            print("continue...")
            if retries == 1:
                raise e1
            retries -= 1
            continue
    return page


def has_data(filename):
    with open(filename, 'r', encoding="utf-8") as csv_file:
        reader = csv.reader(csv_file)
        row_count = sum(1 for _ in reader)
        return row_count > 1


def not_matching_announce(columns):
    prohibited_words_lower_case = [prohibited_word.lower()
                                for prohibited_word in prohibited_words]
    return [column for column in columns if any(prohibited_word in str(
        column).lower() for prohibited_word in prohibited_words_lower_case)]


i = 0
files_to_send = []

def load_announce_data(request_headers, request_url, update_cookie=False):
    if update_cookie:
        global cj
        cj = browser_cookie3.chrome()
    one_response = get_page(request_url, request_headers)
    parser_soup = BeautifulSoup(one_response.content, "html.parser")
    parsedData = parser_soup.find("script", id="__NEXT_DATA__")
    return parser_soup, parsedData


page_index = 2
while True:
    response = get_page(url.strip(), headers)
    print(response)
    soup = BeautifulSoup(response.content, "html.parser")

    sections = soup.find_all("div", class_="BellowZone-sc-1moc6c6-0 hVWXfW")

    for section in sections:
        card2_element = section.find_previous_sibling(class_='Card__ContentZone-sc-7insep-2 diTKck')
        if card2_element and card2_element.find('div', string=re.compile(r'Contenu sponsorisé', re.IGNORECASE)):
            print("detected sponsored content, skip it")
            continue

        timeout_between_requests = random.randint(
            min_timeout_between_requests, max_timeout_between_requests)
        time.sleep(timeout_between_requests)
        a_tag = section.find('a')
        href = a_tag['href']
        if "seloger.com" in href:
            one_url = href
        else:
            one_url = base_url + href
        i += 1
        print(f"{i} {one_url}")

        one_soup, page_data = load_announce_data(headers, one_url)
        print(page_data)

        while page_data is None:
            print("error no page data for " + one_url)
            # Check if a Captcha was detected
            captcha_detected = False
            for script in one_soup.find_all('script'):
                src = script.get('src')
                if src and 'captcha' in src:
                    captcha_detected = True
                    break

            if captcha_detected:
                # If a Captcha was detected, solve it in the browser and enter any key to continue
                input(
                    "Captcha detected, solve it in the browser then press any button to continue ")
                print("continue...")
                one_soup, page_data = load_announce_data(
                    headers, one_url, True)
            else:
                # If no Captcha was detected, wait and try again
                print("Something went wrong!, has page data changed ?")
                time.sleep(min_timeout_between_requests)
                one_soup, page_data = load_announce_data(headers, one_url)

        json_data = json.loads(page_data.text)
        beautified_json = json.dumps(json_data, indent=4)

        if 'props' in json_data and 'pageProps' in json_data['props'] and 'title' in json_data['props']['pageProps']:
            print("correct page data.")
        else:
            print("wrong page data.")
            continue
        try:
            titre = json_data['props']['pageProps']['title']
            prix = json_data['props']['pageProps']['listingData']['listing']['listingDetail']['listingPrice']['price']
            city = json_data['props']['pageProps']['params']['city']
            surface = json_data['props']['pageProps']['listingData']['listing']['listingDetail']['surface']
            postal_code = json_data['props']['pageProps']['listingData']['listing']['listingDetail']['address']['postalCode']
            quartier = json_data['props']['pageProps']['listingData']['listing']['listingDetail']['address']['district']
            street = json_data['props']['pageProps']['listingData']['listing']['listingDetail']['address']['street']

            meta_description = json_data['props']['pageProps']['listingData']['listing']['listingDetail']['descriptive']
            room_count = json_data['props']['pageProps']['listingData']['listing']['listingDetail']['roomCount']
            reference = json_data['props']['pageProps']['listingData']['listing']['listingDetail']['id']
            electricity = json_data['props']['pageProps']['listingData']['listing'][
                'listingDetail']['energyPerformanceCertificate']['electricityRating']
            gaz = json_data['props']['pageProps']['listingData']['listing']['listingDetail']['energyPerformanceCertificate']['gasRating']
            number_of_photos = json_data['props']['pageProps']['listingData'][
                'listing']['listingDetail']['media']['totalPhotoCount']
            has_3d_visit = json_data['props']['pageProps']['listingData']['listing']['listingDetail']['media']['videoUrl'] is not None
            property_type = json_data['props']['pageProps']['listingData']['listing']['listingDetail']['propertyType']
            latitude = json_data['props']['pageProps']['listingData']['listing']['listingDetail']['coordinates']['latitude']
            longitude = json_data['props']['pageProps']['listingData']['listing']['listingDetail']['coordinates']['longitude']
            link = json_data['props']['pageProps']['canonicalUrl']
            construction_year = json_data['props']['pageProps']['listingData'][
                'listing']['listingDetail']['yearOfConstruction']
            feature_categories = json_data['props']['pageProps']['listingData']['listing']['listingDetail']['featureCategories']
            transport_dict = json_data['props']['pageProps']['listingData']['listing']['listingDetail']['transport']
            features_output = json_data['props']['pageProps']['listingData']['listing']['listingDetail']['featuresPopupTitle']
        except KeyError as e:
            raise Exception(
                "Unexpected data: JSON data is not in the expected format.") from e
        if street is None or quartier is None:
            address = street or quartier
        else:
            address = f"{street}/{quartier}"

        for category_name, category in feature_categories.items():
            # Skip categories that are null
            if category is None:
                continue

            print(f"Category: {category['title']}")
            features_output += f"\nCategory: {category['title']}"

            for feature in category["features"]:
                print(f" - Feature: {feature['title']}")
                features_output += f"\n - Feature: {feature['title']}"
        line_keys = ["metroLines", "rerLines", "transilienLines", "tramLines"]
        line_names = ""

        for key in line_keys:
            if transport_dict is not None and transport_dict[key] is not None:
                # remove the "Lines" suffix from the key name
                line_type = key[:-5]

                for line in transport_dict[key]:
                    name = line["name"]
                    line_names += f"{line_type} {name}\n"
                    print(f"{line_type} {name}")
        print(titre)
        print(prix)
        print(city)
        print(f"annonce numero {i}")
        row_data = [titre, prix, city, surface, postal_code, address, meta_description, room_count, reference, electricity, gaz,
                   number_of_photos, has_3d_visit, property_type, latitude, longitude, link, construction_year, features_output, line_names]
        filter_result = not_matching_announce(row_data)
        if bool(filter_result):
            with open('temp_rejected_apparts.csv', 'a', newline='', encoding="utf-8") as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow([filter_result] + row_data)
            print(f"discarded row {str(row_data)}")
        else:
            with open('temp_apparts.csv', 'a', newline='', encoding="utf-8") as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(row_data)

    timeout_between_requests = random.randint(
        min_timeout_between_requests, max_timeout_between_requests)
    time.sleep(timeout_between_requests)

    # check if there is a next page
    next_page = soup.find("a", {'data-testid': 'gsl.uilib.Paging.nextButton'})
    if next_page:
        # update the URL to the next page if there is one
        url = first_url + "&LISTING-LISTpg=" + str(page_index)
        page_index += 1
        print(url)
    else:
        # stop scraping if there are no more pages
        break

if path.exists('apparts.csv'):
    old_csv_data = []
    new_csv_data = []
    with open('apparts.csv', 'r', newline='', encoding="utf-8") as previous_file:
        old_csv = csv.DictReader(previous_file)
        old_csv_data = list(old_csv)
    with open('temp_apparts.csv', 'r', newline='', encoding="utf-8") as new_file:
        new_csv = csv.DictReader(new_file)
        new_csv_data = list(new_csv)
    with open('updated_apparts.csv', 'w', newline='', encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(csv_header)

    with open('added_apparts.csv', 'w', newline='', encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(csv_header)

    previous_data = {}
    new_data = {}

    for row in old_csv_data:
        previous_data[row['reference']] = row

    for row in new_csv_data:
        new_data[row['reference']] = row

    # find new rows
    for key, value in new_data.items():
        if key not in previous_data:
            print('Found new row:')
            print(value)
            with open('added_apparts.csv', 'a', newline='', encoding="utf-8") as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(value.values())

    # find modified rows
    for key, value in new_data.items():
        if key in previous_data:
            old_row = previous_data[key]
            new_row = value
            modified = False
            for column in old_row:
                if old_row[column] is None or old_row[column].isspace():
                    old_row[column] = ""
                if new_row[column] is None or new_row[column].isspace():
                    new_row[column] = ""
                if old_row[column].strip() != new_row[column].strip():
                    modified = True
                    print(f'Found modified row with ID {key}:')
                    print(f'Old value for {column}: {old_row[column]}')
                    print(f'New value for {column}: {new_row[column]}')
            if modified:
                with open('updated_apparts.csv', 'a', newline='', encoding="utf-8") as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow(new_row.values())
    if path.exists('old_apparts.csv'):
        os.remove('old_apparts.csv')
    os.rename('apparts.csv', 'old_apparts.csv')
    files_to_send.append('added_apparts.csv')
    files_to_send.append('updated_apparts.csv')

os.rename('temp_apparts.csv', 'apparts.csv')
files_to_send.append('apparts.csv')

if path.exists('rejected_apparts.csv'):
    os.remove('rejected_apparts.csv')

if has_data('temp_rejected_apparts.csv'):
    os.rename('temp_rejected_apparts.csv', 'rejected_apparts.csv')
    files_to_send.append('rejected_apparts.csv')
else:
    os.remove('temp_rejected_apparts.csv')

with open("credentials.yaml", "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)
email = config['email']
app_key = config['password']

recipients = config["recipients"]
send_email("Seloger Scraper Alert",
           "Scraping se loger website with you search criteria has finished.\nPlease find attached the generated files", email, app_key, recipients, files_to_send)
print("seloger scraping ended")