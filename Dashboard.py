import streamlit as st
import pandas as pd
import datetime
import os

# Set page configuration
st.set_page_config(page_title="IIM Shillong Timetable Hub", page_icon="📅", layout="wide")

st.title("📅 Class Schedule & Attendance Hub")

# Function to load and clean data
def load_data():
    df = pd.read_excel('My_Timetable.xlsx')
    df['parsed_date'] = pd.to_datetime(df['Day']).dt.date
    # Normalize empty or missing fields in Attended column
    df['Attended'] = df['Attended'].fillna('')
    return df

# Save data back to CSV file
def save_data(dataframe):
    save_df = dataframe.copy()
    if 'parsed_date' in save_df.columns:
        save_df = save_df.drop(columns=['parsed_date'])
    save_df.to_excel('My_Timetable.xlsx', index=False)

# Initialize data state to make sure actions save instantly on click
if 'df' not in st.session_state:
    st.session_state.df = load_data()

df = st.session_state.df

# Date range optimization configuration
min_date = df['parsed_date'].min()
max_date = df['parsed_date'].max()
today_actual = datetime.date.today()

# Default dynamically to mid-June 2026 if today's date falls outside the term scope
if min_date <= today_actual <= max_date:
    default_date = today_actual
else:
    default_date = datetime.date(2026, 6, 9)

# --- SIDEBAR SETTINGS & ATTENDANCE PROGRESS BARS ---
st.sidebar.header("📊 Dashboard Settings")
today = st.sidebar.date_input("Select 'Today's' Date:", default_date)
free_days_horizon = st.sidebar.slider("Lookahead horizon for free days:", min_value=7, max_value=30, value=14)

st.sidebar.markdown("---")
st.sidebar.subheader("📉 Course Attendance Tracker")

# Calculate metrics across unique courses
subjects = sorted(df['Subject'].unique())
for sub in subjects:
    sub_df = df[df['Subject'] == sub]
    total_classes = len(sub_df)
    attended_count = len(sub_df[sub_df['Attended'] == 'Y'])
    absent_count = len(sub_df[sub_df['Attended'] == 'N'])
    
    # Track criteria against classes that have passed/been logged
    marked_classes = attended_count + absent_count
    if marked_classes > 0:
        attendance_pct = (attended_count / marked_classes) * 100
        label = f"{sub} ({attendance_pct:.1f}%)"
        # Flag visual alert if status falls below standard 75% threshold criteria
        if attendance_pct >= 75:
            st.sidebar.progress(attendance_pct / 100, text=f"🍏 {label}")
        else:
            st.sidebar.progress(attendance_pct / 100, text=f"🚨 {label} (Below 75%)")
    else:
        st.sidebar.caption(f"⚪ {sub} (No sessions logged yet — 0/{total_classes})")

# Relative calculations
next_day = today + datetime.timedelta(days=1)
next_week_start = today + datetime.timedelta(days=1)
next_week_end = today + datetime.timedelta(days=7)

# --- APP LAYOUT TABS ---
tab1, tab2, tab3, tab4 = st.tabs([
    "🌅 Next Day Schedule", 
    "📅 Next Week Tracker", 
    "🏖️ Upcoming Free Days",
    "📚 Subject-Wise Overview"
])

