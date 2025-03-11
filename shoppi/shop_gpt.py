import streamlit as st
from openai import OpenAI
import os, json
from mods import ecommerce_data, email_analytics_summary, google_analytics_summary, shop_report

USER_PREFIX = "" # the account prefix you want to access - example: D1

icon_path = os.path.join(os.getcwd(), "static","osgpt_favicon.png")

st.set_page_config(
    page_title="OpenShopGPT",
    page_icon=icon_path
)

st.session_state['username'] = USER_PREFIX
logo_path = os.path.join(os.getcwd(), "static","osgpt_favicon.png")
st.logo(logo_path)

with st.sidebar:
    welcome_msg = f"Hello {USER_PREFIX.upper()}!"
    st.write(welcome_msg)
    st.subheader("GUIDES", divider="gray")
    st.write(
        """
        **[FULL DOCS](https://openshopgpt.com/)**\n
        **[TUTORIALS](https://www.youtube.com/@DaveedValencia)**\n
        **[@DaveedValencia](https://x.com/DaveedValencia)**
        """
                )
    st.subheader("PROMPTS", divider="gray")
    st.write(
        """
        What is my channel conversion rate in 2025 so far?\n
        How did my website traffic perform in January 2025?\n
        How many first time customers did I get in February 2025?\n
        Give me a full status report for 2024.
        """
                )
    st.subheader("", divider="gray")

client = OpenAI(api_key=os.environ["open_secret"],organization=os.environ["open_organization"])
assistant_id = os.environ['central_hub']

st.title("OpenShopGPT")

if "thread" not in st.session_state:
    st.session_state["thread"] = client.beta.threads.create()

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("How can I help?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.empty()
    
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        thread = st.session_state['thread']
        message = client.beta.threads.messages.create(
            thread_id=thread.id, 
            role="user", 
            content=prompt
            )
        run = client.beta.threads.runs.create_and_poll(thread_id=thread.id,assistant_id=assistant_id)
        print(run.status)
        if run.status == 'completed':
            messages = client.beta.threads.messages.list(
                thread_id=thread.id,
                order="asc"
            )
            response = messages.data[-1].content[0].text.value
            response = json.loads(response)
            statement = response['statement'].replace('$','\\$')
            
            st.session_state.messages.append({"role": "assistant", "content": statement})
            display_response = st.write(statement)
            
        
        elif run.status == 'requires_action':
            tool_outputs = []
            for tool in run.required_action.submit_tool_outputs.tool_calls:
                if tool.function.name == 'ecommerce_sales':
                    msg = "Analyzing Shopify data..."
                    st.write(msg)

                    user_question = json.loads(tool.function.arguments)
                    tables = st.session_state['username']
                    tool_outputs.append({
                        "tool_call_id": tool.id,
                        "output": ecommerce_data(user_question['user_input'],tables)
                    })

                    try:
                        run = client.beta.threads.runs.submit_tool_outputs_and_poll(
                            thread_id=thread.id,
                            run_id=run.id,
                            tool_outputs=tool_outputs
                        )
                        
                    except Exception as e:
                        print(e)
                
                
                elif tool.function.name == 'email_campaign_data':
                    msg = "Analyzing email data..."
                    st.write(msg)

                    user_question = json.loads(tool.function.arguments)
                    tables = st.session_state['username']

                    tool_outputs.append({
                        "tool_call_id": tool.id,
                        "output": email_analytics_summary(user_question['user_input'],tables)
                    })

                    try:
                        run = client.beta.threads.runs.submit_tool_outputs_and_poll(
                            thread_id=thread.id,
                            run_id=run.id,
                            tool_outputs=tool_outputs
                        )
                        
                    except Exception as e:
                        print(e)

                elif tool.function.name == 'google_analytics_data':
                    msg = "Analyzing Google Analytics..."
                    st.write(msg)

                    user_question = json.loads(tool.function.arguments)
                    tables = st.session_state['username']
                    tool_outputs.append({
                        "tool_call_id": tool.id,
                        "output": google_analytics_summary(user_question['user_input'],tables)
                    })

                    try:
                        run = client.beta.threads.runs.submit_tool_outputs_and_poll(
                            thread_id=thread.id,
                            run_id=run.id,
                            tool_outputs=tool_outputs
                        )
                        
                    except Exception as e:
                        print(e)

                elif tool.function.name == 'status_report':
                    msg = "Building report, this will take a moment..."
                    st.write(msg)

                    report_dates = json.loads(tool.function.arguments)
                    tables = st.session_state['username']

                    tool_outputs.append({
                        "tool_call_id": tool.id,
                        "output": shop_report(tables,report_dates['start_date'],report_dates['end_date'])
                    })

                    try:
                        run = client.beta.threads.runs.submit_tool_outputs_and_poll(
                            thread_id=thread.id,
                            run_id=run.id,
                            tool_outputs=tool_outputs
                        )
                        
                    except Exception as e:
                        print(e)


            if run.status == 'failed':
                msg = 'something went wrong...\nTry rephrasing your request.'
                st.session_state.messages.append({"role": "assistant", "content": msg})
                st.write(msg)

            elif run.status == 'completed':
                messages = client.beta.threads.messages.list(thread_id=thread.id)
                statement = json.loads(messages.data[0].content[0].text.value)
                statement = statement['statement'].replace('$','\\$')

                st.session_state.messages.append({"role": "assistant", "content": statement})
                st.write(statement)
