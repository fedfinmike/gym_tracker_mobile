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

# ===== MOBILE-OPTIMIZED GYM TRACKER V7 - ENHANCED =====
class GymTracker:
    def __init__(self, db_name='gym_tracker_MASTER.db'):
        """Initialize Gym Tracker - MASTER database for all future versions"""
        self.db_name = db_name
        self.init_database()
        self.migrate_old_data()  # Migrate data from ALL previous versions
        
    def migrate_old_data(self):
        """Migrate data from ALL previous versions based on your file history"""
        import os
        
        # COMPLETE list of ALL your old database names from the file history
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
        
        # Only migrate if current database is empty
        if not current_data.empty:
            return
        
        st.info("🔍 Checking for data from previous versions...")
        
        for old_db in old_db_names:
            if os.path.exists(old_db) and old_db != self.db_name:
                try:
                    # Connect to old database
                    old_conn = sqlite3.connect(old_db)
                    cursor = old_conn.cursor()
                    
                    # Check what tables exist in this old database
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                    tables = [row[0] for row in cursor.fetchall()]
                    
                    # Migrate workouts table
                    if 'workouts' in tables:
                        old_df = pd.read_sql_query('SELECT * FROM workouts', old_conn)
                        
                        if not old_df.empty:
                            # Migrate to new database
                            new_conn = sqlite3.connect(self.db_name)
                            old_df.to_sql('workouts', new_conn, if_exists='append', index=False)
                            new_conn.close()
                            
                            st.success(f"✅ Migrated {len(old_df)} workout records from {old_db}")
                            migrated_any = True
                    
                    # Migrate templates table
                    if 'workout_templates' in tables:
                        old_templates = pd.read_sql_query('SELECT * FROM workout_templates', old_conn)
                        if not old_templates.empty:
                            new_conn = sqlite3.connect(self.db_name)
                            old_templates.to_sql('workout_templates', new_conn, if_exists='append', index=False)
                            new_conn.close()
                            st.success(f"✅ Migrated {len(old_templates)} templates from {old_db}")
                    
                    # Migrate custom exercises table
                    if 'custom_exercises' in tables:
                        old_exercises = pd.read_sql_query('SELECT * FROM custom_exercises', old_conn)
                        if not old_exercises.empty:
                            new_conn = sqlite3.connect(self.db_name)
                            old_exercises.to_sql('custom_exercises', new_conn, if_exists='append', index=False)
                            new_conn.close()
                            st.success(f"✅ Migrated {len(old_exercises)} custom exercises from {old_db}")
                    
                    # Migrate daily programs table
                    if 'daily_programs' in tables:
                        old_programs = pd.read_sql_query('SELECT * FROM daily_programs', old_conn)
                        if not old_programs.empty:
                            new_conn = sqlite3.connect(self.db_name)
                            old_programs.to_sql('daily_programs', new_conn, if_exists='append', index=False)
                            new_conn.close()
                            st.success(f"✅ Migrated {len(old_programs)} programs from {old_db}")
                    
                    old_conn.close()
                    
                    # If we found data in this database, we're done
                    if migrated_any:
                        st.balloons()
                        st.success(f"🎉 All your workout history has been preserved from {old_db}!")
                        break
                        
                except Exception as e:
                    st.warning(f"⚠️ Could not migrate from {old_db}: {str(e)}")
                    continue
        
        if not migrated_any:
            st.info("📊 Starting fresh - no previous data found to migrate")
    
    # Data Export/Import Functions
    def export_data(self, export_file='gym_tracker_backup.json'):
        """Export all data to JSON file for backup"""
        try:
            export_data = {}
            
            # Export workouts
            workouts_df = self.get_data()
            if not workouts_df.empty:
                workouts_df['date'] = workouts_df['date'].dt.strftime('%Y-%m-%d')
                export_data['workouts'] = workouts_df.to_dict('records')
            
            # Export templates
            templates = self.get_templates()
            if templates:
                export_data['templates'] = templates
            
            # Export custom exercises
            custom_exercises = self.get_custom_exercises()
            if not custom_exercises.empty:
                export_data['custom_exercises'] = custom_exercises.to_dict('records')
            
            # Export daily programs
            conn = sqlite3.connect(self.db_name)
            try:
                programs_df = pd.read_sql_query('SELECT * FROM daily_programs', conn)
                if not programs_df.empty:
                    export_data['daily_programs'] = programs_df.to_dict('records')
            except:
                pass
            conn.close()
            
            # Save to file
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
            
            # Import workouts
            if 'workouts' in import_data:
                workouts_df = pd.DataFrame(import_data['workouts'])
                workouts_df.to_sql('workouts', conn, if_exists='append', index=False)
                imported_items.append(f"{len(workouts_df)} workouts")
            
            # Import templates
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
            
            # Import custom exercises
            if 'custom_exercises' in import_data:
                exercises_df = pd.DataFrame(import_data['custom_exercises'])
                exercises_df.to_sql('custom_exercises', conn, if_exists='append', index=False)
                imported_items.append(f"{len(exercises_df)} custom exercises")
            
            # Import daily programs
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
        
        # Main workouts table with enhanced notes
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
        
        # Custom exercises table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS custom_exercises (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                exercise_name TEXT UNIQUE NOT NULL,
                category TEXT,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Daily workout programs table
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
        
        # Custom Templates table
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
    
    # Delete individual sets
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
    
    # Get full day's workout with set IDs for deletion
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
        
        # Delete existing program for this date
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
    
    # Template Management Methods
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
        
        # Update last_used timestamp
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
        
        # Calculate various metrics
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
    
    # Body part mapping for exercises
    def get_exercise_body_part(self, exercise):
        """Map exercise to body part based on exercise science"""
        exercise_body_parts = {
            # Chest
            'Bench Press': 'Chest',
            'Incline Bench Press': 'Chest',
            'Inclined Smith Machine Chest Press': 'Chest',
            'Dips': 'Chest',
            'Close Grip Bench Press': 'Triceps',
            
            # Back
            'Deadlift': 'Back',
            'Barbell Row': 'Back',
            'Chest Supported Row': 'Back',
            'T-Bar Row': 'Back',
            'Lat Pulldown': 'Back',
            'Wide Grip Pulldown': 'Back',
            'Pull-ups': 'Back',
            'Chin Up': 'Back',
            'Face Pulls': 'Back',
            
            # Legs - Quads
            'Squat': 'Quadriceps',
            'Front Squat': 'Quadriceps',
            'Hack Squat': 'Quadriceps',
            'Leg Press': 'Quadriceps',
            'Leg Extension': 'Quadriceps',
            'Bulgarian Split Squats': 'Quadriceps',
            'Walking Lunges': 'Quadriceps',
            
            # Legs - Hamstrings/Glutes
            'RDL': 'Hamstrings',
            'Romanian Deadlift': 'Hamstrings',
            'Lying Hamstring Curl': 'Hamstrings',
            'Hip Thrusts': 'Glutes',
            
            # Shoulders
            'Overhead Press': 'Shoulders',
            'Military Press': 'Shoulders',
            'Machine Shoulder Press': 'Shoulders',
            'Lateral Raises': 'Shoulders',
            
            # Arms - Biceps
            'Bicep Curls': 'Biceps',
            'Hammer Curls': 'Biceps',
            
            # Arms - Triceps
            'Tricep Pushdown': 'Triceps',
            
            # Calves
            'Calf Raises': 'Calves'
        }
        
        return exercise_body_parts.get(exercise, 'Other')
    
    def get_weekly_body_part_volume(self, start_date, end_date):
        """Get weekly body part training volume"""
        df = self.get_data()
        if df.empty:
            return pd.DataFrame()
        
        # Filter by date range
        df['date'] = pd.to_datetime(df['date'])
        week_data = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
        
        if week_data.empty:
            return pd.DataFrame()
        
        # Add body parts
        week_data['body_part'] = week_data['exercise'].apply(self.get_exercise_body_part)
        
        # Calculate volume by body part
        body_part_stats = week_data.groupby('body_part').agg({
            'set_number': 'count',  # Total sets
            'reps': 'sum',          # Total reps
            'weight': lambda x: (week_data.loc[x.index, 'reps'] * x).sum()  # Total volume
        }).round(2)
        
        body_part_stats.columns = ['total_sets', 'total_reps', 'total_volume']
        body_part_stats = body_part_stats.sort_values('total_sets', ascending=False)
        
        return body_part_stats

