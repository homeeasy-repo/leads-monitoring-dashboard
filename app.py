import streamlit as st
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
import json
import numpy as np
import requests

# Set page configuration
st.set_page_config(
    page_title="Client Dashboard",
    page_icon="📊",
    layout="wide"
)


def get_db_connection():
    db_params = {
        'dbname': st.secrets["database"]["DB_NAME"],
        'user': st.secrets["database"]["DB_USER"],
        'password': st.secrets["database"]["DB_PASSWORD"],
        'host': st.secrets["database"]["DB_HOST"],
        'port': st.secrets["database"]["DB_PORT"]
    }
    conn = psycopg2.connect(**db_params)
    return conn


def load_client_data(start_date=None, end_date=None, state=None, budget_sort=None, requirements_status=None, employee_type=None):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    query = """
    SELECT DISTINCT ON (c.id)
    c.id, c.fullname, c.created, c.fphone1, c.assigned_employee_name, c.addresses, c.assigned_employee,
    r.move_in_date, r.budget, r.budget_max, r.beds, r.baths, r.moving_reason, r.credit_score, r.neighborhood
    FROM client c
    LEFT JOIN requirements r ON c.id = r.client_id
    WHERE 1=1
    """
    
    params = []
    

    if start_date and end_date:
        query += " AND c.created BETWEEN %s AND %s"
        params.extend([start_date, end_date])
    
    if state and state != "All":
        query += " AND c.addresses::text LIKE %s"
        params.append(f'%"state": "{state}"%')
    
    # if requirements_status == "Requirements Gathered":
    #     query += " AND r.budget IS NOT NULL AND r.move_in_date IS NOT NULL AND r.moving_reason IS NOT NULL AND r.credit_score IS NOT NULL AND r.neighborhood IS NOT NULL"
    # elif requirements_status == "Partial Requirements":
    #     query += " AND r.client_id IS NOT NULL AND (r.budget IS NULL OR r.move_in_date IS NULL OR r.moving_reason IS NULL OR r.credit_score IS NULL OR r.neighborhood IS NULL)"
    # elif requirements_status == "No Requirements":
    #     query += " AND r.client_id IS NULL"
    if requirements_status == "Requirements Gathered":
        query += """
            AND r.budget IS NOT NULL AND r.move_in_date IS NOT NULL 
            AND r.moving_reason IS NOT NULL AND r.credit_score IS NOT NULL 
            AND r.neighborhood IS NOT NULL
        """
    elif requirements_status == "Partial Requirements":
        query += """
            AND r.client_id IS NOT NULL 
            AND (
                r.budget IS NOT NULL OR 
                r.move_in_date IS NOT NULL OR 
                r.moving_reason IS NOT NULL OR 
                r.credit_score IS NOT NULL OR 
                r.neighborhood IS NOT NULL
            )
            AND (
                r.budget IS NULL OR 
                r.move_in_date IS NULL OR 
                r.moving_reason IS NULL OR 
                r.credit_score IS NULL OR 
                r.neighborhood IS NULL
            )
        """
    elif requirements_status == "No Requirements":
        query += """
            AND r.client_id IS NOT NULL 
            AND (
                r.budget IS NULL AND 
                r.move_in_date IS NULL AND 
                r.moving_reason IS NULL AND 
                r.credit_score IS NULL AND 
                r.neighborhood IS NULL
            )
        """
    
    if employee_type == "Amy Accounts":
        query += " AND c.assigned_employee IN (317, 318, 319, 410, 415, 416)"
    elif employee_type == "Regular Employees":
        query += " AND (c.assigned_employee IS NULL OR c.assigned_employee NOT IN (317, 318, 319, 410, 415, 416))"
    
    if budget_sort == "Low to High":
        query += " ORDER BY r.budget ASC"
    elif budget_sort == "High to Low":
        query += " ORDER BY r.budget DESC"
    
    cursor.execute(query, params)
    results = cursor.fetchall()
    df = pd.DataFrame(results)
    
    cursor.close()
    conn.close()
    
    return df


def is_empty(value):
    if value is None:
        return True
    if isinstance(value, float) and np.isnan(value):
        return True
    if isinstance(value, (list, set, np.ndarray)):
        # Consider empty if length is zero
        return len(value) == 0
    return pd.isna(value)


