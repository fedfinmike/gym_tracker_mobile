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

# ===== MOBILE-OPTIMIZED GYM TRACKER V7 - CLEAN =====
class GymTracker:
    def __init__(self, db_name='gym_tracker_MASTER.db'):
        """Initialize Gym Tracker - MASTER database for all future versions"""
        self.db_name = db_name
        self.init_database()
        self.migrate_old_data()
        
    def migrate_old_data(self):
        """Migrate data from ALL previous versions based on your file history"""
        import os
        
        old_db_names = [
            'complete_gym_app.db',
            'demo_workout.db',
            'gym_app.db',
            'gym_tracker_v2.db', 
            'gym_tracker_v2.1.db',
            'gym_tracker_v3.db',
            'gym_tracker_v4.db',
            'gym_tracker_v5.db',
            'gym_tracker_v6.db',
            'workout_tracker.db'
        ]
        
        current_data = self.get_data()
        migrated_any = False
        
        if not current_data.empty:
            return
        
        st.info("🔍 Checking for data from previous versions...")
        
        for old_db in old_db_names:
            if os.path.exists(old_db) and old_db != self.db_name:
                try:
                    old_conn = sqlite3.connect(old_db)
                    cursor = old_conn.cursor()
                    
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                    tables = [row[0] for row in cursor.fetchall()]
                    
                    if 'workouts' in tables:
                        old_df = pd.read_sql_query('SELECT * FROM workouts', old_conn)
                        
                        if not old_df.empty:
                            new_conn = sqlite3.connect(self.db_name)
                            old_df.to_sql('workouts', new_conn, if_exists='append', index=False)
                            new_conn.close()
                            
                            st.success(f"✅ Migrated {len(old_df)} workout records from {old_db}")
                            migrated_any = True
                    
                    if 'workout_templates' in tables:
                        old_templates = pd.read_sql_query('SELECT * FROM workout_templates', old_conn)
                        if not old_templates.empty:
                            new_conn = sqlite3.connect(self.db_name)
                            old_templates.to_sql('workout_templates', new_conn, if_exists='append', index=False)
                            new_conn.close()
                            st.success(f"✅ Migrated {len(old_templates)} templates from {old_db}")
                    
                    if 'custom_exercises' in tables:
                        old_exercises = pd.read_sql_query('SELECT * FROM custom_exercises', old_conn)
                        if not old_exercises.empty:
                            new_conn = sqlite3.connect(self.db_name)
                            old_exercises.to_sql('custom_exercises', new_conn, if_exists='append', index=False)
                            new_conn.close()
                            st.success(f"✅ Migrated {len(old_exercises)} custom exercises from {old_db}")
                    
                    if 'daily_programs' in tables:
                        old_programs = pd.read_sql_query('SELECT * FROM daily_programs', old_conn)
                        if not old_programs.empty:
                            new_conn = sqlite3.connect(self.db_name)
                            old_programs.to_sql('daily_programs', new_conn, if_exists='append', index=False)
                            new_conn.close()
                            st.success(f"✅ Migrated {len(old_programs)} programs from {old_db}")
                    
                    old_conn.close()
                    
                    if migrated_any:
                        st.balloons()
                        st.success(f"🎉 All your workout history has been preserved from {old_db}!")
                        break
                        
                except Exception as e:
                    st.warning(f"⚠️ Could not migrate from {old_db}: {str(e)}")
                    continue
        
        if not migrated_any:
            st.info("📊 Starting fresh - no previous data found to migrate")
    
    def export_data(self, export_file='gym_tracker_backup.json'):
        """Export all data to JSON file for backup"""
        try:
            export_data = {}
            
            workouts_df = self.get_data()
            if not workouts_df.empty:
                workouts_df['date'] = workouts_df['date'].dt.strftime('%Y-%m-%d')
                export_data['workouts'] = workouts_df.to_dict('records')
            
            templates = self.get_templates()
            if templates:
                export_data['templates'] = templates
            
            custom_exercises = self.get_custom_exercises()
            if not custom_exercises.empty:
                export_data['custom_exercises'] = custom_exercises.to_dict('records')
            
            conn = sqlite3.connect(self.db_name)
            try:
                programs_df = pd.read_sql_query('SELECT * FROM daily_programs', conn)
                if not programs_df.empty:
                    export_data['daily_programs'] = programs_df.to_dict('records')
            except:
                pass
            conn.close()
            
            with open(export_file, 'w') as f:
                json.dump(export_data, f, indent=2, default=str)
            
            return f"✅ Data exported to {export_file}"
            
        except Exception as e:
            return f"❌ Export failed: {str(e)}"
    
    def import_data(self, import_file='gym_tracker_backup.json'):
        """Import data from JSON backup file"""
        try:
            with open(import_file, 'r') as f:
                import_data = json.load(f)
            
            conn = sqlite3.connect(self.db_name)
            imported_items = []
            
            if 'workouts' in import_data:
                workouts_df = pd.DataFrame(import_data['workouts'])
                workouts_df.to_sql('workouts', conn, if_exists='append', index=False)
                imported_items.append(f"{len(workouts_df)} workouts")
            
            if 'templates' in import_data:
                for template in import_data['templates']:
                    try:
                        exercises_json = json.dumps(template['exercises'])
                        cursor = conn.cursor()
                        cursor.execute('''
                            INSERT OR REPLACE INTO workout_templates 
                            (template_name, category, description, created_by, exercises, is_public, created_at, last_used)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (template['name'], template['category'], template['description'], 
                              template['created_by'], exercises_json, int(template['is_public']),
                              template['created_at'], template['last_used']))
                    except:
                        continue
                imported_items.append(f"{len(import_data['templates'])} templates")
            
            if 'custom_exercises' in import_data:
                exercises_df = pd.DataFrame(import_data['custom_exercises'])
                exercises_df.to_sql('custom_exercises', conn, if_exists='append', index=False)
                imported_items.append(f"{len(exercises_df)} custom exercises")
            
            if 'daily_programs' in import_data:
                programs_df = pd.DataFrame(import_data['daily_programs'])
                programs_df.to_sql('daily_programs', conn, if_exists='append', index=False)
                imported_items.append(f"{len(programs_df)} programs")
            
            conn.commit()
            conn.close()
            
            return f"✅ Imported: {', '.join(imported_items)}"
            
        except Exception as e:
            return f"❌ Import failed: {str(e)}"
        
    def init_database(self):
        """Create all database tables including templates"""
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
            CREATE TABLE IF NOT EXISTS daily_programs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                program_name TEXT,
                created_by TEXT,
                program_notes TEXT,
                exercises TEXT,
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
        """Log a complete workout with enhanced notes"""
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
        return f"✅ Logged {len(sets_data)} sets for {exercise} on {date_str}"
    
    def quick_log(self, exercise, reps, weight, rpe=None, set_notes="", workout_notes="", date_str=None):
        """Quick log a single set with notes"""
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
        
        if rows_affected > 0:
            return "✅ Set deleted successfully!"
        else:
            return "❌ Set not found!"
    
    def get_daily_workout(self, date_str):
        """Get all exercises and sets for a specific date"""
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
            return f"✅ Successfully added: {exercise_name}"
        except sqlite3.IntegrityError:
            conn.close()
            return f"❌ Exercise '{exercise_name}' already exists!"
    
    def create_daily_program(self, date_str, program_name, created_by, program_notes, exercises_list):
        """Create a daily workout program"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        exercises_json = json.dumps(exercises_list)
        
        cursor.execute('DELETE FROM daily_programs WHERE date = ?', (date_str,))
        
        cursor.execute('''
            INSERT INTO daily_programs (date, program_name, created_by, program_notes, exercises)
            VALUES (?, ?, ?, ?, ?)
        ''', (date_str, program_name, created_by, program_notes, exercises_json))
        
        conn.commit()
        conn.close()
        return f"✅ Created program '{program_name}' for {date_str}"
    
    def get_daily_program(self, date_str):
        """Get the daily program for a specific date"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM daily_programs WHERE date = ?', (date_str,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'id': result[0],
                'date': result[1],
                'program_name': result[2],
                'created_by': result[3],
                'program_notes': result[4],
                'exercises': json.loads(result[5]),
                'created_at': result[6]
            }
        return None
    
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
            return f"✅ Template '{template_name}' saved successfully!"
        except sqlite3.IntegrityError:
            conn.close()
            return f"❌ Template '{template_name}' already exists!"

    def get_templates(self, category=None, created_by=None):
        """Get workout templates with optional filtering"""
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
        
        query += ' ORDER BY last_used DESC, created_at DESC'
        
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

    def load_template(self, template_id):
        """Load a specific template and update last_used"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('UPDATE workout_templates SET last_used = CURRENT_TIMESTAMP WHERE id = ?', (template_id,))
        
        cursor.execute('SELECT * FROM workout_templates WHERE id = ?', (template_id,))
        template = cursor.fetchone()
        conn.commit()
        conn.close()
        
        if template:
            return {
                'id': template[0],
                'name': template[1],
                'category': template[2],
                'description': template[3],
                'created_by': template[4],
                'exercises': json.loads(template[5]),
                'is_public': bool(template[6]),
                'created_at': template[7],
                'last_used': template[8]
            }
        return None

    def delete_template(self, template_id):
        """Delete a workout template"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM workout_templates WHERE id = ?', (template_id,))
        rows_affected = cursor.rowcount
        conn.commit()
        conn.close()
        
        if rows_affected > 0:
            return "✅ Template deleted successfully!"
        else:
            return "❌ Template not found!"

    def get_template_categories(self):
        """Get all unique template categories"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('SELECT DISTINCT category FROM workout_templates WHERE category IS NOT NULL ORDER BY category')
        categories = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        return categories
    
    def get_all_exercises(self):
        """Get all exercises including built-in and custom ones"""
        built_in_exercises = [
            'Hack Squat', 'Leg Press', 'Bench Press', 'Machine Shoulder Press',
            'RDL', 'Romanian Deadlift', 'Chest Supported Row', 'Bicep Curls', 
            'Tricep Pushdown', 'Chin Up', 'Pull-ups', 'Lying Hamstring Curl', 
            'Inclined Smith Machine Chest Press', 'Deadlift', 'Squat',
            'Overhead Press', 'Barbell Row', 'Dips', 'Incline Bench Press',
            'Front Squat', 'Military Press', 'Lat Pulldown', 'Leg Extension',
            'Calf Raises', 'Lateral Raises', 'Face Pulls', 'Hip Thrusts',
            'Bulgarian Split Squats', 'Walking Lunges', 'Hammer Curls',
            'Close Grip Bench Press', 'Wide Grip Pulldown', 'T-Bar Row'
        ]
        
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('SELECT exercise_name FROM custom_exercises ORDER BY exercise_name')
        custom_exercises = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        all_exercises = built_in_exercises + custom_exercises
        return sorted(list(set(all_exercises)))
    
    def get_custom_exercises(self):
        """Get all custom exercises with details"""
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
    
    def get_exercise_list(self):
        """Get list of exercises that have been logged"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT DISTINCT exercise FROM workouts ORDER BY exercise')
            exercises = [row[0] for row in cursor.fetchall()]
            conn.close()
            return exercises
        except:
            conn.close()
            return []
    
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
    
    def get_exercise_body_part(self, exercise):
        """Map exercise to body part based on exercise science"""
        exercise_body_parts = {
            'Bench Press': 'Chest',
            'Incline Bench Press': 'Chest',
            'Inclined Smith Machine Chest Press': 'Chest',
            'Dips': 'Chest',
            'Close Grip Bench Press': 'Triceps',
            'Deadlift': 'Back',
            'Barbell Row': 'Back',
            'Chest Supported Row': 'Back',
            'T-Bar Row': 'Back',
            'Lat Pulldown': 'Back',
            'Wide Grip Pulldown': 'Back',
            'Pull-ups': 'Back',
            'Chin Up': 'Back',
            'Face Pulls': 'Back',
            'Squat': 'Quadriceps',
            'Front Squat': 'Quadriceps',
            'Hack Squat': 'Quadriceps',
            'Leg Press': 'Quadriceps',
            'Leg Extension': 'Quadriceps',
            'Bulgarian Split Squats': 'Quadriceps',
            'Walking Lunges': 'Quadriceps',
            'RDL': 'Hamstrings',
            'Romanian Deadlift': 'Hamstrings',
            'Lying Hamstring Curl': 'Hamstrings',
            'Hip Thrusts': 'Glutes',
            'Overhead Press': 'Shoulders',
            'Military Press': 'Shoulders',
            'Machine Shoulder Press': 'Shoulders',
            'Lateral Raises': 'Shoulders',
            'Bicep Curls': 'Biceps',
            'Hammer Curls': 'Biceps',
            'Tricep Pushdown': 'Triceps',
            'Calf Raises': 'Calves'
        }
        
        return exercise_body_parts.get(exercise, 'Other')
    
    def get_weekly_body_part_volume(self, start_date, end_date):
        """Get weekly body part training volume"""
        df = self.get_data()
        if df.empty:
            return pd.DataFrame()
        
        df['date'] = pd.to_datetime(df['date'])
        week_data = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
        
        if week_data.empty:
            return pd.DataFrame()
        
        week_data['body_part'] = week_data['exercise'].apply(self.get_exercise_body_part)
        
        body_part_stats = week_data.groupby('body_part').agg({
            'set_number': 'count',
            'reps': 'sum',
            'weight': lambda x: (week_data.loc[x.index, 'reps'] * x).sum()
        }).round(2)
        
        body_part_stats.columns = ['total_sets', 'total_reps', 'total_volume']
        body_part_stats = body_part_stats.sort_values('total_sets', ascending=False)
        
        return body_part_stats

# ===== STREAMLIT APP SETUP =====
st.set_page_config(
    page_title="💪 Gym Tracker",
    page_icon="💪",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    .stApp {
        background-color: #000000;
        color: #ffffff;
    }
    
    .main-header {
        font-size: 2rem;
        font-weight: bold;
        text-align: center;
        color: #ffffff;
        margin-bottom: 1rem;
        padding: 1rem;
        background-color: #333333;
        border-radius: 8px;
    }
    
    .stButton > button {
        width: 100% !important;
        height: 3rem !important;
        font-size: 1rem !important;
        font-weight: bold !important;
        border-radius: 6px !important;
        border: 2px solid #ffffff !important;
        background-color: #333333 !important;
        color: #ffffff !important;
        transition: all 0.2s ease !important;
    }
    
    .stButton > button:hover {
        background-color: #555555 !important;
    }
    
    .stButton > button[kind="primary"] {
        background-color: #0066cc !important;
        border: 2px solid #0066cc !important;
        color: #ffffff !important;
        font-size: 1.1rem !important;
        height: 3.5rem !important;
    }
    
    .stButton > button[kind="primary"]:hover {
        background-color: #0052a3 !important;
    }
    
    .date-header {
        background-color: #222222;
        color: #ffffff;
        padding: 1rem;
        border-radius: 6px;
        margin: 1rem 0;
        text-align: center;
        font-size: 1rem;
        font-weight: bold;
        border: 1px solid #444444;
    }
    
    .workout-card {
        background-color: #111111;
        padding: 1rem;
        border-radius: 6px;
        margin: 1rem 0;
        border: 1px solid #333333;
        color: #ffffff;
    }
    
    .program-card {
        background-color: #111111;
        padding: 1rem;
        border-radius: 6px;
        margin: 1rem 0;
        border: 1px solid #0066cc;
        color: #ffffff;
    }
    
    .stats-card {
        background-color: #222222;
        color: #ffffff;
        padding: 1rem;
        border-radius: 6px;
        text-align: center;
        margin: 0.5rem;
        font-size: 0.9rem;
        font-weight: bold;
        border: 1px solid #444444;
    }
    
    .set-item {
        background-color: #222222;
        padding: 0.75rem;
        border-radius: 4px;
        margin: 0.5rem 0;
        border-left: 3px solid #0066cc;
        color: #ffffff;
        font-size: 0.9rem;
    }
    
    .stSelectbox > div > div {
        font-size: 1rem !important;
        padding: 0.5rem !important;
        background-color: #222222 !important;
        color: #ffffff !important;
        border-radius: 4px !important;
        border: 2px solid #666666 !important;
    }
    
    .stNumberInput > div > div > input {
        font-size: 1rem !important;
        height: 2.5rem !important;
        background-color: #222222 !important;
        color: #ffffff !important;
        border-radius: 4px !important;
        border: 2px solid #666666 !important;
        text-align: center !important;
        font-weight: bold !important;
    }
    
    .stTextInput > div > div > input {
        font-size: 1rem !important;
        padding: 0.5rem !important;
        background-color: #222222 !important;
        color: #ffffff !important;
        border-radius: 4px !important;
        border: 2px solid #666666 !important;
    }
    
    .stTextArea > div > div > textarea {
        font-size: 1rem !important;
        padding: 0.5rem !important;
        background-color: #222222 !important;
        color: #ffffff !important;
        border-radius: 4px !important;
        border: 2px solid #666666 !important;
    }
    
    .stButton button[title*="Delete"], .stButton button[aria-label*="Delete"] {
        background-color: #cc0000 !important;
        color: #ffffff !important;
        font-size: 0.8rem !important;
        padding: 0.25rem !important;
        border-radius: 4px !important;
        border: 1px solid #cc0000 !important;
        height: 2rem !important;
    }
    
    .notes-section {
        background-color: #111111;
        padding: 0.75rem;
        border-radius: 4px;
        border-left: 3px solid #0066cc;
        margin: 0.5rem 0;
        color: #ffffff;
        font-size: 0.9rem;
        border: 1px solid #333333;
    }
    
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 2.5rem;
        font-size: 0.9rem;
        font-weight: bold;
        border-radius: 4px;
        background-color: #222222;
        color: #ffffff;
        border: 1px solid #444444;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: #0066cc !important;
        color: #ffffff !important;
        border: 1px solid #0066cc !important;
    }
    
    .stSuccess {
        background-color: #006600 !important;
        color: #ffffff !important;
        font-size: 1rem !important;
        padding: 1rem !important;
        border-radius: 4px !important;
        border: 1px solid #008800 !important;
    }
    
    .stError {
        background-color: #cc0000 !important;
        color: #ffffff !important;
        font-size: 1rem !important;
        padding: 1rem !important;
        border-radius: 4px !important;
        border: 1px solid #ff0000 !important;
    }
    
    .stWarning {
        background-color: #cc6600 !important;
        color: #ffffff !important;
        font-size: 1rem !important;
        padding: 1rem !important;
        border-radius: 4px !important;
        border: 1px solid #ff8800 !important;
    }
    
    .stInfo {
        background-color: #0066cc !important;
        color: #ffffff !important;
        font-size: 1rem !important;
        padding: 1rem !important;
        border-radius: 4px !important;
        border: 1px solid #0088ff !important;
    }
    
    .stForm {
        background-color: #111111;
        padding: 1rem;
        border-radius: 6px;
        border: 1px solid #333333;
        margin: 1rem 0;
    }
    
    @media (max-width: 768px) {
        .main-header {
            font-size: 1.5rem;
        }
        
        .stButton > button {
            height: 2.8rem !important;
            font-size: 0.9rem !important;
        }
        
        .stButton > button[kind="primary"] {
            height: 3.2rem !important;
            font-size: 1rem !important;
        }
    }
    
    .stProgress > div > div > div {
        background-color: #0066cc !important;
        border-radius: 2px !important;
        height: 0.5rem !important;
    }
    
    .streamlit-expanderHeader {
        background-color: #222222 !important;
        color: #ffffff !important;
        font-size: 1rem !important;
        font-weight: bold !important;
        border-radius: 4px !important;
        padding: 0.75rem !important;
        border: 1px solid #444444 !important;
    }
    
    [data-testid="metric-container"] {
        background-color: #222222;
        border-radius: 4px;
        padding: 0.75rem;
        border: 1px solid #444444;
    }
    
    [data-testid="metric-container"] label {
        color: #ffffff !important;
        font-size: 0.8rem !important;
        font-weight: bold !important;
    }
    
    [data-testid="metric-container"] div[data-testid="metric-value"] {
        color: #ffffff !important;
        font-size: 1.2rem !important;
        font-weight: bold !important;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'tracker' not in st.session_state:
    st.session_state.tracker = GymTracker()

if 'program_exercises' not in st.session_state:
    st.session_state.program_exercises = []

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

def create_sample_data():
    """Sample data disabled by default"""
    if st.session_state.get('sample_data_created', False):
        return
    
    df = st.session_state.tracker.get_data()
    
    if not df.empty:
        st.session_state.sample_data_created = True
        return
    
    if not st.session_state.get('user_wants_sample_data', False):
        st.session_state.sample_data_created = True
        return

def clean_old_sample_data():
    """Aggressively remove ALL sample data that shouldn't be there"""
    tracker = st.session_state.tracker
    
    df = tracker.get_data()
    
    if df.empty:
        return "No data to clean"
    
    sample_workout_notes = [
        "Great leg session! Gym was quiet, felt strong.",
        "Finished with leg press, good pump"
    ]
    
    sample_set_notes = [
        "Warm up set, felt good",
        "Working weight", 
        "Heavy set, good depth",
        "Full range of motion",
        "Slight fatigue"
    ]
    
    suspicious_rows = df[
        df['workout_notes'].isin(sample_workout_notes) | 
        df['set_notes'].isin(sample_set_notes) |
        ((df['exercise'] == 'Hack Squat') & (df['weight'].isin([80.0, 90.0, 100.0])) & (df['reps'].isin([12, 10, 8]))) |
        ((df['exercise'] == 'Leg Press') & (df['weight'].isin([150.0, 170.0])) & (df['reps'].isin([15, 12]))) |
        ((df['exercise'] == 'Hack Squat') & (df['rpe'] == 7) & (df['weight'] == 80.0)) |
        ((df['exercise'] == 'Hack Squat') & (df['rpe'] == 8) & (df['weight'] == 90.0)) |
        ((df['exercise'] == 'Hack Squat') & (df['rpe'] == 9) & (df['weight'] == 100.0)) |
        ((df['exercise'] == 'Leg Press') & (df['rpe'] == 7) & (df['weight'] == 150.0)) |
        ((df['exercise'] == 'Leg Press') & (df['rpe'] == 8) & (df['weight'] == 170.0))
    ]
    
    if suspicious_rows.empty:
        return "✅ No sample data found to clean"
    
    conn = sqlite3.connect(tracker.db_name)
    cursor = conn.cursor()
    
    deleted_count = 0
    for row_id in suspicious_rows['id'].values:
        cursor.execute('DELETE FROM workouts WHERE id = ?', (row_id,))
        deleted_count += 1
    
    conn.commit()
    conn.close()
    
    return f"✅ Removed {deleted_count} sample data entries - refresh the page!"

def nuclear_data_reset():
    """NUCLEAR OPTION: Clear ALL workout data (keep templates and exercises)"""
    tracker = st.session_state.tracker
    
    conn = sqlite3.connect(tracker.db_name)
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM workouts')
    
    conn.commit()
    conn.close()
    
    return "🚨 ALL WORKOUT DATA DELETED - Fresh start!"

def show_enhanced_success_animation():
    """Show clean success feedback"""
    st.success("✅ SET LOGGED SUCCESSFULLY!")
    time.sleep(0.3)
    st.balloons()

def todays_workout_page():
    """Today's workout with clean mobile layout"""
    st.header("🔥 Today's Workout")
    
    selected_date = st.date_input(
        "📅 Workout Date", 
        value=date.today(),
        help="Select the date for this workout"
    )
    
    if selected_date == date.today():
        st.markdown('<div class="date-header">🔥 <strong>TODAY\'S WORKOUT</strong><br>' + 
                   selected_date.strftime('%A, %B %d, %Y') + '</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="date-header">📅 <strong>WORKOUT REVIEW</strong><br>' + 
                   selected_date.strftime('%A, %B %d, %Y') + '</div>', unsafe_allow_html=True)
    
    date_str = selected_date.strftime('%Y-%m-%d')
    
    program = st.session_state.tracker.get_daily_program(date_str)
    
    if program:
        st.markdown(f'<div class="program-card">', unsafe_allow_html=True)
        st.subheader(f"📋 {program['program_name']}")
        
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**👨‍⚕️ Created by:** {program['created_by']}")
        with col2:
            st.write(f"**📅 Created:** {program['created_at'][:10]}")
        
        if program['program_notes']:
            st.markdown(f'<div class="notes-section"><strong>📝 Program Notes:</strong><br>{program["program_notes"]}</div>', unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        exercises = program['exercises']
        
        completed_exercises = []
        df = st.session_state.tracker.get_data()
        if not df.empty:
            today_data = df[df['date'] == date_str]
            completed_exercises = today_data['exercise'].unique().tolist()
        
        progress_percentage = (len(completed_exercises) / len(exercises)) * 100 if exercises else 0
        
        st.subheader(f"📈 Progress: {progress_percentage:.0f}% Complete")
        st.progress(progress_percentage / 100)
        
        if completed_exercises:
            col1, col2, col3 = st.columns(3)
            today_data = df[df['date'] == date_str]
            
            with col1:
                st.metric("💪 Exercises Done", len(completed_exercises))
            with col2:
                st.metric("🎯 Total Sets", len(today_data))
            with col3:
                total_volume = (today_data['reps'] * today_data['weight']).sum()
                st.metric("🏋️ Volume", f"{total_volume:,.0f} kg")
        
        for i, exercise_info in enumerate(exercises, 1):
            exercise_name = exercise_info['exercise']
            target_sets = exercise_info.get('sets', 3)
            target_reps = exercise_info.get('reps', 10)
            exercise_notes = exercise_info.get('notes', '')
            rest_time = exercise_info.get('rest', 90)
            
            is_completed = exercise_name in completed_exercises
            status_emoji = "✅" if is_completed else "🔥"
            
            with st.expander(f"{status_emoji} {exercise_name} - {target_sets}×{target_reps} (Rest: {rest_time}s)", expanded=not is_completed):
                
                last_workout = get_last_workout_for_exercise(exercise_name)
                
                if last_workout is not None:
                    st.markdown("**📚 Last Performance:**")
                    last_date = last_workout['date'].iloc[0].strftime('%Y-%m-%d')
                    st.markdown(f"*📅 {last_date}*")
                    
                    for _, row in last_workout.iterrows():
                        notes_text = f" - *{row['set_notes']}*" if row['set_notes'] else ""
                        rpe_color = "🟢" if row['rpe'] <= 7 else "🟡" if row['rpe'] <= 8 else "🔴"
                        st.markdown(f"**Set {row['set_number']}:** {row['reps']} reps @ {row['weight']}kg {rpe_color}RPE:{row['rpe']}{notes_text}")
                else:
                    st.markdown("**🆕 First time doing this exercise!**")
                
                if exercise_notes:
                    st.markdown(f'<div class="notes-section"><strong>💡 Exercise Notes:</strong> {exercise_notes}</div>', unsafe_allow_html=True)
                
                st.markdown("**🎯 Log Your Set:**")
                
                with st.form(f"log_{exercise_name.replace(' ', '_')}_{i}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        reps = st.number_input("🎯 Reps", min_value=1, max_value=50, value=target_reps, key=f"reps_{i}")
                    with col2:
                        weight = st.number_input("⚖️ Weight (kg)", min_value=0.0, value=0.0, step=0.625, key=f"weight_{i}")
                    
                    rpe = st.select_slider("💥 RPE", options=[6, 7, 8, 9, 10], value=8, key=f"rpe_{i}")
                    set_notes = st.text_input("📝 Notes", placeholder="Form, fatigue, equipment...", key=f"set_notes_{i}")
                    
                    if st.form_submit_button(f"🚀 LOG SET", use_container_width=True, type="primary"):
                        result = st.session_state.tracker.log_workout(
                            date_str, 
                            exercise_name, 
                            [{'reps': reps, 'weight': weight, 'rpe': rpe, 'set_notes': set_notes}], 
                            ""
                        )
                        show_enhanced_success_animation()
                        st.rerun()
    
    else:
        st.info("📋 No program set for today. Use 'Quick Log' for freestyle training or create a program!")
    
    st.subheader("📊 Today's Statistics")
    
    df = st.session_state.tracker.get_data()
    if not df.empty:
        today_data = df[df['date'] == date_str]
        
        if not today_data.empty:
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.markdown('<div class="stats-card">💪 <strong>Exercises</strong><br>' + 
                           str(len(today_data['exercise'].unique())) + '</div>', unsafe_allow_html=True)
            
            with col2:
                st.markdown('<div class="stats-card">🎯 <strong>Sets</strong><br>' + 
                           str(len(today_data)) + '</div>', unsafe_allow_html=True)
            
            with col3:
                volume = (today_data['reps'] * today_data['weight']).sum()
                st.markdown('<div class="stats-card">🏋️ <strong>Volume</strong><br>' + 
                           f'{volume:,.0f} kg</div>', unsafe_allow_html=True)
            
            with col4:
                st.markdown('<div class="stats-card">🔥 <strong>Total Reps</strong><br>' + 
                           str(today_data['reps'].sum()) + '</div>', unsafe_allow_html=True)
            
            avg_rpe = today_data['rpe'].mean() if today_data['rpe'].notna().any() else 0
            if avg_rpe > 0:
                st.subheader("🔥 Intensity")
                if avg_rpe <= 7:
                    st.success(f"🟢 Moderate - Average RPE: {avg_rpe:.1f}")
                elif avg_rpe <= 8.5:
                    st.warning(f"🟡 High - Average RPE: {avg_rpe:.1f}")
                else:
                    st.error(f"🔴 MAXIMUM - Average RPE: {avg_rpe:.1f}")

def enhanced_quick_log_page():
    """Clean mobile-optimized quick log"""
    st.header("⚡ Quick Log")
    
    log_date = st.date_input(
        "📅 Select Date", 
        value=date.today(),
        help="Choose the date for this workout"
    )
    
    if log_date == date.today():
        st.markdown('<div class="date-header">🔥 <strong>TODAY\'S QUICK LOG</strong><br>' + 
                   log_date.strftime('%A, %B %d, %Y') + '</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="date-header">📅 <strong>WORKOUT REVIEW</strong><br>' + 
                   log_date.strftime('%A, %B %d, %Y') + '</div>', unsafe_allow_html=True)
    
    date_str = log_date.strftime('%Y-%m-%d')
    all_exercises = st.session_state.tracker.get_all_exercises()
    
    st.subheader("🚀 Quick Exercise Buttons")
    
    col1, col2, col3 = st.columns(3)
    
    common_exercises = ['Bench Press', 'Squat', 'Deadlift', 'Hack Squat', 'Leg Press', 'Machine Shoulder Press']
    
    for i, exercise in enumerate(common_exercises[:3]):
        with col1 if i == 0 else col2 if i == 1 else col3:
            if st.button(f"💪 {exercise}", key=f"quick_{exercise}", use_container_width=True):
                st.session_state.last_exercise = exercise
                st.rerun()
    
    for i, exercise in enumerate(common_exercises[3:], 3):
        with col1 if i == 3 else col2 if i == 4 else col3:
            if st.button(f"💪 {exercise}", key=f"quick_{exercise}", use_container_width=True):
                st.session_state.last_exercise = exercise
                st.rerun()
    
    st.subheader("📝 Log Your Set")
    
    with st.form("quick_log", clear_on_submit=True):
        exercise_index = 0
        if st.session_state.last_exercise in all_exercises:
            exercise_index = all_exercises.index(st.session_state.last_exercise)
        
        exercise = st.selectbox("💪 Exercise", all_exercises, index=exercise_index)
        
        if exercise:
            last_workout = get_last_workout_for_exercise(exercise)
            if last_workout is not None:
                last_set = last_workout.iloc[-1]
                st.info(f"🔥 Last Performance: {last_set['reps']} reps @ {last_set['weight']}kg (RPE: {last_set['rpe']})")
        
        col1, col2 = st.columns(2)
        with col1:
            reps = st.number_input("🎯 Reps", min_value=1, max_value=50, value=st.session_state.last_reps)
        with col2:
            weight = st.number_input("⚖️ Weight (kg)", min_value=0.0, value=st.session_state.last_weight, step=0.625)
        
        rpe = st.select_slider("💥 RPE", options=[6, 7, 8, 9, 10], value=st.session_state.last_rpe)
        set_notes = st.text_input("📝 Notes", placeholder="How did that feel? Form notes, equipment, etc...")
        
        if st.form_submit_button("🚀 LOG SET", use_container_width=True, type="primary"):
            st.session_state.tracker.quick_log(exercise, reps, weight, rpe, set_notes, "", date_str)
            
            st.session_state.last_exercise = exercise
            st.session_state.last_reps = reps
            st.session_state.last_weight = weight
            st.session_state.last_rpe = rpe
            
            show_enhanced_success_animation()
            st.rerun()
    
    st.subheader("📋 Today's Complete Workout")
    
    daily_workout = st.session_state.tracker.get_daily_workout(date_str)
    
    if not daily_workout.empty:
        exercises_done = daily_workout['exercise'].unique()
        
        for exercise in exercises_done:
            exercise_sets = daily_workout[daily_workout['exercise'] == exercise]
            
            total_volume = (exercise_sets['reps'] * exercise_sets['weight']).sum()
            max_weight = exercise_sets['weight'].max()
            avg_rpe = exercise_sets['rpe'].mean()
            
            st.markdown(f'<div class="workout-card">', unsafe_allow_html=True)
            st.markdown(f"**🏋️ {exercise}** ({len(exercise_sets)} sets)")
            st.markdown(f"**📊 Stats:** {total_volume:.0f}kg volume • {max_weight}kg max • {avg_rpe:.1f} avg RPE")
            
            for _, set_row in exercise_sets.iterrows():
                col1, col2 = st.columns([4, 1])
                
                with col1:
                    notes_display = f" - *{set_row['set_notes']}*" if set_row['set_notes'] else ""
                    rpe_emoji = "🟢" if set_row['rpe'] <= 7 else "🟡" if set_row['rpe'] <= 8 else "🔴"
                    st.markdown(f'<div class="set-item">**Set {set_row["set_number"]}:** {set_row["reps"]} reps @ {set_row["weight"]}kg {rpe_emoji}RPE:{set_row["rpe"]}{notes_display}</div>', 
                               unsafe_allow_html=True)
                
                with col2:
                    if st.button("🗑️", key=f"delete_{set_row['id']}", help="Delete this set"):
                        if st.session_state.get('confirm_delete_set') == set_row['id']:
                            result = st.session_state.tracker.delete_set(set_row['id'])
                            st.success(result)
                            st.session_state.pop('confirm_delete_set', None)
                            st.rerun()
                        else:
                            st.session_state.confirm_delete_set = set_row['id']
                            st.warning("⚠️ Tap again to confirm deletion")
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        total_sets = len(daily_workout)
        total_reps = daily_workout['reps'].sum()
        total_volume = (daily_workout['reps'] * daily_workout['weight']).sum()
        avg_rpe = daily_workout['rpe'].mean() if daily_workout['rpe'].notna().any() else 0
        
        st.subheader("📊 Daily Summary")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown('<div class="stats-card">💪 <strong>Exercises</strong><br>' + 
                       str(len(exercises_done)) + '</div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown('<div class="stats-card">🎯 <strong>Sets</strong><br>' + 
                       str(total_sets) + '</div>', unsafe_allow_html=True)
        
        with col3:
            st.markdown('<div class="stats-card">🏋️ <strong>Volume</strong><br>' + 
                       f'{total_volume:,.0f} kg</div>', unsafe_allow_html=True)
        
        with col4:
            st.markdown('<div class="stats-card">🔥 <strong>Reps</strong><br>' + 
                       str(total_reps) + '</div>', unsafe_allow_html=True)
        
        if avg_rpe > 0:
            st.subheader("🔥 Intensity Analysis")
            intensity_col1, intensity_col2 = st.columns(2)
            
            with intensity_col1:
                if avg_rpe <= 7:
                    st.success(f"🟢 Moderate - {avg_rpe:.1f} avg RPE")
                elif avg_rpe <= 8.5:
                    st.warning(f"🟡 High - {avg_rpe:.1f} avg RPE")
                else:
                    st.error(f"🔴 MAXIMUM - {avg_rpe:.1f} avg RPE")
            
            with intensity_col2:
                rpe_counts = daily_workout['rpe'].value_counts().sort_index()
                for rpe_val, count in rpe_counts.items():
                    emoji = "🟢" if rpe_val <= 7 else "🟡" if rpe_val <= 8 else "🔴"
                    st.write(f"{emoji} RPE {rpe_val}: {count} sets")
    
    else:
        st.info("💡 No exercises logged yet today. Time to get started! 🔥")

def visual_progress_page():
    """Simple progress page"""
    st.header("📈 Progress")
    
    df = st.session_state.tracker.get_data()
    
    if df.empty:
        st.warning("No workout data yet. Start logging to see progress! 🚀")
        return
    
    all_exercises = st.session_state.tracker.get_all_exercises()
    available_exercises = [ex for ex in all_exercises if ex in df['exercise'].unique()]
    
    if not available_exercises:
        st.warning("No exercises with logged data yet.")
        return
    
    selected_exercise = st.selectbox("🏋️ Choose Exercise", available_exercises)
    
    stats = st.session_state.tracker.get_exercise_stats(selected_exercise)
    
    if not stats:
        return
    
    st.subheader(f"📊 {selected_exercise} - Statistics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f'<div class="stats-card">🏆 <strong>Max Weight</strong><br>{stats["max_weight"]} kg</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown(f'<div class="stats-card">🎯 <strong>Total Sets</strong><br>{stats["total_sets"]}</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown(f'<div class="stats-card">📦 <strong>Total Volume</strong><br>{stats["total_volume"]:,.0f} kg</div>', unsafe_allow_html=True)
    
    with col4:
        st.markdown(f'<div class="stats-card">💥 <strong>Avg RPE</strong><br>{stats["avg_rpe"]:.1f}</div>', unsafe_allow_html=True)
    
    st.subheader("📈 Weight Progress")
    
    daily_stats = stats['daily_stats']
    
    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(
        x=daily_stats['date'], 
        y=daily_stats['max_weight'],
        mode='lines+markers',
        name='Max Weight',
        line=dict(color='#0066cc', width=3),
        marker=dict(size=8, color='#0066cc')
    ))
    
    fig1.update_layout(
        title=f'{selected_exercise} - Weight Progression',
        xaxis_title='Date',
        yaxis_title='Weight (kg)',
        height=400,
        paper_bgcolor='#000000',
        plot_bgcolor='#111111',
        font=dict(color='white', size=12),
        xaxis=dict(gridcolor='#333333'),
        yaxis=dict(gridcolor='#333333')
    )
    st.plotly_chart(fig1, use_container_width=True)

def program_creator_page():
    """Simple program creator"""
    st.header("📅 Program Creator")
    
    template_tab, create_tab = st.tabs(["📚 Templates", "🆕 Create"])
    
    with template_tab:
        st.subheader("📚 Your Templates")
        
        templates = st.session_state.tracker.get_templates()
        
        if templates:
            for template in templates:
                with st.expander(f"📋 {template['name']}", expanded=False):
                    st.write(f"**Creator:** {template['created_by']}")
                    st.write(f"**Created:** {template['created_at'][:10]}")
                    
                    if template['description']:
                        st.markdown(f'<div class="notes-section">{template["description"]}</div>', unsafe_allow_html=True)
                    
                    st.write("**Exercises:**")
                    for i, ex in enumerate(template['exercises'], 1):
                        st.write(f"{i}. **{ex['exercise']}** - {ex['sets']}×{ex['reps']}")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        if st.button(f"📅 Use", key=f"use_{template['id']}", use_container_width=True):
                            st.session_state.program_exercises = template['exercises'].copy()
                            st.success(f"✅ Loaded: {template['name']}")
                            st.rerun()
                    
                    with col2:
                        if st.button(f"🗑️ Delete", key=f"del_{template['id']}", use_container_width=True):
                            if st.session_state.get('confirm_delete') == template['id']:
                                result = st.session_state.tracker.delete_template(template['id'])
                                st.success(result)
                                st.session_state.pop('confirm_delete', None)
                                st.rerun()
                            else:
                                st.session_state.confirm_delete = template['id']
                                st.warning("⚠️ Tap again to confirm")
        else:
            st.info("📋 No templates found. Create your first one!")
    
    with create_tab:
        st.subheader("🆕 Create Program")
        
        program_date = st.date_input("📅 Program Date", value=date.today())
        program_name = st.text_input("Program Name", value=f"Training - {date.today().strftime('%b %d')}")
        
        col1, col2 = st.columns(2)
        with col1:
            template_category = st.selectbox("Category", ["Upper Body", "Lower Body", "Full Body", "Custom"])
        with col2:
            created_by = st.selectbox("Created By", ["Personal Trainer", "Myself"])
        
        program_notes = st.text_area("Description", placeholder="Session goals, focus areas...")
        save_as_template = st.checkbox("💾 Save as Template", value=True)
        
        st.write("**Quick Templates:**")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("💪 Upper Body", use_container_width=True):
                st.session_state.program_exercises = [
                    {'exercise': 'Bench Press', 'sets': 4, 'reps': 6, 'rest': 120},
                    {'exercise': 'Machine Shoulder Press', 'sets': 3, 'reps': 10, 'rest': 90},
                    {'exercise': 'Chest Supported Row', 'sets': 3, 'reps': 10, 'rest': 90}
                ]
                st.rerun()
        
        with col2:
            if st.button("🦵 Lower Body", use_container_width=True):
                st.session_state.program_exercises = [
                    {'exercise': 'Hack Squat', 'sets': 4, 'reps': 8, 'rest': 120},
                    {'exercise': 'RDL', 'sets': 3, 'reps': 10, 'rest': 90},
                    {'exercise': 'Leg Press', 'sets': 3, 'reps': 15, 'rest': 90}
                ]
                st.rerun()
        
        with col3:
            if st.button("🔄 Full Body", use_container_width=True):
                st.session_state.program_exercises = [
                    {'exercise': 'Squat', 'sets': 3, 'reps': 10, 'rest': 120},
                    {'exercise': 'Bench Press', 'sets': 3, 'reps': 8, 'rest': 120},
                    {'exercise': 'Deadlift', 'sets': 3, 'reps': 5, 'rest': 150}
                ]
                st.rerun()
        
        st.subheader("🏋️ Add Exercises")
        
        with st.expander("➕ Add Exercise", expanded=True):
            all_exercises = st.session_state.tracker.get_all_exercises()
            
            exercise_name = st.selectbox("Exercise", all_exercises)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                sets = st.number_input("Sets", min_value=1, max_value=10, value=3)
            with col2:
                reps = st.number_input("Reps", min_value=1, max_value=50, value=10)
            with col3:
                rest_time = st.number_input("Rest (sec)", min_value=30, max_value=300, value=90, step=15)
            
            if st.button("➕ Add Exercise", use_container_width=True, type="primary"):
                new_exercise = {
                    'exercise': exercise_name,
                    'sets': sets,
                    'reps': reps,
                    'rest': rest_time
                }
                st.session_state.program_exercises.append(new_exercise)
                st.success(f"✅ Added {exercise_name}")
                st.rerun()
        
        if st.session_state.program_exercises:
            st.subheader("📋 Current Program")
            
            st.markdown('<div class="program-card">', unsafe_allow_html=True)
            
            for i, ex in enumerate(st.session_state.program_exercises):
                col1, col2 = st.columns([5, 1])
                
                with col1:
                    st.write(f"**{i+1}. {ex['exercise']}** - {ex['sets']}×{ex['reps']} (Rest: {ex.get('rest', 90)}s)")
                
                with col2:
                    if st.button("🗑️", key=f"remove_{i}", help="Remove"):
                        st.session_state.program_exercises.pop(i)
                        st.rerun()
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("💾 Save Program", use_container_width=True):
                    if program_name and st.session_state.program_exercises:
                        date_str = program_date.strftime('%Y-%m-%d')
                        result = st.session_state.tracker.create_daily_program(
                            date_str, program_name, created_by, program_notes, st.session_state.program_exercises
                        )
                        st.success(result)
                        
                        if save_as_template:
                            template_result = st.session_state.tracker.save_template(
                                program_name, template_category, program_notes, created_by, 
                                st.session_state.program_exercises
                            )
                            st.success(template_result)
                        
                        st.balloons()
                        st.session_state.program_exercises = []
                        st.rerun()
                    else:
                        st.error("❌ Enter name and add exercises")
            
            with col2:
                if st.button("🗑️ Clear All", use_container_width=True):
                    st.session_state.program_exercises = []
                    st.rerun()

def add_exercises_page():
    """Simple add exercises page"""
    st.header("➕ Exercise Manager")
    
    st.subheader("🆕 Create Exercise")
    
    with st.form("add_exercise_form", clear_on_submit=True):
        exercise_name = st.text_input("Exercise Name", placeholder="e.g., Cable Crossover")
        
        col1, col2 = st.columns(2)
        with col1:
            category = st.selectbox("Category", ["Chest", "Back", "Shoulders", "Arms", "Legs", "Core", "Other"])
        with col2:
            description = st.text_area("Description", placeholder="Setup, form cues...")
        
        if st.form_submit_button("➕ Create Exercise", use_container_width=True, type="primary"):
            if exercise_name.strip():
                result = st.session_state.tracker.add_custom_exercise(
                    exercise_name.strip(), category, description.strip()
                )
                if "Successfully added" in result:
                    st.success(result)
                    st.balloons()
                else:
                    st.error(result)
                st.rerun()
            else:
                st.error("❌ Please enter an exercise name!")
    
    st.subheader("🌟 Your Custom Exercises")
    
    custom_exercises_df = st.session_state.tracker.get_custom_exercises()
    
    if not custom_exercises_df.empty:
        for category in custom_exercises_df['category'].unique():
            st.markdown(f'<div class="workout-card">', unsafe_allow_html=True)
            st.write(f"**📂 {category} Exercises**")
            
            category_exercises = custom_exercises_df[custom_exercises_df['category'] == category]
            
            for _, exercise in category_exercises.iterrows():
                st.write(f"**🌟 {exercise['exercise_name']}**")
                if exercise['description']:
                    st.write(f"💡 *{exercise['description']}*")
                st.write(f"📅 *Added: {exercise['created_at'][:10]}*")
                st.write("---")
            
            st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("🎯 No custom exercises yet. Create your first one!")

def data_manager_page():
    """Clean data manager with cleaning tools"""
    st.header("💾 Data Manager")
    
    st.subheader("📊 Your Data Overview")
    
    df = st.session_state.tracker.get_data()
    templates = st.session_state.tracker.get_templates()
    custom_exercises = st.session_state.tracker.get_custom_exercises()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        workout_count = len(df) if not df.empty else 0
        st.markdown(f'<div class="stats-card">🏋️ <strong>Total Sets</strong><br>{workout_count:,}</div>', unsafe_allow_html=True)
    
    with col2:
        exercise_count = len(df['exercise'].unique()) if not df.empty else 0
        st.markdown(f'<div class="stats-card">📝 <strong>Exercises</strong><br>{exercise_count}</div>', unsafe_allow_html=True)
    
    with col3:
        template_count = len(templates)
        st.markdown(f'<div class="stats-card">📋 <strong>Templates</strong><br>{template_count}</div>', unsafe_allow_html=True)
    
    with col4:
        custom_count = len(custom_exercises) if not custom_exercises.empty else 0
        st.markdown(f'<div class="stats-card">⭐ <strong>Custom</strong><br>{custom_count}</div>', unsafe_allow_html=True)
    
    st.subheader("🧹 Data Cleaning & Management")
    
    st.markdown('<div class="program-card">', unsafe_allow_html=True)
    st.write("**🧹 Remove Sample Data**")
    st.write("If you see fake workouts (Hack Squats with 'Warm up set, felt good' notes), remove them:")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🧹 Clean Sample Data", use_container_width=True):
            result = clean_old_sample_data()
            if "✅" in result:
                st.success(result)
                time.sleep(1)
                st.rerun()
            else:
                st.info(result)
    
    with col2:
        if st.button("🚨 RESET ALL DATA", use_container_width=True):
            if st.session_state.get('confirm_nuclear', False):
                result = nuclear_data_reset()
                st.error(result)
                st.session_state.pop('confirm_nuclear', None)
                time.sleep(1)
                st.rerun()
            else:
                st.session_state.confirm_nuclear = True
                st.warning("⚠️ Tap again to DELETE ALL workout data!")
    
    if st.button("🔍 Show Current Data (Debug)", use_container_width=True):
        if not df.empty:
            st.subheader("🔍 Current Workout Data")
            
            recent_data = df.head(10)[['date', 'exercise', 'reps', 'weight', 'rpe', 'set_notes', 'workout_notes']]
            st.dataframe(recent_data, use_container_width=True)
            
            suspicious_notes = df[
                df['set_notes'].str.contains('Warm up set|Working weight|Heavy set', case=False, na=False) |
                df['workout_notes'].str.contains('Great leg session|Finished with leg press', case=False, na=False)
            ]
            
            if not suspicious_notes.empty:
                st.warning(f"🚨 Found {len(suspicious_notes)} suspicious sample data entries:")
                st.dataframe(suspicious_notes[['exercise', 'reps', 'weight', 'set_notes', 'workout_notes']], use_container_width=True)
            else:
                st.success("✅ No obvious sample data detected!")
        else:
            st.info("📊 No workout data found")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    if not df.empty:
        st.subheader("📊 Analytics")
        
        total_volume = (df['reps'] * df['weight']).sum()
        total_days = len(df['date'].unique())
        avg_rpe = df['rpe'].mean() if df['rpe'].notna().any() else 0
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown(f'<div class="stats-card">🏋️ <strong>Total Volume</strong><br>{total_volume:,.0f} kg</div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown(f'<div class="stats-card">📅 <strong>Training Days</strong><br>{total_days}</div>', unsafe_allow_html=True)
        
        with col3:
            if avg_rpe > 0:
                st.markdown(f'<div class="stats-card">💥 <strong>Avg RPE</strong><br>{avg_rpe:.1f}</div>', unsafe_allow_html=True)
    
    st.subheader("💾 Backup & Restore")
    
    st.markdown(f'<div class="program-card">', unsafe_allow_html=True)
    st.write("**📤 Export Your Data**")
    
    export_filename = st.text_input("Backup filename", value=f"gym_backup_{date.today().strftime('%Y%m%d')}.json")
    
    if st.button("📤 Export Data", use_container_width=True):
        result = st.session_state.tracker.export_data(export_filename)
        if "✅" in result:
            st.success(result)
            st.balloons()
        else:
            st.error(result)
    
    st.write("---")
    st.write("**📥 Import Data**")
    
    import_filename = st.text_input("Import filename", value="gym_backup.json")
    
    if st.button("📥 Import Data", use_container_width=True):
        result = st.session_state.tracker.import_data(import_filename)
        if "✅" in result:
            st.success(result)
            st.balloons()
            st.rerun()
        else:
            st.error(result)
    
    st.markdown('</div>', unsafe_allow_html=True)

def main():
    st.markdown('<h1 class="main-header">💪 Gym Tracker</h1>', unsafe_allow_html=True)
    
    st.success("✅ **CLEAN & OPTIMIZED!** High contrast design, aggressive data cleaning, super readable!")
    
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "🔥 Today", 
        "⚡ Quick Log", 
        "📈 Progress", 
        "📋 Programs",
        "➕ Exercises",
        "💾 Data"
    ])
    
    with tab1:
        todays_workout_page()
    
    with tab2:
        enhanced_quick_log_page()
    
    with tab3:
        visual_progress_page()
    
    with tab4:
        program_creator_page()
    
    with tab5:
        add_exercises_page()
    
    with tab6:
        data_manager_page()

if 'sample_data_created' not in st.session_state:
    st.session_state.sample_data_created = True

if __name__ == "__main__":
    main()