# ===== ENHANCED MOBILE-OPTIMIZED STREAMLIT APP =====
st.set_page_config(
    page_title="🏋️ Beast Mode Gym Tracker",
    page_icon="💪",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 🎨 ULTRA-CLEAN MOBILE CSS - High Contrast & Simple
st.markdown("""
<style>
    /* Ultra-clean dark theme */
    .stApp {
        background-color: #000000;
        color: #ffffff;
    }
    
    /* Simple, readable header */
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
    
    /* Ultra-clean buttons */
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
    
    /* Primary button - simple blue */
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
    
    /* Simple date header */
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
    
    /* Ultra-clean cards */
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
    
    /* High contrast stats cards */
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
    
    /* Ultra-readable set items */
    .set-item {
        background-color: #222222;
        padding: 0.75rem;
        border-radius: 4px;
        margin: 0.5rem 0;
        border-left: 3px solid #0066cc;
        color: #ffffff;
        font-size: 0.9rem;
    }
    
    /* High contrast inputs */
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
    
    /* Simple delete buttons */
    .stButton button[title*="Delete"], .stButton button[aria-label*="Delete"] {
        background-color: #cc0000 !important;
        color: #ffffff !important;
        font-size: 0.8rem !important;
        padding: 0.25rem !important;
        border-radius: 4px !important;
        border: 1px solid #cc0000 !important;
        height: 2rem !important;
    }
    
    /* Simple notes section */
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
    
    /* Ultra-clean tabs */
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
    
    /* High contrast messages */
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
    
    /* Simple form styling */
    .stForm {
        background-color: #111111;
        padding: 1rem;
        border-radius: 6px;
        border: 1px solid #333333;
        margin: 1rem 0;
    }
    
    /* Mobile responsive */
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
    
    /* Simple progress bars */
    .stProgress > div > div > div {
        background-color: #0066cc !important;
        border-radius: 2px !important;
        height: 0.5rem !important;
    }
    
    /* Simple expander */
    .streamlit-expanderHeader {
        background-color: #222222 !important;
        color: #ffffff !important;
        font-size: 1rem !important;
        font-weight: bold !important;
        border-radius: 4px !important;
        padding: 0.75rem !important;
        border: 1px solid #444444 !important;
    }
    
    /* Simple metrics */
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
    
    /* Simple date header */
    .date-header {
        background-color: #333333;
        color: white;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
        text-align: center;
        font-size: 1.1rem;
        font-weight: bold;
    }
    
    /* Clean workout cards */
    .workout-card {
        background-color: #2d2d2d;
        padding: 1.5rem;
        border-radius: 10px;
        margin: 1rem 0;
        border-left: 4px solid #4CAF50;
        color: white;
    }
    
    .program-card {
        background-color: #2d2d2d;
        padding: 1.5rem;
        border-radius: 10px;
        margin: 1rem 0;
        border-left: 4px solid #2196F3;
        color: white;
    }
    
    /* Simple stats cards */
    .stats-card {
        background-color: #333333;
        color: white;
        padding: 1.5rem;
        border-radius: 10px;
        text-align: center;
        margin: 0.5rem;
        font-size: 1rem;
        font-weight: bold;
    }
    
    /* Readable set items */
    .set-item {
        background-color: #3d3d3d;
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
        border-left: 3px solid #2196F3;
        color: white;
        font-size: 1rem;
    }
    
    /* Clean mobile inputs */
    .stSelectbox > div > div {
        font-size: 1rem !important;
        padding: 0.75rem !important;
        background-color: #2d2d2d !important;
        color: white !important;
        border-radius: 8px !important;
        border: 2px solid #555 !important;
        height: auto !important;
    }
    
    .stNumberInput > div > div > input {
        font-size: 1.1rem !important;
        height: 2.5rem !important;
        background-color: #2d2d2d !important;
        color: white !important;
        border-radius: 8px !important;
        border: 2px solid #555 !important;
        text-align: center !important;
        font-weight: bold !important;
    }
    
    .stTextInput > div > div > input {
        font-size: 1rem !important;
        padding: 0.75rem !important;
        background-color: #2d2d2d !important;
        color: white !important;
        border-radius: 8px !important;
        border: 2px solid #555 !important;
    }
    
    .stTextArea > div > div > textarea {
        font-size: 1rem !important;
        padding: 0.75rem !important;
        background-color: #2d2d2d !important;
        color: white !important;
        border-radius: 8px !important;
        border: 2px solid #555 !important;
    }
    
    /* Clean delete buttons */
    .stButton button[title*="Delete"], .stButton button[aria-label*="Delete"] {
        background-color: #f44336 !important;
        color: white !important;
        font-size: 0.9rem !important;
        padding: 0.5rem !important;
        border-radius: 6px !important;
        border: 2px solid #f44336 !important;
        height: 2.5rem !important;
    }
    
    /* Clean notes section */
    .notes-section {
        background-color: #2d2d2d;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #2196F3;
        margin: 1rem 0;
        color: white;
        font-size: 0.95rem;
    }
    
    /* Simple tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 3rem;
        font-size: 1rem;
        font-weight: bold;
        border-radius: 8px;
        background-color: #2d2d2d;
        color: white;
        border: 2px solid #555;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: #4CAF50 !important;
        color: white !important;
        border: 2px solid #4CAF50 !important;
    }
    
    /* Clean success/error messages */
    .stSuccess {
        background-color: #4CAF50 !important;
        color: white !important;
        font-size: 1rem !important;
        padding: 1rem !important;
        border-radius: 8px !important;
    }
    
    .stError {
        background-color: #f44336 !important;
        color: white !important;
        font-size: 1rem !important;
        padding: 1rem !important;
        border-radius: 8px !important;
    }
    
    .stWarning {
        background-color: #ff9800 !important;
        color: white !important;
        font-size: 1rem !important;
        padding: 1rem !important;
        border-radius: 8px !important;
    }
    
    .stInfo {
        background-color: #2196F3 !important;
        color: white !important;
        font-size: 1rem !important;
        padding: 1rem !important;
        border-radius: 8px !important;
    }
    
    /* Clean form styling */
    .stForm {
        background-color: #2d2d2d;
        padding: 1.5rem;
        border-radius: 10px;
        border: 2px solid #555;
        margin: 1rem 0;
    }
    
    /* Mobile responsive adjustments */
    @media (max-width: 768px) {
        .main-header {
            font-size: 2rem;
        }
        
        .stButton > button {
            height: 3rem !important;
            font-size: 1rem !important;
        }
        
        .stButton > button[kind="primary"] {
            height: 3.5rem !important;
            font-size: 1.1rem !important;
        }
        
        .date-header {
            padding: 0.75rem;
            font-size: 1rem;
        }
        
        .stats-card {
            margin: 0.25rem;
            padding: 1rem;
            font-size: 0.9rem;
        }
    }
    
    /* Progress bars */
    .stProgress > div > div > div {
        background-color: #4CAF50 !important;
        border-radius: 4px !important;
        height: 0.75rem !important;
    }
    
    /* Expander styling */
    .streamlit-expanderHeader {
        background-color: #2d2d2d !important;
        color: white !important;
        font-size: 1rem !important;
        font-weight: bold !important;
        border-radius: 8px !important;
        padding: 1rem !important;
    }
    
    /* Metric styling */
    [data-testid="metric-container"] {
        background-color: #2d2d2d;
        border-radius: 8px;
        padding: 1rem;
        border-left: 3px solid #2196F3;
    }
    
    [data-testid="metric-container"] label {
        color: white !important;
        font-size: 0.9rem !important;
        font-weight: bold !important;
    }
    
    [data-testid="metric-container"] div[data-testid="metric-value"] {
        color: #2196F3 !important;
        font-size: 1.5rem !important;
        font-weight: bold !important;
    }
</style>
""", unsafe_allow_html=True)

# Audio feedback function
def play_success_sound():
    """Add audio feedback for successful logging"""
    st.markdown("""
    <script>
        const audioContext = new (window.AudioContext || window.webkitAudioContext)();
        
        function playSuccessSound() {
            const oscillator = audioContext.createOscillator();
            const gainNode = audioContext.createGain();
            
            oscillator.connect(gainNode);
            gainNode.connect(audioContext.destination);
            
            oscillator.frequency.setValueAtTime(800, audioContext.currentTime);
            oscillator.frequency.setValueAtTime(1000, audioContext.currentTime + 0.1);
            oscillator.frequency.setValueAtTime(1200, audioContext.currentTime + 0.2);
            
            gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
            gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.3);
            
            oscillator.start(audioContext.currentTime);
            oscillator.stop(audioContext.currentTime + 0.3);
        }
        
        playSuccessSound();
    </script>
    """, unsafe_allow_html=True)

# Initialize session state
if 'tracker' not in st.session_state:
    st.session_state.tracker = GymTracker()

# Initialize program exercises list
if 'program_exercises' not in st.session_state:
    st.session_state.program_exercises = []

# Smart defaults for quick logging
if 'last_exercise' not in st.session_state:
    st.session_state.last_exercise = 'Bench Press'
if 'last_reps' not in st.session_state:
    st.session_state.last_reps = 8
if 'last_weight' not in st.session_state:
    st.session_state.last_weight = 0.0
if 'last_rpe' not in st.session_state:
    st.session_state.last_rpe = 8

# Helper functions
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
    """Create sample data ONLY if database is completely empty"""
    tracker = st.session_state.tracker
    
    # Check if we've already created sample data
    if st.session_state.get('sample_data_created', False):
        return
    
    # Check if there's ANY real data in the database
    df = tracker.get_data()
    
    # If there's already data, don't create sample data
    if not df.empty:
        st.session_state.sample_data_created = True
        return
    
    # Only create sample data on completely fresh installation
    # Check if user specifically wants sample data
    if not st.session_state.get('user_wants_sample_data', False):
        st.session_state.sample_data_created = True  # Skip sample data creation
        return

def clean_old_sample_data():
    """Aggressively remove ALL sample data that shouldn't be there"""
    tracker = st.session_state.tracker
    
    # Get all data
    df = tracker.get_data()
    
    if df.empty:
        return "No data to clean"
    
    # AGGRESSIVE sample data identification
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
    
    # Find ALL suspicious rows - be very aggressive
    suspicious_rows = df[
        # Match exact sample notes
        df['workout_notes'].isin(sample_workout_notes) | 
        df['set_notes'].isin(sample_set_notes) |
        # Match specific sample data patterns from screenshot
        ((df['exercise'] == 'Hack Squat') & (df['weight'].isin([80.0, 90.0, 100.0])) & (df['reps'].isin([12, 10, 8]))) |
        ((df['exercise'] == 'Leg Press') & (df['weight'].isin([150.0, 170.0])) & (df['reps'].isin([15, 12]))) |
        # Match any data with these exact RPE and weight combinations (very specific to sample data)
        ((df['exercise'] == 'Hack Squat') & (df['rpe'] == 7) & (df['weight'] == 80.0)) |
        ((df['exercise'] == 'Hack Squat') & (df['rpe'] == 8) & (df['weight'] == 90.0)) |
        ((df['exercise'] == 'Hack Squat') & (df['rpe'] == 9) & (df['weight'] == 100.0)) |
        ((df['exercise'] == 'Leg Press') & (df['rpe'] == 7) & (df['weight'] == 150.0)) |
        ((df['exercise'] == 'Leg Press') & (df['rpe'] == 8) & (df['weight'] == 170.0))
    ]
    
    if suspicious_rows.empty:
        return "✅ No sample data found to clean"
    
    # Delete ALL suspicious rows
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
    
    # Delete ALL workout data
    cursor.execute('DELETE FROM workouts')
    
    conn.commit()
    conn.close()
    
    return "🚨 ALL WORKOUT DATA DELETED - Fresh start!"

def show_enhanced_success_animation():
    """Show clean success feedback"""
    st.success("✅ SET LOGGED SUCCESSFULLY!")
    time.sleep(0.3)
    st.balloons()

# ===== PAGE FUNCTIONS =====

def todays_workout_page():
    """Today's workout with clean mobile layout"""
    st.header("🔥 Today's Workout")
    
    # Date selection with clean styling
    selected_date = st.date_input(
        "📅 Workout Date", 
        value=date.today(),
        help="Select the date for this workout"
    )
    
    # Clean date header
    if selected_date == date.today():
        st.markdown('<div class="date-header">🔥 <strong>TODAY\'S WORKOUT</strong><br>' + 
                   selected_date.strftime('%A, %B %d, %Y') + '</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="date-header">📅 <strong>WORKOUT REVIEW</strong><br>' + 
                   selected_date.strftime('%A, %B %d, %Y') + '</div>', unsafe_allow_html=True)
    
    date_str = selected_date.strftime('%Y-%m-%d')
    
    # Check for existing program
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
        
        # Display exercises in program
        exercises = program['exercises']
        
        # Enhanced progress indicator
        completed_exercises = []
        df = st.session_state.tracker.get_data()
        if not df.empty:
            today_data = df[df['date'] == date_str]
            completed_exercises = today_data['exercise'].unique().tolist()
        
        progress_percentage = (len(completed_exercises) / len(exercises)) * 100 if exercises else 0
        
        st.subheader(f"📈 Beast Mode Progress: {progress_percentage:.0f}% Complete")
        st.progress(progress_percentage / 100)
        
        # Quick stats for today
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
            
            # Check if exercise is completed
            is_completed = exercise_name in completed_exercises
            status_emoji = "✅" if is_completed else "🔥"
            
            with st.expander(f"{status_emoji} {exercise_name} - {target_sets}×{target_reps} (Rest: {rest_time}s)", expanded=not is_completed):
                
                # Show last workout with enhanced styling
                last_workout = get_last_workout_for_exercise(exercise_name)
                
                if last_workout is not None:
                    st.markdown("**📚 Last Beast Performance:**")
                    last_date = last_workout['date'].iloc[0].strftime('%Y-%m-%d')
                    st.markdown(f"*📅 {last_date}*")
                    
                    for _, row in last_workout.iterrows():
                        notes_text = f" - *{row['set_notes']}*" if row['set_notes'] else ""
                        rpe_color = "🟢" if row['rpe'] <= 7 else "🟡" if row['rpe'] <= 8 else "🔴"
                        st.markdown(f"**Set {row['set_number']}:** {row['reps']} reps @ {row['weight']}kg {rpe_color}RPE:{row['rpe']}{notes_text}")
                else:
                    st.markdown("**🆕 First time unleashing the beast on this exercise!**")
                
                if exercise_notes:
                    st.markdown(f'<div class="notes-section"><strong>💡 Beast Mode Tips:</strong> {exercise_notes}</div>', unsafe_allow_html=True)
                
                # Enhanced mobile logging form
                st.markdown("**🎯 Log Your Beast Set:**")
                
                with st.form(f"log_{exercise_name.replace(' ', '_')}_{i}"):
                    # Enhanced input layout
                    col1, col2 = st.columns(2)
                    with col1:
                        reps = st.number_input("🎯 Reps", min_value=1, max_value=50, value=target_reps, key=f"reps_{i}")
                    with col2:
                        weight = st.number_input("⚖️ Weight (kg)", min_value=0.0, value=0.0, step=0.625, key=f"weight_{i}")
                    
                    rpe = st.select_slider("💥 RPE (Rate of Perceived Exertion)", options=[6, 7, 8, 9, 10], value=8, key=f"rpe_{i}")
                    set_notes = st.text_input("📝 Beast Notes", placeholder="Form, fatigue, equipment, how it felt...", key=f"set_notes_{i}")
                    
                    if st.form_submit_button(f"🚀 LOG BEAST SET", use_container_width=True, type="primary"):
                        result = st.session_state.tracker.log_workout(
                            date_str, 
                            exercise_name, 
                            [{'reps': reps, 'weight': weight, 'rpe': rpe, 'set_notes': set_notes}], 
                            ""
                        )
                        show_enhanced_success_animation()
                        st.rerun()
    
    else:
        st.info("📋 No program set for today. Use 'Quick Log' for freestyle beast mode training or create a program in the Programs tab!")
    
    # Enhanced session statistics
    st.subheader("📊 Today's Beast Mode Statistics")
    
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
            
            # Beast Mode Progress Indicator
            avg_rpe = today_data['rpe'].mean() if today_data['rpe'].notna().any() else 0
            if avg_rpe > 0:
                st.subheader("🔥 Beast Mode Intensity")
                if avg_rpe <= 7:
                    st.success(f"🟢 Moderate Beast Mode - Average RPE: {avg_rpe:.1f}")
                elif avg_rpe <= 8.5:
                    st.warning(f"🟡 High Beast Mode - Average RPE: {avg_rpe:.1f}")
                else:
                    st.error(f"🔴 MAXIMUM BEAST MODE - Average RPE: {avg_rpe:.1f}")

def enhanced_quick_log_page():
    """Clean mobile-optimized quick log"""
    st.header("⚡ Quick Log")
    
    # Date selection with clean styling
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
    
    # Quick access buttons for common exercises
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
    
    # Clean Quick Log Form
    st.subheader("📝 Log Your Set")
    
    with st.form("quick_log", clear_on_submit=True):
        # Smart defaults with last exercise highlighted
        exercise_index = 0
        if st.session_state.last_exercise in all_exercises:
            exercise_index = all_exercises.index(st.session_state.last_exercise)
        
        exercise = st.selectbox("💪 Exercise", all_exercises, index=exercise_index)
        
        # Show last performance for selected exercise
        if exercise:
            last_workout = get_last_workout_for_exercise(exercise)
            if last_workout is not None:
                last_set = last_workout.iloc[-1]  # Get last set
                st.info(f"🔥 Last Performance: {last_set['reps']} reps @ {last_set['weight']}kg (RPE: {last_set['rpe']})")
        
        # Clean input layout
        col1, col2 = st.columns(2)
        with col1:
            reps = st.number_input("🎯 Reps", min_value=1, max_value=50, value=st.session_state.last_reps)
        with col2:
            weight = st.number_input("⚖️ Weight (kg)", min_value=0.0, value=st.session_state.last_weight, step=0.625)
        
        rpe = st.select_slider("💥 RPE", options=[6, 7, 8, 9, 10], value=st.session_state.last_rpe)
        set_notes = st.text_input("📝 Notes", placeholder="How did that feel? Form notes, equipment, etc...")
        
        if st.form_submit_button("🚀 LOG SET", use_container_width=True, type="primary"):
            st.session_state.tracker.quick_log(exercise, reps, weight, rpe, set_notes, "", date_str)
            
            # Update smart defaults
            st.session_state.last_exercise = exercise
            st.session_state.last_reps = reps
            st.session_state.last_weight = weight
            st.session_state.last_rpe = rpe
            
            show_enhanced_success_animation()
            st.rerun()
    
    # Clean Full Day View Section
    st.subheader("📋 Today's Complete Workout")
    
    daily_workout = st.session_state.tracker.get_daily_workout(date_str)
    
    if not daily_workout.empty:
        # Group by exercise with enhanced styling
        exercises_done = daily_workout['exercise'].unique()
        
        for exercise in exercises_done:
            exercise_sets = daily_workout[daily_workout['exercise'] == exercise]
            
            # Calculate exercise stats
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
                    if st.button("🗑️", key=f"delete_{set_row['id']}", help="Delete this beast set"):
                        if st.session_state.get('confirm_delete_set') == set_row['id']:
                            result = st.session_state.tracker.delete_set(set_row['id'])
                            st.success(result)
                            st.session_state.pop('confirm_delete_set', None)
                            st.rerun()
                        else:
                            st.session_state.confirm_delete_set = set_row['id']
                            st.warning("⚠️ Tap again to confirm deletion")
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Enhanced daily summary with streak tracking
        total_sets = len(daily_workout)
        total_reps = daily_workout['reps'].sum()
        total_volume = (daily_workout['reps'] * daily_workout['weight']).sum()
        avg_rpe = daily_workout['rpe'].mean() if daily_workout['rpe'].notna().any() else 0
        
        st.subheader("📊 Daily Beast Mode Summary")
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
        
        # Beast Mode Intensity Indicator
        if avg_rpe > 0:
            st.subheader("🔥 Beast Mode Intensity Analysis")
            intensity_col1, intensity_col2 = st.columns(2)
            
            with intensity_col1:
                if avg_rpe <= 7:
                    st.success(f"🟢 Moderate Beast Mode - {avg_rpe:.1f} avg RPE")
                elif avg_rpe <= 8.5:
                    st.warning(f"🟡 High Beast Mode - {avg_rpe:.1f} avg RPE")
                else:
                    st.error(f"🔴 MAXIMUM BEAST MODE - {avg_rpe:.1f} avg RPE")
            
            with intensity_col2:
                # RPE distribution
                rpe_counts = daily_workout['rpe'].value_counts().sort_index()
                for rpe_val, count in rpe_counts.items():
                    emoji = "🟢" if rpe_val <= 7 else "🟡" if rpe_val <= 8 else "🔴"
                    st.write(f"{emoji} RPE {rpe_val}: {count} sets")
    
    else:
        st.info("💡 No beast mode exercises logged yet today. Time to unleash the beast! 🔥")

def visual_progress_page():
    """Enhanced visual progress with mobile-optimized charts and beast mode analytics"""
    st.header("📈 Beast Mode Progress & Analytics")
    
    df = st.session_state.tracker.get_data()
    
    if df.empty:
        st.warning("No workout data yet. Start logging to see amazing beast mode progress visuals! 🚀")
        return
    
    # Enhanced main sections
    analysis_tab, body_part_tab, streak_tab = st.tabs(["🏋️ Exercise Beast Stats", "💪 Body Analysis", "🔥 Beast Streaks"])
    
    with analysis_tab:
        # Exercise selection with recent activity
        all_exercises = st.session_state.tracker.get_all_exercises()
        available_exercises = [ex for ex in all_exercises if ex in df['exercise'].unique()]
        
        if not available_exercises:
            st.warning("No exercises with logged data yet.")
            return
        
        # Sort by recent activity
        exercise_last_used = {}
        for ex in available_exercises:
            last_date = df[df['exercise'] == ex]['date'].max()
            exercise_last_used[ex] = last_date
        
        available_exercises.sort(key=lambda x: exercise_last_used[x], reverse=True)
        
        selected_exercise = st.selectbox("🏋️ Choose Exercise", available_exercises)
        
        # Get comprehensive stats
        stats = st.session_state.tracker.get_exercise_stats(selected_exercise)
        
        if not stats:
            return
        
        # Enhanced statistics cards
        st.subheader(f"📊 {selected_exercise} - Beast Mode Statistics")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown(f'<div class="stats-card">🏆 <strong>Max Weight</strong><br>{stats["max_weight"]} kg</div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown(f'<div class="stats-card">🎯 <strong>Total Sets</strong><br>{stats["total_sets"]}</div>', unsafe_allow_html=True)
        
        with col3:
            st.markdown(f'<div class="stats-card">📦 <strong>Total Volume</strong><br>{stats["total_volume"]:,.0f} kg</div>', unsafe_allow_html=True)
        
        with col4:
            st.markdown(f'<div class="stats-card">💥 <strong>Avg RPE</strong><br>{stats["avg_rpe"]:.1f}</div>', unsafe_allow_html=True)
        
        # Enhanced chart views
        st.subheader("📈 Beast Mode Weight Progression")
        
        daily_stats = stats['daily_stats']
        
        # Weight progression chart
        fig1 = go.Figure()
        fig1.add_trace(go.Scatter(
            x=daily_stats['date'], 
            y=daily_stats['max_weight'],
            mode='lines+markers',
            name='Max Weight',
            line=dict(color='#FF6B35', width=4),
            marker=dict(size=12, color='#F7931E')
        ))
        
        # Add trend line
        if len(daily_stats) > 1:
            z = np.polyfit(range(len(daily_stats)), daily_stats['max_weight'], 1)
            p = np.poly1d(z)
            fig1.add_trace(go.Scatter(
                x=daily_stats['date'],
                y=p(range(len(daily_stats))),
                mode='lines',
                name='Beast Trend',
                line=dict(color='#00D2FF', width=3, dash='dash')
            ))
        
        fig1.update_layout(
            title=f'{selected_exercise} - Beast Mode Weight Progression',
            xaxis_title='Date',
            yaxis_title='Weight (kg)',
            height=500,
            paper_bgcolor='rgba(15,15,35,0.9)',
            plot_bgcolor='rgba(26,26,46,0.9)',
            font=dict(color='white', size=14),
            xaxis=dict(
                tickformat='%Y-%m-%d',
                tickmode='auto',
                gridcolor='#4A5568'
            ),
            yaxis=dict(gridcolor='#4A5568')
        )
        st.plotly_chart(fig1, use_container_width=True)
        
        # Volume progression chart
        st.subheader("📊 Beast Mode Volume Progression")
        
        fig2 = go.Figure()
        fig2.add_trace(go.Bar(
            x=daily_stats['date'],
            y=daily_stats['volume'],
            name='Daily Volume',
            marker_color='#00D2FF',
            text=daily_stats['volume'].round(0),
            textposition='auto'
        ))
        fig2.update_layout(
            title=f'{selected_exercise} - Beast Mode Training Volume',
            xaxis_title='Date',
            yaxis_title='Volume (kg)',
            height=500,
            paper_bgcolor='rgba(15,15,35,0.9)',
            plot_bgcolor='rgba(26,26,46,0.9)',
            font=dict(color='white', size=14),
            xaxis=dict(
                tickformat='%Y-%m-%d',
                tickmode='auto',
                gridcolor='#4A5568'
            ),
            yaxis=dict(gridcolor='#4A5568')
        )
        st.plotly_chart(fig2, use_container_width=True)
        
        # Enhanced performance analysis
        st.subheader("🔥 Beast Mode Performance Analysis")
        
        if len(daily_stats) > 1:
            # Calculate trends
            weight_trend = daily_stats['max_weight'].pct_change().mean() * 100
            volume_trend = daily_stats['volume'].pct_change().mean() * 100
            
            col1, col2 = st.columns(2)
            
            with col1:
                if weight_trend > 0:
                    st.success(f"🚀 Weight BEAST GAINS: +{weight_trend:.1f}% trend")
                elif weight_trend < -2:
                    st.error(f"📉 Weight declining: {weight_trend:.1f}%")
                else:
                    st.warning(f"📊 Weight stable: {weight_trend:.1f}%")
            
            with col2:
                if volume_trend > 0:
                    st.success(f"💪 Volume BEAST GAINS: +{volume_trend:.1f}% trend")
                elif volume_trend < -2:
                    st.error(f"📉 Volume declining: {volume_trend:.1f}%")
                else:
                    st.warning(f"📊 Volume stable: {volume_trend:.1f}%")
            
            # Beast records
            best_day = daily_stats.loc[daily_stats['max_weight'].idxmax()]
            best_volume_day = daily_stats.loc[daily_stats['volume'].idxmax()]
            
            st.markdown("**🏆 Beast Mode Records:**")
            st.write(f"**Weight PR:** {best_day['max_weight']} kg on {best_day['date'].strftime('%Y-%m-%d')}")
            st.write(f"**Volume PR:** {best_volume_day['volume']:.0f} kg on {best_volume_day['date'].strftime('%Y-%m-%d')}")
            
            # Recent vs. older performance
            recent_avg = daily_stats.tail(3)['max_weight'].mean()
            older_avg = daily_stats.head(3)['max_weight'].mean()
            improvement = ((recent_avg - older_avg) / older_avg) * 100 if older_avg > 0 else 0
            
            if improvement > 5:
                st.success(f"🔥 BEAST MODE ACTIVATED: {improvement:.1f}% stronger than when you started!")
            elif improvement > 0:
                st.info(f"📈 Making gains: {improvement:.1f}% improvement")
            else:
                st.warning(f"💪 Keep pushing: {improvement:.1f}% change")
    
    # Body Part Analysis Tab
    with body_part_tab:
        st.subheader("💪 Weekly Beast Mode Body Analysis")
        
        # Week selection with enhanced UI
        today = date.today()
        start_of_week = today - timedelta(days=today.weekday())
        
        week_start = st.date_input("📅 Week Start (Monday)", value=start_of_week)
        week_end = week_start + timedelta(days=6)
        
        # Get weekly body part data
        weekly_stats = st.session_state.tracker.get_weekly_body_part_volume(
            pd.to_datetime(week_start), 
            pd.to_datetime(week_end)
        )
        
        if not weekly_stats.empty:
            st.subheader(f"📊 Beast Week: {week_start.strftime('%B %d')} - {week_end.strftime('%B %d, %Y')}")
            
            # Enhanced body part chart
            fig_sets = go.Figure(data=[
                go.Bar(
                    x=weekly_stats.index,
                    y=weekly_stats['total_sets'],
                    marker_color=['#FF6B35', '#F7931E', '#00D2FF', '#667eea', '#764ba2', '#ff9a9e', '#fecfef'],
                    text=weekly_stats['total_sets'],
                    textposition='auto',
                    hovertemplate='<b>%{x}</b><br>Sets: %{y}<br>Volume: %{customdata:.0f} kg<extra></extra>',
                    customdata=weekly_stats['total_volume']
                )
            ])
            fig_sets.update_layout(
                title='Beast Mode Sets per Body Part',
                xaxis_title='Body Part',
                yaxis_title='Total Sets',
                height=500,
                paper_bgcolor='rgba(15,15,35,0.9)',
                plot_bgcolor='rgba(26,26,46,0.9)',
                font=dict(color='white', size=14),
                xaxis=dict(gridcolor='#4A5568'),
                yaxis=dict(gridcolor='#4A5568')
            )
            st.plotly_chart(fig_sets, use_container_width=True)
            
            # Enhanced breakdown with beast mode recommendations
            st.subheader("📋 Beast Mode Body Part Breakdown")
            
            body_parts = weekly_stats.index.tolist()
            
            for body_part in body_parts:
                row_data = weekly_stats.loc[body_part]
                sets = int(row_data['total_sets'])
                
                # Enhanced color coding and recommendations
                if sets >= 15:
                    status = "🔥 BEAST MODE MAX"
                    color = "#FF4757"
                    recommendation = "Consider deload or maintenance"
                elif sets >= 10:
                    status = "💪 BEAST MODE ACTIVE"
                    color = "#FF6B35"
                    recommendation = "Perfect beast zone!"
                elif sets >= 6:
                    status = "🟡 Good Work"
                    color = "#F7931E"
                    recommendation = "Add 2-3 more sets"
                else:
                    status = "🔴 Need Beast Mode"
                    color = "#E53E3E"
                    recommendation = "Needs more attention!"
                
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, {color}22 0%, {color}44 100%); 
                           padding: 2rem; border-radius: 20px; margin: 1.5rem 0;
                           border-left: 8px solid {color}; color: white;
                           box-shadow: 0 8px 25px rgba(0,0,0,0.3);">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <h3 style="margin: 0; font-size: 1.4rem;">💪 {body_part}</h3>
                            <p style="margin: 0.5rem 0; font-size: 1.1rem;">{status}</p>
                            <p style="margin: 0; font-size: 1rem; opacity: 0.9;">💡 {recommendation}</p>
                        </div>
                        <div style="text-align: right;">
                            <div style="font-size: 2rem; font-weight: bold;">{sets}</div>
                            <div style="font-size: 0.9rem; opacity: 0.8;">sets</div>
                        </div>
                    </div>
                    <div style="margin-top: 1rem; display: flex; gap: 2rem; font-size: 0.95rem;">
                        <span>🎯 <strong>{int(row_data['total_reps'])} reps</strong></span>
                        <span>🏋️ <strong>{row_data['total_volume']:,.0f} kg volume</strong></span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            # Beast Mode Balance Score
            st.subheader("⚖️ Beast Mode Balance Score")
            
            # Calculate balance based on sets distribution
            set_values = weekly_stats['total_sets'].values
            coefficient_of_variation = np.std(set_values) / np.mean(set_values) if np.mean(set_values) > 0 else 1
            balance_score = max(0, 100 - (coefficient_of_variation * 100))
            
            if balance_score >= 80:
                st.success(f"🏆 PERFECT BEAST BALANCE: {balance_score:.0f}/100")
            elif balance_score >= 60:
                st.warning(f"🟡 Good Balance: {balance_score:.0f}/100")
            else:
                st.error(f"🔴 Needs Better Balance: {balance_score:.0f}/100")
        
        else:
            st.info(f"📅 No beast mode data for week of {week_start.strftime('%B %d')}. Start logging workouts!")
    
    # Beast Streaks Tab
    with streak_tab:
        st.subheader("🔥 Beast Mode Streaks & Consistency")
        
        if not df.empty:
            # Calculate workout streaks
            workout_dates = df['date'].dt.date.unique()
            workout_dates.sort()
            
            # Current streak
            current_streak = 0
            today_date = date.today()
            
            for i in range(len(workout_dates) - 1, -1, -1):
                days_diff = (today_date - workout_dates[i]).days
                if days_diff <= 1:  # Today or yesterday
                    current_streak += 1
                    today_date = workout_dates[i]
                else:
                    break
            
            # Longest streak
            longest_streak = 1
            current_check = 1
            
            for i in range(1, len(workout_dates)):
                if (workout_dates[i] - workout_dates[i-1]).days == 1:
                    current_check += 1
                    longest_streak = max(longest_streak, current_check)
                else:
                    current_check = 1
            
            # Display streaks
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if current_streak >= 7:
                    st.markdown('<div class="stats-card" style="background: linear-gradient(135deg, #FF4757 0%, #FF6B35 100%);">🔥 <strong>Current Streak</strong><br>' + 
                               f'{current_streak} days<br>BEAST MODE!</div>', unsafe_allow_html=True)
                elif current_streak >= 3:
                    st.markdown('<div class="stats-card" style="background: linear-gradient(135deg, #F7931E 0%, #FF6B35 100%);">💪 <strong>Current Streak</strong><br>' + 
                               f'{current_streak} days<br>Keep going!</div>', unsafe_allow_html=True)
                else:
                    st.markdown('<div class="stats-card">📅 <strong>Current Streak</strong><br>' + 
                               f'{current_streak} days</div>', unsafe_allow_html=True)
            
            with col2:
                st.markdown('<div class="stats-card">🏆 <strong>Longest Streak</strong><br>' + 
                           f'{longest_streak} days</div>', unsafe_allow_html=True)
            
            with col3:
                total_days = len(workout_dates)
                st.markdown('<div class="stats-card">💯 <strong>Total Days</strong><br>' + 
                           f'{total_days} sessions</div>', unsafe_allow_html=True)
            
            # Weekly consistency chart
            st.subheader("📊 Weekly Beast Mode Consistency")
            
            # Calculate weekly workout frequency
            df_copy = df.copy()
            df_copy['week'] = df_copy['date'].dt.to_period('W')
            weekly_workouts = df_copy.groupby('week')['date'].nunique().reset_index()
            weekly_workouts['week_str'] = weekly_workouts['week'].astype(str)
            
            fig_consistency = go.Figure(data=[
                go.Bar(
                    x=weekly_workouts['week_str'],
                    y=weekly_workouts['date'],
                    marker_color=['#FF4757' if x >= 5 else '#FF6B35' if x >= 3 else '#F7931E' for x in weekly_workouts['date']],
                    text=weekly_workouts['date'],
                    textposition='auto'
                )
            ])
            fig_consistency.update_layout(
                title='Weekly Beast Mode Sessions',
                xaxis_title='Week',
                yaxis_title='Workout Days',
                height=400,
                paper_bgcolor='rgba(15,15,35,0.9)',
                plot_bgcolor='rgba(26,26,46,0.9)',
                font=dict(color='white', size=14),
                xaxis=dict(gridcolor='#4A5568'),
                yaxis=dict(gridcolor='#4A5568')
            )
            st.plotly_chart(fig_consistency, use_container_width=True)
            
            # Beast Mode Achievements
            st.subheader("🏆 Beast Mode Achievements")
            
            achievements = []
            
            if current_streak >= 7:
                achievements.append("🔥 Week Warrior - 7+ day streak!")
            if longest_streak >= 14:
                achievements.append("💪 Beast Mode Legend - 14+ day streak!")
            if total_days >= 30:
                achievements.append("🏆 Consistency Champion - 30+ sessions!")
            if len(df) >= 100:
                achievements.append("🎯 Set Slayer - 100+ sets logged!")
            
            total_volume = (df['reps'] * df['weight']).sum()
            if total_volume >= 10000:
                achievements.append(f"🏋️ Volume Beast - {total_volume:,.0f}kg total!")
            
            if achievements:
                for achievement in achievements:
                    st.success(achievement)
            else:
                st.info("💪 Keep training to unlock Beast Mode achievements!")

def program_creator_page():
    """Enhanced program creator with AI-like suggestions"""
    st.header("📅 Beast Mode Program Creator")
    
    # Enhanced template management tabs
    template_tab, create_tab, ai_tab = st.tabs(["📚 Templates", "🆕 Create", "🤖 AI Assist"])
    
    with template_tab:
        st.subheader("📚 Your Beast Mode Templates")
        
        # Enhanced template filters
        col1, col2 = st.columns(2)
        
        with col1:
            categories = ["All"] + st.session_state.tracker.get_template_categories()
            selected_category = st.selectbox("Category", categories)
        
        with col2:
            creators = ["All", "Personal Trainer", "Exercise Physiologist", "Beast Mode AI", "Myself"]
            selected_creator = st.selectbox("Creator", creators)
        
        # Get filtered templates
        filter_category = None if selected_category == "All" else selected_category
        filter_creator = None if selected_creator == "All" else selected_creator
        
        templates = st.session_state.tracker.get_templates(filter_category, filter_creator)
        
        if templates:
            for template in templates:
                with st.expander(f"📋 {template['name']} - {template['category']}", expanded=False):
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**👨‍⚕️ Creator:** {template['created_by']}")
                        st.write(f"**📅 Created:** {template['created_at'][:10]}")
                    with col2:
                        if template['last_used']:
                            st.write(f"**🕒 Last Used:** {template['last_used'][:10]}")
                        else:
                            st.write("**🆕 Never Used**")
                    
                    if template['description']:
                        st.markdown(f'<div class="notes-section">{template["description"]}</div>', unsafe_allow_html=True)
                    
                    # Show exercises with enhanced formatting
                    st.write("**🏋️ Beast Mode Exercises:**")
                    total_estimated_time = 0
                    
                    for i, ex in enumerate(template['exercises'], 1):
                        rest_time = ex.get('rest', 90)
                        sets = ex.get('sets', 3)
                        estimated_time = (sets * 45) + ((sets - 1) * rest_time)  # 45 sec per set + rest
                        total_estimated_time += estimated_time
                        
                        st.write(f"**{i}. {ex['exercise']}** - {ex['sets']}×{ex['reps']} (Rest: {rest_time}s)")
                        if ex.get('notes'):
                            st.write(f"   💡 *{ex['notes']}*")
                    
                    st.info(f"⏱️ Estimated workout time: {total_estimated_time // 60} minutes")
                    
                    # Enhanced template actions
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        if st.button(f"📅 Use Today", key=f"use_{template['id']}", use_container_width=True):
                            st.session_state.program_exercises = template['exercises'].copy()
                            st.success(f"✅ Loaded: {template['name']}")
                            st.rerun()
                    
                    with col2:
                        if st.button(f"📝 Edit", key=f"edit_{template['id']}", use_container_width=True):
                            st.session_state.program_exercises = template['exercises'].copy()
                            st.session_state.editing_template = template
                            st.success(f"✅ Editing: {template['name']}")
                            st.rerun()
                    
                    with col3:
                        if st.button(f"🗑️ Delete", key=f"del_{template['id']}", use_container_width=True):
                            if st.session_state.get('confirm_delete') == template['id']:
                                result = st.session_state.tracker.delete_template(template['id'])
                                st.success(result)
                                st.session_state.pop('confirm_delete', None)
                                st.rerun()
                            else:
                                st.session_state.confirm_delete = template['id']
                                st.warning("⚠️ Tap again to confirm deletion")
        else:
            st.info("📋 No templates found. Create your first beast mode template!")
    
    with create_tab:
        st.subheader("🆕 Create Beast Mode Program/Template")
        
        # Check if editing
        editing_template = st.session_state.get('editing_template')
        
        if editing_template:
            st.info(f"✏️ Editing: **{editing_template['name']}**")
            default_name = editing_template['name']
            default_category = editing_template['category']
            default_description = editing_template['description']
            default_creator = editing_template['created_by']
        else:
            default_name = f"Beast Training - {date.today().strftime('%b %d')}"
            default_category = "Custom"
            default_description = ""
            default_creator = "Personal Trainer"
        
        program_date = st.date_input("📅 Beast Mode Program Date", value=date.today())
        program_name = st.text_input("Program Name", value=default_name)
        
        # Enhanced template fields
        col1, col2 = st.columns(2)
        with col1:
            template_category = st.selectbox("Category", [
                "Strength Training", "Cardio", "Flexibility", "Rehabilitation", 
                "Upper Body", "Lower Body", "Full Body", "Sport Specific", "Beast Mode Custom"
            ], index=8)
        
        with col2:
            created_by = st.selectbox("Created By", ["Personal Trainer", "Exercise Physiologist", "Beast Mode AI", "Myself", "Other"])
        
        if created_by == "Other":
            created_by = st.text_input("Creator Name")
        
        program_notes = st.text_area("Description", value=default_description,
                                   placeholder="Session goals, focus areas, beast mode intensity...")
        
        save_as_template = st.checkbox("💾 Save as Beast Mode Template", value=True)
        
        # Enhanced quick templates with beast mode intensity
        st.write("**📋 Beast Mode Quick Start Templates:**")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("💪 Upper Beast", use_container_width=True):
                st.session_state.program_exercises = [
                    {'exercise': 'Bench Press', 'sets': 4, 'reps': 6, 'rest': 120, 'notes': 'Heavy compound movement'},
                    {'exercise': 'Machine Shoulder Press', 'sets': 3, 'reps': 10, 'rest': 90, 'notes': 'Shoulder stability focus'},
                    {'exercise': 'Chest Supported Row', 'sets': 3, 'reps': 10, 'rest': 90, 'notes': 'Back development'},
                    {'exercise': 'Bicep Curls', 'sets': 3, 'reps': 12, 'rest': 60, 'notes': 'Controlled tempo'},
                    {'exercise': 'Tricep Pushdown', 'sets': 3, 'reps': 12, 'rest': 60, 'notes': 'Full range of motion'}
                ]
                st.success("🔥 Upper Beast Mode template loaded!")
                st.rerun()
        
        with col2:
            if st.button("🦵 Lower Beast", use_container_width=True):
                st.session_state.program_exercises = [
                    {'exercise': 'Hack Squat', 'sets': 4, 'reps': 8, 'rest': 120, 'notes': 'Focus on depth and control'},
                    {'exercise': 'RDL', 'sets': 3, 'reps': 10, 'rest': 90, 'notes': 'Hip hinge pattern'},
                    {'exercise': 'Leg Press', 'sets': 3, 'reps': 15, 'rest': 90, 'notes': 'Full range, deep stretch'},
                    {'exercise': 'Lying Hamstring Curl', 'sets': 3, 'reps': 12, 'rest': 75, 'notes': 'Slow negatives'},
                    {'exercise': 'Calf Raises', 'sets': 4, 'reps': 20, 'rest': 60, 'notes': 'Pause at top, full stretch'}
                ]
                st.success("🔥 Lower Beast Mode template loaded!")
                st.rerun()
        
        with col3:
            if st.button("🔄 Full Beast", use_container_width=True):
                st.session_state.program_exercises = [
                    {'exercise': 'Squat', 'sets': 3, 'reps': 10, 'rest': 120, 'notes': 'King of all exercises'},
                    {'exercise': 'Bench Press', 'sets': 3, 'reps': 8, 'rest': 120, 'notes': 'Upper body power'},
                    {'exercise': 'Deadlift', 'sets': 3, 'reps': 5, 'rest': 150, 'notes': 'Posterior chain beast'},
                    {'exercise': 'Overhead Press', 'sets': 3, 'reps': 10, 'rest': 90, 'notes': 'Shoulder strength and stability'}
                ]
                st.success("🔥 Full Beast Mode template loaded!")
                st.rerun()
        
        with col4:
            if st.button("⚡ Beast Burn", use_container_width=True):
                st.session_state.program_exercises = [
                    {'exercise': 'Leg Press', 'sets': 4, 'reps': 20, 'rest': 60, 'notes': 'High rep burn'},
                    {'exercise': 'Machine Shoulder Press', 'sets': 4, 'reps': 15, 'rest': 60, 'notes': 'Shoulder burn'},
                    {'exercise': 'Bicep Curls', 'sets': 4, 'reps': 15, 'rest': 45, 'notes': 'Pump focus'},
                    {'exercise': 'Tricep Pushdown', 'sets': 4, 'reps': 15, 'rest': 45, 'notes': 'Burn out the triceps'}
                ]
                st.success("🔥 Beast Burn template loaded!")
                st.rerun()
        
        # Enhanced exercise builder
        st.subheader("🏋️ Add Beast Mode Exercises")
        
        with st.expander("➕ Add Exercise to Beast Program", expanded=True):
            all_exercises = st.session_state.tracker.get_all_exercises()
            
            exercise_name = st.selectbox("Exercise", all_exercises, key="prog_exercise")
            
            # Show exercise suggestion based on last performance
            last_workout = get_last_workout_for_exercise(exercise_name)
            if last_workout is not None:
                last_set = last_workout.iloc[-1]
                st.info(f"🔥 Last Beast Performance: {last_set['reps']} reps @ {last_set['weight']}kg (RPE: {last_set['rpe']})")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                sets = st.number_input("Sets", min_value=1, max_value=10, value=3, key="prog_sets")
            with col2:
                reps = st.number_input("Reps", min_value=1, max_value=50, value=10, key="prog_reps")
            with col3:
                rest_time = st.number_input("Rest (sec)", min_value=30, max_value=300, value=90, step=15, key="prog_rest")
            
            exercise_notes = st.text_input("Beast Notes", key="prog_notes_input", 
                                         placeholder="Form cues, focus points, beast mode tips...")
            
            if st.button("➕ Add to Beast Program", use_container_width=True, type="primary"):
                new_exercise = {
                    'exercise': exercise_name,
                    'sets': sets,
                    'reps': reps,
                    'rest': rest_time,
                    'notes': exercise_notes
                }
                st.session_state.program_exercises.append(new_exercise)
                st.success(f"✅ Added {exercise_name} to beast program!")
                st.rerun()
        
        # Enhanced current program display
        if st.session_state.program_exercises:
            st.subheader("📋 Current Beast Mode Program")
            
            # Calculate total program time
            total_time = 0
            for ex in st.session_state.program_exercises:
                sets = ex.get('sets', 3)
                rest = ex.get('rest', 90)
                total_time += (sets * 45) + ((sets - 1) * rest)
            
            st.info(f"⏱️ Estimated beast session time: {total_time // 60} minutes")
            
            st.markdown('<div class="program-card">', unsafe_allow_html=True)
            
            for i, ex in enumerate(st.session_state.program_exercises):
                col1, col2 = st.columns([5, 1])
                
                with col1:
                    rest_text = f" (Rest: {ex.get('rest', 90)}s)" if ex.get('rest') else ""
                    st.write(f"**{i+1}. {ex['exercise']}** - {ex['sets']}×{ex['reps']}{rest_text}")
                    if ex.get('notes'):
                        st.write(f"   💡 *{ex['notes']}*")
                
                with col2:
                    if st.button("🗑️", key=f"remove_{i}", help="Remove from program"):
                        st.session_state.program_exercises.pop(i)
                        st.rerun()
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Enhanced save options
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("💾 Save Beast Program", use_container_width=True):
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
                        st.session_state.pop('editing_template', None)
                        st.rerun()
                    else:
                        st.error("❌ Enter program name and add exercises")
            
            with col2:
                if st.button("🗑️ Clear All", use_container_width=True):
                    st.session_state.program_exercises = []
                    st.session_state.pop('editing_template', None)
                    st.rerun()
    
    # Beast Mode AI Assistant Tab
    with ai_tab:
        st.subheader("🤖 Beast Mode AI Program Assistant")
        
        st.info("🔥 **Beast Mode AI** analyzes your training history to create optimized programs!")
        
        # Get user's training data for AI suggestions
        df = st.session_state.tracker.get_data()
        
        if df.empty:
            st.warning("📊 No training data yet. Log some workouts first for AI analysis!")
            return
        
        # AI-style analysis
        st.write("**🧠 Beast Mode AI Analysis:**")
        
        # Analyze most frequent exercises
        exercise_frequency = df['exercise'].value_counts()
        favorite_exercises = exercise_frequency.head(5).index.tolist()
        
        # Analyze body part balance
        df_copy = df.copy()
        df_copy['body_part'] = df_copy['exercise'].apply(st.session_state.tracker.get_exercise_body_part)
        body_part_balance = df_copy['body_part'].value_counts()
        
        # Analyze RPE patterns
        avg_rpe = df['rpe'].mean() if df['rpe'].notna().any() else 8
        
        # Display AI insights
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**📊 Your Beast Mode Profile:**")
            st.write(f"• **Favorite Exercises:** {', '.join(favorite_exercises[:3])}")
            st.write(f"• **Average Intensity:** {avg_rpe:.1f} RPE")
            st.write(f"• **Total Sessions:** {len(df['date'].unique())}")
            st.write(f"• **Most Trained:** {body_part_balance.index[0] if not body_part_balance.empty else 'N/A'}")
        
        with col2:
            st.markdown("**🎯 AI Recommendations:**")
            
            # Generate AI recommendations
            recommendations = []
            
            if body_part_balance.empty:
                recommendations.append("Start with full body workouts")
            else:
                undertrained = [bp for bp in ['Chest', 'Back', 'Shoulders', 'Quadriceps', 'Hamstrings'] 
                              if bp not in body_part_balance.index[:3]]
                if undertrained:
                    recommendations.append(f"Focus on: {', '.join(undertrained[:2])}")
            
            if avg_rpe < 7:
                recommendations.append("Increase intensity (RPE 7-9)")
            elif avg_rpe > 9:
                recommendations.append("Consider deload week")
            
            recent_sessions = len(df[df['date'] >= pd.Timestamp.now() - pd.Timedelta(days=7)]['date'].unique())
            if recent_sessions < 3:
                recommendations.append("Increase frequency (3-4x/week)")
            
            for rec in recommendations:
                st.write(f"• {rec}")
        
        # AI Program Suggestions
        st.subheader("🤖 AI-Generated Beast Programs")
        
        program_col1, program_col2 = st.columns(2)
        
        with program_col1:
            if st.button("🤖 AI Beast Balance", use_container_width=True):
                # Create balanced program based on user's weak points
                ai_program = []
                
                # Add compound movements
                if 'Squat' in favorite_exercises or 'Hack Squat' in favorite_exercises:
                    ai_program.append({'exercise': 'Hack Squat', 'sets': 4, 'reps': 8, 'rest': 120, 'notes': 'AI: Core compound movement'})
                else:
                    ai_program.append({'exercise': 'Leg Press', 'sets': 4, 'reps': 12, 'rest': 90, 'notes': 'AI: Beginner-friendly compound'})
                
                ai_program.extend([
                    {'exercise': 'Bench Press', 'sets': 3, 'reps': 8, 'rest': 120, 'notes': 'AI: Upper body strength'},
                    {'exercise': 'Chest Supported Row', 'sets': 3, 'reps': 10, 'rest': 90, 'notes': 'AI: Balance push/pull'},
                    {'exercise': 'Machine Shoulder Press', 'sets': 3, 'reps': 10, 'rest': 90, 'notes': 'AI: Joint-friendly'}
                ])
                
                st.session_state.program_exercises = ai_program
                st.success("🤖 AI Beast Balance program loaded!")
                st.rerun()
        
        with program_col2:
            if st.button("🤖 AI Progressive Beast", use_container_width=True):
                # Create progressive program based on user's history
                ai_program = []
                
                for exercise in favorite_exercises[:4]:
                    last_workout = get_last_workout_for_exercise(exercise)
                    if last_workout is not None:
                        last_weight = last_workout['weight'].iloc[-1]
                        last_reps = last_workout['reps'].iloc[-1]
                        
                        # AI progression logic
                        if last_reps >= 12:
                            suggested_reps = max(6, last_reps - 2)
                            progression_note = f"AI: Increase weight, reduce reps to {suggested_reps}"
                        else:
                            suggested_reps = min(15, last_reps + 1)
                            progression_note = f"AI: Progress to {suggested_reps} reps"
                        
                        ai_program.append({
                            'exercise': exercise,
                            'sets': 3,
                            'reps': suggested_reps,
                            'rest': 90,
                            'notes': progression_note
                        })
                
                if ai_program:
                    st.session_state.program_exercises = ai_program
                    st.success("🤖 AI Progressive Beast program loaded!")
                    st.rerun()
                else:
                    st.warning("Need more training data for AI progression!")

def add_exercises_page():
    """Enhanced mobile-optimized add exercises page"""
    st.header("➕ Beast Mode Exercise Manager")
    
    # Enhanced add new exercise section
    st.subheader("🆕 Create New Beast Mode Exercise")
    
    with st.form("add_exercise_form", clear_on_submit=True):
        exercise_name = st.text_input("Exercise Name", placeholder="e.g., Cable Crossover High to Low, Beast Mode Curls")
        
        col1, col2 = st.columns(2)
        with col1:
            category = st.selectbox("Category", [
                "Chest", "Back", "Shoulders", "Arms", "Legs", "Core", "Cardio", "Full Body", "Beast Mode Special", "Other"
            ])
        
        with col2:
            difficulty = st.selectbox("Beast Level", ["Beginner", "Intermediate", "Advanced", "Beast Mode"])
        
        description = st.text_area("Description", placeholder="Setup instructions, form cues, beast mode tips...")
        
        # Enhanced exercise tags
        tags = st.multiselect("Tags", [
            "Compound", "Isolation", "Machine", "Free Weight", "Cable", "Bodyweight", 
            "High Intensity", "Beast Mode", "Beginner Friendly", "Advanced Only"
        ])
        
        if st.form_submit_button("➕ Create Beast Exercise", use_container_width=True, type="primary"):
            if exercise_name.strip():
                # Add tags to description
                full_description = description.strip()
                if tags:
                    full_description += f"\n\nTags: {', '.join(tags)}"
                
                result = st.session_state.tracker.add_custom_exercise(
                    exercise_name.strip(), category, full_description
                )
                if "Successfully added" in result:
                    st.success(result)
                    st.balloons()
                else:
                    st.error(result)
                st.rerun()
            else:
                st.error("❌ Please enter an exercise name!")
    
    # Enhanced exercise library display
    st.subheader("🌟 Your Beast Mode Exercise Library")
    
    custom_exercises_df = st.session_state.tracker.get_custom_exercises()
    
    if not custom_exercises_df.empty:
        # Add search functionality
        search_term = st.text_input("🔍 Search exercises", placeholder="Search by name or category...")
        
        if search_term:
            filtered_df = custom_exercises_df[
                custom_exercises_df['exercise_name'].str.contains(search_term, case=False) |
                custom_exercises_df['category'].str.contains(search_term, case=False) |
                custom_exercises_df['description'].str.contains(search_term, case=False, na=False)
            ]
        else:
            filtered_df = custom_exercises_df
        
        # Group by category
        for category in filtered_df['category'].unique():
            category_exercises = filtered_df[filtered_df['category'] == category]
            
            with st.expander(f"📂 {category} Exercises ({len(category_exercises)})", expanded=True):
                
                for _, exercise in category_exercises.iterrows():
                    st.markdown(f'<div class="workout-card">', unsafe_allow_html=True)
                    st.markdown(f"**🌟 {exercise['exercise_name']}**")
                    
                    if exercise['description']:
                        st.write(f"💡 *{exercise['description']}*")
                    
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.write(f"📅 *Added: {exercise['created_at'][:10]}*")
                    with col2:
                        if st.button("🚀 Use", key=f"use_exercise_{exercise['exercise_name']}", help="Add to quick log"):
                            st.session_state.last_exercise = exercise['exercise_name']
                            st.success(f"✅ Selected: {exercise['exercise_name']}")
                    
                    st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("🎯 No custom exercises yet. Create your first beast mode exercise!")
    
    # Beast Mode Exercise Suggestions
    st.subheader("💡 Beast Mode Exercise Suggestions")
    
    suggestions = [
        {
            "name": "Beast Mode Hack Squat Drop Set",
            "category": "Legs",
            "description": "Start heavy for 6 reps, immediately drop weight 20% for 8 more reps, then drop another 20% for 10 final reps. No rest between drops!",
            "tags": ["Advanced Only", "High Intensity", "Beast Mode"]
        },
        {
            "name": "Chest Supported Row Beast Hold",
            "category": "Back", 
            "description": "Perform normal chest supported rows but hold the peak contraction for 3 seconds on each rep. Feel the beast mode burn!",
            "tags": ["Intermediate", "Beast Mode", "Machine"]
        },
        {
            "name": "Machine Shoulder Press 21s",
            "category": "Shoulders",
            "description": "7 partial reps bottom half, 7 partial reps top half, 7 full range reps. 21 total reps of shoulder beast mode torture!",
            "tags": ["Advanced Only", "High Intensity", "Beast Mode"]
        }
    ]
    
    for suggestion in suggestions:
        with st.expander(f"💡 {suggestion['name']} - {suggestion['category']}", expanded=False):
            st.write(f"**Description:** {suggestion['description']}")
            st.write(f"**Tags:** {', '.join(suggestion['tags'])}")
            
            if st.button(f"➕ Add {suggestion['name']}", key=f"add_suggestion_{suggestion['name']}"):
                result = st.session_state.tracker.add_custom_exercise(
                    suggestion['name'], suggestion['category'], 
                    suggestion['description'] + f"\n\nTags: {', '.join(suggestion['tags'])}"
                )
                if "Successfully added" in result:
                    st.success(result)
                    st.rerun()
                else:
                    st.error(result)

def data_manager_page():
    """Enhanced mobile-optimized data manager with analytics and cleaning"""
    st.header("💾 Data Manager")
    
    # Enhanced current data overview
    st.subheader("📊 Your Data Overview")
    
    df = st.session_state.tracker.get_data()
    templates = st.session_state.tracker.get_templates()
    custom_exercises = st.session_state.tracker.get_custom_exercises()
    
    # Enhanced statistics display
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
    
    # Enhanced Data Cleaning Section
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
    # Debug section to see current data
    if st.button("🔍 Show Current Data (Debug)", use_container_width=True):
        if not df.empty:
            st.subheader("🔍 Current Workout Data")
            
            # Show recent entries
            recent_data = df.head(10)[['date', 'exercise', 'reps', 'weight', 'rpe', 'set_notes', 'workout_notes']]
            st.dataframe(recent_data, use_container_width=True)
            
            # Show suspicious patterns
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
    
    # Analytics (only if real data exists)
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
    
    # Enhanced data backup section
    st.subheader("💾 Backup & Restore")
    
    st.markdown(f'<div class="program-card">', unsafe_allow_html=True)
    st.write("**📤 Export Your Data**")
    st.write("💡 Keep your gains safe! Export includes all workouts, templates, and custom exercises.")
    
    export_filename = st.text_input("Backup filename", value=f"gym_backup_{date.today().strftime('%Y%m%d')}.json")
    
    if st.button("📤 Export Data", use_container_width=True):
        result = st.session_state.tracker.export_data(export_filename)
        if "✅" in result:
            st.success(result)
            st.balloons()
            st.info("💡 Save this file safely - it contains all your progress!")
        else:
            st.error(result)
    
    st.write("---")
    st.write("**📥 Import Data**")
    st.write("⚠️ This will add to your existing data (won't overwrite)")
    
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
    
    # Enhanced database statistics
    if st.button("📊 Detailed Statistics", use_container_width=True):
        if not df.empty:
            st.subheader("📈 Your Complete Journey")
            
            # Date range
            date_range = f"{df['date'].min().strftime('%Y-%m-%d')} to {df['date'].max().strftime('%Y-%m-%d')}"
            
            # Most frequent exercises
            top_exercises = df['exercise'].value_counts().head(5)
            
            # Body part distribution
            df_copy = df.copy()
            df_copy['body_part'] = df_copy['exercise'].apply(st.session_state.tracker.get_exercise_body_part)
            body_part_dist = df_copy['body_part'].value_counts()
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**📊 Training Statistics:**")
                st.write(f"- **Training Period:** {date_range}")
                st.write(f"- **Total Volume:** {total_volume:,.0f} kg")
                st.write(f"- **Total Reps:** {df['reps'].sum():,}")
                st.write(f"- **Days Trained:** {total_days}")
                st.write(f"- **Average Sets/Day:** {len(df)/total_days:.1f}")
                
                if avg_rpe > 0:
                    st.write(f"- **Average RPE:** {avg_rpe:.1f}")
            
            with col2:
                st.write("**🏆 Top Exercises:**")
                for i, (exercise, count) in enumerate(top_exercises.items(), 1):
                    st.write(f"{i}. **{exercise}:** {count} sets")
                
                if not body_part_dist.empty:
                    st.write("**💪 Body Part Focus:**")
                    for body_part, count in body_part_dist.head(3).items():
                        percentage = (count / len(df)) * 100
                        st.write(f"- **{body_part}:** {percentage:.1f}%")
            
            # Achievements
            st.subheader("🏆 Achievements Unlocked")
            
            achievements = []
            
            if total_volume >= 50000:
                achievements.append("🔥 Volume Master - 50,000+ kg moved!")
            elif total_volume >= 25000:
                achievements.append("💪 Volume Pro - 25,000+ kg moved!")
            elif total_volume >= 10000:
                achievements.append("🏋️ Volume Crusher - 10,000+ kg moved!")
            
            if len(df) >= 500:
                achievements.append("🎯 Set Master - 500+ sets logged!")
            elif len(df) >= 250:
                achievements.append("🎯 Set Pro - 250+ sets logged!")
            elif len(df) >= 100:
                achievements.append("🎯 Set Crusher - 100+ sets logged!")
            
            if total_days >= 100:
                achievements.append("📅 Consistency Legend - 100+ days!")
            elif total_days >= 50:
                achievements.append("📅 Consistency Master - 50+ days!")
            elif total_days >= 25:
                achievements.append("📅 Consistent Trainer - 25+ days!")
            
            if exercise_count >= 20:
                achievements.append("📝 Exercise Explorer - 20+ exercises!")
            elif exercise_count >= 10:
                achievements.append("📝 Exercise Variety - 10+ exercises!")
            
            if achievements:
                for achievement in achievements:
                    st.success(achievement)
            else:
                st.info("💪 Keep training to unlock achievements!")
        else:
            st.info("📊 No workout data yet. Start your journey!")

# ===== MAIN APP =====
def main():
    st.markdown('<h1 class="main-header">💪 Gym Tracker</h1>', unsafe_allow_html=True)
    
    # Clean, simple success message
    st.success("✅ **CLEAN & OPTIMIZED!** High contrast design, aggressive data cleaning, super readable!")
    
    # Ultra-clean mobile navigation
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

# Skip sample data creation by default
if 'sample_data_created' not in st.session_state:
    st.session_state.sample_data_created = True  # Skip sample data

# Run the beast mode app
if __name__ == "__main__":
    main()
