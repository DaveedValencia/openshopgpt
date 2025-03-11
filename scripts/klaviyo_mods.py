from klaviyo_api import KlaviyoAPI
from datetime import datetime
import pytz
import sqlite3

def clean_time(created_date):
    dt = datetime.fromisoformat(created_date)
    formatted_date = dt.strftime('%Y-%m-%dT%H:%M:%SZ')
    utc = pytz.utc
    central = pytz.timezone("US/Central")
    order_created_date = datetime.strptime(formatted_date, "%Y-%m-%dT%H:%M:%SZ")
    utc_time = utc.localize(order_created_date)
    central_time = utc_time.astimezone(central)

    return central_time


def clean_campaigns(campaigns):
    cleaned = []
    for i in range(len(campaigns['data'])):
        camp_name = campaigns['data'][i]['attributes']['name']
        camp_id = campaigns['data'][i]['id']
        camp_msg_id = campaigns['data'][i]['relationships']['campaign-messages']['data'][0]['id']
        camp_subject_line = campaigns['included'][i]['attributes']['content']['subject']
        camp_preview_text = campaigns['included'][i]['attributes']['content']['preview_text']
        created_at = clean_time(campaigns['data'][i]['attributes']['created_at']).strftime("%Y-%m-%d %H:%M:%S %Z")
        send_time = clean_time(campaigns['data'][i]['attributes']['send_time']).strftime("%Y-%m-%d")

        cleaned.append((
            camp_id,
            camp_name,
            camp_subject_line,
            camp_preview_text,
            send_time
        ))

    return cleaned


def get_kpis(results):
    kpi_results = []
    for result in results:
        camp_id = result.groupings['campaign_id']
        s = result.statistics
        kpi_results.append((
            camp_id,
            s['delivered'],
            s['opens_unique'],
            s['clicks_unique'],
            s['conversions'],
            s['unsubscribes'],
            s['bounced'],
            s['spam_complaints']
        ))
    return kpi_results


def get_campaign_ids(campaigns):
    return [camp[0] for camp in campaigns]


def get_k(camps, creds):
    klaviyo_kpis = KlaviyoAPI(creds['api_key'], max_delay=60, max_retries=3)
    c_ids = ','.join(f'"{c_id}"' for c_id in camps)
    filters = f'contains-any(campaign_id,[{c_ids}])'
    statistics = ["unsubscribes", "clicks_unique", "conversions", "delivered", "recipients", "bounced", "opens_unique", "spam_complaints"]

    body = {
        "data": {
            "type": "campaign-values-report",
            "attributes": {
                "timeframe": {"key": "last_365_days"},
                "statistics": statistics,
                "filter": filters,
                "conversion_metric_id": creds['conversion_metric']
            }
        }
    }

    stats = klaviyo_kpis.Reporting.query_campaign_values(body)
    return get_kpis(stats.data.attributes.results)


def load_email_campaigns(rows, db_path, client):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    INSERT_QUERY = f"""
    INSERT INTO {client}_klaviyo_campaigns (
        campaign_id,
        campaign_name,
        subject_line,
        preview_text,
        sent_time,
        delivered_emails,
        opens,
        clicks,
        conversions,
        unsubscribes,
        bounced,
        spam_complaints
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(campaign_id) DO UPDATE SET
        opens = excluded.opens,
        clicks = excluded.clicks,
        conversions = excluded.conversions,
        unsubscribes = excluded.unsubscribes,
        bounced = excluded.bounced,
        spam_complaints = excluded.spam_complaints
    """

    try:
        cur.executemany(INSERT_QUERY, rows)
        conn.commit()
        print("Klaviyo Campaigns Loaded")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        cur.close()
        conn.close()


def match_results(camp_list, kpi_list):
    matched_result = [
        (*a, *b[1:])
        for a in camp_list
        for b in kpi_list
        if a[0] == b[0]
    ]
    return matched_result
