## Client Dashboard

A Streamlit dashboard for displaying and filtering client data from a database.

## Features

- View client data with filtering by date range
- Filter clients by state (TX, IL)
- Sort clients by budget (high to low or low to high)
- View detailed client information
- Visualize client distribution by state and budget

## Setup

1. Install the required dependencies:

```bash
pip install -r requirements.txt
```

2. Set up your Streamlit secrets file (.streamlit/secrets.toml) with your database credentials:

```toml
[database]
DB_NAME = "your_database_name"
DB_USER = "your_database_user"
DB_PASSWORD = "your_database_password"
DB_HOST = "your_database_host"
DB_PORT = "your_database_port"
```

3. Run the Streamlit app:

```bash
streamlit run app.py
```

## Database Schema

The dashboard expects the following database schema:

### Client Table
- `id`: Unique identifier for the client
- `fullname`: Client's full name
- `created`: Date when the client was created
- `fphone1`: Client's phone number
- `assigned_employee_name`: Name of the employee assigned to the client
- `addresses`: JSON string containing address information (city, state, etc.)

### Requirements Table
- `client_id`: Foreign key referencing the client table
- `move_in_date`: Client's desired move-in date
- `budget`: Minimum budget
- `budget_max`: Maximum budget
- `beds`: Number of bedrooms required
- `baths`: Number of bathrooms required
- `moving_reason`: Reason for moving
- `credit_score`: Client's credit score
- `neighborhood`: Preferred neighborhood

## Usage

1. Use the sidebar to filter clients by date range, state, and budget sort order
2. View the client data table with all relevant information
3. Check the visualizations section for insights on client distribution
4. Select a specific client from the dropdown to view detailed information