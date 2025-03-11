from openai import OpenAI
import streamlit as st
import json, os, sqlite3
import pandas as pd
from datetime import datetime

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DB_PATH = os.path.join(base_dir, 'shop.db')

client = OpenAI(api_key=st.secrets["open_secret"],
                organization=st.secrets["open_organization"])

# You can choose a different model for functions here.
open_model = "gpt-4o-mini-2024-07-18"

def today_date():
    return datetime.now().strftime('%Y-%m-%d')

def make_call(sys_prompt, user_input):
    chat_completion = client.chat.completions.create(
        messages=[
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_input}
        ],
        model=open_model,
        response_format={"type": "json_object"},
        temperature=0.1
    )
    response = json.loads(chat_completion.choices[0].message.content)
    return response

def call_sql(gpt_response):
    gpt_query = gpt_response['query']
    print(gpt_query) #prints query for debugging
    print()

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(gpt_query)
        query_response = [x for x in cursor.fetchall()]
        conn.commit()  # commit if there are any changes
        return query_response

    except Exception as e:
        print(f"Error: {e}")
        return False

    finally:
        try:
            cursor.close()
            conn.close()
        except Exception:
            pass

    

def ecommerce_data(user_input,table_id):
    """Pass the user input and their table id and get back an executed query."""

    today = today_date()

    sys_prompt = f"""
        You will be assisting with generating Python SQLite queries for an e-commerce transaction database. The database has three tables: 
        - \"{table_id}_orders\"
        - \"{table_id}_customers\"
        - \"{table_id}_line_items\"

        When asked a specific question or request, respond **only** with the appropriate SQLite query that reads from these tables.

        Use the following rules:

        1. **Read-Only**: You have read access to these three tables and **no** access to any other tables. 
        2. **Refusals**: Refuse any query if it cannot be answered with these three tables.
        3. **Case-Insensitive Filtering**: Use `NOCASE` (i.e., `COLLATE NOCASE`) and `LIKE` where appropriate to ensure case-insensitive, partial-match searching.
        4. **Foreign Key Relationships**: Leverage any relationships (e.g., `order_id`, `customer_id`) using **explicit** JOINs when needed.
        5. **Result Limiting**: If the user input includes the words \"list\", \"show\", or \"who\", limit the query results to 10 rows (e.g., `LIMIT 10`).
        6. **Date Constraints**: 
        - Use today's date of {today} for any \"today\" references.
        - Use `date(column)` as needed for date comparisons in SQLite.
        - DO NOT USE CASE with dates.
        7. **Column Names**: Do not alter table or column names (no singular ↔ plural changes).
        8. **Aggregate vs. List**: Assume the user wants total/aggregate values unless they specifically ask for a list or say \"show\" or \"who\" (which also implies a `LIMIT 10`).
        9. **Output Format**: Your response **must** be in JSON with the structure:
            ```
            {{
                "query": "YOUR QUERY HERE",
                "column_names": "COLUMN NAMES"
            }}
            ```

        ---
        # Table Definitions

        1. {table_id}_orders:
        - order_id (TEXT PRIMARY KEY): Unique identifier for each order.
        - order_date (TEXT): Ordered date (YYYY-MM-DD).
        - order_name (TEXT): Order name reference.
        - order_total (REAL): Total order amount.
        - order_cost (REAL): Total cost for the order.
        - order_tags (TEXT): Optional tags on the order.
        - order_discounts (REAL): Total discount amount for the order.
        - order_shipping (REAL): Amount paid by the customer for shipping.
        - sales_channel_source (TEXT): Sales channel (e.g., website, pos).
        - customer_name (TEXT): Name of the ordering customer.
        - customer_id (TEXT): References the customer in {table_id}_customers.

        2. {table_id}_customers:
        - customer_id (TEXT PRIMARY KEY): Unique ID for the customer refrences {table_id}_orders.
        - customer_name (TEXT): Full name.
        - customer_email (TEXT): Email address.
        - customer_city (TEXT): City of residence.
        - customer_state_code (TEXT): State/province code.
        - customer_country_code (TEXT): Country code.
        - customer_state_name (TEXT): State/province full name.
        - customer_country_name (TEXT): Country full name.
        - customer_tags (TEXT): Optional tags on the customer.

        3. {table_id}_line_items:
        - line_item_id (TEXT PRIMARY KEY): Unique ID for the line item.
        - order_id (TEXT): References the order as {table_id}_orders.
        - order_name (TEXT): Name reference.
        - customer_id (TEXT): References the same customer in {table_id}_orders.
        - product_sku (TEXT): SKU of the product.
        - product_title (TEXT): Product name.
        - product_vendor (TEXT): Vendor or supplier.
        - ordered_quantity (INTEGER): How many of this product were ordered.
        - product_price (REAL): Price per product (before discount).
        - product_cost (REAL): Cost per product.
        - product_discount (REAL): Discount applied to this product.
        - product_id (TEXT): ID of the product.
        - product_tags (TEXT): Tags for this product (e.g., color, size).

        ---
        # Steps

        1. Parse the user query.
        2. Determine the necessary filters/conditions.
        3. Apply case-insensitive filters (using LIKE with `COLLATE NOCASE`).
        4. Use {today} as 'today' if relevant;
        5. Limit results to 10 if the user input includes "list", "show", or "who".
        6. Construct and output the final SQLite query.

        ---
        # Example

        **User Input**: "What was my store performance for November 2024?"

        **Expected JSON Output**:
        {{
        "query": "
            SELECT
                SUM(order_total) AS total_revenue,
                SUM(order_cost) AS total_cost,
                SUM(order_discounts) AS total_discounts,
                SUM(order_shipping) AS total_shipping,
                COUNT(order_id) AS total_orders,
                AVG(order_total) AS avg_order_value
            FROM {table_id}_orders
            WHERE date(order_date) >= '2024-11-01'
            AND date(order_date) < '2024-12-01';
        ",
        "column_names": "total_revenue, total_cost, total_discounts, total_shipping, total_orders, avg_order_value"
        }}

        **User Input**: "who were my top customers in 2024?"

        **Expected JSON Output**:
        {{
        "query": "
            SELECT 
                c.customer_id,
                c.customer_name,
                SUM(o.order_total) AS total_spent
            FROM {table_id}_orders AS o
            JOIN {table_id}_customers AS c
                ON o.customer_id = c.customer_id
            WHERE date(o.order_date) BETWEEN '2024-01-01' AND '2024-12-31'
            GROUP BY c.customer_id, c.customer_name
            ORDER BY total_spent DESC
            LIMIT 10;
        ",
        "column_names": "customer_id, customer_name, total_spent"
        }}

        **User Input**: "How many first time customers did I have in May 2024?"

        **Expected JSON Output**:
        {{
        "query": "
        SELECT 
            COUNT(DISTINCT o.customer_id) AS first_time_buyers
        FROM {table_id}_orders AS o
        WHERE date(o.order_date) BETWEEN '2024-05-01' AND '2024-05-31'
            AND date(o.order_date) = (
                SELECT MIN(date(o2.order_date))
                FROM {table_id}_orders AS o2
                WHERE o2.customer_id = o.customer_id
            );",
        "column_names": "first_time_buyers"
        }}

        **User Input**: "What were my top selling products in january 2024"

        **Expected JSON Output**:
        {{
        "query": "SELECT li.product_sku, li.product_title, SUM(li.ordered_quantity) AS total_sold FROM {table_id}_line_items AS li JOIN {table_id}_orders AS o ON li.order_id = o.order_id WHERE date(o.order_date) BETWEEN '2024-01-01' AND '2024-01-31' GROUP BY li.product_sku, li.product_title ORDER BY total_sold DESC;",
        "column_names": "product_sku, product_title, total_sold"
        }}


    """
    
    response = make_call(sys_prompt,user_input)
    query_result = call_sql(response)

    if query_result == False:
        return "Something went wrong. Please refresh your tab and start again."
    
    else:
        column_names = response['column_names']
        columns = column_names.split(',')
        df = pd.DataFrame(query_result, columns=columns)
        result = df.round(2).to_string(index=False)
        return result


