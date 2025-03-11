import sqlite3

# Connect to the SQLite3 database
conn = sqlite3.connect('shop.db')
cursor = conn.cursor()

clients = [] # account prefix that will identify each client database tables ("d1","d2","d3",etc.)

def create_orders_table(client):
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {client}_orders (
            order_id TEXT PRIMARY KEY,
            order_date TEXT,
            order_name TEXT,
            order_total REAL,
            order_cost REAL,
            order_tags TEXT,
            order_discounts REAL,
            order_shipping REAL,
            sales_channel_source TEXT,
            customer_id TEXT,
            customer_name TEXT
        );""")
    conn.commit()



def create_customers_table(client):
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {client}_customers (
            customer_id TEXT PRIMARY KEY,
            customer_name TEXT,
            customer_email TEXT,
            customer_city TEXT,
            customer_state_code TEXT,
            customer_country_code TEXT,
            customer_state_name TEXT,
            customer_country_name TEXT,
            customer_tags TEXT
        );""")
    conn.commit()


def create_line_items_table(client):
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {client}_line_items (
            line_item_id TEXT PRIMARY KEY,
            order_id TEXT,
            order_name TEXT,
            customer_id TEXT,
            product_sku TEXT,
            product_title TEXT,
            product_vendor TEXT,
            ordered_quantity INTEGER,
            product_price REAL,
            product_cost REAL,
            product_discount REAL,
            product_id TEXT,
            product_tags TEXT
        );""")
    conn.commit()


def create_klaviyo_campaigns(client):
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {client}_klaviyo_campaigns (
            campaign_id TEXT PRIMARY KEY,
            campaign_name TEXT,
            subject_line TEXT,
            preview_text TEXT,
            sent_time TEXT,
            delivered_emails INTEGER,
            opens INTEGER,
            clicks INTEGER,
            conversions INTEGER,
            unsubscribes INTEGER,
            bounced INTEGER,
            spam_complaints INTEGER
        );""")
    conn.commit()

def create_google_analytics(client):
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {client}_google_analytics (
            channel_id TEXT PRIMARY KEY,
            channel_name TEXT,
            channel_source TEXT,
            channel_sessions INTEGER,
            channel_carts INTEGER,
            channel_checkouts INTEGER,
            channel_transactions REAL,
            channel_revenue REAL,
            channel_date TEXT
        );""")
    conn.commit()

for client in clients:
    create_orders_table(client)
    create_customers_table(client)
    create_line_items_table(client)
    create_klaviyo_campaigns(client)
    create_google_analytics(client)

conn.close()

