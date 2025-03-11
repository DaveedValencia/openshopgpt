from klaviyo_api import KlaviyoAPI
import os
import json

client = "d1" # Currently only handles one account per run.

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
shop_creds_path = os.path.join(base_dir, 'creds', f"{client}_klaviyo.json")

with open(shop_creds_path, 'r') as f:
    creds = json.load(f)

klaviyo = KlaviyoAPI(creds['api_key'], max_delay=60, max_retries=3, test_host=None)

filters = "equals(integration.name,'Shopify')"
fields_metric = ["name"]
m = klaviyo.Metrics.get_metrics(filter=filters)

for x in m.data:
    print(x.attributes.name)
    print(x.id)
    print()