def email_data(user_input,table_id):
    """Pass the user input and their table id and get back an executed query."""

    today = today_date()

    sys_prompt = f"""
        You will be assisting with generating Python SQLite queries for a database containing Klaviyo email data. This database has only one table: \"{table_id}_klaviyo_campaigns\". You have read-only access to this table—no other tables are available.

        Use the following rules when constructing queries:

        1. **Single Table**: Only query \"{table_id}_klaviyo_campaigns\". Refuse if it cannot be answered with this table alone.
        2. **Case-Insensitive Searches**: Apply `LIKE` with `COLLATE NOCASE` where partial text matching is needed.
        3. **Date Handling**: Today is {today}. Use `DATE('now', '-X day')` if referencing the last X days, or {today} if referencing \"today.\" 
        4. **Limit Results**: If the user input contains \"list,\" \"show,\" or \"who,\" add `LIMIT 10` to the query.
        5. **Naming**: Do not change or pluralize/singularize column names or the user’s text/title cases.
        6. **Aggregate by Default**: Assume the user wants total/aggregated metrics unless they explicitly ask to \"list\" or \"show\" row-level data.
        7. **Output JSON Only**: Return the final SQLite query in JSON format:
            ```
            {{
                "query": "YOUR QUERY HERE",
                "column_names": "COLUMN NAMES HERE"
            }}
            ```

        # Table Definition

        TABLE {table_id}_klaviyo_campaigns:
        - `campaign_id` (TEXT PRIMARY KEY): Unique campaign identifier.
        - `campaign_name` (TEXT): Name of the email campaign.
        - `subject_line` (TEXT): Subject line used in the campaign emails.
        - `preview_text` (TEXT): Preview text shown in inbox.
        - `sent_time` (TEXT): When the campaign was sent (YYYY-MM-DD HH:MM:SS).
        - `delivered_emails` (INTEGER): Total emails successfully delivered.
        - `opens` (INTEGER): Number of opened emails.
        - `clicks` (INTEGER): Number of link clicks in the emails.
        - `conversions` (INTEGER): Number of conversions (e.g., orders placed).
        - `unsubscribes` (INTEGER): Recipients who unsubscribed.
        - `bounced` (INTEGER): Emails that failed delivery.
        - `spam_complaints` (INTEGER): Number of spam complaints.

        # Example Queries

        **Input**: "What was my open rate over the last 30 days?"
        **Output**:
        {{
        "query": "SELECT (SUM(opens) * 100.0 / NULLIF(SUM(delivered_emails), 0)) AS open_rate 
            FROM {table_id}_klaviyo_campaigns 
            WHERE DATE(sent_time) BETWEEN DATE('now', '-30 day') AND DATE('now');",
        "column_names": "open_rate"
        }}

        **Input**: "What was my conversion rate over the last 30 days?"
        **Output**:
        {{
        "query": "SELECT (SUM(conversions)*100.0 / NULLIF(SUM(delivered_emails),0)) AS conversion_rate FROM {table_id}_klaviyo_campaigns WHERE DATE(sent_time) >= DATE('now','-30 day');",
        "column_names": "conversion_rate"
        }}

        **Input**: "What are my best performing subject lines?"
        **Output**:
        {{
        "query": "SELECT subject_line, SUM(conversions) AS total_conversions, (SUM(opens)*100.0 / NULLIF(SUM(delivered_emails),0)) AS open_rate, (SUM(conversions)*100.0 / NULLIF(SUM(opens),0)) AS conversion_rate FROM {table_id}_klaviyo_campaigns GROUP BY subject_line ORDER BY total_conversions DESC, conversion_rate DESC, open_rate DESC LIMIT 10;",
        "column_names": "subject_line, total_conversions, open_rate, conversion_rate"
        }}
        """
    
    response = make_call(sys_prompt,user_input)
    query_result = call_sql(response)

    if query_result == False:
        return "Something went wrong. Please refresh your tab and start again."
    
    else:
        column_names = response['column_names']
        columns = column_names.split(',')
        df = pd.DataFrame(query_result, columns=columns)
        result = df.round(2).to_string(index=False)
        return result
    
