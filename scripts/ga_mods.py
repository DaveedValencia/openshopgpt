from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange,
    Dimension,
    Metric,
    RunReportRequest
)

from datetime import datetime
import sqlite3

def clean_date(date_input):
    formatted_date = datetime.strptime(date_input, "%Y%m%d").date()
    return str(formatted_date)

def run_report(property_id, start_date, end_date):
    """Runs a report of active users grouped by country."""
    client = BetaAnalyticsDataClient()

    request = RunReportRequest(
        property=f"properties/{property_id}",
        dimensions=[
            Dimension(name="sessionDefaultChannelGroup"),
            Dimension(name="date"),
            Dimension(name="sessionSource"),
        ],
        metrics=[
            Metric(name="sessions"),
            Metric(name="addToCarts"),
            Metric(name="checkouts"),
            Metric(name="transactions"),
            Metric(name="totalRevenue")
        ],
        date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
    )
    response = client.run_report(request)

    rows = []
    for x in response.rows:
        dimension_values = [dim.value for dim in x.dimension_values]
        # Extract metric values
        metric_values = [met.value for met in x.metric_values]
        # Combine into a tuple
        result_tuple = tuple(dimension_values + metric_values)
        rows.append(result_tuple)
    
    return rows

def clean_source(row):
    channel_source = ''

    # Email
    if "email" in row[0].lower():
        if "klaviyo" in row[2].lower():
            channel_source = "klaviyo"
        elif "shopify" in row[2].lower():
            channel_source = "shopify"
        else:
            channel_source = 'other'
    
    # Referral
    elif "referral" in row[0].lower():
        channel_source = 'other'
    
    # Unassigned
    elif "unassigned" in row[0].lower():
        channel_source = 'unknown'

    # Cross-network
    elif "cross-network" in row[0].lower():
        if "google" in row[2].lower():
            channel_source = 'google'
        else:
            channel_source = 'other'
    
    # Direct
    elif "direct" in row[0].lower():
        channel_source = 'direct'

    # Affiliates
    elif "affiliates" in row[0].lower():
        channel_source = 'affiliates'

    # Display
    elif "display" in row[0].lower():
        if "google" in row[2].lower():
            channel_source = 'google'
        else:
            channel_source = 'other'

    # Organic Social
    elif "organic social" in row[0].lower():
        if "facebook" in row[2].lower():
            channel_source = 'facebook'
        elif "instagram" in row[2].lower():
            channel_source = 'instagram'
        elif "pinterest" in row[2].lower():
            channel_source = 'pinterest'
        elif "reddit" in row[2].lower():
            channel_source = 'reddit'
        else:
            channel_source = 'other'
    
    # Organic Search
    elif "organic search" in row[0].lower():
        if "google" in row[2].lower():
            channel_source = 'google'
        elif "bing" in row[2].lower():
            channel_source = 'bing'
        elif "yahoo" in row[2].lower():
            channel_source = 'yahoo'
        elif "duckduck" in row[2].lower():
            channel_source = 'duckduckgo'
        else:
            channel_source = 'other'
    
    # Organic Shopping
    elif "organic shopping" in row[0].lower():
        if "igshopping" in row[2].lower():
            channel_source = 'igshopping'
        elif "google" in row[2].lower():
            channel_source = 'google'
        else:
            channel_source = 'other'
    
    # Paid Social
    elif "paid social" in row[0].lower():
        if "facebook" in row[2].lower():
            channel_source = 'facebook'
        elif "fb" in row[2].lower():
            channel_source = 'facebook'
        elif "pinterest" in row[2].lower():
            channel_source = 'pinterest'
        else:
            channel_source = 'other'

    # Paid Search
    elif "paid search" in row[0].lower():
        if "bing" in row[2].lower():
            channel_source = 'bing'
        elif "google" in row[2].lower():
            channel_source = 'google'
        else:
            channel_source = 'other'
    
    # Paid Shopping
    elif "paid shopping" in row[0].lower():
        if "bing" in row[2].lower():
            channel_source = 'bing'
        elif "google" in row[2].lower():
            channel_source = 'google'
        else:
            channel_source = 'other'

    # Paid Video
    elif "paid video" in row[0].lower():
        if "bing" in row[2].lower():
            channel_source = 'bing'
        elif "google" in row[2].lower():
            channel_source = 'google'
        else:
            channel_source = 'other'

    # Paid Other
    elif "paid other" in row[0].lower():
        channel_source = 'paid other'

    # Organic Video
    elif "organic video" in row[0].lower():
        if "youtube" in row[2].lower():
            channel_source = 'youtube'
        else:
            channel_source = 'other'

    return channel_source

def clean_channels(channels):
    clean_channels_list = []

    for row in channels:
        channel_name = row[0]  # TEXT
        channel_date = clean_date(row[1])  # DATE
        channel_source = clean_source(row)  # TEXT
        channel_sessions = int(row[3])  # NUMERIC
        channel_carts = int(row[4])  # NUMERIC
        channel_checkouts = int(row[5])  # NUMERIC
        channel_transactions = float(row[6])  # REAL
        channel_revenue = float(row[-1])  # REAL
        pk_source = row[2]
        primary_key = f"{channel_date}_{channel_name}_{pk_source}"
        clean_channels_list.append((
            primary_key, channel_date, channel_name, channel_source, channel_sessions,
            channel_carts, channel_checkouts, channel_transactions, channel_revenue
        ))
    sorted_data = sorted(clean_channels_list, key=lambda x: x[0])
    return sorted_data

def load_channels(clean_data, DB_PATH, client):
    INSERT_QUERY = f"""
    INSERT INTO {client}_google_analytics (
        channel_id,
        channel_date,
        channel_name,
        channel_source,
        channel_sessions,
        channel_carts,
        channel_checkouts,
        channel_transactions,
        channel_revenue
    )
    VALUES (?,?,?,?,?,?,?,?,?)
    ON CONFLICT(channel_id) DO UPDATE SET
        channel_sessions = excluded.channel_sessions,
        channel_carts = excluded.channel_carts,
        channel_checkouts = excluded.channel_checkouts,
        channel_transactions = excluded.channel_transactions,
        channel_revenue = excluded.channel_revenue;
    """
    try:
        # Connect to the SQLite database
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()

        # Insert data in bulk using executemany
        cur.executemany(INSERT_QUERY, clean_data)

        # Commit changes
        conn.commit()
        print("Google Channels Loaded")

    except Exception as e:
        print(f"An error occurred: {e}")

    finally:
        # Close the cursor and connection
        if cur:
            cur.close()
        if conn:
            conn.close()
