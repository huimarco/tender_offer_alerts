import pandas as pd
import os
from datetime import timedelta, date
import requests
from edgar import *

def get_tenders(my_identity):
  try:
    # set user agent for SEC EDGAR API calls
    set_identity(my_identity)

    # retrieve filings (can specify a year; must include quarter if current year)
    filings = get_filings()

    # filter for tender offer related forms (including ammendments)
    tenders = filings.filter(form=['SC TO-I', 'SC TO-C', 'SC 13E-3', 'SC 13E-4'], amendments=True)

    # return results as pandas dataframe
    return tenders.to_pandas()

  except Exception as e:
    # return an empty dataframe on error
    print(f"An error occurred in get_tender_offers: {e}")
    return pd.DataFrame()

def get_yesterday_tenders(my_identity):
  # calculate yesterday's date
  yesterday = date.today() - timedelta(days=1)

  # filter for tender offer forms filed yesterday and return
  tenders_df = get_tenders(my_identity)

  # Break if the filing_date is missing
  if 'filing_date' not in tenders_df.columns:
      print("Error: 'filing_date' column not found in DataFrame")
      return
  
  new_to = tenders_df[tenders_df['filing_date']==yesterday]
  return new_to

def check_odd_lot(accession_number):
    # Download the first two attachments
    filing = get_by_accession_number(accession_number)
    attachment0 = filing.attachments[0].download()
    attachment1 = filing.attachments[1].download()

    # Define the regex pattern for 'odd-lot' or 'odd lot' (case-insensitive)
    pattern = re.compile(r'\bodd[-\s]lot\b', re.IGNORECASE)
    
    # Check for matches in the first two attachments
    if re.search(pattern, attachment0) or re.search(pattern, attachment1):
        return 1
    else:
        return 0

def send_teams_message(webhook_url, dataframe):
    # Convert the DataFrame to HTML table
    html_table = dataframe.to_html(index=False)

    # Prepare the Teams message payload
    message = {
        "title": "New Tender Offer Filings from Yesterday",
        "text": f"Here are the tender offers found:\n{html_table}"
    }

    # Send the message to Teams via the Webhook
    headers = {'Content-Type': 'application/json'}
    response = requests.post(webhook_url, json=message, headers=headers)

    # Check the response
    if response.status_code == 200:
        print("Message sent successfully to Microsoft Teams!")
    else:
        print(f"Failed to send message. Status code: {response.status_code}, Response: {response.text}")

print('Running script on', date.today())

# define variables
my_identity = os.getenv('API_IDENTITY')
teams_webhook_url = os.getenv('TEAMS_WEBHOOK_URL')

# retrieve tender offer filings from yesterday
yesterday_tenders = get_yesterday_tenders(my_identity)

# send dataframe to Teams
if not yesterday_tenders.empty:
    # Check if 'odd lot' is mentioned in filing attachments
    yesterday_tenders['odd_lot'] = yesterday_tenders['accession_number'].apply(check_odd_lot)
    print('New tender offer filings found. Attempting to send email...')
    send_teams_message(teams_webhook_url, yesterday_tenders)
else:
    print("No new tender offer filings found. No message sent.")
