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

# ===== GYM TRACKER VERSION 6 CLASS =====
class GymTracker:
    def __init__(self, db_name='gym_tracker_MASTER.db'):
        """Initialize Gym Tracker - MASTER database for all future versions"""
        self.db_name = db_name
        self.init_database()
        self.migrate_old_data()  # 🆕 NEW: Migrate data from ALL previous versions
        
    def migrate_old_data(self):
        """🆕 NEW: Migrate data from ALL previous versions based on your file history"""
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
    
    # 🆕 NEW: Data Export/Import Functions
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
    
    # NEW: Delete individual sets
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
    
    # NEW: Get full day's workout with set IDs for deletion
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
    
    # NEW: Body part mapping for exercises
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

# ===== STREAMLIT APP CONFIGURATION =====
st.set_page_config(
    page_title="💪 Gym Tracker V6",
    page_icon="🏋️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Enhanced CSS for better visuals
st.markdown("""
<style>
    .main-header {
        font-size: 2.8rem;
        font-weight: bold;
        text-align: center;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 2rem;
    }
    .stButton > button {
        width: 100%;
        height: 3rem;
        font-size: 1.2rem;
        font-weight: bold;
        border-radius: 10px;
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(0,0,0,0.2);
    }
    .date-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 15px;
        margin: 1rem 0;
        text-align: center;
        box-shadow: 0 8px 25px rgba(0,0,0,0.15);
    }
    .exercise-category {
        background: linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%);
        padding: 1.5rem;
        border-radius: 15px;
        margin: 1rem 0;
        box-shadow: 0 5px 15px rgba(0,0,0,0.1);
    }
    .custom-exercise {
        background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%);
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        border-left: 5px solid #FF6B6B;
    }
    .program-card {
        background: linear-gradient(135deg, #d299c2 0%, #fef9d7 100%);
        padding: 1.5rem;
        border-radius: 15px;
        margin: 1rem 0;
        border-left: 8px solid #4ECDC4;
        box-shadow: 0 5px 20px rgba(0,0,0,0.1);
    }
    .stats-card {
        background: linear-gradient(135deg, #89f7fe 0%, #66a6ff 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 15px;
        text-align: center;
        margin: 0.5rem;
        box-shadow: 0 5px 15px rgba(0,0,0,0.2);
    }
    .workout-card {
        background: linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%);
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        border-left: 5px solid #4ECDC4;
    }
    .set-item {
        background: #f8f9fa;
        padding: 0.5rem;
        border-radius: 5px;
        margin: 0.2rem 0;
        border-left: 3px solid #17a2b8;
    }
    .delete-btn {
        background-color: #dc3545;
        color: white;
        border: none;
        border-radius: 3px;
        padding: 0.2rem 0.5rem;
        font-size: 0.8rem;
        cursor: pointer;
    }
    .notes-section {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 10px;
        border-left: 4px solid #17a2b8;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'tracker' not in st.session_state:
    st.session_state.tracker = GymTracker()

# Initialize program exercises list
if 'program_exercises' not in st.session_state:
    st.session_state.program_exercises = []

# NEW: Smart defaults for quick logging
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
    """Create sample data with enhanced features - only once"""
    tracker = st.session_state.tracker
    
    # Check if we've already created sample data before
    if st.session_state.get('sample_data_created', False):
        return
    
    df = tracker.get_data()
    if not df.empty:
        st.session_state.sample_data_created = True
        return
    
    # Only create sample data on very first run
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    today = date.today().strftime('%Y-%m-%d')
    
    # Sample workouts with notes
    tracker.log_workout(yesterday, 'Hack Squat', [
        {'reps': 12, 'weight': 80, 'rpe': 7, 'set_notes': 'Warm up set, felt good'},
        {'reps': 10, 'weight': 90, 'rpe': 8, 'set_notes': 'Working weight'},
        {'reps': 8, 'weight': 100, 'rpe': 9, 'set_notes': 'Heavy set, good depth'}
    ], "Great leg session! Gym was quiet, felt strong.")
    
    tracker.log_workout(yesterday, 'Leg Press', [
        {'reps': 15, 'weight': 150, 'rpe': 7, 'set_notes': 'Full range of motion'},
        {'reps': 12, 'weight': 170, 'rpe': 8, 'set_notes': 'Slight fatigue'}
    ], "Finished with leg press, good pump")
    
    # Mark that we've created sample data
    st.session_state.sample_data_created = True

# ===== PAGE FUNCTIONS =====

def todays_workout_page():
    """Today's workout with program support"""
    st.header("🗓️ Today's Workout")
    
    # Date selection
    col1, col2 = st.columns([1, 2])
    
    with col1:
        selected_date = st.date_input(
            "📅 Workout Date", 
            value=date.today(),
            help="Select the date for this workout"
        )
    
    with col2:
        if selected_date == date.today():
            st.markdown('<div class="date-header">🔥 <strong>TODAY\'S TRAINING SESSION</strong><br>' + 
                       selected_date.strftime('%A, %B %d, %Y') + '</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="date-header">📅 <strong>WORKOUT SESSION</strong><br>' + 
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
        
        # Progress indicator
        completed_exercises = []
        df = st.session_state.tracker.get_data()
        if not df.empty:
            today_data = df[df['date'] == date_str]
            completed_exercises = today_data['exercise'].unique().tolist()
        
        progress_percentage = (len(completed_exercises) / len(exercises)) * 100 if exercises else 0
        
        st.subheader(f"📈 Program Progress: {progress_percentage:.0f}%")
        st.progress(progress_percentage / 100)
        
        for i, exercise_info in enumerate(exercises, 1):
            exercise_name = exercise_info['exercise']
            target_sets = exercise_info.get('sets', 3)
            target_reps = exercise_info.get('reps', 10)
            exercise_notes = exercise_info.get('notes', '')
            
            # Check if exercise is completed
            is_completed = exercise_name in completed_exercises
            status_emoji = "✅" if is_completed else "⏳"
            
            with st.expander(f"{status_emoji} Exercise {i}: {exercise_name} - {target_sets} sets × {target_reps} reps", expanded=not is_completed):
                
                # Show last workout
                last_workout = get_last_workout_for_exercise(exercise_name)
                
                if last_workout is not None:
                    st.write("**📚 Last Workout Performance:**")
                    last_date = last_workout['date'].iloc[0].strftime('%Y-%m-%d')
                    st.write(f"*Date: {last_date}*")
                    
                    for _, row in last_workout.iterrows():
                        notes_text = f" - *{row['set_notes']}*" if row['set_notes'] else ""
                        st.write(f"Set {row['set_number']}: {row['reps']} reps @ {row['weight']}kg (RPE: {row['rpe']}){notes_text}")
                else:
                    st.write("**📚 First time doing this exercise!**")
                
                if exercise_notes:
                    st.markdown(f'<div class="notes-section"><strong>💡 Exercise Notes:</strong> {exercise_notes}</div>', unsafe_allow_html=True)
                
                # Enhanced logging form
                st.write("**🎯 Log Today's Sets:**")
                
                with st.form(f"log_{exercise_name.replace(' ', '_')}_{i}"):
                    col_reps, col_weight, col_rpe = st.columns(3)
                    
                    with col_reps:
                        reps = st.number_input("Reps", min_value=1, max_value=50, value=target_reps, key=f"reps_{i}")
                    with col_weight:
                        weight = st.number_input("Weight (kg)", min_value=0.0, value=0.0, step=0.625, key=f"weight_{i}")
                    with col_rpe:
                        rpe = st.selectbox("RPE", options=[6, 7, 8, 9, 10], index=2, key=f"rpe_{i}")
                    
                    set_notes = st.text_input("Set Notes", placeholder="e.g., felt heavy, good form, dropped weight...", key=f"set_notes_{i}")
                    
                    if st.form_submit_button(f"✅ Log Set for {exercise_name}", use_container_width=True):
                        result = st.session_state.tracker.log_workout(
                            date_str, 
                            exercise_name, 
                            [{'reps': reps, 'weight': weight, 'rpe': rpe, 'set_notes': set_notes}], 
                            ""
                        )
                        st.success(result)
                        st.rerun()
    
    else:
        st.info("📋 No workout program set for this date. Create one in the 'Program Creator' tab or use 'Quick Log' for freestyle training!")
    
    # Visual progress summary
    st.subheader("📊 Session Statistics")
    
    df = st.session_state.tracker.get_data()
    if not df.empty:
        today_data = df[df['date'] == date_str]
        
        if not today_data.empty:
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.markdown('<div class="stats-card">✅ <strong>Exercises</strong><br>' + 
                           str(len(today_data['exercise'].unique())) + '</div>', unsafe_allow_html=True)
            with col2:
                st.markdown('<div class="stats-card">🎯 <strong>Sets</strong><br>' + 
                           str(len(today_data)) + '</div>', unsafe_allow_html=True)
            with col3:
                st.markdown('<div class="stats-card">💪 <strong>Total Reps</strong><br>' + 
                           str(today_data['reps'].sum()) + '</div>', unsafe_allow_html=True)
            with col4:
                volume = (today_data['reps'] * today_data['weight']).sum()
                st.markdown('<div class="stats-card">🏋️ <strong>Volume</strong><br>' + 
                           f'{volume:,.0f} kg</div>', unsafe_allow_html=True)

def enhanced_quick_log_page():
    """NEW: Enhanced quick log with full day view and delete functionality"""
    st.header("📱 Quick Log & Full Day View")
    
    # Date selection
    col1, col2 = st.columns([1, 2])
    
    with col1:
        log_date = st.date_input(
            "📅 Select Date", 
            value=date.today(),
            help="Choose the date for this workout"
        )
    
    with col2:
        if log_date == date.today():
            st.markdown('<div class="date-header">🔥 <strong>TODAY\'S TRAINING</strong><br>' + 
                       log_date.strftime('%A, %B %d, %Y') + '</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="date-header">📅 <strong>WORKOUT REVIEW</strong><br>' + 
                       log_date.strftime('%A, %B %d, %Y') + '</div>', unsafe_allow_html=True)
    
    date_str = log_date.strftime('%Y-%m-%d')
    all_exercises = st.session_state.tracker.get_all_exercises()
    
    # Two columns: Quick Log and Day View
    log_col, view_col = st.columns([1, 1])
    
    with log_col:
        st.subheader("🎯 Quick Log Set")
        
        with st.form("enhanced_quick_log", clear_on_submit=True):
            # NEW: Use smart defaults from last logged exercise
            exercise_index = 0
            if st.session_state.last_exercise in all_exercises:
                exercise_index = all_exercises.index(st.session_state.last_exercise)
            
            exercise = st.selectbox("Exercise", all_exercises, index=exercise_index)
            
            col_reps, col_weight = st.columns(2)
            with col_reps:
                reps = st.number_input("Reps", min_value=1, max_value=50, value=st.session_state.last_reps)
            with col_weight:
                weight = st.number_input("Weight (kg)", min_value=0.0, value=st.session_state.last_weight, step=0.625)
            
            rpe = st.select_slider("RPE", options=[6, 7, 8, 9, 10], value=st.session_state.last_rpe)
            set_notes = st.text_area("Set Notes", placeholder="Form notes, fatigue level...")
            
            if st.form_submit_button("🚀 LOG SET", use_container_width=True):
                st.session_state.tracker.quick_log(exercise, reps, weight, rpe, set_notes, "", date_str)
                
                # NEW: Update smart defaults for next log
                st.session_state.last_exercise = exercise
                st.session_state.last_reps = reps
                st.session_state.last_weight = weight
                st.session_state.last_rpe = rpe
                
                st.success(f"✅ **{exercise}**: {reps} reps @ {weight}kg (RPE {rpe})")
                st.rerun()
    
    with view_col:
        st.subheader("📋 Full Day's Workout")
        
        # NEW: Get and display full day's workout
        daily_workout = st.session_state.tracker.get_daily_workout(date_str)
        
        if not daily_workout.empty:
            # Group by exercise
            exercises_done = daily_workout['exercise'].unique()
            
            for exercise in exercises_done:
                exercise_sets = daily_workout[daily_workout['exercise'] == exercise]
                
                st.markdown(f'<div class="workout-card">', unsafe_allow_html=True)
                st.write(f"**🏋️ {exercise}** ({len(exercise_sets)} sets)")
                
                for _, set_row in exercise_sets.iterrows():
                    col1, col2 = st.columns([4, 1])
                    
                    with col1:
                        notes_display = f" - *{set_row['set_notes']}*" if set_row['set_notes'] else ""
                        st.markdown(f'<div class="set-item">Set {set_row["set_number"]}: {set_row["reps"]} reps @ {set_row["weight"]}kg (RPE: {set_row["rpe"]}){notes_display}</div>', 
                                   unsafe_allow_html=True)
                    
                    with col2:
                        # NEW: Delete button for each set
                        if st.button("🗑️", key=f"delete_{set_row['id']}", help="Delete this set"):
                            if st.session_state.get('confirm_delete_set') == set_row['id']:
                                result = st.session_state.tracker.delete_set(set_row['id'])
                                st.success(result)
                                st.session_state.pop('confirm_delete_set', None)
                                st.rerun()
                            else:
                                st.session_state.confirm_delete_set = set_row['id']
                                st.warning("⚠️ Click again to confirm deletion")
                
                st.markdown('</div>', unsafe_allow_html=True)
            
            # Daily summary
            total_sets = len(daily_workout)
            total_reps = daily_workout['reps'].sum()
            total_volume = (daily_workout['reps'] * daily_workout['weight']).sum()
            
            st.markdown(f"""
            **📊 Daily Summary:**
            - **Exercises:** {len(exercises_done)}
            - **Total Sets:** {total_sets}
            - **Total Reps:** {total_reps}
            - **Total Volume:** {total_volume:,.0f} kg
            """)
        else:
            st.info("💡 No exercises logged for this date yet. Start logging sets above!")

def visual_progress_page():
    """Enhanced visual progress with advanced charts and body part tracking"""
    st.header("📊 Visual Progress & Analytics")
    
    df = st.session_state.tracker.get_data()
    
    if df.empty:
        st.warning("No workout data yet. Start logging workouts to see beautiful progress visuals!")
        return
    
    # Two main sections: Exercise Analysis and Body Part Tracking
    analysis_tab, body_part_tab = st.tabs(["🏋️ Exercise Analysis", "💪 Body Part Tracking"])
    
    with analysis_tab:
        # Exercise selection
        all_exercises = st.session_state.tracker.get_all_exercises()
        available_exercises = [ex for ex in all_exercises if ex in df['exercise'].unique()]
        
        if not available_exercises:
            st.warning("No exercises with logged data yet.")
            return
        
        selected_exercise = st.selectbox("🏋️ Select Exercise for Analysis", available_exercises)
        
        # Get comprehensive stats
        stats = st.session_state.tracker.get_exercise_stats(selected_exercise)
        
        if not stats:
            return
        
        # Visual statistics cards
        st.subheader(f"📈 {selected_exercise} - Complete Analysis")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown(f'<div class="stats-card">🏆 <strong>Max Weight</strong><br>{stats["max_weight"]} kg</div>', unsafe_allow_html=True)
        with col2:
            st.markdown(f'<div class="stats-card">📦 <strong>Total Volume</strong><br>{stats["total_volume"]:,.0f} kg</div>', unsafe_allow_html=True)
        with col3:
            st.markdown(f'<div class="stats-card">🎯 <strong>Total Sets</strong><br>{stats["total_sets"]}</div>', unsafe_allow_html=True)
        with col4:
            st.markdown(f'<div class="stats-card">💪 <strong>Avg RPE</strong><br>{stats["avg_rpe"]:.1f}</div>', unsafe_allow_html=True)
        
        # Multiple chart views
        chart_col1, chart_col2 = st.columns(2)
        
        with chart_col1:
            st.subheader("📈 Weight Progress")
            
            daily_stats = stats['daily_stats']
            
            fig1 = go.Figure()
            fig1.add_trace(go.Scatter(
                x=daily_stats['date'], 
                y=daily_stats['max_weight'],
                mode='lines+markers',
                name='Max Weight',
                line=dict(color='#FF6B6B', width=3),
                marker=dict(size=8)
            ))
            fig1.add_trace(go.Scatter(
                x=daily_stats['date'], 
                y=daily_stats['avg_weight'],
                mode='lines+markers',
                name='Avg Weight',
                line=dict(color='#4ECDC4', width=2),
                marker=dict(size=6)
            ))
            # NEW: Fixed date formatting
            fig1.update_layout(
                title=f'{selected_exercise} - Weight Progression',
                xaxis_title='Date',
                yaxis_title='Weight (kg)',
                height=400,
                showlegend=True,
                xaxis=dict(
                    tickformat='%Y-%m-%d',
                    tickmode='auto'
                )
            )
            st.plotly_chart(fig1, use_container_width=True)
        
        with chart_col2:
            st.subheader("📊 Volume Progress")
            
            fig2 = go.Figure()
            fig2.add_trace(go.Bar(
                x=daily_stats['date'],
                y=daily_stats['volume'],
                name='Daily Volume',
                marker_color='#667eea'
            ))
            # NEW: Fixed date formatting
            fig2.update_layout(
                title=f'{selected_exercise} - Training Volume',
                xaxis_title='Date',
                yaxis_title='Volume (kg)',
                height=400,
                xaxis=dict(
                    tickformat='%Y-%m-%d',
                    tickmode='auto'
                )
            )
            st.plotly_chart(fig2, use_container_width=True)
        
        # Advanced analytics
        st.subheader("🔬 Advanced Analytics")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**📈 Performance Trends:**")
            
            # Calculate trend
            if len(daily_stats) > 1:
                weight_trend = daily_stats['max_weight'].pct_change().mean() * 100
                volume_trend = daily_stats['volume'].pct_change().mean() * 100
                
                if weight_trend > 0:
                    st.success(f"🔥 Weight trending UP: +{weight_trend:.1f}% per workout")
                else:
                    st.warning(f"📉 Weight trending down: {weight_trend:.1f}% per workout")
                
                if volume_trend > 0:
                    st.success(f"💪 Volume trending UP: +{volume_trend:.1f}% per workout")
                else:
                    st.warning(f"📉 Volume trending down: {volume_trend:.1f}% per workout")
        
        with col2:
            st.write("**🎯 Workout Consistency:**")
            
            # Calculate workout frequency
            date_range = (daily_stats['date'].max() - daily_stats['date'].min()).days
            if date_range > 0:
                frequency = len(daily_stats) / (date_range / 7)  # workouts per week
                st.metric("📅 Frequency", f"{frequency:.1f} workouts/week")
            
            # Best performance
            best_day = daily_stats.loc[daily_stats['max_weight'].idxmax()]
            st.write(f"**🏆 Best Performance:** {best_day['max_weight']} kg on {best_day['date'].strftime('%Y-%m-%d')}")
        
        # Detailed workout log with notes
        st.subheader("📋 Detailed Workout History")
        
        exercise_data = df[df['exercise'] == selected_exercise].sort_values('date', ascending=False)
        
        # Enhanced table display
        display_data = exercise_data.copy()
        display_data['date'] = display_data['date'].dt.strftime('%Y-%m-%d')
        
        # Color code by performance
        def highlight_performance(row):
            if row['weight'] == stats['max_weight']:
                return ['background-color: #ffeb3b'] * len(row)  # Highlight PR
            return [''] * len(row)
        
        styled_df = display_data[['date', 'set_number', 'reps', 'weight', 'rpe', 'set_notes']].head(20).style.apply(highlight_performance, axis=1)
        
        st.dataframe(styled_df, use_container_width=True)
    
    # NEW: Body Part Tracking Tab
    with body_part_tab:
        st.subheader("💪 Weekly Body Part Training Analysis")
        
        # Week selection
        col1, col2 = st.columns(2)
        
        with col1:
            # Default to current week
            today = date.today()
            start_of_week = today - timedelta(days=today.weekday())
            
            week_start = st.date_input("📅 Week Start (Monday)", value=start_of_week)
        
        with col2:
            week_end = week_start + timedelta(days=6)
            st.write(f"**Week End (Sunday):** {week_end.strftime('%Y-%m-%d')}")
        
        # Get weekly body part data
        weekly_stats = st.session_state.tracker.get_weekly_body_part_volume(
            pd.to_datetime(week_start), 
            pd.to_datetime(week_end)
        )
        
        if not weekly_stats.empty:
            st.subheader(f"📊 Body Part Volume - Week of {week_start.strftime('%B %d, %Y')}")
            
            # Visual body part comparison
            col1, col2 = st.columns(2)
            
            with col1:
                # Sets per body part
                fig_sets = go.Figure(data=[
                    go.Bar(
                        x=weekly_stats.index,
                        y=weekly_stats['total_sets'],
                        marker_color='#FF6B6B'
                    )
                ])
                fig_sets.update_layout(
                    title='Sets per Body Part',
                    xaxis_title='Body Part',
                    yaxis_title='Total Sets',
                    height=400
                )
                st.plotly_chart(fig_sets, use_container_width=True)
            
            with col2:
                # Volume per body part
                fig_volume = go.Figure(data=[
                    go.Bar(
                        x=weekly_stats.index,
                        y=weekly_stats['total_volume'],
                        marker_color='#4ECDC4'
                    )
                ])
                fig_volume.update_layout(
                    title='Training Volume per Body Part',
                    xaxis_title='Body Part',
                    yaxis_title='Total Volume (kg)',
                    height=400
                )
                st.plotly_chart(fig_volume, use_container_width=True)
            
            # Detailed breakdown
            st.subheader("📋 Detailed Body Part Breakdown")
            
            # Create columns for stats display
            body_parts = weekly_stats.index.tolist()
            
            for i, body_part in enumerate(body_parts):
                row_data = weekly_stats.loc[body_part]
                
                # Color coding for balance
                sets = int(row_data['total_sets'])
                if sets >= 12:
                    status = "🟢 Well Trained"
                    color = "#d4edda"
                elif sets >= 6:
                    status = "🟡 Moderate"
                    color = "#fff3cd"
                else:
                    status = "🔴 Under Trained"
                    color = "#f8d7da"
                
                st.markdown(f"""
                <div style="background-color: {color}; padding: 1rem; border-radius: 10px; margin: 0.5rem 0;">
                    <strong>💪 {body_part}</strong> - {status}<br>
                    📊 <strong>Sets:</strong> {sets} | 
                    🎯 <strong>Reps:</strong> {int(row_data['total_reps'])} | 
                    🏋️ <strong>Volume:</strong> {row_data['total_volume']:,.0f} kg
                </div>
                """, unsafe_allow_html=True)
            
            # Training balance recommendations
            st.subheader("💡 Training Balance Recommendations")
            
            under_trained = weekly_stats[weekly_stats['total_sets'] < 6].index.tolist()
            over_trained = weekly_stats[weekly_stats['total_sets'] > 20].index.tolist()
            
            if under_trained:
                st.warning(f"🔴 **Under-trained body parts:** {', '.join(under_trained)}")
                st.write("💡 Consider adding more exercises for these muscle groups")
            
            if over_trained:
                st.warning(f"🟠 **Potentially over-trained:** {', '.join(over_trained)}")
                st.write("💡 Consider reducing volume or ensuring adequate recovery")
            
            if not under_trained and not over_trained:
                st.success("🎉 **Great balance!** Your training seems well distributed across body parts")
        
        else:
            st.info(f"📅 No workout data found for the week of {week_start.strftime('%B %d, %Y')}. Select a different week or start logging workouts!")

def program_creator_page():
    """Enhanced program creator with template management"""
    st.header("📅 Workout Program Creator & Template Manager")
    
    # Template management tabs
    template_tab, create_tab = st.tabs(["📚 Template Library", "🆕 Create Program"])
    
    with template_tab:
        st.subheader("📚 Your Template Library")
        
        # Template filters
        col1, col2, col3 = st.columns(3)
        
        with col1:
            categories = ["All"] + st.session_state.tracker.get_template_categories()
            selected_category = st.selectbox("Filter by Category", categories)
        
        with col2:
            creators = ["All", "Personal Trainer", "Exercise Physiologist", "Myself"]
            selected_creator = st.selectbox("Filter by Creator", creators)
        
        with col3:
            if st.button("🔄 Refresh Templates", use_container_width=True):
                st.rerun()
        
        # Get filtered templates
        filter_category = None if selected_category == "All" else selected_category
        filter_creator = None if selected_creator == "All" else selected_creator
        
        templates = st.session_state.tracker.get_templates(filter_category, filter_creator)
        
        if templates:
            # Display templates in an organized way
            for template in templates:
                with st.expander(f"📋 {template['name']} ({template['category']})", expanded=False):
                    
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.write(f"**👨‍⚕️ Created by:** {template['created_by']}")
                        st.write(f"**📅 Created:** {template['created_at'][:10]}")
                        if template['last_used']:
                            st.write(f"**🕐 Last Used:** {template['last_used'][:10]}")
                        
                        if template['description']:
                            st.markdown(f'<div class="notes-section"><strong>📝 Description:</strong><br>{template["description"]}</div>', unsafe_allow_html=True)
                        
                        # Show exercises
                        st.write("**🏋️ Exercises:**")
                        for i, ex in enumerate(template['exercises'], 1):
                            rest_text = f" (Rest: {ex.get('rest', 90)}s)" if ex.get('rest') else ""
                            st.write(f"{i}. **{ex['exercise']}** - {ex['sets']} sets × {ex['reps']} reps{rest_text}")
                            if ex.get('notes'):
                                st.write(f"   💡 *{ex['notes']}*")
                    
                    with col2:
                        # Template actions
                        if st.button(f"📅 Use Template", key=f"use_{template['id']}", use_container_width=True):
                            st.session_state.program_exercises = template['exercises'].copy()
                            st.success(f"✅ Loaded template: {template['name']}")
                            st.rerun()
                        
                        if st.button(f"📝 Edit", key=f"edit_{template['id']}", use_container_width=True):
                            st.session_state.program_exercises = template['exercises'].copy()
                            st.session_state.editing_template = template
                            st.success(f"✅ Editing template: {template['name']}")
                            st.rerun()
                        
                        if st.button(f"🗑️ Delete", key=f"del_{template['id']}", use_container_width=True):
                            if st.session_state.get('confirm_delete') == template['id']:
                                result = st.session_state.tracker.delete_template(template['id'])
                                st.success(result)
                                st.session_state.pop('confirm_delete', None)
                                st.rerun()
                            else:
                                st.session_state.confirm_delete = template['id']
                                st.warning("⚠️ Click again to confirm deletion")
        else:
            st.info("📋 No templates found. Create your first template below!")
    
    with create_tab:
        st.subheader("🆕 Create New Program/Template")
        
        # Check if we're editing an existing template
        editing_template = st.session_state.get('editing_template')
        
        if editing_template:
            st.info(f"✏️ Editing template: **{editing_template['name']}**")
            default_name = editing_template['name']
            default_category = editing_template['category']
            default_description = editing_template['description']
            default_creator = editing_template['created_by']
        else:
            default_name = f"Training Session - {date.today().strftime('%b %d')}"
            default_category = "Custom"
            default_description = ""
            default_creator = "Personal Trainer"
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            program_date = st.date_input("📅 Program Date", value=date.today())
            program_name = st.text_input("Program Name", value=default_name)
            
            # Template-specific fields
            template_category = st.selectbox("Template Category", [
                "Strength Training", "Cardio", "Flexibility", "Rehabilitation", 
                "Upper Body", "Lower Body", "Full Body", "Sport Specific", "Custom"
            ], index=8)
            
            created_by = st.selectbox("Created By", ["Personal Trainer", "Exercise Physiologist", "Myself", "Other"])
            
            if created_by == "Other":
                created_by = st.text_input("Creator Name")
            
            program_notes = st.text_area("Program/Template Description", value=default_description,
                                       placeholder="Overall session goals, focus areas, special instructions...")
            
            # Template save options
            save_as_template = st.checkbox("💾 Save as Template", value=True, 
                                         help="Save this program as a reusable template")
        
        with col2:
            st.write("**📋 Quick Templates:**")
            
            if st.button("💪 Upper Body Strength", use_container_width=True):
                st.session_state.program_exercises = [
                    {'exercise': 'Bench Press', 'sets': 4, 'reps': 6, 'rest': 120, 'notes': 'Heavy compound movement, focus on control'},
                    {'exercise': 'Inclined Smith Machine Chest Press', 'sets': 3, 'reps': 8, 'rest': 90, 'notes': 'Upper chest development'},
                    {'exercise': 'Machine Shoulder Press', 'sets': 3, 'reps': 10, 'rest': 90, 'notes': 'Shoulder stability'},
                    {'exercise': 'Chest Supported Row', 'sets': 3, 'reps': 10, 'rest': 90, 'notes': 'Back development, squeeze shoulder blades'},
                    {'exercise': 'Lateral Raises', 'sets': 3, 'reps': 12, 'rest': 60, 'notes': 'Controlled movement, slight lean forward'},
                    {'exercise': 'Bicep Curls', 'sets': 3, 'reps': 12, 'rest': 60, 'notes': 'Controlled movement'},
                    {'exercise': 'Tricep Pushdown', 'sets': 3, 'reps': 12, 'rest': 60, 'notes': 'Full range of motion'}
                ]
                st.rerun()
            
            if st.button("🦵 Lower Body Power", use_container_width=True):
                st.session_state.program_exercises = [
                    {'exercise': 'Hack Squat', 'sets': 4, 'reps': 8, 'rest': 120, 'notes': 'Focus on depth and control'},
                    {'exercise': 'RDL', 'sets': 3, 'reps': 10, 'rest': 90, 'notes': 'Hip hinge pattern, feel hamstring stretch'},
                    {'exercise': 'Leg Press', 'sets': 3, 'reps': 15, 'rest': 90, 'notes': 'Full range of motion'},
                    {'exercise': 'Lying Hamstring Curl', 'sets': 3, 'reps': 12, 'rest': 75, 'notes': 'Slow negatives'},
                    {'exercise': 'Leg Extension', 'sets': 3, 'reps': 15, 'rest': 75, 'notes': 'Quad isolation'},
                    {'exercise': 'Calf Raises', 'sets': 4, 'reps': 20, 'rest': 60, 'notes': 'Pause at top'}
                ]
                st.rerun()
            
            if st.button("🔄 Full Body Circuit", use_container_width=True):
                st.session_state.program_exercises = [
                    {'exercise': 'Squat', 'sets': 3, 'reps': 10, 'rest': 120, 'notes': 'Compound movement'},
                    {'exercise': 'Bench Press', 'sets': 3, 'reps': 8, 'rest': 120, 'notes': 'Upper body power'},
                    {'exercise': 'Deadlift', 'sets': 3, 'reps': 5, 'rest': 150, 'notes': 'Posterior chain focus'},
                    {'exercise': 'Overhead Press', 'sets': 3, 'reps': 10, 'rest': 90, 'notes': 'Shoulder strength'},
                    {'exercise': 'Barbell Row', 'sets': 3, 'reps': 10, 'rest': 90, 'notes': 'Back development'}
                ]
                st.rerun()
        
        # Exercise builder
        st.subheader("🏋️ Build Exercise List")
        
        # Add exercise to program
        with st.expander("➕ Add Exercise to Program", expanded=True):
            col1, col2, col3, col4, col5 = st.columns(5)
            
            all_exercises = st.session_state.tracker.get_all_exercises()
            
            with col1:
                exercise_name = st.selectbox("Exercise", all_exercises, key="prog_exercise")
            with col2:
                sets = st.number_input("Sets", min_value=1, max_value=10, value=3, key="prog_sets")
            with col3:
                reps = st.number_input("Target Reps", min_value=1, max_value=50, value=10, key="prog_reps")
            with col4:
                rest_time = st.number_input("Rest (sec)", min_value=30, max_value=300, value=90, step=15, key="prog_rest")
            with col5:
                if st.button("➕ Add", use_container_width=True, key="add_exercise_btn"):
                    exercise_notes = st.text_input("Exercise Notes", key="prog_notes_input", 
                                                 placeholder="Form cues, focus points...")
                    
                    new_exercise = {
                        'exercise': exercise_name,
                        'sets': sets,
                        'reps': reps,
                        'rest': rest_time,
                        'notes': exercise_notes
                    }
                    st.session_state.program_exercises.append(new_exercise)
                    st.success(f"✅ Added {exercise_name}")
                    st.rerun()
        
        # Show current program
        if st.session_state.program_exercises:
            st.subheader("📋 Current Program")
            
            st.markdown('<div class="program-card">', unsafe_allow_html=True)
            
            for i, ex in enumerate(st.session_state.program_exercises):
                col1, col2 = st.columns([5, 1])
                
                with col1:
                    rest_text = f" (Rest: {ex.get('rest', 90)}s)" if ex.get('rest') else ""
                    st.write(f"**{i+1}. {ex['exercise']}** - {ex['sets']} sets × {ex['reps']} reps{rest_text}")
                    if ex.get('notes'):
                        st.write(f"   💡 *{ex['notes']}*")
                
                with col2:
                    if st.button("🗑️", key=f"remove_{i}", help="Remove exercise"):
                        st.session_state.program_exercises.pop(i)
                        st.rerun()
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Save options
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                if st.button("💾 Save Program", use_container_width=True):
                    if program_name and st.session_state.program_exercises:
                        date_str = program_date.strftime('%Y-%m-%d')
                        result = st.session_state.tracker.create_daily_program(
                            date_str, program_name, created_by, program_notes, st.session_state.program_exercises
                        )
                        st.success(result)
                        
                        # Also save as template if requested
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
                        st.error("❌ Please enter program name and add exercises")
            
            with col2:
                if save_as_template and st.button("💾 Save Template Only", use_container_width=True):
                    if program_name and st.session_state.program_exercises:
                        result = st.session_state.tracker.save_template(
                            program_name, template_category, program_notes, created_by, 
                            st.session_state.program_exercises
                        )
                        if "successfully" in result:
                            st.success(result)
                            st.balloons()
                        else:
                            st.error(result)
                        st.session_state.program_exercises = []
                        st.session_state.pop('editing_template', None)
                        st.rerun()
                    else:
                        st.error("❌ Please enter template name and add exercises")
            
            with col3:
                if editing_template and st.button("💾 Update Template", use_container_width=True):
                    # Delete old template and create new one
                    st.session_state.tracker.delete_template(editing_template['id'])
                    result = st.session_state.tracker.save_template(
                        program_name, template_category, program_notes, created_by, 
                        st.session_state.program_exercises
                    )
                    st.success("✅ Template updated successfully!")
                    st.session_state.program_exercises = []
                    st.session_state.pop('editing_template', None)
                    st.rerun()
            
            with col4:
                if st.button("🗑️ Clear All", use_container_width=True):
                    st.session_state.program_exercises = []
                    st.session_state.pop('editing_template', None)
                    st.rerun()

def add_exercises_page():
    """Enhanced add exercises page"""
    st.header("➕ Manage Your Exercises")
    
    # Add new exercise
    st.subheader("🆕 Create Custom Exercise")
    
    with st.form("add_exercise_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            exercise_name = st.text_input("Exercise Name", placeholder="e.g., Cable Crossover High to Low")
            category = st.selectbox("Category", [
                "Chest", "Back", "Shoulders", "Arms", "Legs", "Core", "Cardio", "Full Body", "Other"
            ])
        
        with col2:
            description = st.text_area("Description", placeholder="Setup instructions, form cues, equipment needed...")
        
        if st.form_submit_button("➕ Create Exercise", use_container_width=True):
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
    
    # Show existing custom exercises
    st.subheader("🌟 Your Custom Exercises")
    
    custom_exercises_df = st.session_state.tracker.get_custom_exercises()
    
    if not custom_exercises_df.empty:
        # Group by category with enhanced display
        for category in custom_exercises_df['category'].unique():
            st.markdown(f'<div class="exercise-category">', unsafe_allow_html=True)
            st.write(f"**📂 {category} Exercises ({len(custom_exercises_df[custom_exercises_df['category'] == category])})**")
            
            category_exercises = custom_exercises_df[custom_exercises_df['category'] == category]
            
            for _, exercise in category_exercises.iterrows():
                st.markdown(f'<div class="custom-exercise">', unsafe_allow_html=True)
                st.write(f"**🌟 {exercise['exercise_name']}**")
                if exercise['description']:
                    st.write(f"💡 *{exercise['description']}*")
                st.write(f"📅 *Added: {exercise['created_at']}*")
                st.markdown('</div>', unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("🎯 No custom exercises yet. Create your first one above!")

def data_manager_page():
    """NEW: Data backup, migration, and management"""
    st.header("💾 Data Manager")
    
    # Current data overview
    st.subheader("📊 Your Data Overview")
    
    df = st.session_state.tracker.get_data()
    templates = st.session_state.tracker.get_templates()
    custom_exercises = st.session_state.tracker.get_custom_exercises()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        workout_count = len(df) if not df.empty else 0
        st.markdown(f'<div class="stats-card">🏋️ <strong>Total Sets</strong><br>{workout_count}</div>', unsafe_allow_html=True)
    
    with col2:
        exercise_count = len(df['exercise'].unique()) if not df.empty else 0
        st.markdown(f'<div class="stats-card">📝 <strong>Exercises</strong><br>{exercise_count}</div>', unsafe_allow_html=True)
    
    with col3:
        template_count = len(templates)
        st.markdown(f'<div class="stats-card">📋 <strong>Templates</strong><br>{template_count}</div>', unsafe_allow_html=True)
    
    with col4:
        custom_count = len(custom_exercises) if not custom_exercises.empty else 0
        st.markdown(f'<div class="stats-card">⭐ <strong>Custom Exercises</strong><br>{custom_count}</div>', unsafe_allow_html=True)
    
    # Data backup section
    st.subheader("💾 Data Backup & Restore")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f'<div class="program-card">', unsafe_allow_html=True)
        st.write("**📤 Export Your Data**")
        st.write("Create a backup file with all your workouts, templates, and custom exercises.")
        
        export_filename = st.text_input("Backup filename", value=f"gym_backup_{date.today().strftime('%Y%m%d')}.json")
        
        if st.button("📤 Export Data", use_container_width=True):
            result = st.session_state.tracker.export_data(export_filename)
            if "✅" in result:
                st.success(result)
                st.balloons()
                st.info("💡 Save this file safely! You can use it to restore your data later.")
            else:
                st.error(result)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown(f'<div class="program-card">', unsafe_allow_html=True)
        st.write("**📥 Import Data**")
        st.write("Restore data from a backup file. This will add to your existing data.")
        
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
    
    # Migration info
    st.subheader("🔄 Version Migration")
    
    st.markdown(f'<div class="notes-section">', unsafe_allow_html=True)
    st.write("**🛡️ Data Protection Features:**")
    st.write("✅ **Automatic Migration:** When you upgrade versions, your data automatically transfers")
    st.write("✅ **Consistent Database:** All versions now use the same database file (`gym_tracker_MASTER.db`)")
    st.write("✅ **Manual Backup:** Export your data anytime for extra safety")
    st.write("✅ **Import/Restore:** Easily restore from backup files")
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Data maintenance
    st.subheader("🧹 Data Maintenance")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📊 Database Statistics", use_container_width=True):
            if not df.empty:
                st.write("**📈 Workout Statistics:**")
                st.write(f"- **Date Range:** {df['date'].min().strftime('%Y-%m-%d')} to {df['date'].max().strftime('%Y-%m-%d')}")
                st.write(f"- **Total Volume:** {(df['reps'] * df['weight']).sum():,.0f} kg")
                st.write(f"- **Average RPE:** {df['rpe'].mean():.1f}")
                st.write(f"- **Days Trained:** {len(df['date'].unique())}")
            else:
                st.info("No workout data yet!")
    
    with col2:
        st.warning("⚠️ **Danger Zone**")
        if st.button("🗑️ Clear Sample Data", use_container_width=True):
            if st.session_state.get('confirm_clear_sample'):
                # Delete sample data (data from before today)
                today_str = date.today().strftime('%Y-%m-%d')
                conn = sqlite3.connect(st.session_state.tracker.db_name)
                cursor = conn.cursor()
                cursor.execute('DELETE FROM workouts WHERE date < ?', (today_str,))
                deleted = cursor.rowcount
                conn.commit()
                conn.close()
                
                st.success(f"✅ Deleted {deleted} sample workout records")
                st.session_state.pop('confirm_clear_sample', None)
                st.rerun()
            else:
                st.session_state.confirm_clear_sample = True
                st.warning("⚠️ Click again to confirm deletion of sample data")
    
    # Tips
    st.subheader("💡 Data Management Tips")
    
    st.info("""
    **📱 For Mobile Use:**
    - Export your data before major app updates
    - Keep backup files in cloud storage (Google Drive, iCloud)
    - Your data automatically syncs between devices when using the cloud version
    
    **🔒 Data Safety:**
    - Regular backups ensure you never lose workout history
    - The app now preserves data between version updates
    - Export before trying experimental features
    """)

# ===== MAIN APP NAVIGATION =====
def main():
    st.markdown('<h1 class="main-header">💪 Gym Tracker Version 6</h1>', unsafe_allow_html=True)
    
    # Success message with enhanced styling
    st.success("🎉 **VERSION 6 FEATURES!** ✅ Smart exercise defaults ✅ Clean date charts ✅ Body part tracking ✅ Data preservation ✅ Complete mobile ready!")
    
    # Enhanced Navigation with Data Management
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "🏋️ Today's Workout", 
        "📱 Quick Log & Day View", 
        "📊 Visual Progress", 
        "📅 Program Creator",
        "➕ Add Exercises",
        "💾 Data Manager"
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

# Only create sample data if this is a new installation
if 'sample_data_created' not in st.session_state:
    create_sample_data()

# Run the app
if __name__ == "__main__":
    main()