def extract_address_info(addresses_json):
    try:
        if pd.isna(addresses_json) or addresses_json == "":
            return {"city": "", "state": ""}
        
        if isinstance(addresses_json, str):
            addresses = json.loads(addresses_json)
        else:
            addresses = addresses_json
            
        if isinstance(addresses, list) and len(addresses) > 0:
            return {
                "city": addresses[0].get("city", ""),
                "state": addresses[0].get("state", "")
            }
        return {"city": "", "state": ""}
    except:
        return {"city": "", "state": ""}


# Function to create FUB URL
def create_fub_url(client_id):
    return f"https://services.followupboss.com/2/people/view/{client_id}"


def find_inventory_for_client(client_id):
    """
    Makes a request to find building options for a client and returns the status
    """
    BUILDING_OPTIONS_URL = st.secrets["buildingURL"]["BUILDING_OPTIONS_URL"]
    url = f"{BUILDING_OPTIONS_URL}/find_building_options/{client_id}/0"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return True, "Building Options has been pushed on Slack -- inventory-note channel. Note: It might take time sometime up to 2-3 min."
        else:
            return False, f"Error: Received status code {response.status_code}"
    except Exception as e:
        return False, f"Error: {str(e)}"


st.title("Client Dashboard")
st.markdown("View and filter client data from the database")

# Sidebar for filters
st.sidebar.header("Filters")

# Date range filter
st.sidebar.subheader("Date Range")
date_options = [
    "Today",
    "Last 7 Days",
    "Last 30 Days",
    "Last 90 Days",
    "Custom Range",
    "All Time",
]
date_selection = st.sidebar.selectbox("Select Time Period", date_options)

start_date = None
end_date = None

if date_selection == "Custom Range":
    col1, col2 = st.sidebar.columns(2)
    start_date = col1.date_input("Start Date", datetime.now() - timedelta(days=30))
    end_date = col2.date_input("End Date", datetime.now())
    start_date = start_date.strftime("%Y-%m-%d")
    end_date = end_date.strftime("%Y-%m-%d")
elif date_selection == "Today":
    start_date = datetime.now().strftime("%Y-%m-%d")
    end_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
elif date_selection == "Last 7 Days":
    start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    end_date = datetime.now().strftime("%Y-%m-%d")
elif date_selection == "Last 30 Days":
    start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    end_date = datetime.now().strftime("%Y-%m-%d")
elif date_selection == "Last 90 Days":
    start_date = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
    end_date = datetime.now().strftime("%Y-%m-%d")


st.sidebar.subheader("State")
state_options = ["All", "TX", "IL"]
state_selection = st.sidebar.selectbox("Select State", state_options)

st.sidebar.subheader("Requirements Status")
requirements_options = ["All", "Requirements Gathered", "Partial Requirements", "No Requirements"]
requirements_status = st.sidebar.selectbox("Requirements Status", requirements_options)

st.sidebar.subheader("Employee Assignment")
employee_options = ["All", "Amy Accounts", "Regular Employees"]
employee_type = st.sidebar.selectbox("Employee Type", employee_options)

st.sidebar.subheader("Budget Sort")
budget_sort_options = ["None", "Low to High", "High to Low"]
budget_sort = st.sidebar.selectbox("Sort by Budget", budget_sort_options)

df = load_client_data(
    start_date, 
    end_date, 
    state_selection if state_selection != "All" else None,
    budget_sort if budget_sort != "None" else None,
    requirements_status if requirements_status != "All" else None,
    employee_type if employee_type != "All" else None
)

if not df.empty and 'addresses' in df.columns:
    address_info = df['addresses'].apply(extract_address_info)
    df['city'] = address_info.apply(lambda x: x['city'])
    df['state'] = address_info.apply(lambda x: x['state'])

# Add FUB URL to dataframe
if not df.empty and 'id' in df.columns:
    df['fub_url'] = df['id'].apply(create_fub_url)
    df['fub_link'] = df['fub_url']
st.header("Dashboard Metrics")
col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Total Clients", len(df))

with col2:
    avg_budget = df['budget'].mean() if not df.empty and 'budget' in df.columns and not df['budget'].isna().all() else 0
    st.metric("Average Budget", f"${avg_budget:,.2f}")

