import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
import sqlite3
import numpy as np
import json
import time

class GymTracker:
    def __init__(self, db_name='gym_tracker_MASTER.db'):
        """Initialize Gym Tracker - MASTER database for all future versions"""
        self.db_name = db_name
        self.init_database()
        
    def init_database(self):
        """Create all database tables"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS workouts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                exercise TEXT NOT NULL,
                set_number INTEGER NOT NULL,
                reps INTEGER NOT NULL,
                weight REAL NOT NULL,
                rpe INTEGER,
                set_notes TEXT,
                workout_notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS custom_exercises (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                exercise_name TEXT UNIQUE NOT NULL,
                category TEXT,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS workout_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                template_name TEXT UNIQUE NOT NULL,
                category TEXT,
                description TEXT,
                created_by TEXT,
                exercises TEXT,
                is_public INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_used TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def log_workout(self, date_str, exercise, sets_data, workout_notes=""):
        """Log a complete workout"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        for i, set_data in enumerate(sets_data, 1):
            cursor.execute('''
                INSERT INTO workouts (date, exercise, set_number, reps, weight, rpe, set_notes, workout_notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (date_str, exercise, i, set_data['reps'], set_data['weight'], 
                  set_data.get('rpe'), set_data.get('set_notes', ''), workout_notes))
        
        conn.commit()
        conn.close()
        return f"✅ Logged {len(sets_data)} sets for {exercise}"
    
    def quick_log(self, exercise, reps, weight, rpe=None, set_notes="", workout_notes="", date_str=None):
        """Quick log a single set"""
        if date_str is None:
            date_str = date.today().strftime('%Y-%m-%d')
        
        self.log_workout(date_str, exercise, [{'reps': reps, 'weight': weight, 'rpe': rpe, 'set_notes': set_notes}], workout_notes)
    
    def delete_set(self, set_id):
        """Delete a specific set by ID"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM workouts WHERE id = ?', (set_id,))
        rows_affected = cursor.rowcount
        conn.commit()
        conn.close()
        
        return "✅ Set deleted!" if rows_affected > 0 else "❌ Set not found!"
    
    def get_daily_workout(self, date_str):
        """Get all exercises for a specific date"""
        conn = sqlite3.connect(self.db_name)
        try:
            df = pd.read_sql_query('''
                SELECT id, exercise, set_number, reps, weight, rpe, set_notes, workout_notes, created_at
                FROM workouts 
                WHERE date = ? 
                ORDER BY exercise, set_number
            ''', conn, params=(date_str,))
            conn.close()
            return df
        except:
            conn.close()
            return pd.DataFrame()
    
    def add_custom_exercise(self, exercise_name, category="Custom", description=""):
        """Add a new custom exercise"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO custom_exercises (exercise_name, category, description)
                VALUES (?, ?, ?)
            ''', (exercise_name, category, description))
            conn.commit()
            conn.close()
            return f"✅ Added: {exercise_name}"
        except sqlite3.IntegrityError:
            conn.close()
            return f"❌ Exercise '{exercise_name}' already exists!"
    
    def save_template(self, template_name, category, description, created_by, exercises_list, is_public=False):
        """Save a workout template"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        exercises_json = json.dumps(exercises_list)
        
        try:
            cursor.execute('''
                INSERT INTO workout_templates (template_name, category, description, created_by, exercises, is_public)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (template_name, category, description, created_by, exercises_json, int(is_public)))
            
            conn.commit()
            conn.close()
            return f"✅ Template '{template_name}' saved!"
        except sqlite3.IntegrityError:
            conn.close()
            return f"❌ Template '{template_name}' already exists!"

    def get_templates(self, category=None, created_by=None):
        """Get workout templates"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        query = 'SELECT * FROM workout_templates WHERE 1=1'
        params = []
        
        if category:
            query += ' AND category = ?'
            params.append(category)
        
        if created_by:
            query += ' AND created_by = ?'
            params.append(created_by)
        
        query += ' ORDER BY created_at DESC'
        
        cursor.execute(query, params)
        templates = cursor.fetchall()
        conn.close()
        
        template_list = []
        for template in templates:
            template_list.append({
                'id': template[0],
                'name': template[1],
                'category': template[2],
                'description': template[3],
                'created_by': template[4],
                'exercises': json.loads(template[5]),
                'is_public': bool(template[6]),
                'created_at': template[7],
                'last_used': template[8]
            })
        
        return template_list

    def delete_template(self, template_id):
        """Delete a workout template"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM workout_templates WHERE id = ?', (template_id,))
        rows_affected = cursor.rowcount
        conn.commit()
        conn.close()
        
        return "✅ Template deleted!" if rows_affected > 0 else "❌ Template not found!"
    
    def get_all_exercises(self):
        """Get all exercises including built-in and custom ones"""
        built_in_exercises = [
            'Bench Press', 'Squat', 'Deadlift', 'Overhead Press', 'Barbell Row',
            'Incline Bench Press', 'Machine Shoulder Press', 'Lat Pulldown', 'Pull-ups',
            'Hack Squat', 'Leg Press', 'Romanian Deadlift', 'Hip Thrust', 'Leg Curl',
            'Leg Extension', 'Calf Raises', 'Bicep Curls', 'Tricep Pushdown', 'Dips',
            'Lateral Raises', 'Face Pulls', 'Bulgarian Split Squats', 'Walking Lunges',
            'Close Grip Bench Press', 'Wide Grip Pulldown', 'T-Bar Row', 'Hammer Curls',
            'Chest Supported Row', 'Front Squat', 'Military Press', 'Chin Up'
        ]
        
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('SELECT exercise_name FROM custom_exercises ORDER BY exercise_name')
        custom_exercises = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        all_exercises = built_in_exercises + custom_exercises
        return sorted(list(set(all_exercises)))
    
    def get_custom_exercises(self):
        """Get all custom exercises"""
        conn = sqlite3.connect(self.db_name)
        try:
            df = pd.read_sql_query('''
                SELECT exercise_name, category, description, created_at 
                FROM custom_exercises 
                ORDER BY created_at DESC
            ''', conn)
            conn.close()
            return df
        except:
            conn.close()
            return pd.DataFrame()
    
    def get_data(self):
        """Get all workout data"""
        conn = sqlite3.connect(self.db_name)
        try:
            df = pd.read_sql_query('SELECT * FROM workouts ORDER BY date DESC, exercise, set_number', conn)
            conn.close()
            if not df.empty:
                df['date'] = pd.to_datetime(df['date'])
            return df
        except:
            conn.close()
            return pd.DataFrame()
    
    def get_exercise_stats(self, exercise):
        """Get comprehensive stats for an exercise"""
        df = self.get_data()
        if df.empty:
            return None
        
        exercise_data = df[df['exercise'] == exercise]
        if exercise_data.empty:
            return None
        
        daily_stats = exercise_data.groupby('date').agg({
            'weight': ['max', 'mean'],
            'reps': ['sum', 'mean'],
            'set_number': 'count'
        }).round(2)
        
        daily_stats.columns = ['max_weight', 'avg_weight', 'total_reps', 'avg_reps', 'total_sets']
        daily_stats['volume'] = exercise_data.groupby('date').apply(lambda x: (x['reps'] * x['weight']).sum())
        daily_stats.reset_index(inplace=True)
        
        return {
            'daily_stats': daily_stats,
            'max_weight': exercise_data['weight'].max(),
            'total_volume': (exercise_data['reps'] * exercise_data['weight']).sum(),
            'total_sets': len(exercise_data),
            'workout_count': len(exercise_data['date'].unique()),
            'avg_rpe': exercise_data['rpe'].mean() if exercise_data['rpe'].notna().any() else 0
        }
    
    def clean_sample_data(self):
        """Remove obvious sample/fake data"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        # Target specific fake data patterns
        fake_patterns = [
            "Warm up set, felt good",
            "Working weight", 
            "Heavy set, good depth",
            "Full range of motion",
            "Great leg session! Gym was quiet, felt strong.",
            "Finished with leg press, good pump"
        ]
        
        deleted_count = 0
        for pattern in fake_patterns:
            cursor.execute('DELETE FROM workouts WHERE set_notes LIKE ? OR workout_notes LIKE ?', 
                          (f'%{pattern}%', f'%{pattern}%'))
            deleted_count += cursor.rowcount
        
        # Remove specific fake workout combinations
        cursor.execute('''DELETE FROM workouts WHERE 
                         exercise = 'Hack Squat' AND weight IN (80.0, 90.0, 100.0) AND reps IN (12, 10, 8)''')
        deleted_count += cursor.rowcount
        
        cursor.execute('''DELETE FROM workouts WHERE 
                         exercise = 'Leg Press' AND weight IN (150.0, 170.0) AND reps IN (15, 12)''')
        deleted_count += cursor.rowcount
        
        conn.commit()
        conn.close()
        
        return f"✅ Removed {deleted_count} fake data entries" if deleted_count > 0 else "✅ No fake data found"
    
    def reset_all_data(self):
        """Nuclear option - delete all workout data"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM workouts')
        conn.commit()
        conn.close()
        return "🚨 ALL WORKOUT DATA DELETED"

# Streamlit App Setup
st.set_page_config(
    page_title="💪 Beast Mode Gym Tracker",
    page_icon="💪",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Professional CSS Styling
st.markdown("""
<style>
    .stApp {
        background-color: #0e1117;
        color: #ffffff;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    
    .main-header {
        background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 12px;
        text-align: center;
        font-size: 1.8rem;
        font-weight: 600;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 20px rgba(59, 130, 246, 0.3);
    }
    
    .stButton > button {
        background: linear-gradient(135deg, #374151 0%, #4b5563 100%);
        color: white;
        border: 1px solid #6b7280;
        border-radius: 8px;
        padding: 0.75rem 1rem;
        font-size: 0.95rem;
        font-weight: 500;
        width: 100%;
        height: 3rem;
        transition: all 0.2s ease;
    }
    
    .stButton > button:hover {
        background: linear-gradient(135deg, #4b5563 0%, #6b7280 100%);
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
    }
    
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #1e40af 0%, #3b82f6 100%);
        border: 1px solid #3b82f6;
        color: white;
        font-weight: 600;
        height: 3.5rem;
    }
    
    .stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, #1d4ed8 0%, #2563eb 100%);
        box-shadow: 0 4px 16px rgba(59, 130, 246, 0.4);
    }
    
    .workout-card {
        background: linear-gradient(135deg, #1f2937 0%, #374151 100%);
        padding: 1.5rem;
        border-radius: 12px;
        margin: 1rem 0;
        border: 1px solid #4b5563;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
    }
    
    .stats-card {
        background: linear-gradient(135deg, #374151 0%, #4b5563 100%);
        color: white;
        padding: 1.2rem;
        border-radius: 10px;
        text-align: center;
        margin: 0.5rem;
        border: 1px solid #6b7280;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
    }
    
    .set-item {
        background: linear-gradient(135deg, #374151 0%, #4b5563 100%);
        padding: 0.8rem;
        border-radius: 8px;
        margin: 0.5rem 0;
        border-left: 4px solid #3b82f6;
        color: white;
        font-size: 0.9rem;
    }
    
    .stSelectbox > div > div {
        background: #374151;
        color: white;
        border: 1px solid #6b7280;
        border-radius: 8px;
        font-size: 0.95rem;
    }
    
    .stNumberInput > div > div > input {
        background: #374151;
        color: white;
        border: 1px solid #6b7280;
        border-radius: 8px;
        font-size: 1rem;
        text-align: center;
        font-weight: 600;
        height: 2.8rem;
    }
    
    .stTextInput > div > div > input {
        background: #374151;
        color: white;
        border: 1px solid #6b7280;
        border-radius: 8px;
        font-size: 0.95rem;
        padding: 0.6rem;
    }
    
    .stTextArea > div > div > textarea {
        background: #374151;
        color: white;
        border: 1px solid #6b7280;
        border-radius: 8px;
        font-size: 0.95rem;
        padding: 0.6rem;
    }
    
    .search-container {
        background: #1f2937;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #4b5563;
        margin: 0.5rem 0;
    }
    
    .date-header {
        background: linear-gradient(135deg, #1f2937 0%, #374151 100%);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
        font-size: 1.1rem;
        font-weight: 500;
        margin: 1rem 0;
        border: 1px solid #4b5563;
    }
    
    .stSuccess {
        background: linear-gradient(135deg, #065f46 0%, #047857 100%);
        color: white;
        border: 1px solid #047857;
        border-radius: 8px;
        padding: 1rem;
    }
    
    .stError {
        background: linear-gradient(135deg, #991b1b 0%, #dc2626 100%);
        color: white;
        border: 1px solid #dc2626;
        border-radius: 8px;
        padding: 1rem;
    }
    
    .stWarning {
        background: linear-gradient(135deg, #92400e 0%, #d97706 100%);
        color: white;
        border: 1px solid #d97706;
        border-radius: 8px;
        padding: 1rem;
    }
    
    .stInfo {
        background: linear-gradient(135deg, #1e40af 0%, #3b82f6 100%);
        color: white;
        border: 1px solid #3b82f6;
        border-radius: 8px;
        padding: 1rem;
    }
    
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: rgba(31, 41, 55, 0.8);
        padding: 8px;
        border-radius: 12px;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 2.8rem;
        font-size: 0.9rem;
        font-weight: 500;
        border-radius: 8px;
        background: transparent;
        color: rgba(255, 255, 255, 0.7);
        border: 1px solid transparent;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #1e40af 0%, #3b82f6 100%);
        color: white;
        border: 1px solid #3b82f6;
    }
    
    [data-testid="metric-container"] {
        background: #374151;
        border-radius: 8px;
        padding: 1rem;
        border: 1px solid #6b7280;
    }
    
    [data-testid="metric-container"] label {
        color: rgba(255, 255, 255, 0.8);
        font-size: 0.85rem;
        font-weight: 500;
    }
    
    [data-testid="metric-container"] div[data-testid="metric-value"] {
        color: #3b82f6;
        font-size: 1.3rem;
        font-weight: 700;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'tracker' not in st.session_state:
    st.session_state.tracker = GymTracker()

if 'last_exercise' not in st.session_state:
    st.session_state.last_exercise = 'Bench Press'
if 'last_reps' not in st.session_state:
    st.session_state.last_reps = 8
if 'last_weight' not in st.session_state:
    st.session_state.last_weight = 0.0
if 'last_rpe' not in st.session_state:
    st.session_state.last_rpe = 8

def get_last_workout_for_exercise(exercise):
    """Get the last workout data for a specific exercise"""
    df = st.session_state.tracker.get_data()
    if df.empty:
        return None
    
    exercise_data = df[df['exercise'] == exercise]
    if exercise_data.empty:
        return None
    
    last_date = exercise_data['date'].max()
    last_workout = exercise_data[exercise_data['date'] == last_date]
    return last_workout

def searchable_exercise_selector(all_exercises, default_exercise=None, key="exercise_search"):
    """Create a searchable exercise selector"""
    
    # Search input
    search_term = st.text_input(
        "🔍 Search Exercise", 
        placeholder="Type to search...",
        key=f"{key}_search",
        help="Start typing to filter exercises"
    )
    
    # Filter exercises based on search
    if search_term:
        filtered_exercises = [ex for ex in all_exercises if search_term.lower() in ex.lower()]
        if not filtered_exercises:
            st.warning(f"No exercises found matching '{search_term}'")
            return default_exercise or all_exercises[0] if all_exercises else ""
        exercises_to_show = filtered_exercises[:10]  # Limit to 10 results
    else:
        exercises_to_show = all_exercises
    
    # Select from filtered/all exercises
    if exercises_to_show:
        default_index = 0
        if default_exercise and default_exercise in exercises_to_show:
            default_index = exercises_to_show.index(default_exercise)
        
        selected_exercise = st.selectbox(
            "Select Exercise",
            options=exercises_to_show,
            index=default_index,
            key=f"{key}_select"
        )
        return selected_exercise
    
    return default_exercise or ""

def enhanced_quick_log_page():
    """Enhanced quick log with searchable exercises"""
    st.header("⚡ Quick Log")
    
    log_date = st.date_input("📅 Select Date", value=date.today())
    date_str = log_date.strftime('%Y-%m-%d')
    
    if log_date == date.today():
        st.markdown('<div class="date-header">🔥 <strong>TODAY\'S QUICK LOG</strong><br>' + 
                   log_date.strftime('%A, %B %d, %Y') + '</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="date-header">📅 <strong>WORKOUT LOG</strong><br>' + 
                   log_date.strftime('%A, %B %d, %Y') + '</div>', unsafe_allow_html=True)
    
    # Quick access buttons
    st.subheader("🚀 Quick Exercise Buttons")
    common_exercises = ['Bench Press', 'Squat', 'Deadlift', 'Overhead Press', 'Barbell Row', 'Pull-ups']
    
    cols = st.columns(3)
    for i, exercise in enumerate(common_exercises):
        col_idx = i % 3
        with cols[col_idx]:
            if st.button(f"💪 {exercise}", key=f"quick_{i}", use_container_width=True):
                st.session_state.last_exercise = exercise
                st.rerun()
    
    st.subheader("📝 Log Your Set")
    
    # Get all exercises
    all_exercises = st.session_state.tracker.get_all_exercises()
    
    # Exercise selection (outside form to avoid conflicts)
    exercise = searchable_exercise_selector(
        all_exercises, 
        default_exercise=st.session_state.last_exercise,
        key="quick_log"
    )
    
    # Show last performance
    if exercise:
        last_workout = get_last_workout_for_exercise(exercise)
        if last_workout is not None:
            last_set = last_workout.iloc[-1]
            st.success(f"🔥 Last: {last_set['reps']} reps @ {last_set['weight']}kg (RPE: {last_set['rpe']})")
    
    # Logging form
    with st.form("quick_log_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            reps = st.number_input("🎯 Reps", min_value=1, max_value=50, value=st.session_state.last_reps)
        with col2:
            weight = st.number_input("⚖️ Weight (kg)", min_value=0.0, value=st.session_state.last_weight, step=0.625)
        
        rpe = st.select_slider("💥 RPE", options=[6, 7, 8, 9, 10], value=st.session_state.last_rpe)
        set_notes = st.text_input("📝 Notes", placeholder="Form, fatigue, equipment...")
        
        submitted = st.form_submit_button("🚀 LOG SET", use_container_width=True, type="primary")
        
        if submitted and exercise:
            st.session_state.tracker.quick_log(exercise, reps, weight, rpe, set_notes, "", date_str)
            
            # Update session state
            st.session_state.last_exercise = exercise
            st.session_state.last_reps = reps
            st.session_state.last_weight = weight
            st.session_state.last_rpe = rpe
            
            st.success("✅ Set logged successfully!")
            st.balloons()
            st.rerun()
    
    # Today's workout summary
    st.subheader("📋 Today's Workout")
    daily_workout = st.session_state.tracker.get_daily_workout(date_str)
    
    if not daily_workout.empty:
        exercises_done = daily_workout['exercise'].unique()
        
        for exercise_name in exercises_done:
            exercise_sets = daily_workout[daily_workout['exercise'] == exercise_name]
            total_volume = (exercise_sets['reps'] * exercise_sets['weight']).sum()
            
            st.markdown(f'<div class="workout-card">', unsafe_allow_html=True)
            st.markdown(f"**🏋️ {exercise_name}** ({len(exercise_sets)} sets)")
            st.markdown(f"**Volume:** {total_volume:.0f}kg")
            
            for _, set_row in exercise_sets.iterrows():
                col1, col2 = st.columns([5, 1])
                
                with col1:
                    notes_display = f" - *{set_row['set_notes']}*" if set_row['set_notes'] else ""
                    rpe_emoji = "🟢" if set_row['rpe'] <= 7 else "🟡" if set_row['rpe'] <= 8 else "🔴"
                    st.markdown(f'<div class="set-item">Set {set_row["set_number"]}: {set_row["reps"]} reps @ {set_row["weight"]}kg {rpe_emoji}RPE:{set_row["rpe"]}{notes_display}</div>', 
                               unsafe_allow_html=True)
                
                with col2:
                    if st.button("🗑️", key=f"delete_{set_row['id']}", help="Delete set"):
                        result = st.session_state.tracker.delete_set(set_row['id'])
                        st.success(result)
                        st.rerun()
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Daily summary
        total_sets = len(daily_workout)
        total_volume = (daily_workout['reps'] * daily_workout['weight']).sum()
        avg_rpe = daily_workout['rpe'].mean() if daily_workout['rpe'].notna().any() else 0
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(f'<div class="stats-card"><strong>Exercises</strong><br>{len(exercises_done)}</div>', unsafe_allow_html=True)
        with col2:
            st.markdown(f'<div class="stats-card"><strong>Sets</strong><br>{total_sets}</div>', unsafe_allow_html=True)
        with col3:
            st.markdown(f'<div class="stats-card"><strong>Volume</strong><br>{total_volume:,.0f} kg</div>', unsafe_allow_html=True)
        with col4:
            if avg_rpe > 0:
                st.markdown(f'<div class="stats-card"><strong>Avg RPE</strong><br>{avg_rpe:.1f}</div>', unsafe_allow_html=True)
    else:
        st.info("💡 No exercises logged yet. Start your workout! 🔥")

def progress_page():
    """Progress tracking page"""
    st.header("📈 Progress")
    
    df = st.session_state.tracker.get_data()
    
    if df.empty:
        st.warning("No workout data yet. Start logging to see progress! 🚀")
        return
    
    available_exercises = df['exercise'].unique()
    selected_exercise = st.selectbox("🏋️ Choose Exercise", available_exercises)
    
    stats = st.session_state.tracker.get_exercise_stats(selected_exercise)
    
    if stats:
        st.subheader(f"📊 {selected_exercise} Statistics")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("🏆 Max Weight", f"{stats['max_weight']} kg")
        with col2:
            st.metric("🎯 Total Sets", stats['total_sets'])
        with col3:
            st.metric("📦 Total Volume", f"{stats['total_volume']:,.0f} kg")
        with col4:
            st.metric("💥 Avg RPE", f"{stats['avg_rpe']:.1f}")
        
        # Weight progression chart
        st.subheader("📈 Weight Progression")
        
        daily_stats = stats['daily_stats']
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=daily_stats['date'], 
            y=daily_stats['max_weight'],
            mode='lines+markers',
            name='Max Weight',
            line=dict(color='#3b82f6', width=3),
            marker=dict(size=8, color='#3b82f6')
        ))
        
        fig.update_layout(
            title=f'{selected_exercise} - Weight Progress',
            xaxis_title='Date',
            yaxis_title='Weight (kg)',
            height=400,
            paper_bgcolor='#0e1117',
            plot_bgcolor='#1f2937',
            font=dict(color='white', size=12),
            xaxis=dict(gridcolor='#374151'),
            yaxis=dict(gridcolor='#374151')
        )
        st.plotly_chart(fig, use_container_width=True)

def templates_page():
    """Templates management page"""
    st.header("📋 Workout Templates")
    
    create_tab, manage_tab = st.tabs(["🆕 Create", "📚 Templates"])
    
    with create_tab:
        st.subheader("🆕 Create New Template")
        
        template_name = st.text_input("Template Name", placeholder="e.g., Upper Body Power")
        
        col1, col2 = st.columns(2)
        with col1:
            category = st.selectbox("Category", ["Upper Body", "Lower Body", "Full Body", "Custom"])
        with col2:
            created_by = st.selectbox("Created By", ["Personal Trainer", "Myself"])
        
        description = st.text_area("Description", placeholder="Template goals and notes...")
        
        # Quick templates
        st.write("**Quick Templates:**")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("💪 Upper Body", use_container_width=True):
                if 'template_exercises' not in st.session_state:
                    st.session_state.template_exercises = []
                st.session_state.template_exercises = [
                    {'exercise': 'Bench Press', 'sets': 4, 'reps': 6},
                    {'exercise': 'Overhead Press', 'sets': 3, 'reps': 8},
                    {'exercise': 'Barbell Row', 'sets': 3, 'reps': 8}
                ]
                st.rerun()
        
        with col2:
            if st.button("🦵 Lower Body", use_container_width=True):
                if 'template_exercises' not in st.session_state:
                    st.session_state.template_exercises = []
                st.session_state.template_exercises = [
                    {'exercise': 'Squat', 'sets': 4, 'reps': 8},
                    {'exercise': 'Romanian Deadlift', 'sets': 3, 'reps': 10},
                    {'exercise': 'Leg Press', 'sets': 3, 'reps': 12}
                ]
                st.rerun()
        
        with col3:
            if st.button("🔄 Full Body", use_container_width=True):
                if 'template_exercises' not in st.session_state:
                    st.session_state.template_exercises = []
                st.session_state.template_exercises = [
                    {'exercise': 'Squat', 'sets': 3, 'reps': 8},
                    {'exercise': 'Bench Press', 'sets': 3, 'reps': 8},
                    {'exercise': 'Barbell Row', 'sets': 3, 'reps': 8}
                ]
                st.rerun()
        
        # Add exercises to template
        if 'template_exercises' not in st.session_state:
            st.session_state.template_exercises = []
        
        st.subheader("➕ Add Exercise")
        all_exercises = st.session_state.tracker.get_all_exercises()
        
        # Exercise selection
        exercise_name = searchable_exercise_selector(all_exercises, key="template_exercise")
        
        with st.form("add_exercise_template"):
            col1, col2 = st.columns(2)
            with col1:
                sets = st.number_input("Sets", min_value=1, max_value=10, value=3)
            with col2:
                reps = st.number_input("Reps", min_value=1, max_value=50, value=10)
            
            submitted = st.form_submit_button("➕ Add Exercise", use_container_width=True)
            
            if submitted and exercise_name:
                new_exercise = {'exercise': exercise_name, 'sets': sets, 'reps': reps}
                st.session_state.template_exercises.append(new_exercise)
                st.success(f"✅ Added {exercise_name}")
                st.rerun()
        
        # Show current template
        if st.session_state.template_exercises:
            st.subheader("📋 Current Template")
            
            for i, ex in enumerate(st.session_state.template_exercises):
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.write(f"**{i+1}. {ex['exercise']}** - {ex['sets']}×{ex['reps']}")
                with col2:
                    if st.button("🗑️", key=f"remove_{i}"):
                        st.session_state.template_exercises.pop(i)
                        st.rerun()
            
            # Save template
            col1, col2 = st.columns(2)
            with col1:
                if st.button("💾 Save Template", use_container_width=True):
                    if template_name and st.session_state.template_exercises:
                        result = st.session_state.tracker.save_template(
                            template_name, category, description, created_by, 
                            st.session_state.template_exercises
                        )
                        st.success(result)
                        st.balloons()
                        st.session_state.template_exercises = []
                        st.rerun()
                    else:
                        st.error("Enter template name and add exercises")
            
            with col2:
                if st.button("🗑️ Clear All", use_container_width=True):
                    st.session_state.template_exercises = []
                    st.rerun()
    
    with manage_tab:
        st.subheader("📚 Your Templates")
        
        templates = st.session_state.tracker.get_templates()
        
        if templates:
            for template in templates:
                with st.expander(f"📋 {template['name']}", expanded=False):
                    st.write(f"**Creator:** {template['created_by']}")
                    st.write(f"**Category:** {template['category']}")
                    
                    if template['description']:
                        st.write(f"**Description:** {template['description']}")
                    
                    st.write("**Exercises:**")
                    for i, ex in enumerate(template['exercises'], 1):
                        st.write(f"{i}. **{ex['exercise']}** - {ex['sets']}×{ex['reps']}")
                    
                    if st.button(f"🗑️ Delete Template", key=f"del_{template['id']}"):
                        result = st.session_state.tracker.delete_template(template['id'])
                        st.success(result)
                        st.rerun()
        else:
            st.info("📋 No templates found. Create your first one!")

def exercises_page():
    """Exercise management page"""
    st.header("➕ Exercise Manager")
    
    st.subheader("🆕 Add Custom Exercise")
    
    with st.form("add_exercise_form", clear_on_submit=True):
        exercise_name = st.text_input("Exercise Name", placeholder="e.g., Cable Crossover")
        
        col1, col2 = st.columns(2)
        with col1:
            category = st.selectbox("Category", [
                "Chest", "Back", "Shoulders", "Arms", "Legs", "Core", "Cardio", "Other"
            ])
        with col2:
            difficulty = st.selectbox("Difficulty", ["Beginner", "Intermediate", "Advanced"])
        
        description = st.text_area("Description", placeholder="Form cues, setup instructions...")
        
        submitted = st.form_submit_button("➕ Add Exercise", use_container_width=True, type="primary")
        
        if submitted and exercise_name.strip():
            full_description = f"{description}\nDifficulty: {difficulty}" if description else f"Difficulty: {difficulty}"
            result = st.session_state.tracker.add_custom_exercise(exercise_name.strip(), category, full_description)
            
            if "✅" in result:
                st.success(result)
                st.balloons()
            else:
                st.error(result)
            st.rerun()
    
    st.subheader("🌟 Your Custom Exercises")
    
    custom_exercises = st.session_state.tracker.get_custom_exercises()
    
    if not custom_exercises.empty:
        for category in custom_exercises['category'].unique():
            category_exercises = custom_exercises[custom_exercises['category'] == category]
            
            with st.expander(f"📂 {category} ({len(category_exercises)} exercises)"):
                for _, exercise in category_exercises.iterrows():
                    st.markdown(f"**🌟 {exercise['exercise_name']}**")
                    if exercise['description']:
                        st.write(f"💡 {exercise['description']}")
                    st.caption(f"📅 Added: {exercise['created_at'][:10]}")
                    st.write("---")
    else:
        st.info("🎯 No custom exercises yet. Add your first one above!")

def data_manager_page():
    """Data management page"""
    st.header("💾 Data Manager")
    
    df = st.session_state.tracker.get_data()
    templates = st.session_state.tracker.get_templates()
    custom_exercises = st.session_state.tracker.get_custom_exercises()
    
    st.subheader("📊 Data Overview")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        workout_count = len(df) if not df.empty else 0
        st.metric("🏋️ Total Sets", f"{workout_count:,}")
    
    with col2:
        exercise_count = len(df['exercise'].unique()) if not df.empty else 0
        st.metric("📝 Exercises", exercise_count)
    
    with col3:
        st.metric("📋 Templates", len(templates))
    
    with col4:
        custom_count = len(custom_exercises) if not custom_exercises.empty else 0
        st.metric("⭐ Custom", custom_count)
    
    st.subheader("🧹 Data Cleaning")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🧹 Clean Sample Data", use_container_width=True):
            result = st.session_state.tracker.clean_sample_data()
            st.success(result)
            st.rerun()
    
    with col2:
        if st.button("🚨 Reset All Data", use_container_width=True):
            if st.session_state.get('confirm_reset', False):
                result = st.session_state.tracker.reset_all_data()
                st.error(result)
                st.session_state.pop('confirm_reset', None)
                st.rerun()
            else:
                st.session_state.confirm_reset = True
                st.warning("⚠️ Tap again to confirm deletion!")
    
    if not df.empty:
        st.subheader("📈 Analytics")
        
        total_volume = (df['reps'] * df['weight']).sum()
        total_days = len(df['date'].unique())
        avg_rpe = df['rpe'].mean() if df['rpe'].notna().any() else 0
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("🏋️ Total Volume", f"{total_volume:,.0f} kg")
        with col2:
            st.metric("📅 Training Days", total_days)
        with col3:
            if avg_rpe > 0:
                st.metric("💥 Average RPE", f"{avg_rpe:.1f}")

def main():
    """Main application"""
    st.markdown('<div class="main-header">💪 Beast Mode Gym Tracker Pro</div>', unsafe_allow_html=True)
    
    st.success("✅ **Professional Edition** - Clean UI, searchable exercises, robust data management!")
    
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "⚡ Quick Log", 
        "📈 Progress", 
        "📋 Templates",
        "➕ Exercises",
        "💾 Data",
        "ℹ️ Info"
    ])
    
    with tab1:
        enhanced_quick_log_page()
    
    with tab2:
        progress_page()
    
    with tab3:
        templates_page()
    
    with tab4:
        exercises_page()
    
    with tab5:
        data_manager_page()
    
    with tab6:
        st.header("ℹ️ About Beast Mode Gym Tracker")
        st.write("**Version:** Pro v8.0")
        st.write("**Features:**")
        st.write("✅ Searchable exercise database")
        st.write("✅ Professional UI design") 
        st.write("✅ Robust data management")
        st.write("✅ Progress tracking & analytics")
        st.write("✅ Custom workout templates")
        st.write("✅ Mobile-optimized interface")
        
        st.write("**Data Storage:**")
        st.write("• All data stored in SQLite database")
        st.write("• Automatic data persistence") 
        st.write("• Built-in backup/restore functions")
        
        st.write("**Usage:**")
        st.write("• Log sets in Quick Log tab")
        st.write("• Track progress in Progress tab")
        st.write("• Create templates for repeated workouts")
        st.write("• Add custom exercises as needed")

if __name__ == "__main__":
    main()