def explain_this(sequel_response):
    today = today_date()

    sys_prompt = f"""
    You are helpful digital marketing analyst. Today is {today}. You will be given a data set, you role will be to summerize the data into actionable insights.     
    Your response will be in JSON format using the provided template:
    {{
        "query": "Your Summary Here"
    }}
    
    """
    chat_completion = client.chat.completions.create(
        messages=[
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": sequel_response}
        ],
        model=open_model,
        response_format={ "type": "json_object" },
        temperature=0.1
    )
    response = json.loads(chat_completion.choices[0].message.content)

    return response

def google_analytics(user_input, table_id):
    today = today_date()

    sys_prompt = f"""
    You will create SQLite queries to extract insights from a Google Analytics dataset. Today is {today}, and the database is synced daily. Below is the structure of the relevant table you will query:

    Table {table_id}_google_analytics Structure:
    - channel_id (TEXT): Primary Key
    - channel_name (TEXT): The traffic channel, one of [Direct, Organic Search, Organic Social, Email, Organic Shopping, Referral, Paid Search, Paid Social, Organic Video, Unassigned]
    - channel_source (TEXT): The specific source of the traffic (e.g., facebook, klaviyo, google, bing)
    - channel_sessions (INTEGER): Number of sessions initiated through the channel
    - channel_carts (INTEGER): Number of items added to cart
    - channel_checkouts (INTEGER): Number of checkouts started
    - channel_transactions (INTEGER): Number of transactions (conversions)
    - channel_revenue (INTEGER): Revenue generated by the channel
    - channel_date (TEXT): Date of recorded web traffic activity (YYYY-MM-DD)

    By default, queries should include columns for sessions, carts, checkouts, transactions, and revenue. Always sort results by the calculated or summed `total_sessions` in descending order.

    # Steps

    1. **Clarify the Question**: Identify which data or calculations the user wants.
    2. **Select Relevant Columns**: Determine which columns you need to include.
    3. **Construct the Query**: Write a valid SQLite statement to retrieve or aggregate the needed data.
    4. **Test/Validate**: Ensure the query is syntactically correct and returns the expected data.
    5. **Refine if Needed**: Optimize your query if necessary.

    # Output Format

    Return a single JSON object with the following structure:
    {{ 
        "query": "YOUR QUERY HERE", 
        "column_names": "COLUMN NAMES" 
    }}
    
    **Examples**

    **Input**: "Website performance for November 2024"
    **Output**:
    {{
        "query": "SELECT 
                    channel_name, 
                    SUM(channel_sessions) AS total_sessions, 
                    SUM(channel_carts) AS total_carts, 
                    SUM(channel_checkouts) AS total_checkouts, 
                    SUM(channel_transactions) AS total_transactions, 
                    SUM(channel_revenue) AS total_revenue 
                FROM {table_id}_google_analytics 
                WHERE DATE(channel_date) BETWEEN '2024-11-01' AND '2024-11-30' 
                GROUP BY channel_name 
                ORDER BY total_sessions DESC;",
        "column_names": "channel_name,total_sessions,total_carts,total_checkouts,total_transactions,total_revenue"
    }}

    **Input**: "Organic Social Sources breakdown for December 2024"
    **Output**:
    {{
        "query": "SELECT 
                    channel_source, 
                    SUM(channel_sessions) AS total_sessions, 
                    SUM(channel_carts) AS total_carts, 
                    SUM(channel_checkouts) AS total_checkouts, 
                    SUM(channel_transactions) AS total_transactions, 
                    SUM(channel_revenue) AS total_revenue 
                FROM {table_id}_google_analytics 
                WHERE LOWER(channel_name) LIKE '%organic social%'
                    AND DATE(channel_date) BETWEEN '2024-12-01' AND '2024-12-31' 
                GROUP BY channel_source 
                ORDER BY total_sessions DESC;
                ",
        "column_names": "channel_source,total_sessions,total_carts,total_checkouts,total_transactions,total_revenue"
    }}

    **Input**: "Facebook performance for September 2024"
    **Output**:
    {{
        "query": "SELECT 
                    channel_name, 
                    channel_source, 
                    SUM(channel_sessions) AS total_sessions, 
                    SUM(channel_carts) AS total_carts, 
                    SUM(channel_checkouts) AS total_checkouts, 
                    SUM(channel_transactions) AS total_transactions, 
                    SUM(channel_revenue) AS total_revenue 
                FROM {table_id}_google_analytics 
                WHERE LOWER(channel_source) LIKE '%facebook%' 
                    AND DATE(channel_date) BETWEEN '2024-09-01' AND '2024-09-30' 
                GROUP BY channel_name, channel_source 
                ORDER BY total_sessions DESC;
                ",
        "column_names": "channel_name,channel_source,total_sessions,total_carts,total_checkouts,total_transactions,total_revenue"
    }}

    **Input**: "How did SEO perform in July 2024?"
    **Output**:
    {{
        "query": "SELECT 
                    channel_name, 
                    SUM(channel_sessions) AS total_sessions, 
                    SUM(channel_carts) AS total_carts, 
                    SUM(channel_checkouts) AS total_checkouts, 
                    SUM(channel_transactions) AS total_transactions, 
                    SUM(channel_revenue) AS total_revenue 
                FROM {table_id}_google_analytics 
                WHERE LOWER(channel_name) LIKE '%organic search%' 
                    AND DATE(channel_date) BETWEEN '2024-07-01' AND '2024-07-31' 
                GROUP BY channel_name 
                ORDER BY total_sessions DESC;
                ",
        "column_names": "channel_name,total_sessions,total_carts,total_checkouts,total_transactions,total_revenue"
    }}

    **Input**: "How did SEO perform in the year 2024?"
    **Output**:
    {{
        "query": "SELECT 
                    SUBSTR(DATE(channel_date), 1, 7) AS month, 
                    SUM(channel_sessions) AS total_sessions, 
                    SUM(channel_carts) AS total_carts, 
                    SUM(channel_checkouts) AS total_checkouts, 
                    SUM(channel_transactions) AS total_transactions, 
                    SUM(channel_revenue) AS total_revenue 
                FROM {table_id}_google_analytics 
                WHERE LOWER(channel_name) LIKE '%organic search%' 
                    AND DATE(channel_date) BETWEEN '2024-01-01' AND '2024-12-31' 
                GROUP BY month 
                ORDER BY total_sessions DESC;
                ",
        "column_names": "month,total_sessions,total_carts,total_checkouts,total_transactions,total_revenue"
    }}

    # Notes

    - Ensure each query references only {table_id}_google_analytics.
    - Use `LIKE` and `LOWER(...)` for case-insensitive matching.
    - Always return the final query in valid SQLite syntax, ensuring correct date comparisons.
    """

    response = make_call(sys_prompt,user_input)
    query_result = call_sql(response)

    if query_result == False:
        return "Something went wrong."
    
    else:
        column_names = response['column_names']
        columns = column_names.split(',')
        df = pd.DataFrame(query_result, columns=columns)
        result = df.round(2).to_string(index=False)
        return result
    
