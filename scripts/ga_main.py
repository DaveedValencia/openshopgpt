import os
from ga_mods import run_report, clean_channels, load_channels

clients = [] # account prefix that will identify each client database tables ("d1","d2","d3",etc.)

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

for client_id in clients:
    # key = account prefix
    # value = account ga4 property id.
    # prefilled with example data
    client_ids = {
        "d1": "0001",
        "d2":"0002",
        "d3":"0003",
    }

    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.path.join(base_dir, 'creds', 'ga_creds.json')

    DB_PATH = 'shop.db'

    property_id = client_ids[client_id]
    start_date = "2024-01-01"  # Start to load data date.
    end_date = "2025-12-31"    # Always set to a future date.

    run_sample = run_report(property_id, start_date, end_date)
    rows = clean_channels(run_sample)

    load_channels(rows, DB_PATH, client_id)

    print(f"{client_id} GA4 data done loading.\n")