import sqlite3
from datetime import datetime


# Utility functions
def clean_time(created_date):
    dt = datetime.fromisoformat(created_date.replace('Z', '+00:00'))
    sqlite_string = dt.strftime('%Y-%m-%d')
    return sqlite_string

def next_page(page_info):
    """Check if there is a next set of results. Returns True or False"""
    if page_info['hasNextPage'] == True:
        page = 'after: "{}"'
        return page.format(page_info['endCursor'])
    else:
        return False

def return_line_item_total(line_items):
    """Returns a dictionary containing total quanties and total cost."""
    total_cost = 0
    for node in line_items:
        item = node['node']
        quantity = item['quantity']
        try:
            cost = float(item['variant']['inventoryItem']['unitCost']['amount'])
        except:
            cost = 0.0
        total = quantity * cost
        total_cost += total
    return total_cost

def check_sku(node):
    sku = node['sku']
    if sku == None:
        try:
            sku = node['customAttributes'][0]['value']
        except IndexError:
            sku = None
    return sku

def clean_tags(tags):
    try:
        clean = list(set(tags))
        clean = ' '.join(clean)
        
    except:
        clean = None
    finally:
        return clean

# Data cleaning functions
def clean_orders(orders):
    clean_nodes = []
    for order in orders:
        n = order['node']
        order_created_date = clean_time(n['processedAt'])
        order_id = n['id'].split("/")[-1]
        order_name = n['name']
        sales_channel_source = n['sourceName']
        order_tags = clean_tags(n['tags'])
        order_total = round(float(n['totalPriceSet']['shopMoney']['amount']), 2)
        order_cost = round(return_line_item_total(n['lineItems']['edges']), 2)
        order_discounts = round(float(n['totalDiscountsSet']['shopMoney']['amount']), 2)
        order_shipping = round(float(n['totalShippingPriceSet']['shopMoney']['amount']), 2)

        customer = n['customer']

        try:
            customer_name = customer['displayName']
            customer_id = customer['id'].split("/")[-1]

        except:
            customer_name = "N/A"
            customer_id = 1  

        cleaned_row = (
            order_id, order_created_date, order_name, order_total, order_cost,
            order_tags, order_discounts, order_shipping,
            sales_channel_source, customer_id, customer_name
        )
        clean_nodes.append(cleaned_row)
    return clean_nodes

def clean_customers(orders):
    """Clean daily customers info and returns a list of tuples."""

    clean_nodes = []

    for order in orders:
        n = order['node']
        customer = n['customer']

        try:
            customer_name = customer['displayName']
            customer_id = customer['id'].split("/")[-1]
            customer_email = customer['email']
            customer_tags = clean_tags(customer['tags'])
        except:
            customer_name = "N/A"
            customer_id = 1
            customer_email = None
            customer_tags = None
        
        try:
            address = customer['defaultAddress']
            customer_city = address['city']
            country_name = address['country']
            country_code = address['countryCodeV2']
            state_province_name = address['province']
            state_province_code = address['provinceCode']
        except:
            customer_city = None
            country_name = None
            country_code = None
            state_province_name = None
            state_province_code = None

        cleaned_row = (
            customer_id, customer_name, customer_email, customer_city,
            state_province_code, country_code, state_province_name,
            country_name, customer_tags
        )
        clean_nodes.append(cleaned_row)
    return clean_nodes

def clean_line_items(orders):
    """Clean line items and returns a list of tuples."""
    clean_nodes = []

    for order in orders:
        n = order['node']
        order_id = n['id'].split("/")[-1]
        order_name = n['name']
        customer = n['customer']

        try:
            customer_id = customer['id'].split("/")[-1]
        except:
            customer_id = None

        line_items = n['lineItems']['edges']

        for line_item in line_items:
            line = line_item['node']
            line_id = line['id'].split("/")[-1]

            try:
                product = line['product']
                product_id = product['id'].split("/")[-1]
                product_tags = clean_tags(product['tags'])
                product_vendor = product['vendor']
            except:
                product_id = None
                product_tags = None
                product_vendor = None

            line_quantity = int(line['quantity'])
            line_sku = check_sku(line)
            line_title = line['title']

            try:
                line_cost = float(line['variant']['inventoryItem']['unitCost']['amount'])
            except:
                line_cost = None
            
            try:
                line_msrp = float(line['originalUnitPriceSet']['shopMoney']['amount'])
            except:
                line_msrp = None

            line_discount = float(line['totalDiscountSet']['shopMoney']['amount'])
            line_unit_price = round((line_msrp * line_quantity - line_discount)/line_quantity,2)
            line_unit_discount = round(line_discount/line_quantity,2)

            cleaned_row = (
                line_id, order_id, order_name, customer_id, line_sku, line_title,
                product_vendor, line_quantity, line_unit_price, line_cost,
                line_unit_discount, product_id, product_tags
            )
            clean_nodes.append(cleaned_row)
    return clean_nodes


# Load data functions
def insert_data(query, data):
    conn = sqlite3.connect('shop.db') # Database name
    cursor = conn.cursor()
    try:
        cursor.executemany(query, data)
        conn.commit()
        print("Data Loaded Successfully")
    except sqlite3.Error as e:
        print(f"SQLite Error: {e}")
    finally:
        cursor.close()
        conn.close()

# Load orders
def load_orders(clean_data, client):
    insert_query = f"""
    INSERT INTO {client}_orders (
        order_id, order_date, order_name, order_total, order_cost,
        order_tags, order_discounts, order_shipping, sales_channel_source,
        customer_id, customer_name)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""
    insert_data(insert_query, clean_data)

# Load customers
def load_customers(clean_data, client):
    insert_query = f"""
    INSERT OR IGNORE INTO {client}_customers (
        customer_id, customer_name, customer_email, customer_city,
        customer_state_code, customer_country_code, customer_state_name,
        customer_country_name, customer_tags)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"""
    insert_data(insert_query, clean_data)

# Load line items
def load_line_items(clean_data, client):
    insert_query = f"""
    INSERT INTO {client}_line_items (
        line_item_id, order_id, order_name, customer_id, product_sku,
        product_title, product_vendor, ordered_quantity, product_price,
        product_cost, product_discount, product_id, product_tags)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""
    insert_data(insert_query, clean_data)

querygql = """
{
  orders(
   first: 250
   query: "created_at:>='DATE_ORDER_STARTT00:00:00-06:00' AND created_at:<='DATE_ORDER_ENDT00:00:00-06:00'"
   XXREMOVEXX
   ) {
    edges {
      node {
        id
        createdAt
        updatedAt
        processedAt
        name
        sourceName
        tags
        totalDiscountsSet {
          shopMoney {
            amount
          }
        }
        totalShippingPriceSet {
          shopMoney {
            amount
          }
        }
        totalPriceSet {
          shopMoney {
            amount
          }
        }
        lineItems(first: 250) {
          edges {
            node {
              product {
                id
                tags
                vendor
              }
              id
              sku
              quantity
              title
              customAttributes {
                key
                value
              }
              originalUnitPriceSet {
                shopMoney {
                  amount
                }
              }
              totalDiscountSet {
                shopMoney {
                  amount
                }
              }
              variant {
                price
                inventoryItem {
                  unitCost {
                    amount
                  }
                }
              }
            }
          }
        }
        customer {
          id
          displayName
          tags
          email
          defaultAddress {
            city
            province
            provinceCode
            country
            countryCodeV2
          }
        }
      }
    }
    pageInfo {
      hasNextPage
      endCursor
    }
  }
}
""".strip()