def google_analytics_summary(user_input,table_id):
    raw_data = google_analytics(user_input,table_id)
    explanation = explain_this(raw_data)
    summery = raw_data + "\nsummary: " + explanation['query']
    return summery

def email_analytics_summary(user_input,table_id):
    raw_data = email_data(user_input,table_id)
    explanation = explain_this(raw_data)
    summery = raw_data + "\nsummary: " + explanation['query']
    return summery


def call_sql_report(query):

    try:
        conn = sqlite3.connect(DB_PATH)
        
        cursor = conn.cursor()
        cursor.execute(query)
        
        query_response = [x for x in cursor.fetchall()]
        return query_response
    
    except Exception as e:
        print(f"Error: {e}")
        query_response = False
        return query_response

    finally:
        if conn:
            cursor.close()
            conn.close()

def collect_data(table_id,start_date,end_date):

    shop_status = f"""
        SELECT
            COUNT(DISTINCT O.ORDER_ID) AS TOTAL_ORDERS,
            SUM(O.ORDER_TOTAL) AS TOTAL_SALES,
            SUM(O.ORDER_DISCOUNTS) AS TOTAL_DISCOUNTS,
            SUM(O.ORDER_SHIPPING) AS TOTAL_SHIPPING,
            SUM(O.ORDER_COST) AS TOTAL_COST,
            SUM(O.ORDER_TOTAL) / COUNT(DISTINCT O.ORDER_ID) AS AVERAGE_ORDER_VALUE,
            (SUM(O.ORDER_TOTAL) - SUM(O.ORDER_COST)) * 1.0 / SUM(O.ORDER_TOTAL) AS MARGIN,
            COUNT(DISTINCT CASE WHEN C2.CUSTOMER_ID IS NULL THEN O.CUSTOMER_ID END) AS NEW_CUSTOMERS
        FROM
            {table_id}_ORDERS O
        LEFT JOIN (
            SELECT DISTINCT CUSTOMER_ID
            FROM {table_id}_ORDERS
            WHERE DATE(ORDER_DATE) < DATE('{start_date}')
        ) C2 ON O.CUSTOMER_ID = C2.CUSTOMER_ID
        WHERE
            DATE(O.ORDER_DATE) BETWEEN DATE('{start_date}') AND DATE('{end_date}');
    """

    shop_stats = call_sql_report(shop_status)
    shop_columns = ['Total Orders','Total Sales','Total Discounts','Total Shipping','Total Cost','AOV','Margin','New Customers']
    df = pd.DataFrame(shop_stats, columns=shop_columns)
    shop_result = df.round(2).to_string(index=False)

    ga_status = f"""
        SELECT
            CHANNEL_NAME,
            SUM(CHANNEL_SESSIONS) AS TOTAL_SESSIONS,
            SUM(CHANNEL_CARTS) AS TOTAL_CARTS,
            SUM(CHANNEL_CHECKOUTS) AS TOTAL_CHECKOUTS,
            SUM(CHANNEL_TRANSACTIONS) AS TOTAL_TRANSACTIONS,
            SUM(CHANNEL_REVENUE) AS TOTAL_REVENUE
        FROM
            {table_id}_GOOGLE_ANALYTICS
        WHERE
            DATE(CHANNEL_DATE) BETWEEN DATE('{start_date}') AND DATE('{end_date}')
        GROUP BY
            CHANNEL_NAME
        ORDER BY
            TOTAL_SESSIONS DESC;
    """

    ga_stats = call_sql_report(ga_status)
    ga_columns = ['Channel','Total Sessions','Total Carts','Checkout Started','Total Orders','Total Revenue']
    df = pd.DataFrame(ga_stats, columns=ga_columns)
    ga_result = df.round(2).to_string(index=False)

    email_status = f"""
        SELECT
            COUNT(CAMPAIGN_ID) AS TOTAL_EMAIL_CAMPAIGNS_SENT,
            SUM(DELIVERED_EMAILS) AS TOTAL_EMAILS_DELIVERED,
            (CAST(SUM(OPENS) AS FLOAT) / NULLIF(SUM(DELIVERED_EMAILS), 0)) * 100 AS OPEN_RATE,
            (CAST(SUM(CLICKS) AS FLOAT) / NULLIF(SUM(DELIVERED_EMAILS), 0)) * 100 AS CLICK_THROUGH_RATE,
            (CAST(SUM(CONVERSIONS) AS FLOAT) / NULLIF(SUM(DELIVERED_EMAILS), 0)) * 100 AS CONVERSION_RATE,
            SUM(CONVERSIONS) AS TOTAL_CONVERSIONS
        FROM
            {table_id}_KLAVIYO_CAMPAIGNS
        WHERE
            DATE(SENT_TIME) BETWEEN DATE('{start_date}') AND DATE('{end_date}');
    """

    email_stats = call_sql_report(email_status)
    email_columns = ['Total Campaigns','Emails Delivered','Open Rate','Click Through Rate','Conversion Rate','Total Orders']
    df = pd.DataFrame(email_stats, columns=email_columns)
    email_result = df.round(2).to_string(index=False)
    results = {'shop':shop_result,'ga':ga_result,'email':email_result}

    return results


