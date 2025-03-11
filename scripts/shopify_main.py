import shopify
import json
import os
from shopify_loaders import (
    next_page,
    clean_orders,
    clean_customers,
    clean_line_items,
    load_orders,
    load_customers,
    load_line_items,
    querygql
)
from pprint import pprint


clients = [] # account prefix that will identify each client database tables ("d1","d2","d3",etc.)

query_start = "2024-01-01"  # start with this date
query_end = "2025-01-01"    # up to but not including this date


base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DB_PATH = 'shop.db'

for client in clients:
    shop_creds_path = os.path.join(base_dir, 'creds', f'{client}_shop.json')
    
    with open(shop_creds_path) as f:
        shop_creds = json.load(f)

    # CONFIG
    shop_url = shop_creds['shop_url']
    api_version = "2024-07"
    api_token = shop_creds['api_token']

    # INITIATE SESSION
    session = shopify.Session(shop_url, api_version, api_token)
    shopify.ShopifyResource.activate_session(session)

    # FIRST CALL
    query = querygql.replace("XXREMOVEXX","")
    query = query.replace("DATE_ORDER_START",query_start)
    query = query.replace("DATE_ORDER_END",query_end)
    result = shopify.GraphQL().execute(query)
    result = json.loads(result)

    orders_result = result['data']['orders']['edges']
    page_info = result['data']['orders']['pageInfo']
    query_cost = result['extensions']['cost']
    end_cursor = next_page(page_info)

    # CLEAN ORDERS
    orders = clean_orders(orders_result)
    customers = clean_customers(orders_result)
    line_items = clean_line_items(orders_result)

    # INSERT FIRST RESULTS

    if len(orders) > 0:
        load_orders(orders,client)
        load_customers(customers,client)
        load_line_items(line_items,client)
    else:
        print("No orders to process")

    # SET COUNTER
    page = 1
    print(page)
    pprint(query_cost)

    # NEXT PAGE CALLS
    flag = True
    if end_cursor == False:
        flag = False

    # LOOP TRHOUGH ALL PAGES
    while flag:
        query = querygql.replace("XXREMOVEXX",end_cursor)
        query = query.replace("DATE_ORDER_START",query_start)
        query = query.replace("DATE_ORDER_END",query_end)
        result = shopify.GraphQL().execute(query)
        result = json.loads(result)

        orders_result = result['data']['orders']['edges']
        page_info = result['data']['orders']['pageInfo']
        query_cost = result['extensions']['cost']

        end_cursor = next_page(page_info)
        orders = clean_orders(orders_result)
        customers = clean_customers(orders_result)
        line_items = clean_line_items(orders_result)

        page += 1
        print(page)
        pprint(query_cost)
        print()

        if end_cursor == False:
            flag = False

        load_orders(orders,client)
        load_customers(customers,client)
        load_line_items(line_items,client)
    print(f"{client} orders done loading.\n")