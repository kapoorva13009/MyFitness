#--------------------------------------------------------------------------------------
                             #Importing modules
import streamlit as st
import pandas as pd
from datetime import timedelta, datetime
#--------------------------------------------------------------------------------------

# Set page config
st.set_page_config(page_title="My Fitness Report", layout="wide")

#--------------------------------------------------------------------------------------

# Helper functions
@st.cache_data
def load_data():
    data = pd.read_csv("Refined_data.csv")
    data['Date'] = pd.to_datetime(data['Date'])
    return data

def custom_quarter(date):
    month = date.month
    year = date.year
    if month in [2, 3, 4]:
        return pd.Period(year=year, quarter=1, freq='Q')
    elif month in [5, 6, 7]:
        return pd.Period(year=year, quarter=2, freq='Q')
    elif month in [8, 9, 10]:
        return pd.Period(year=year, quarter=3, freq='Q')
    else:  # month in [11, 12, 1]
        return pd.Period(year=year if month != 1 else year-1, quarter=4, freq='Q')
    
def aggregate_data(df, freq):
    if freq == 'Q':
        df = df.copy()
        df['CUSTOM_Q'] = df['Date'].apply(custom_quarter)
        df_agg = df.groupby('CUSTOM_Q').agg({
            'Move Minutes count': 'sum',
            'Calories (kcal)': 'sum',
            'Distance (m)': 'sum',
            'Heart Points': 'sum',
        })
        return df_agg
    else:
        return df.resample(freq, on='Date').agg({
            'Move Minutes count': 'sum',
            'Calories (kcal)': 'sum',
            'Distance (m)': 'sum',
            'Heart Points': 'sum',
        })
        
        
def get_weekly_data(df):
    return aggregate_data(df, 'W-MON')

def get_monthly_data(df):
    return aggregate_data(df, 'M')

def get_quarterly_data(df):
    return aggregate_data(df, 'Q')

#def format_with_commas(number):
#    return f"{number:,}"

def create_metric_chart(df, column, color, chart_type, height=150, time_frame='Daily'):
    chart_data = df[[column]].copy()
    if time_frame == 'Quarterly':
        chart_data.index = chart_data.index.strftime('%Y Q%q ')
    if chart_type=='Line':
        st.line_chart(chart_data, y=column, color=color, height=height)
    if chart_type=='Area':
        st.area_chart(chart_data, y=column, color=color, height=height)

def is_period_complete(date, freq):
    today = datetime.now()
    if freq == 'D':
        return date.date() < today.date()
    elif freq == 'W':
        return date + timedelta(days=6) < today
    elif freq == 'M':
        next_month = date.replace(day=28) + timedelta(days=4)
        return next_month.replace(day=1) <= today
    elif freq == 'Q':
        current_quarter = custom_quarter(today)
        return date < current_quarter

def calculate_delta(df, column):
    if len(df) < 2:
        return 0, 0
    current_value = df[column].iloc[-1]
    previous_value = df[column].iloc[-2]
    delta = current_value - previous_value
    delta_percent = (delta / previous_value) * 100 if previous_value != 0 else 0
    return delta, delta_percent

def display_metric(col, title, value, df, column, color, time_frame):
    with col:
        with st.container(border=True):
            delta, delta_percent = calculate_delta(df, column)
            delta_str = f"{delta:+,.0f} ({delta_percent:+.2f}%)"
            #st.metric(title, format_with_commas(value), delta=delta_str)
            st.metric(title, value, delta=delta_str)
            create_metric_chart(df, column, color, time_frame=time_frame, chart_type=chart_selection)
            
            last_period = df.index[-1]
            freq = {'Daily': 'D', 'Weekly': 'W', 'Monthly': 'M', 'Quarterly': 'Q'}[time_frame]
            if not is_period_complete(last_period, freq):
                st.caption(f"Note: The last {time_frame.lower()[:-2] if time_frame != 'Daily' else 'day'} is incomplete.")

#--------------------------------------------------------------------------------------

# Load data
df = load_data()

# Set up input widgets

st.sidebar.image("images/logo.png", width=500)
with st.sidebar:
    st.title("My Fitness Tracker")
    st.header("🔽 Filter")
    
    max_date = df['Date'].max().date()
    default_start_date = max_date - timedelta(days=365)  # Show a year by default
    default_end_date = max_date
    start_date = st.date_input("Start date", default_start_date, min_value=df['Date'].min().date(), max_value=max_date)
    end_date = st.date_input("End date", default_end_date, min_value=df['Date'].min().date(), max_value=max_date)
    time_frame = st.selectbox("Select time frame",
                              ("Daily", "Weekly", "Monthly", "Quarterly"),
    )
    chart_selection = st.selectbox("Select a chart type",
                                   ("Line", "Area"))

# Prepare data based on selected time frame
if time_frame == 'Daily':
    df_display = df.set_index('Date')
elif time_frame == 'Weekly':
    df_display = get_weekly_data(df)
elif time_frame == 'Monthly':
    df_display = get_monthly_data(df)
elif time_frame == 'Quarterly':
    df_display = get_quarterly_data(df)

#Note
with st.expander("ℹ️ Note:"):
    st.info("The Percentage changes in metrics is based on your Recent and Last to Recent workout data")




# Display Key Metrics
st.subheader("All-Time Statistics")

metrics = [
    ("Total Hours", "Move Minutes count", '#29b5e8'),
    ("Total Calories Burnt", "Calories (kcal)", '#FF9F36'),
    ("Total Distance Covered", "Distance (m)", '#D45B90'),
    ("Total Heart Points", "Heart Points", '#7D44CF')
]

cols = st.columns(4)
for col, (title, column, color) in zip(cols, metrics):
    total_value = df[column].sum()
    if column == "Move Minutes count":
        total_value = f"{total_value//60} Hours"
    elif column == "Calories (kcal)":
        total_value = f"{total_value/1000:.1f}K"
    elif column == "Distance (m)":
        total_value = f"{total_value//1000} KM"
    elif column == "Heart Points":
        total_value = f"{total_value/1000:.1f}K"
    display_metric(col, title, total_value, df_display, column, color, time_frame)
    

st.subheader("Selected Duration")

if time_frame == 'Quarterly':
    start_quarter = custom_quarter(start_date)
    end_quarter = custom_quarter(end_date)
    mask = (df_display.index >= start_quarter) & (df_display.index <= end_quarter)
else:
    mask = (df_display.index >= pd.Timestamp(start_date)) & (df_display.index <= pd.Timestamp(end_date))
df_filtered = df_display.loc[mask]

cols = st.columns(4)
for col, (title, column, color) in zip(cols, metrics):
    total_value = df_filtered[column].sum()
    if column == "Move Minutes count":
        total_value = f"{total_value//60} Hours"
    elif column == "Calories (kcal)":
        total_value = f"{total_value/1000:.1f}K"
    elif column == "Distance (m)":
        total_value = f"{total_value//1000} KM"
    elif column == "Heart Points":
        total_value = f"{total_value/1000:.1f}K"
    display_metric(col, title, total_value , df_filtered, column, color, time_frame)

# DataFrame display
with st.expander('See The Data Used to show the metrics for Selected time frame'):
    st.dataframe(df_filtered)

st.markdown("**Quote of the day**")
st.success("Consistency over intensity. Progress over perfection.")