def explain_shop(data_sets):
    today = today_date()

    sys_prompt = f"""
    You are helpful digital marketing analyst. Today is {today}. You will be given a Shopify data set, your role will be to provide a summary with insights.     
    Your response will be in JSON format using the provided template:
    {{
        "query": "Your Summary Here"
    }}
    
    """
    chat_completion = client.chat.completions.create(
        messages=[
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": data_sets}
        ],
        model=open_model,
        response_format={ "type": "json_object" },
        temperature=0.1
    )
    response = json.loads(chat_completion.choices[0].message.content)

    return response

def explain_ga(data_sets):
    today = today_date()

    sys_prompt = f"""
    You are helpful digital marketing analyst. Today is {today}. You will be given a google analytics data set for an ecommerce store. The data set is all the channels that drove traffic to the website. "Cross-Network" is Google Paid Ads Channel. This should be considered a paid channel. Your role will be to provide a summary with insights.     
    Your response will be in JSON format using the provided template:
    {{
        "query": "Your Summary Here"
    }}
    
    """
    chat_completion = client.chat.completions.create(
        messages=[
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": data_sets}
        ],
        model=open_model,
        response_format={ "type": "json_object" },
        temperature=0.1
    )
    response = json.loads(chat_completion.choices[0].message.content)

    return response

def explain_email(data_sets):
    today = today_date()

    sys_prompt = f"""
    You are helpful email marketing analyst. Today is {today}. You will be given an email data set for an ecommerce store. Your role will be to provide a summary with insights.    
    Your response will be in JSON format using the provided template:
    {{
        "query": "Your Summary Here"
    }}
    
    """
    chat_completion = client.chat.completions.create(
        messages=[
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": data_sets}
        ],
        model=open_model,
        response_format={ "type": "json_object" },
        temperature=0.1
    )
    response = json.loads(chat_completion.choices[0].message.content)

    return response

def shop_report(table_id,start_date,end_date):
    data_sets = collect_data(table_id,start_date,end_date)

    shop = explain_shop(data_sets['shop'])['query']
    shop_result = f"{data_sets['shop']}\nSummary: {shop}"

    ga4 = explain_ga(data_sets['ga'])['query']
    ga4_result = f"{data_sets['ga']}\nSummary: {ga4}"

    email = explain_email(data_sets['email'])['query']
    email_result = f"{data_sets['email']}\nSummary: {email}"
    
    result = f"{shop_result}\n{ga4_result}\n{email_result}"

    return result

