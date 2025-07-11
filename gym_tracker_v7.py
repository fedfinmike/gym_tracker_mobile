import streamlit as st
import pandas as pd
import sqlite3
from datetime import date
import json
import plotly.graph_objects as go

# --- GymTracker Data Layer ---
class GymTracker:
    def __init__(self, db_name='gym_tracker_MASTER.db'):
        self.db_name = db_name
        self.init_database()

    def init_database(self):
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS workouts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                exercise TEXT,
                set_number INTEGER,
                reps INTEGER,
                weight REAL,
                rpe INTEGER,
                set_notes TEXT
            )
        ''')
        conn.commit()
        conn.close()

    def log_workout(self, date_str, exercise, sets_data):
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()
        for i, s in enumerate(sets_data, start=1):
            c.execute(
                'INSERT INTO workouts(date,exercise,set_number,reps,weight,rpe,set_notes) VALUES (?,?,?,?,?,?,?)',
                (date_str, exercise, i, s['reps'], s['weight'], s.get('rpe'), s.get('set_notes',''))
            )
        conn.commit()
        conn.close()

    def get_data(self):
        conn = sqlite3.connect(self.db_name)
        df = pd.read_sql('SELECT * FROM workouts ORDER BY date', conn)
        conn.close()
        return df

# --- Streamlit Setup & Styling ---
st.set_page_config(page_title="Gym Tracker", layout="wide")
st.markdown(
    '''<style>
    .date-header { background:#1f2937; padding:0.5rem; border-radius:5px; color:#fff; text-align:center; }
    button[type="submit"] { background:#3b82f6; color:#fff; }
    </style>''', unsafe_allow_html=True
)

# Initialize
def get_tracker():
    if 'tracker' not in st.session_state:
        st.session_state.tracker = GymTracker()
    return st.session_state.tracker

# --- Page: Quick Log ---
def quick_log_page():
    st.header("Quick Log")
    tracker = get_tracker()
    log_date = st.date_input("Date", value=date.today())
    ds = log_date.strftime('%Y-%m-%d')

    st.markdown(f'<div class="date-header">{log_date.strftime("%A, %B %d, %Y")}</div>', unsafe_allow_html=True)
    exercise = st.text_input("Exercise", value="Bench Press")
    with st.form("log_form", clear_on_submit=True):
        reps = st.number_input("Reps", min_value=1, value=5)
        weight = st.number_input("Weight (kg)", min_value=0.0, value=50.0)
        rpe = st.selectbox("RPE", options=[None,6,7,8,9,10], index=1)
        notes = st.text_input("Notes")
        submitted = st.form_submit_button("Log Set")
        if submitted:
            tracker.log_workout(ds, exercise, [{'reps':reps,'weight':weight,'rpe':rpe,'set_notes':notes}])
            st.success("Logged!")

    df = tracker.get_data()
    if not df.empty:
        st.write(df)

# --- Page: Progress ---
def progress_page():
    st.header("Progress")
    tracker = get_tracker()
    df = tracker.get_data()
    if df.empty:
        st.info("No data logged yet.")
        return
    exercises = df['exercise'].unique().tolist()
    ex = st.selectbox("Select exercise", exercises)
    dfx = df[df['exercise']==ex]
    fig = go.Figure()
    last = dfx.groupby('date')['weight'].max().reset_index()
    fig.add_trace(go.Scatter(x=last['date'], y=last['weight'], mode='lines+markers'))
    fig.update_layout(title=f'{ex} max weight over time', xaxis_title='Date', yaxis_title='Weight')
    st.plotly_chart(fig, use_container_width=True)

# --- Main ---
def main():
    st.sidebar.title("Menu")
    page = st.sidebar.radio("Go to", ["Quick Log","Progress"])
    if page=="Quick Log": quick_log_page()
    else: progress_page()

if __name__ == '__main__':
    main()
```
