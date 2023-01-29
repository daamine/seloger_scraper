# Seloger Scraping

A script for scraping rental and sale apartments from <https://www.seloger.com>. 
You can run it periodically to track new or updated listings.

## Features

Extracts details  and save it to CSV files.  
Filters out unwanted data based on excluded words.  
Send email notications with added and updated apartments.

## Requirements

Python 3  
yaml  
requests  
BeautifulSoup  
browser_cookie3  

Use below command to install requirements:  
`pip install -r requirements.txt`

## Usage

Configure config.yaml with desired parameters  
Run the script python seloger_scraping.py  
Scraped data will be saved in apparts.csv. Rejected data will be saved in rejected_apparts.csv.  
added_apparts.csv contains newly added listings since last execution  
updated_apparts.csv contains updated listings.  

## Config.yaml options  
insee_codes: list of INSEE codes for desired cities  
projects: type of project (rental or sale)  
types: list of property types (e.g. apartments, houses)  
min_price: minimum price for properties  
max_price: maximum price for properties  
min_surface: minimum surface area for properties  
max_surface: maximum surface area for properties  
furnished: boolean value indicating furnished properties  
min_timeout_between_requests: minimum wait time between requests  
max_timeout_between_requests: maximum wait time between requests  
max_request_retries_when_connection_error: maximum number of retries for connection errors  
filter: list of words to filter out data  
headers: headers for the request  

## Email Notifications

Update credential.yaml in order to get email notifications using smtplib.
