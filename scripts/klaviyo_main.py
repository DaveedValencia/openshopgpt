from klaviyo_api import KlaviyoAPI
import os
import json, time
from klaviyo_mods import clean_campaigns, get_campaign_ids, get_k, load_email_campaigns, match_results

clients = [] # account prefix that will identify each client database tables ("d1","d2","d3",etc.)

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

for client in clients:
    shop_creds_path = os.path.join(base_dir, 'creds', f"{client}_klaviyo.json")

    with open(shop_creds_path, 'r') as f:
        creds = json.load(f)

    DB_PATH = 'shop.db'

    klaviyo = KlaviyoAPI(creds['api_key'],max_delay=60,max_retries=3,test_host=None)

    # Date is passed through filters
    filters = "and(equals(messages.channel,'email'),equals(status,'Sent'),greater-or-equal(scheduled_at,2024-01-01T00:00:00Z))"
    fields_campaign_message = ['content.subject','content.preview_text']

    # Make first api call to campaigns
    campaigns = klaviyo.Campaigns.get_campaigns(filter=filters,fields_campaign_message=fields_campaign_message,include=["campaign-messages"])

    camps = clean_campaigns(campaigns) # Loads campaign data into a tuple
    camp_ids = get_campaign_ids(camps) # Creates a list of campaign ids to get the stats
    kpis = get_k(camp_ids,creds) # Gets the stats for this set of campaigns
    matched_results = match_results(camps,kpis)
    print("Campaign IDs: ",len(camp_ids))
    print("Matched IDs: ",len(matched_results))

    load_email_campaigns(matched_results,DB_PATH,client) # Loads campaigns into database and ignores if it already exists

    # next page of results
    link = campaigns['links']['next']
    flag = False
    count = 1

    if link != None:
        flag = True
        print(count)
        time.sleep(30)

    while flag:
        campaigns = klaviyo.Campaigns.get_campaigns(filter=filters,fields_campaign_message=fields_campaign_message,include=["campaign-messages"],page_cursor=link)
        camps = clean_campaigns(campaigns)
        camp_ids = get_campaign_ids(camps)
        kpis = get_k(camp_ids,creds)
        matched_results = match_results(camps,kpis)
        print("Campaign IDs: ",len(camp_ids))
        print("Matched IDs: ",len(matched_results))
        load_email_campaigns(matched_results,DB_PATH,client)
        link = campaigns['links']['next']
        count += 1
        print(count)
        print()
        
        if link == None:
            flag = False
        if len(matched_results) == 0:
            flag = False
        time.sleep(30)

    print(f"{client} email campaigns done loading.\n")
    time.sleep(30)