with col3:
    recent_clients = df[df['created'] >= (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")].shape[0] if not df.empty else 0
    st.metric("New Clients (Last 7 Days)", recent_clients)


st.header("Client Data")

if not df.empty:
    display_columns = [
        'id', 'fullname', 'created', 'fphone1', 'assigned_employee_name', 
        'city', 'state', 'move_in_date', 'budget', 'budget_max', 
        'beds', 'baths', 'moving_reason', 'credit_score', 'neighborhood', 'fub_link'
    ]
    
    # Only include columns that exist in the dataframe
    display_columns = [col for col in display_columns if col in df.columns]
    st.dataframe(df[display_columns], use_container_width=True)

else:
    st.info("No client data found with the current filters.")

if not df.empty:
    st.header("Visualizations")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Clients by State")
        state_counts = df['state'].value_counts().reset_index()
        state_counts.columns = ['State', 'Count']
        st.bar_chart(state_counts.set_index('State'))
    
    with col2:
        st.subheader("Budget Distribution")
        if 'budget' in df.columns and not df['budget'].isna().all():
            hist_values = df['budget'].dropna()
            st.bar_chart(hist_values.value_counts(bins=10).sort_index())

st.header("Client Details")
if not df.empty:
    client_id = st.selectbox("Select Client to View Details", df['fullname'].tolist())
    
    if client_id:
        client_data = df[df['fullname'] == client_id].iloc[0]
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Client Information")
            st.write(f"**Name:** {client_data['fullname']}")
            st.write(f"**Created:** {client_data['created']}")
            st.write(f"**Phone:** {client_data['fphone1']}")
            st.write(f"**Assigned Employee:** {client_data['assigned_employee_name']}")
            if 'city' in client_data and 'state' in client_data:
                st.write(f"**Location:** {client_data['city']}, {client_data['state']}")
            
            # Add FUB link in client details
            if 'fub_url' in client_data:
                st.markdown(f"**[View in Follow Up Boss]({client_data['fub_url']})**", unsafe_allow_html=True)
            
            # Add Find Inventory button
            if 'id' in client_data:
                if st.button("Find Inventory For Client"):
                    success, message = find_inventory_for_client(client_data['id'])
                    if success:
                        st.success(message)
                    else:
                        st.error(message)
        
        with col2:
            st.subheader("Requirements")
            
            # Use safer checks for NaN values
            if 'move_in_date' in client_data and not is_empty(client_data['move_in_date']):
                st.write(f"**Move-in Date:** {client_data['move_in_date']}")
            
            # Fix for the TypeError by adding null checks
            if ('budget' in client_data and not is_empty(client_data['budget']) and 
                'budget_max' in client_data and not is_empty(client_data['budget_max'])):
                st.write(f"**Budget Range:** ${float(client_data['budget']):,.2f} - ${float(client_data['budget_max']):,.2f}")
            elif 'budget' in client_data and not is_empty(client_data['budget']):
                st.write(f"**Budget:** ${float(client_data['budget']):,.2f}")
            elif 'budget_max' in client_data and not is_empty(client_data['budget_max']):
                st.write(f"**Budget Max:** ${float(client_data['budget_max']):,.2f}")
            
            if ('beds' in client_data and not is_empty(client_data['beds']) and 
                'baths' in client_data and not is_empty(client_data['baths'])):
                st.write(f"**Beds/Baths:** {client_data['beds']} bed, {client_data['baths']} bath")
            elif 'beds' in client_data and not is_empty(client_data['beds']):
                st.write(f"**Beds:** {client_data['beds']}")
            elif 'baths' in client_data and not is_empty(client_data['baths']):
                st.write(f"**Baths:** {client_data['baths']}")
            
            if 'moving_reason' in client_data and not is_empty(client_data['moving_reason']):
                st.write(f"**Moving Reason:** {client_data['moving_reason']}")
            
            if 'credit_score' in client_data and not is_empty(client_data['credit_score']):
                st.write(f"**Credit Score:** {client_data['credit_score']}")
            
            if 'neighborhood' in client_data and not is_empty(client_data['neighborhood']):
                st.write(f"**Preferred Neighborhood:** {client_data['neighborhood']}")