# TAB 1: INTERACTIVE NEXT DAY SCHEDULE + ATTENDANCE LOGGER
with tab1:
    st.subheader(f"Schedule for Tomorrow: {next_day.strftime('%A, %b %d, %Y')}")
    next_day_indices = df[df['parsed_date'] == next_day].index
    
    if len(next_day_indices) > 0:
        st.info("Log your attendance below. Changes write directly back to your CSV file.")
        
        for idx in next_day_indices:
            row = df.loc[idx]
            col1, col2, col3 = st.columns([2, 3, 2])
            
            with col1:
                st.markdown(f"**⏰ {row['Time Slot']}**")
            with col2:
                st.markdown(f"📖 `{row['Subject']}`")
            with col3:
                current_status = row['Attended']
                options = ['', 'Y', 'N']
                default_idx = options.index(current_status) if current_status in options else 0
                
                choice = st.selectbox(
                    "Status", 
                    options=options, 
                    index=default_idx, 
                    key=f"tomorrow_{idx}",
                    format_func=lambda x: "🕒 Pending" if x == "" else ("✅ Attended (Y)" if x == "Y" else "❌ Absent (N)")
                )
                
                # Check for adjustment, execute save function, and refresh state
                if choice != current_status:
                    df.at[idx, 'Attended'] = choice
                    save_data(df)
                    st.rerun()
    else:
        st.success("🎉 No classes scheduled tomorrow! Enjoy your day off!")

# TAB 2: NEXT WEEK DATA VIEWER
with tab2:
    st.subheader(f"Schedule: {next_week_start.strftime('%b %d')} to {next_week_end.strftime('%b %d, %Y')}")
    next_week_df = df[(df['parsed_date'] >= next_week_start) & (df['parsed_date'] <= next_week_end)].copy()
    
    if not next_week_df.empty:
        display_week = next_week_df[['parsed_date', 'Date', 'Time Slot', 'Subject', 'Attended']].copy()
        display_week.columns = ['Calendar Date', 'Day', 'Time Slot', 'Subject', 'Attended Status']
        display_week['Attended Status'] = display_week['Attended Status'].replace({'Y': '✅ Attended', 'N': '❌ Absent', '': '🕒 Scheduled'})
        st.dataframe(display_week.sort_values(by='Calendar Date').reset_index(drop=True), use_container_width=True)
    else:
        st.info("No classes scheduled for the coming week timeframe.")

# TAB 3: HOLIDAY OR FREE DAY DETECTOR
with tab3:
    st.subheader(f"🏖️ Free Day Horizons (Next {free_days_horizon} Days)")
    all_days = [today + datetime.timedelta(days=i) for i in range(1, free_days_horizon + 1)]
    busy_days = set(df['parsed_date'].unique())
    free_days = [d for d in all_days if d not in busy_days]
    
    if free_days:
        st.markdown(f"Found **{len(free_days)} fully free days** inside your chosen track window:")
        free_days_df = pd.DataFrame({
            'Calendar Date': free_days,
            'Day of the Week': [d.strftime('%A') for d in free_days]
        })
        st.dataframe(free_days_df, use_container_width=True)
    else:
        st.warning("Intense block detected! No entirely free days found in this horizon timeframe.")

# TAB 4: SUBJECT-WISE TIMELINE DRILL DOWN
with tab4:
    st.subheader("📚 Subject Calendar Breakdown")
    selected_subject = st.selectbox("Select a subject to drill down into:", subjects)
    
    subject_filter = df[df['Subject'] == selected_subject].sort_values(by='parsed_date')
    
    stat_col1, stat_col2, stat_col3 = st.columns(3)
    total_sub_classes = len(subject_filter)
    sub_attended = len(subject_filter[subject_filter['Attended'] == 'Y'])
    sub_absent = len(subject_filter[subject_filter['Attended'] == 'N'])
    
    stat_col1.metric("Total Scheduled Sessions", total_sub_classes)
    stat_col2.metric("Attended Sessions", sub_attended)
    stat_col3.metric("Absent Sessions", sub_absent)
    
    st.markdown("#### Full Term Matrix for this Course")
    display_sub = subject_filter[['parsed_date', 'Date', 'Time Slot', 'Attended']].copy()
    display_sub.columns = ['Calendar Date', 'Day of Week', 'Time Slot', 'Marked Status']
    display_sub['Marked Status'] = display_sub['Marked Status'].replace({'Y': '✅ Attended', 'N': '❌ Absent', '': '🕒 Scheduled'})
    
    st.dataframe(display_sub.reset_index(drop=True), use_container_width=True)