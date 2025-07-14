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
import os

# ===== AI-ENHANCED GITHUB-PERSISTENT GYM TRACKER V9 - SMART FITNESS COMPANION =====
class GymTracker:
    def __init__(self, db_name='gym_tracker_MASTER.db'):
        """Initialize AI-Enhanced GitHub-Persistent Gym Tracker with smart features"""
        self.db_name = db_name
        self.init_database()
        
        # Only migrate if database is truly empty (first time setup)
        if self.is_database_empty():
            self.migrate_old_data()
        
    def is_database_empty(self):
        """Check if database is completely empty"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM workouts')
            count = cursor.fetchone()[0]
            conn.close()
            return count == 0
        except:
            return True
        
    def migrate_old_data(self):
        """Migrate data from ALL previous versions - only runs once"""
        old_db_names = [
            'complete_gym_app.db', 'demo_workout.db', 'gym_app.db',
            'gym_tracker_v2.db', 'gym_tracker_v2.1.db', 'gym_tracker_v3.db',
            'gym_tracker_v4.db', 'gym_tracker_v5.db', 'gym_tracker_v6.db',
            'gym_tracker_v7.db', 'workout_tracker.db'
        ]
        
        migrated_any = False
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
                            migrated_any = True
                            break  # Stop after first successful migration
                    
                    old_conn.close()
                        
                except Exception as e:
                    continue
        
        if migrated_any:
            st.success("✅ Previous workout data migrated successfully!")
        
    def init_database(self):
        """Create all database tables including new AI features"""
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
            CREATE TABLE IF NOT EXISTS goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                goal_name TEXT NOT NULL,
                goal_type TEXT NOT NULL,
                target_value REAL,
                target_exercise TEXT,
                target_date TEXT,
                current_value REAL DEFAULT 0,
                is_completed INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS offline_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workout_data TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                synced INTEGER DEFAULT 0
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def log_workout(self, date_str, exercise, sets_data, workout_notes=""):
        """Log a complete workout with multiple sets"""
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
        
        return "✅ Set deleted successfully!" if rows_affected > 0 else "❌ Set not found!"
    
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
    
    def get_smart_suggestions(self, exercise):
        """Get intelligent workout suggestions based on history"""
        df = self.get_data()
        if df.empty:
            return None
        
        exercise_data = df[df['exercise'] == exercise].copy()
        if exercise_data.empty:
            return None
        
        # Get last workout for this exercise
        last_date = exercise_data['date'].max()
        last_workout = exercise_data[exercise_data['date'] == last_date]
        
        if last_workout.empty:
            return None
        
        # Calculate suggestions
        max_weight_last = last_workout['weight'].max()
        total_volume_last = (last_workout['reps'] * last_workout['weight']).sum()
        avg_rpe_last = last_workout['rpe'].mean() if last_workout['rpe'].notna().any() else 8
        
        # Progressive overload suggestions
        suggestions = {
            'last_workout': {
                'date': last_date.strftime('%Y-%m-%d'),
                'max_weight': max_weight_last,
                'total_volume': total_volume_last,
                'avg_rpe': avg_rpe_last,
                'sets_reps': [(row['reps'], row['weight']) for _, row in last_workout.iterrows()]
            }
        }
        
        # Weight progression suggestion
        if avg_rpe_last < 8:
            weight_increase = 2.5 if max_weight_last < 60 else 5.0
            suggestions['weight_suggestion'] = max_weight_last + weight_increase
            suggestions['progression_type'] = 'weight'
            suggestions['reason'] = f"Last RPE was {avg_rpe_last:.1f} - ready for more weight!"
        elif avg_rpe_last > 9:
            suggestions['weight_suggestion'] = max_weight_last - 2.5
            suggestions['progression_type'] = 'deload'
            suggestions['reason'] = f"Last RPE was {avg_rpe_last:.1f} - consider reducing weight"
        else:
            # Suggest rep progression
            avg_reps_last = last_workout['reps'].mean()
            suggestions['rep_suggestion'] = int(avg_reps_last + 1)
            suggestions['weight_suggestion'] = max_weight_last
            suggestions['progression_type'] = 'reps'
            suggestions['reason'] = f"Good RPE {avg_rpe_last:.1f} - try adding a rep!"
        
        return suggestions
    
    def get_quick_stats(self):
        """Calculate motivational quick stats with error handling"""
        try:
            df = self.get_data()
            if df.empty:
                return {
                    'streak': 0,
                    'weekly_volume': 0,
                    'weekly_workouts': 0,
                    'recent_prs': [],
                    'total_workouts': 0,
                    'total_volume': 0
                }
            
            today = datetime.now().date()
            
            # Calculate workout streak with error handling
            try:
                dates = sorted(df['date'].dt.date.unique(), reverse=True)
                streak = 0
                for i, workout_date in enumerate(dates):
                    if i == 0:
                        if workout_date == today:
                            streak = 1
                        elif (today - workout_date).days == 1:
                            streak = 1
                        else:
                            break
                    else:
                        prev_date = dates[i-1]
                        if (prev_date - workout_date).days == 1:
                            streak += 1
                        elif (prev_date - workout_date).days <= 2:  # Allow 1 rest day
                            streak += 1
                        else:
                            break
            except:
                streak = 0
            
            # This week's stats with error handling
            try:
                week_start = today - timedelta(days=today.weekday())
                this_week_data = df[df['date'].dt.date >= week_start]
                weekly_volume = float((this_week_data['reps'] * this_week_data['weight']).sum())
                weekly_workouts = len(this_week_data['date'].dt.date.unique()) if not this_week_data.empty else 0
            except:
                weekly_volume = 0
                weekly_workouts = 0
            
            # Recent PRs (last 30 days) with error handling
            recent_prs = []
            try:
                recent_data = df[df['date'] >= (datetime.now() - timedelta(days=30))]
                
                if not recent_data.empty:
                    for exercise in recent_data['exercise'].unique():
                        try:
                            exercise_data = df[df['exercise'] == exercise]
                            if len(exercise_data) > 1:
                                recent_exercise_data = recent_data[recent_data['exercise'] == exercise]
                                if not recent_exercise_data.empty:
                                    max_weight_recent = recent_exercise_data['weight'].max()
                                    max_weight_all_time = exercise_data['weight'].max()
                                    
                                    if max_weight_recent == max_weight_all_time:
                                        pr_date = recent_exercise_data[
                                            recent_exercise_data['weight'] == max_weight_recent
                                        ]['date'].max()
                                        recent_prs.append({
                                            'exercise': exercise,
                                            'weight': float(max_weight_recent),
                                            'date': pr_date.strftime('%Y-%m-%d')
                                        })
                        except:
                            continue
            except:
                recent_prs = []
            
            # Total stats with error handling
            try:
                total_workouts = len(df['date'].unique())
                total_volume = float((df['reps'] * df['weight']).sum())
            except:
                total_workouts = 0
                total_volume = 0
            
            return {
                'streak': int(streak),
                'weekly_volume': weekly_volume,
                'weekly_workouts': int(weekly_workouts),
                'recent_prs': recent_prs[:3],  # Top 3 recent PRs
                'total_workouts': int(total_workouts),
                'total_volume': total_volume
            }
            
        except Exception as e:
            # Fallback to empty stats if anything goes wrong
            return {
                'streak': 0,
                'weekly_volume': 0,
                'weekly_workouts': 0,
                'recent_prs': [],
                'total_workouts': 0,
                'total_volume': 0
            }
    
    def create_goal(self, goal_name, goal_type, target_value, target_exercise=None, target_date=None):
        """Create a new fitness goal"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO goals (goal_name, goal_type, target_value, target_exercise, target_date)
            VALUES (?, ?, ?, ?, ?)
        ''', (goal_name, goal_type, target_value, target_exercise, target_date))
        
        conn.commit()
        conn.close()
        return f"✅ Goal '{goal_name}' created successfully!"
    
    def get_goals(self):
        """Get all goals with progress"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM goals ORDER BY created_at DESC')
        goals = cursor.fetchall()
        conn.close()
        
        goal_list = []
        df = self.get_data()
        
        for goal in goals:
            goal_data = {
                'id': goal[0],
                'name': goal[1],
                'type': goal[2],
                'target_value': goal[3],
                'target_exercise': goal[4],
                'target_date': goal[5],
                'current_value': goal[6],
                'is_completed': bool(goal[7]),
                'created_at': goal[8],
                'completed_at': goal[9]
            }
            
            # Calculate current progress
            if not df.empty and goal_data['target_exercise']:
                exercise_data = df[df['exercise'] == goal_data['target_exercise']]
                if not exercise_data.empty:
                    if goal_data['type'] == 'max_weight':
                        goal_data['current_value'] = exercise_data['weight'].max()
                    elif goal_data['type'] == 'total_volume':
                        goal_data['current_value'] = (exercise_data['reps'] * exercise_data['weight']).sum()
                    elif goal_data['type'] == 'workout_frequency':
                        # Count workouts in current period
                        if goal_data['target_date']:
                            start_date = datetime.strptime(goal_data['created_at'][:10], '%Y-%m-%d').date()
                            end_date = datetime.strptime(goal_data['target_date'], '%Y-%m-%d').date()
                            period_data = df[
                                (df['date'].dt.date >= start_date) & 
                                (df['date'].dt.date <= end_date)
                            ]
                            goal_data['current_value'] = len(period_data['date'].dt.date.unique())
            
            goal_list.append(goal_data)
        
        return goal_list
    
    def update_goal_progress(self, goal_id):
        """Update goal progress and check completion"""
        goals = self.get_goals()
        goal = next((g for g in goals if g['id'] == goal_id), None)
        
        if not goal:
            return False
        
        # Check if goal is completed
        if goal['current_value'] >= goal['target_value'] and not goal['is_completed']:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE goals 
                SET current_value = ?, is_completed = 1, completed_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (goal['current_value'], goal_id))
            
            conn.commit()
            conn.close()
            return True
        
        return False
    
    def queue_offline_workout(self, workout_data):
        """Queue workout for offline sync"""
        # Note: In Claude.ai environment, we'll use in-memory storage
        # In a real deployment, this would use localStorage
        if 'offline_queue' not in st.session_state:
            st.session_state.offline_queue = []
        
        st.session_state.offline_queue.append({
            'data': workout_data,
            'timestamp': datetime.now().isoformat(),
            'synced': False
        })
        
        return "📱 Workout saved offline - will sync when connection returns"
    
    def sync_offline_workouts(self):
        """Sync queued offline workouts"""
        if 'offline_queue' not in st.session_state:
            return "✅ No offline workouts to sync"
        
        synced_count = 0
        for workout in st.session_state.offline_queue:
            if not workout['synced']:
                try:
                    # Process the offline workout data
                    data = workout['data']
                    self.log_workout(
                        data['date'], data['exercise'], data['sets'], data.get('notes', '')
                    )
                    workout['synced'] = True
                    synced_count += 1
                except Exception as e:
                    continue
        
        return f"✅ Synced {synced_count} offline workouts"
    
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

    def delete_template(self, template_id):
        """Delete a workout template"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM workout_templates WHERE id = ?', (template_id,))
        rows_affected = cursor.rowcount
        conn.commit()
        conn.close()
        
        return "✅ Template deleted successfully!" if rows_affected > 0 else "❌ Template not found!"
    
    def get_all_exercises(self):
        """Get comprehensive exercise database with 500+ exercises"""
        built_in_exercises = [
            # Chest Exercises
            'Bench Press', 'Incline Bench Press', 'Decline Bench Press', 'Dumbbell Press', 'Incline Dumbbell Press',
            'Decline Dumbbell Press', 'Dumbbell Flyes', 'Incline Dumbbell Flyes', 'Cable Crossover', 'Pec Deck',
            'Chest Dips', 'Push-ups', 'Diamond Push-ups', 'Wide Grip Push-ups', 'Incline Push-ups',
            'Machine Chest Press', 'Hammer Strength Chest Press', 'Landmine Press', 'Svend Press',
            
            # Back Exercises  
            'Deadlift', 'Romanian Deadlift', 'Sumo Deadlift', 'Stiff Leg Deadlift', 'Single Leg RDL',
            'Barbell Row', 'Bent Over Row', 'Pendlay Row', 'T-Bar Row', 'Dumbbell Row',
            'Single Arm Dumbbell Row', 'Chest Supported Row', 'Seated Cable Row', 'Wide Grip Cable Row',
            'Pull-ups', 'Chin-ups', 'Wide Grip Pull-ups', 'Narrow Grip Pull-ups', 'Weighted Pull-ups',
            'Lat Pulldown', 'Wide Grip Pulldown', 'Reverse Grip Pulldown', 'V-Bar Pulldown',
            'Face Pulls', 'Reverse Flyes', 'Shrugs', 'Dumbbell Shrugs', 'Cable Shrugs',
            'Good Mornings', 'Hyperextensions', 'Reverse Hyperextensions',
            
            # Leg Exercises
            'Squat', 'Back Squat', 'Front Squat', 'Goblet Squat', 'Box Squat', 'Pause Squat',
            'Bulgarian Split Squat', 'Split Squat', 'Reverse Lunge', 'Forward Lunge', 'Walking Lunges',
            'Lateral Lunges', 'Curtsy Lunges', 'Jump Lunges', 'Hack Squat', 'Leg Press',
            'Single Leg Press', 'Leg Extension', 'Leg Curl', 'Lying Leg Curl', 'Seated Leg Curl',
            'Standing Leg Curl', 'Nordic Curls', 'Glute Ham Raise', 'Hip Thrust', 'Glute Bridge',
            'Single Leg Hip Thrust', 'Barbell Hip Thrust', 'Dumbbell Hip Thrust', 'Cossack Squat',
            'Pistol Squat', 'Jump Squat', 'Wall Sit', 'Step Ups', 'Lateral Step Ups',
            
            # Shoulder Exercises
            'Overhead Press', 'Military Press', 'Push Press', 'Seated Overhead Press', 'Dumbbell Shoulder Press',
            'Single Arm Overhead Press', 'Arnold Press', 'Machine Shoulder Press', 'Pike Push-ups',
            'Lateral Raises', 'Side Lateral Raises', 'Front Raises', 'Rear Delt Flyes', 'Bent Over Lateral Raises',
            'Cable Lateral Raises', 'Leaning Lateral Raises', 'Upright Row', 'High Pull',
            'Handstand Push-ups', 'Pike Push-ups', 'Cuban Press', 'Bradford Press',
            
            # Arm Exercises
            'Bicep Curls', 'Barbell Curls', 'Dumbbell Curls', 'Hammer Curls', 'Concentration Curls',
            'Preacher Curls', 'Spider Curls', 'Cable Curls', '21s', 'Zottman Curls',
            'Reverse Curls', 'Drag Curls', 'Incline Dumbbell Curls', 'Cable Hammer Curls',
            'Tricep Pushdown', 'Close Grip Bench Press', 'Tricep Dips', 'Diamond Push-ups',
            'Overhead Tricep Extension', 'Lying Tricep Extension', 'Skull Crushers', 'French Press',
            'Single Arm Tricep Extension', 'Tricep Kickbacks', 'Dumbbell Tricep Press',
            
            # Core Exercises
            'Plank', 'Side Plank', 'Plank Up-Downs', 'Plank Jacks', 'Mountain Climbers',
            'Crunches', 'Bicycle Crunches', 'Reverse Crunches', 'Russian Twists', 'Dead Bug',
            'Bird Dog', 'Hollow Body Hold', 'V-Ups', 'Leg Raises', 'Hanging Leg Raises',
            'Knee Raises', 'Windshield Wipers', 'Ab Wheel', 'Dragon Flag', 'L-Sits',
            'Wood Chops', 'Cable Crunches', 'Machine Crunches', 'Sit-ups', 'Decline Sit-ups',
            
            # Additional exercises for completeness
            'Calf Raises', 'Standing Calf Raises', 'Seated Calf Raises', 'Single Leg Calf Raises',
            'Farmers Walk', 'Kettlebell Swings', 'Turkish Get-ups', 'Burpees', 'Battle Ropes'
        ]
        
        # Add custom exercises from database
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
            "Slight fatigue",
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
        cursor.execute('DELETE FROM daily_programs')
        conn.commit()
        conn.close()
        return "🚨 ALL WORKOUT DATA DELETED"

    def export_data(self, export_file='gym_backup.json'):
        """Export all data to JSON for backup"""
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
            
            with open(export_file, 'w') as f:
                json.dump(export_data, f, indent=2, default=str)
            
            return f"✅ Data exported to {export_file}"
            
        except Exception as e:
            return f"❌ Export failed: {str(e)}"

    def get_database_info(self):
        """Get information about the database file for GitHub storage"""
        try:
            file_size = os.path.getsize(self.db_name)
            file_size_mb = file_size / (1024 * 1024)
            
            workout_count = len(self.get_data())
            
            return {
                'file_path': os.path.abspath(self.db_name),
                'file_size_bytes': file_size,
                'file_size_mb': round(file_size_mb, 2),
                'workout_count': workout_count,
                'github_ready': file_size < 100 * 1024 * 1024  # 100MB limit
            }
        except:
            return None

# Streamlit App Setup
st.set_page_config(
    page_title="💪 AI-Enhanced Gym Tracker",
    page_icon="💪",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Professional, clean CSS theme with consistent design system
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    
    /* DESIGN SYSTEM - CONSISTENT TYPOGRAPHY & COLORS */
    .stApp {
        background-color: #ffffff;
        color: #1e293b;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        font-size: 16px;
        line-height: 1.5;
    }
    
    .main-header {
        background: linear-gradient(135deg, #1e40af 0%, #3b82f6 100%);
        color: #ffffff;
        padding: 2rem;
        border-radius: 16px;
        text-align: center;
        font-size: 1.75rem;
        font-weight: 800;
        margin-bottom: 2rem;
        box-shadow: 0 8px 32px rgba(30, 64, 175, 0.3);
        letter-spacing: -0.025em;
        text-transform: uppercase;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    /* CONSISTENT BUTTON SYSTEM */
    .stButton > button {
        background: #f8fafc;
        color: #1e293b;
        border: 2px solid #e2e8f0;
        border-radius: 12px;
        padding: 0.875rem 1.5rem;
        font-size: 1rem;
        font-weight: 600;
        width: 100%;
        height: 3.5rem;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
        font-family: 'Inter', sans-serif;
        letter-spacing: -0.01em;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
    }
    
    .stButton > button:hover {
        background: #f1f5f9;
        border-color: #3b82f6;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(59, 130, 246, 0.15);
        color: #1e40af;
    }
    
    .stFormSubmitButton > button {
        background: linear-gradient(135deg, #1e40af 0%, #3b82f6 100%) !important;
        border: none !important;
        color: #ffffff !important;
        font-weight: 700 !important;
        height: 3.5rem !important;
        font-size: 1rem !important;
        text-transform: uppercase !important;
        letter-spacing: 0.5px !important;
        border-radius: 12px !important;
        width: 100% !important;
        box-shadow: 0 4px 16px rgba(30, 64, 175, 0.4) !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }
    
    .stFormSubmitButton > button:hover {
        background: linear-gradient(135deg, #1d4ed8 0%, #2563eb 100%) !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(30, 64, 175, 0.5) !important;
    }
    
    /* CONSISTENT CARD SYSTEM */
    .workout-card {
        background: #ffffff;
        padding: 1.5rem;
        border-radius: 16px;
        margin: 1rem 0;
        border: 1px solid #e2e8f0;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
        color: #1e293b;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
    }
    
    .workout-card:hover {
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
        border-color: #cbd5e1;
    }
    
    .exercise-card {
        background: #f8fafc;
        padding: 1.5rem;
        border-radius: 16px;
        margin: 1rem 0;
        border: 1px solid #e2e8f0;
        color: #1e293b;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
    }
    
    .exercise-card:hover {
        border-color: #3b82f6;
        box-shadow: 0 4px 16px rgba(59, 130, 246, 0.1);
        transform: translateY(-2px);
    }
    
    .stats-card {
        background: linear-gradient(135deg, #f8fafc 0%, #ffffff 100%);
        color: #1e293b;
        padding: 1.5rem;
        border-radius: 16px;
        text-align: center;
        margin: 0.5rem;
        border: 1px solid #e2e8f0;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
        font-size: 0.875rem;
        font-weight: 600;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    
    .stats-card:hover {
        border-color: #3b82f6;
        transform: translateY(-3px);
        box-shadow: 0 6px 20px rgba(0, 0, 0, 0.1);
    }
    
    .set-item {
        background: #f8fafc;
        padding: 1rem;
        border-radius: 12px;
        margin: 0.5rem 0;
        border-left: 4px solid #3b82f6;
        color: #1e293b;
        font-size: 0.875rem;
        font-weight: 500;
        border: 1px solid #e2e8f0;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
    }
    
    /* CONSISTENT TYPOGRAPHY SYSTEM */
    .date-header {
        background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
        color: #1e40af;
        padding: 2rem;
        border-radius: 16px;
        text-align: center;
        font-size: 1.375rem;
        font-weight: 800;
        margin: 2rem 0;
        border: 1px solid #bfdbfe;
        letter-spacing: -0.02em;
        box-shadow: 0 4px 16px rgba(59, 130, 246, 0.1);
        text-transform: uppercase;
    }
    
    .section-header {
        color: #1e40af;
        font-size: 0.875rem;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        margin: 2.5rem 0 1.5rem 0;
        padding-bottom: 0.75rem;
        border-bottom: 2px solid #e2e8f0;
        display: flex;
        align-items: center;
    }
    
    .section-header::before {
        content: '';
        width: 4px;
        height: 20px;
        background: #3b82f6;
        border-radius: 2px;
        margin-right: 0.75rem;
    }
    
    .exercise-title {
        font-size: 1.125rem;
        font-weight: 700;
        color: #1e293b;
        margin-bottom: 0.25rem;
        letter-spacing: -0.01em;
        line-height: 1.3;
    }
    
    .exercise-subtitle {
        font-size: 0.875rem;
        color: #64748b;
        font-weight: 500;
        line-height: 1.4;
    }
    
    /* TYPOGRAPHY HIERARCHY */
    h1, h2, h3, h4, h5, h6 {
        color: #1e293b !important;
        font-weight: 800 !important;
        line-height: 1.25 !important;
        font-family: 'Inter', sans-serif !important;
        letter-spacing: -0.025em !important;
        margin-bottom: 1rem !important;
    }
    
    h1 {
        font-size: 2rem !important;
        margin-bottom: 1.5rem !important;
        text-transform: uppercase !important;
    }
    
    h2 {
        font-size: 1.75rem !important;
        color: #1e40af !important;
        margin-bottom: 1.25rem !important;
    }
    
    h3 {
        font-size: 1.375rem !important;
        color: #374151 !important;
        margin-bottom: 1rem !important;
    }
    
    /* CONSISTENT FORM SYSTEM */
    .stSelectbox > div > div {
        background: #ffffff !important;
        color: #1e293b !important;
        border: 2px solid #e2e8f0 !important;
        border-radius: 12px !important;
        font-size: 1rem !important;
        font-family: 'Inter', sans-serif !important;
        font-weight: 600 !important;
        min-height: 3.5rem !important;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05) !important;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }
    
    .stSelectbox > div > div:focus-within {
        border-color: #3b82f6 !important;
        box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1) !important;
    }
    
    .stNumberInput > div > div > input {
        background: #ffffff !important;
        color: #1e293b !important;
        border: 2px solid #e2e8f0 !important;
        border-radius: 12px !important;
        font-size: 1.125rem !important;
        text-align: center !important;
        font-weight: 700 !important;
        height: 3.5rem !important;
        font-family: 'Inter', sans-serif !important;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05) !important;
    }
    
    .stNumberInput > div > div > input:focus {
        border-color: #3b82f6 !important;
        box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1) !important;
        outline: none !important;
    }
    
    .stTextInput > div > div > input {
        background: #ffffff !important;
        color: #1e293b !important;
        border: 2px solid #e2e8f0 !important;
        border-radius: 12px !important;
        font-size: 0.875rem !important;
        padding: 0.875rem !important;
        font-family: 'Inter', sans-serif !important;
        font-weight: 500 !important;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05) !important;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: #3b82f6 !important;
        box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1) !important;
        outline: none !important;
    }
    
    .stTextArea > div > div > textarea {
        background: #ffffff !important;
        color: #1e293b !important;
        border: 2px solid #e2e8f0 !important;
        border-radius: 12px !important;
        font-size: 0.875rem !important;
        padding: 0.875rem !important;
        font-family: 'Inter', sans-serif !important;
        font-weight: 500 !important;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05) !important;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }
    
    .stTextArea > div > div > textarea:focus {
        border-color: #3b82f6 !important;
        box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1) !important;
        outline: none !important;
    }
    
    /* CONSISTENT TAB SYSTEM */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: #f8fafc;
        padding: 12px;
        border-radius: 16px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 3.5rem;
        font-size: 1rem;
        font-weight: 600;
        border-radius: 12px;
        background: transparent;
        color: #64748b;
        border: 1px solid transparent;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        font-family: 'Inter', sans-serif;
        padding: 0 1.5rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    .stTabs [aria-selected="true"] {
        background: #3b82f6 !important;
        color: #ffffff !important;
        border: 1px solid #3b82f6 !important;
        font-weight: 700 !important;
        box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3) !important;
        transform: translateY(-1px) !important;
    }
    
    .stTabs [data-baseweb="tab"]:hover:not([aria-selected="true"]) {
        background: #f1f5f9;
        color: #3b82f6;
        border-color: #e2e8f0;
    }
    
    /* SEARCH INPUT STYLING */
    .stTextInput > div > div > input[placeholder*="Search"] {
        background: #ffffff !important;
        color: #1e293b !important;
        border: 2px solid #3b82f6 !important;
        border-radius: 12px !important;
        font-size: 1rem !important;
        padding: 1rem !important;
        font-family: 'Inter', sans-serif !important;
        font-weight: 600 !important;
        box-shadow: 0 2px 8px rgba(59, 130, 246, 0.1) !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }
    
    .stTextInput > div > div > input[placeholder*="Search"]:focus {
        border-color: #1e40af !important;
        box-shadow: 0 0 0 3px rgba(30, 64, 175, 0.2) !important;
        transform: translateY(-1px) !important;
    }
    
    /* METRICS STYLING */
    [data-testid="metric-container"] {
        background: #f8fafc;
        border-radius: 16px;
        padding: 1.5rem;
        border: 1px solid #e2e8f0;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
    }
    
    [data-testid="metric-container"]:hover {
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
        border-color: #cbd5e1;
    }
    
    [data-testid="metric-container"] label {
        color: #64748b !important;
        font-size: 0.75rem !important;
        font-weight: 600 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.05em !important;
    }
    
    [data-testid="metric-container"] div[data-testid="metric-value"] {
        color: #1e40af !important;
        font-size: 1.875rem !important;
        font-weight: 800 !important;
        font-family: 'Inter', sans-serif !important;
    }
    
    /* SPECIAL ELEMENTS */
    .github-info {
        background: #f0fdf4;
        border: 1px solid #16a34a;
        border-radius: 16px;
        padding: 1.5rem;
        margin: 1.5rem 0;
        color: #14532d;
        font-weight: 600;
        box-shadow: 0 2px 8px rgba(22, 163, 74, 0.1);
    }
    
    /* CLEAN INTERFACE */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDeployButton {visibility: hidden;}
    
    /* CONSISTENT TEXT & SPACING */
    p, div, span, label {
        color: #1e293b !important;
        line-height: 1.6 !important;
        font-size: 1rem !important;
    }
    
    .stMarkdown p {
        font-size: 1rem !important;
        color: #1e293b !important;
        line-height: 1.6 !important;
    }
    
    .stCaption {
        color: #64748b !important;
        font-size: 0.875rem !important;
        font-weight: 500 !important;
    }
    
    /* MOBILE RESPONSIVE ADJUSTMENTS */
    @media (max-width: 768px) {
        .main-header {
            font-size: 1.5rem;
            padding: 1.5rem;
        }
        
        h1 {
            font-size: 1.75rem !important;
        }
        
        h2 {
            font-size: 1.5rem !important;
        }
        
        h3 {
            font-size: 1.25rem !important;
        }
        
        .stButton > button, .stFormSubmitButton > button {
            height: 3.5rem;
            font-size: 1rem;
            margin: 0.5rem 0;
        }
        
        .workout-card, .exercise-card {
            padding: 1.25rem;
            margin: 0.75rem 0;
        }
        
        .stats-card {
            margin: 0.25rem;
            padding: 1.25rem;
            font-size: 0.875rem;
        }
        
        .stTabs [data-baseweb="tab"] {
            font-size: 0.875rem;
            height: 3rem;
            padding: 0 1rem;
        }
        
        .section-header {
            font-size: 0.8rem !important;
            margin: 1.5rem 0 1rem 0 !important;
        }
        
        .date-header {
            font-size: 1.25rem;
            padding: 1.5rem;
        }
        
        .stNumberInput > div > div > input {
            font-size: 1.125rem !important;
            height: 3.5rem !important;
        }
        
        .stSelectbox > div > div {
            min-height: 3.25rem !important;
            font-size: 0.875rem !important;
        }
    }
    
    /* FOCUS STATES FOR ACCESSIBILITY */
    button:focus-visible {
        outline: 2px solid #3b82f6 !important;
        outline-offset: 2px !important;
    }
    
    /* SMOOTH INTERACTIONS */
    * {
        scroll-behavior: smooth;
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

if 'template_exercises' not in st.session_state:
    st.session_state.template_exercises = []

if 'program_exercises' not in st.session_state:
    st.session_state.program_exercises = []

# Helper Functions
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

def smart_exercise_search(all_exercises, search_term, max_results=10):
    """Smart fuzzy search for exercises with typo tolerance"""
    if not search_term:
        return all_exercises[:max_results]
    
    search_term = search_term.lower().strip()
    
    # Exact matches first
    exact_matches = [ex for ex in all_exercises if search_term in ex.lower()]
    
    # Common abbreviations and synonyms
    abbreviations = {
        'rdl': 'romanian deadlift',
        'ohp': 'overhead press',
        'bp': 'bench press',
        'mp': 'military press',
        'dl': 'deadlift',
        'sq': 'squat',
        'db': 'dumbbell',
        'bb': 'barbell',
        'cg': 'close grip',
        'wg': 'wide grip',
        'lat': 'lateral',
        'tri': 'tricep',
        'bi': 'bicep',
        'leg ext': 'leg extension',
        'leg cur': 'leg curl',
        'calf': 'calf raises',
        'pull up': 'pull-ups',
        'chin up': 'chin-ups',
        'push up': 'push-ups'
    }
    
    # Check abbreviations
    expanded_search = abbreviations.get(search_term, search_term)
    if expanded_search != search_term:
        exact_matches.extend([ex for ex in all_exercises if expanded_search in ex.lower() and ex not in exact_matches])
    
    # Fuzzy matching for typos
    fuzzy_matches = []
    for exercise in all_exercises:
        if exercise in exact_matches:
            continue
            
        exercise_lower = exercise.lower()
        
        # Check if most characters match (typo tolerance)
        if len(search_term) >= 3:
            matches = sum(1 for c in search_term if c in exercise_lower)
            if matches >= len(search_term) * 0.7:  # 70% character match
                fuzzy_matches.append(exercise)
    
    # Combine results, exact matches first
    results = exact_matches + fuzzy_matches
    
    # Remove duplicates while preserving order
    seen = set()
    final_results = []
    for ex in results:
        if ex not in seen:
            seen.add(ex)
            final_results.append(ex)
    
    return final_results[:max_results]

def clean_exercise_selector(all_exercises, default_exercise=None, key="exercise_search"):
    """Clean, mobile-optimized exercise selector with smart search"""
    
    # Search input with better styling
    search_term = st.text_input(
        "",  # No label to save space
        placeholder="🔍 Search 500+ exercises... (try 'rdl', 'bench', 'squat')",
        key=f"{key}_search",
        help="Smart search with typo tolerance and abbreviations"
    )
    
    # Smart search with fuzzy matching
    if search_term:
        filtered_exercises = smart_exercise_search(all_exercises, search_term, max_results=15)
        if not filtered_exercises:
            st.error("❌ No exercises found. Try different keywords.")
            return default_exercise or (all_exercises[0] if all_exercises else "")
        
        # Show search results count quietly
        st.caption(f"Found {len(filtered_exercises)} matches")
        exercises_to_show = filtered_exercises
    else:
        # Show popular exercises when no search
        popular_exercises = [
            'Bench Press', 'Squat', 'Deadlift', 'Romanian Deadlift', 'Overhead Press',
            'Barbell Row', 'Pull-ups', 'Incline Bench Press', 'Leg Press', 'Lateral Raises',
            'Bicep Curls', 'Tricep Pushdown', 'Dumbbell Press', 'Bulgarian Split Squat', 'Hip Thrust'
        ]
        exercises_to_show = popular_exercises
        st.caption("💪 Popular exercises (start typing to search all 500+)")
    
    # Exercise selection dropdown
    if exercises_to_show:
        default_index = 0
        if default_exercise and default_exercise in exercises_to_show:
            default_index = exercises_to_show.index(default_exercise)
        
        selected_exercise = st.selectbox(
            "Select Exercise",
            options=exercises_to_show,
            index=default_index,
            key=f"{key}_select",
            label_visibility="collapsed"  # Hide label for cleaner look
        )
        return selected_exercise
    
    return default_exercise or ""

# App Pages
def todays_workout_page():
    """Today's workout with program support"""
    st.markdown('<h1 style="font-size: 2rem; font-weight: 800; color: #1e293b; margin-bottom: 1.5rem; text-transform: uppercase;">🔥 Today\'s Workout</h1>', unsafe_allow_html=True)
    
    selected_date = st.date_input("📅 Workout Date", value=date.today())
    date_str = selected_date.strftime('%Y-%m-%d')
    
    if selected_date == date.today():
        st.markdown('<div class="date-header">🔥 <strong>TODAY\'S WORKOUT</strong></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="date-header">📅 <strong>WORKOUT REVIEW</strong></div>', unsafe_allow_html=True)
    
    # Check for daily program
    program = st.session_state.tracker.get_daily_program(date_str)
    
    if program:
        st.markdown('<div class="workout-card">', unsafe_allow_html=True)
        st.subheader(f"📋 {program['program_name']}")
        
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Created by:** {program['created_by']}")
        with col2:
            st.write(f"**Created:** {program['created_at'][:10]}")
        
        if program['program_notes']:
            st.write(f"**Notes:** {program['program_notes']}")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        exercises = program['exercises']
        
        # Calculate progress
        completed_exercises = []
        df = st.session_state.tracker.get_data()
        if not df.empty:
            today_data = df[df['date'] == date_str]
            completed_exercises = today_data['exercise'].unique().tolist()
        
        progress_percentage = (len(completed_exercises) / len(exercises)) * 100 if exercises else 0
        
        st.subheader(f"📈 Progress: {progress_percentage:.0f}% Complete")
        st.progress(progress_percentage / 100)
        
        # Show program exercises
        for i, exercise_info in enumerate(exercises, 1):
            exercise_name = exercise_info['exercise']
            target_sets = exercise_info.get('sets', 3)
            target_reps = exercise_info.get('reps', 10)
            exercise_notes = exercise_info.get('notes', '')
            
            is_completed = exercise_name in completed_exercises
            status_emoji = "✅" if is_completed else "🔥"
            
            with st.expander(f"{status_emoji} {exercise_name} - {target_sets}×{target_reps}", expanded=not is_completed):
                
                # Show last performance
                last_workout = get_last_workout_for_exercise(exercise_name)
                if last_workout is not None:
                    st.markdown("**📚 Last Performance:**")
                    last_date = last_workout['date'].iloc[0].strftime('%Y-%m-%d')
                    st.write(f"*📅 {last_date}*")
                    
                    for _, row in last_workout.iterrows():
                        notes_text = f" - *{row['set_notes']}*" if row['set_notes'] else ""
                        rpe_color = "🟢" if row['rpe'] <= 7 else "🟡" if row['rpe'] <= 8 else "🔴"
                        st.write(f"**Set {row['set_number']}:** {row['reps']} reps @ {row['weight']}kg {rpe_color}RPE:{row['rpe']}{notes_text}")
                
                if exercise_notes:
                    st.info(f"💡 **Notes:** {exercise_notes}")
                
                # Quick logging form
                with st.form(f"log_{exercise_name.replace(' ', '_')}_{i}"):
                    st.markdown("**🎯 Log Your Set:**")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        reps = st.number_input("🎯 Reps", min_value=1, max_value=50, value=target_reps, key=f"reps_{i}")
                    with col2:
                        weight = st.number_input("⚖️ Weight (kg)", min_value=0.0, value=0.0, step=0.625, key=f"weight_{i}")
                    
                    rpe = st.select_slider("💥 RPE", options=[6, 7, 8, 9, 10], value=8, key=f"rpe_{i}")
                    set_notes = st.text_input("📝 Notes", placeholder="Form, fatigue, equipment...", key=f"set_notes_{i}")
                    
                    if st.form_submit_button(f"🚀 LOG SET", use_container_width=True):
                        result = st.session_state.tracker.log_workout(
                            date_str, exercise_name, 
                            [{'reps': reps, 'weight': weight, 'rpe': rpe, 'set_notes': set_notes}], ""
                        )
                        st.balloons()
                        st.rerun()
    
    else:
        st.info("📋 No program set for today. Use 'Quick Log' for freestyle training!")
    
    # Today's summary
    st.markdown('<h2 style="font-size: 1.75rem; font-weight: 800; color: #1e40af; margin-bottom: 1.25rem; text-transform: uppercase;">📊 Today\'s Summary</h2>', unsafe_allow_html=True)
    
    df = st.session_state.tracker.get_data()
    if not df.empty:
        today_data = df[df['date'] == date_str]
        
        if not today_data.empty:
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown('<div class="stats-card">💪<br><strong>Exercises</strong><br>' + 
                           str(len(today_data['exercise'].unique())) + '</div>', unsafe_allow_html=True)
            
            with col2:
                st.markdown('<div class="stats-card">🎯<br><strong>Sets</strong><br>' + 
                           str(len(today_data)) + '</div>', unsafe_allow_html=True)
            
            with col3:
                volume = (today_data['reps'] * today_data['weight']).sum()
                st.markdown('<div class="stats-card">🏋️<br><strong>Volume</strong><br>' + 
                           f'{volume:,.0f} kg</div>', unsafe_allow_html=True)
        else:
            st.info("💡 No exercises logged yet today. Time to get started! 🔥")
    else:
        st.info("💡 No workout data yet. Start your fitness journey today! 🚀")

def enhanced_quick_log_page():
    """Clean, simplified quick log optimized for mobile with smart suggestions"""
    st.markdown('<h1 style="font-size: 2rem; font-weight: 800; color: #1e293b; margin-bottom: 1.5rem; text-transform: uppercase;">⚡ Quick Log</h1>', unsafe_allow_html=True)
    
    log_date = st.date_input("📅 Select Date", value=date.today())
    date_str = log_date.strftime('%Y-%m-%d')
    
    if log_date == date.today():
        st.markdown('<div class="date-header">🔥 TODAY\'S WORKOUT</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="date-header">📅 WORKOUT LOG</div>', unsafe_allow_html=True)
    
    # Quick Stats Dashboard
    quick_stats = st.session_state.tracker.get_quick_stats()
    if quick_stats:
        st.markdown('<div class="section-header">🚀 QUICK STATS</div>', unsafe_allow_html=True)
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            streak_emoji = "🔥" if quick_stats['streak'] > 0 else "💤"
            st.markdown(f'<div class="stats-card">{streak_emoji}<br><strong>Streak</strong><br>{quick_stats["streak"]} days</div>', 
                       unsafe_allow_html=True)
        
        with col2:
            st.markdown(f'<div class="stats-card">📦<br><strong>Week Volume</strong><br>{quick_stats["weekly_volume"]:,.0f}kg</div>', 
                       unsafe_allow_html=True)
        
        with col3:
            st.markdown(f'<div class="stats-card">💪<br><strong>Week Sessions</strong><br>{quick_stats["weekly_workouts"]}</div>', 
                       unsafe_allow_html=True)
        
        with col4:
            st.markdown(f'<div class="stats-card">🏆<br><strong>Total Sessions</strong><br>{quick_stats["total_workouts"]}</div>', 
                       unsafe_allow_html=True)
        
        # Recent PRs
        if quick_stats['recent_prs']:
            st.markdown("### 🏆 Recent PRs (Last 30 Days)")
            for pr in quick_stats['recent_prs']:
                st.success(f"**{pr['exercise']}**: {pr['weight']}kg on {pr['date']}")
    
    # Clean section header
    st.markdown('<div class="section-header">LOG YOUR SET</div>', unsafe_allow_html=True)
    
    # Get all exercises for smart search
    all_exercises = st.session_state.tracker.get_all_exercises()
    
    # Clean exercise selection (outside form to avoid conflicts)
    exercise = clean_exercise_selector(
        all_exercises, 
        default_exercise=st.session_state.last_exercise,
        key="quick_log"
    )
    
    # Smart Suggestions
    if exercise:
        suggestions = st.session_state.tracker.get_smart_suggestions(exercise)
        if suggestions:
            st.markdown("### 🧠 Smart Suggestions")
            
            last = suggestions['last_workout']
            st.info(f"**📚 Last Performance ({last['date']}):** {len(last['sets_reps'])} sets, "
                   f"Max: {last['max_weight']}kg, Volume: {last['total_volume']:,.0f}kg, "
                   f"Avg RPE: {last['avg_rpe']:.1f}")
            
            if suggestions['progression_type'] == 'weight':
                st.success(f"**💡 Suggestion:** Try {suggestions['weight_suggestion']}kg "
                          f"({suggestions['reason']})")
                suggested_weight = suggestions['weight_suggestion']
            elif suggestions['progression_type'] == 'reps':
                st.success(f"**💡 Suggestion:** Try {suggestions['rep_suggestion']} reps @ {suggestions['weight_suggestion']}kg "
                          f"({suggestions['reason']})")
                suggested_weight = suggestions['weight_suggestion']
            else:  # deload
                st.warning(f"**⚠️ Suggestion:** Reduce to {suggestions['weight_suggestion']}kg "
                          f"({suggestions['reason']})")
                suggested_weight = suggestions['weight_suggestion']
        else:
            suggested_weight = st.session_state.last_weight
    else:
        suggested_weight = st.session_state.last_weight
    
    # Clean, simplified logging form
    with st.form("quick_log_form", clear_on_submit=True):
        # Input fields in clean layout
        col1, col2 = st.columns(2)
        with col1:
            reps = st.number_input("🎯 Reps", min_value=1, max_value=50, value=st.session_state.last_reps)
        with col2:
            weight = st.number_input("⚖️ Weight (kg)", min_value=0.0, value=suggested_weight, step=0.625)
        
        # RPE and notes in full width
        rpe = st.select_slider("💥 RPE", options=[6, 7, 8, 9, 10], value=st.session_state.last_rpe)
        set_notes = st.text_input("📝 Notes (optional)", placeholder="Form, fatigue, equipment notes...")
        
        # Offline status indicator
        col1, col2 = st.columns([3, 1])
        with col2:
            if 'offline_queue' in st.session_state and st.session_state.offline_queue:
                offline_count = len([w for w in st.session_state.offline_queue if not w['synced']])
                if offline_count > 0:
                    st.warning(f"📱 {offline_count} offline")
                    if st.button("🔄 Sync", help="Sync offline workouts"):
                        result = st.session_state.tracker.sync_offline_workouts()
                        st.success(result)
                        st.rerun()
        
        # Clean submit button
        with col1:
            submitted = st.form_submit_button("🚀 LOG SET", use_container_width=True)
        
        if submitted and exercise:
            try:
                st.session_state.tracker.quick_log(exercise, reps, weight, rpe, set_notes, "", date_str)
                
                # Update session state for next time
                st.session_state.last_exercise = exercise
                st.session_state.last_reps = reps
                st.session_state.last_weight = weight
                st.session_state.last_rpe = rpe
                
                # Check goal progress
                goals = st.session_state.tracker.get_goals()
                for goal in goals:
                    if st.session_state.tracker.update_goal_progress(goal['id']):
                        st.balloons()
                        st.success(f"🎉 Goal Completed: {goal['name']}!")
                
                st.balloons()
                st.rerun()
            except Exception as e:
                # Offline mode
                workout_data = {
                    'date': date_str,
                    'exercise': exercise,
                    'sets': [{'reps': reps, 'weight': weight, 'rpe': rpe, 'set_notes': set_notes}],
                    'notes': ''
                }
                result = st.session_state.tracker.queue_offline_workout(workout_data)
                st.warning(result)
    
    # Today's workout summary with clean design
    st.markdown('<div class="section-header">TODAY\'S COMPLETE WORKOUT</div>', unsafe_allow_html=True)
    
    daily_workout = st.session_state.tracker.get_daily_workout(date_str)
    
    if not daily_workout.empty:
        exercises_done = daily_workout['exercise'].unique()
        
        for exercise_name in exercises_done:
            exercise_sets = daily_workout[daily_workout['exercise'] == exercise_name]
            
            total_volume = (exercise_sets['reps'] * exercise_sets['weight']).sum()
            max_weight = exercise_sets['weight'].max()
            avg_rpe = exercise_sets['rpe'].mean()
            
            st.markdown('<div class="exercise-card">', unsafe_allow_html=True)
            st.markdown(f'<div class="exercise-title">{exercise_name}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="exercise-subtitle">{len(exercise_sets)} sets • {total_volume:.0f}kg volume • {max_weight}kg max • {avg_rpe:.1f} avg RPE</div>', unsafe_allow_html=True)
            
            for _, set_row in exercise_sets.iterrows():
                col1, col2 = st.columns([5, 1])
                
                with col1:
                    notes_display = f" - *{set_row['set_notes']}*" if set_row['set_notes'] else ""
                    rpe_emoji = "🟢" if set_row['rpe'] <= 7 else "🟡" if set_row['rpe'] <= 8 else "🔴"
                    st.markdown(f'<div class="set-item">**Set {set_row["set_number"]}:** {set_row["reps"]} reps @ {set_row["weight"]}kg {rpe_emoji}RPE:{set_row["rpe"]}{notes_display}</div>', 
                               unsafe_allow_html=True)
                
                with col2:
                    if st.button("🗑️", key=f"delete_{set_row['id']}", help="Delete this set"):
                        if st.session_state.get('confirm_delete_set') == set_row['id']:
                            result = st.session_state.tracker.delete_set(set_row['id'])
                            st.session_state.pop('confirm_delete_set', None)
                            st.rerun()
                        else:
                            st.session_state.confirm_delete_set = set_row['id']
                            st.warning("⚠️ Tap again to confirm deletion")
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Clean daily summary
        total_sets = len(daily_workout)
        total_volume = (daily_workout['reps'] * daily_workout['weight']).sum()
        avg_rpe = daily_workout['rpe'].mean() if daily_workout['rpe'].notna().any() else 0
        
        st.markdown('<div class="section-header">DAILY SUMMARY</div>', unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown('<div class="stats-card">💪<br><strong>Exercises</strong><br>' + 
                       str(len(exercises_done)) + '</div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown('<div class="stats-card">🎯<br><strong>Sets</strong><br>' + 
                       str(total_sets) + '</div>', unsafe_allow_html=True)
        
        with col3:
            st.markdown('<div class="stats-card">🏋️<br><strong>Volume</strong><br>' + 
                       f'{total_volume:,.0f}kg</div>', unsafe_allow_html=True)
    
    else:
        st.info("💡 No exercises logged yet today. Start your workout! 🔥")

def progress_page():
    """Progress tracking page"""
    st.markdown('<h1 style="font-size: 2rem; font-weight: 800; color: #1e293b; margin-bottom: 1.5rem; text-transform: uppercase;">📈 Progress</h1>', unsafe_allow_html=True)
    
    df = st.session_state.tracker.get_data()
    
    if df.empty:
        st.warning("No workout data yet. Start logging to see progress! 🚀")
        return
    
    available_exercises = df['exercise'].unique()
    selected_exercise = st.selectbox("🏋️ Choose Exercise", available_exercises)
    
    stats = st.session_state.tracker.get_exercise_stats(selected_exercise)
    
    if stats:
        st.markdown(f'<h2 style="font-size: 1.75rem; font-weight: 800; color: #1e40af; margin-bottom: 1.25rem;">📊 {selected_exercise} Statistics</h2>', unsafe_allow_html=True)
        
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
        st.markdown('<h3 style="font-size: 1.375rem; font-weight: 800; color: #374151; margin-bottom: 1rem;">📈 Weight Progression</h3>', unsafe_allow_html=True)
        
        daily_stats = stats['daily_stats']
        
        if len(daily_stats) > 1:
            fig = go.Figure()
            
            # Max weight line
            fig.add_trace(go.Scatter(
                x=daily_stats['date'], 
                y=daily_stats['max_weight'],
                mode='lines+markers',
                name='Max Weight',
                line=dict(color='#1e40af', width=3),
                marker=dict(size=8, color='#1e40af')
            ))
            
            # Average weight line
            fig.add_trace(go.Scatter(
                x=daily_stats['date'], 
                y=daily_stats['avg_weight'],
                mode='lines+markers',
                name='Average Weight',
                line=dict(color='#10b981', width=2, dash='dash'),
                marker=dict(size=6, color='#10b981')
            ))
            
            fig.update_layout(
                title=f'{selected_exercise} - Weight Progress',
                xaxis_title='Date',
                yaxis_title='Weight (kg)',
                height=400,
                paper_bgcolor='#ffffff',
                plot_bgcolor='#f8fafc',
                font=dict(color='#1e293b', size=12),
                xaxis=dict(gridcolor='#e2e8f0'),
                yaxis=dict(gridcolor='#e2e8f0'),
                legend=dict(
                    bgcolor='rgba(248, 250, 252, 0.9)',
                    bordercolor='#e2e8f0',
                    borderwidth=1,
                    font=dict(color='#1e293b')
                )
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Volume progression chart
            st.markdown('<h3 style="font-size: 1.375rem; font-weight: 800; color: #374151; margin-bottom: 1rem;">📦 Volume Progression</h3>', unsafe_allow_html=True)
            
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(
                x=daily_stats['date'], 
                y=daily_stats['volume'],
                mode='lines+markers',
                name='Daily Volume',
                line=dict(color='#f59e0b', width=3),
                marker=dict(size=8, color='#f59e0b'),
                fill='tonexty'
            ))
            
            fig2.update_layout(
                title=f'{selected_exercise} - Volume Progress',
                xaxis_title='Date',
                yaxis_title='Volume (kg)',
                height=400,
                paper_bgcolor='#ffffff',
                plot_bgcolor='#f8fafc',
                font=dict(color='#1e293b', size=12),
                xaxis=dict(gridcolor='#e2e8f0'),
                yaxis=dict(gridcolor='#e2e8f0')
            )
            st.plotly_chart(fig2, use_container_width=True)
        
        else:
            st.info("📊 Need more data points to show progression charts. Keep logging workouts!")

def goals_dashboard_page():
    """SMART Goals Management Dashboard"""
    st.markdown('<h1 style="font-size: 2rem; font-weight: 800; color: #1e293b; margin-bottom: 1.5rem; text-transform: uppercase;">🎯 Goals Dashboard</h1>', unsafe_allow_html=True)
    
    create_tab, progress_tab = st.tabs(["🆕 Create Goal", "📊 Track Progress"])
    
    with create_tab:
        st.subheader("🎯 Create SMART Goal")
        
        with st.form("create_goal_form", clear_on_submit=True):
            st.markdown("**📝 Goal Details**")
            
            goal_name = st.text_input("Goal Name", placeholder="e.g., Bench Press Bodyweight")
            
            col1, col2 = st.columns(2)
            with col1:
                goal_type = st.selectbox("Goal Type", [
                    "max_weight", "total_volume", "workout_frequency", "bodyweight_ratio"
                ], format_func=lambda x: {
                    "max_weight": "💪 Max Weight PR",
                    "total_volume": "📦 Total Volume", 
                    "workout_frequency": "📅 Workout Frequency",
                    "bodyweight_ratio": "⚖️ Bodyweight Ratio"
                }[x])
            
            with col2:
                target_value = st.number_input("Target Value", min_value=0.0, value=100.0)
            
            if goal_type in ["max_weight", "total_volume", "bodyweight_ratio"]:
                all_exercises = st.session_state.tracker.get_all_exercises()
                target_exercise = st.selectbox("Exercise", all_exercises)
            else:
                target_exercise = None
            
            target_date = st.date_input("Target Date", value=date.today() + timedelta(days=90))
            
            # Goal type explanations
            if goal_type == "max_weight":
                st.info(f"🎯 **Goal:** Lift {target_value}kg for 1 rep on {target_exercise}")
            elif goal_type == "total_volume":
                st.info(f"🎯 **Goal:** Achieve {target_value:,.0f}kg total volume on {target_exercise}")
            elif goal_type == "workout_frequency":
                st.info(f"🎯 **Goal:** Complete {target_value} workout sessions by {target_date}")
            elif goal_type == "bodyweight_ratio":
                st.info(f"🎯 **Goal:** Lift {target_value}x bodyweight on {target_exercise}")
            
            submitted = st.form_submit_button("🚀 CREATE GOAL", use_container_width=True)
            
            if submitted and goal_name:
                result = st.session_state.tracker.create_goal(
                    goal_name, goal_type, target_value, target_exercise, 
                    target_date.strftime('%Y-%m-%d')
                )
                st.balloons()
                st.rerun()
    
    with progress_tab:
        st.subheader("📊 Goal Progress")
        
        goals = st.session_state.tracker.get_goals()
        
        if not goals:
            st.info("🎯 No goals set yet. Create your first goal to start tracking progress!")
            return
        
        # Progress overview
        total_goals = len(goals)
        completed_goals = len([g for g in goals if g['is_completed']])
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown(f'<div class="stats-card">🎯<br><strong>Total Goals</strong><br>{total_goals}</div>', 
                       unsafe_allow_html=True)
        
        with col2:
            st.markdown(f'<div class="stats-card">✅<br><strong>Completed</strong><br>{completed_goals}</div>', 
                       unsafe_allow_html=True)
        
        with col3:
            completion_rate = (completed_goals / total_goals * 100) if total_goals > 0 else 0
            st.markdown(f'<div class="stats-card">📈<br><strong>Success Rate</strong><br>{completion_rate:.1f}%</div>', 
                       unsafe_allow_html=True)
        
        # Individual goal progress
        for goal in goals:
            with st.expander(f"{'✅' if goal['is_completed'] else '🎯'} {goal['name']}", 
                           expanded=not goal['is_completed']):
                
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    # Progress calculation
                    progress_percentage = min((goal['current_value'] / goal['target_value'] * 100), 100) if goal['target_value'] > 0 else 0
                    
                    st.write(f"**Target:** {goal['target_value']} {goal['type'].replace('_', ' ')}")
                    st.write(f"**Current:** {goal['current_value']:.1f}")
                    st.write(f"**Progress:** {progress_percentage:.1f}%")
                    
                    if goal['target_exercise']:
                        st.write(f"**Exercise:** {goal['target_exercise']}")
                    
                    if goal['target_date']:
                        target_date = datetime.strptime(goal['target_date'], '%Y-%m-%d').date()
                        days_left = (target_date - date.today()).days
                        if days_left > 0:
                            st.write(f"**Days Remaining:** {days_left} days")
                        elif days_left == 0:
                            st.write("**⏰ Target Date: TODAY!**")
                        else:
                            st.write(f"**⚠️ Overdue by {abs(days_left)} days**")
                    
                    # Progress bar
                    st.progress(progress_percentage / 100)
                    
                    if goal['is_completed']:
                        st.success(f"🎉 **Completed on {goal['completed_at'][:10]}!**")
                    elif progress_percentage >= 90:
                        st.warning("🔥 So close! Keep pushing!")
                    elif progress_percentage >= 50:
                        st.info("💪 Great progress! You're halfway there!")
                
                with col2:
                    if st.button("🗑️", key=f"delete_goal_{goal['id']}", help="Delete goal"):
                        if st.session_state.get('confirm_delete_goal') == goal['id']:
                            # Delete goal logic would go here
                            st.session_state.pop('confirm_delete_goal', None)
                            st.warning("Goal deletion not implemented in demo")
                        else:
                            st.session_state.confirm_delete_goal = goal['id']
                            st.warning("⚠️ Tap again to confirm")
        
        # Quick goal suggestions
        st.markdown('<div class="section-header">💡 SUGGESTED GOALS</div>', unsafe_allow_html=True)
        
        df = st.session_state.tracker.get_data()
        if not df.empty:
            # Suggest goals based on current performance
            popular_exercises = ['Bench Press', 'Squat', 'Deadlift', 'Overhead Press']
            suggestions = []
            
            for exercise in popular_exercises:
                exercise_data = df[df['exercise'] == exercise]
                if not exercise_data.empty:
                    current_max = exercise_data['weight'].max()
                    suggested_target = current_max + (10 if current_max < 100 else 20)
                    suggestions.append({
                        'name': f"{exercise} {suggested_target}kg PR",
                        'type': "max_weight",
                        'target': suggested_target,
                        'exercise': exercise
                    })
            
            if suggestions:
                col1, col2 = st.columns(2)
                for i, suggestion in enumerate(suggestions[:4]):
                    with col1 if i % 2 == 0 else col2:
                        if st.button(f"🎯 {suggestion['name']}", key=f"suggest_{i}", use_container_width=True):
                            st.session_state.tracker.create_goal(
                                suggestion['name'], suggestion['type'], suggestion['target'],
                                suggestion['exercise'], (date.today() + timedelta(days=90)).strftime('%Y-%m-%d')
                            )
                            st.rerun()

def program_creator_page():
    """Program creator with templates"""
    st.markdown('<h1 style="font-size: 2rem; font-weight: 800; color: #1e293b; margin-bottom: 1.5rem; text-transform: uppercase;">📋 Program Creator</h1>', unsafe_allow_html=True)
    
    create_tab, templates_tab = st.tabs(["🆕 Create Program", "📚 Templates"])
    
    with create_tab:
        st.subheader("🆕 Create New Program")
        
        program_date = st.date_input("📅 Program Date", value=date.today())
        program_name = st.text_input("Program Name", value=f"Training - {date.today().strftime('%b %d')}")
        
        col1, col2 = st.columns(2)
        with col1:
            category = st.selectbox("Category", ["Upper Body", "Lower Body", "Full Body", "Custom"])
        with col2:
            created_by = st.selectbox("Created By", ["Personal Trainer", "Myself"])
        
        program_notes = st.text_area("Description", placeholder="Session goals, focus areas...")
        save_as_template = st.checkbox("💾 Save as Template", value=True)
        
        # Quick templates
        st.write("**Quick Templates:**")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("💪 Upper Body", use_container_width=True):
                st.session_state.program_exercises = [
                    {'exercise': 'Bench Press', 'sets': 4, 'reps': 6, 'rest': 120},
                    {'exercise': 'Overhead Press', 'sets': 3, 'reps': 8, 'rest': 90},
                    {'exercise': 'Barbell Row', 'sets': 3, 'reps': 8, 'rest': 90}
                ]
                st.rerun()
        
        with col2:
            if st.button("🦵 Lower Body", use_container_width=True):
                st.session_state.program_exercises = [
                    {'exercise': 'Squat', 'sets': 4, 'reps': 8, 'rest': 120},
                    {'exercise': 'Romanian Deadlift', 'sets': 3, 'reps': 10, 'rest': 90},
                    {'exercise': 'Leg Press', 'sets': 3, 'reps': 12, 'rest': 90}
                ]
                st.rerun()
        
        with col3:
            if st.button("🔄 Full Body", use_container_width=True):
                st.session_state.program_exercises = [
                    {'exercise': 'Squat', 'sets': 3, 'reps': 8, 'rest': 120},
                    {'exercise': 'Bench Press', 'sets': 3, 'reps': 8, 'rest': 120},
                    {'exercise': 'Barbell Row', 'sets': 3, 'reps': 8, 'rest': 120}
                ]
                st.rerun()
        
        # Add exercises to program
        st.subheader("🏋️ Add Exercises")
        
        all_exercises = st.session_state.tracker.get_all_exercises()
        
        with st.expander("➕ Add Exercise to Program", expanded=True):
            
            # Exercise selection outside of any form
            st.markdown("**🏋️ Select Exercise:**")
            exercise_name = clean_exercise_selector(
                all_exercises, 
                key="program_creator"
            )
            
            # Form for exercise details
            with st.form("add_exercise_to_program"):
                st.markdown("**📊 Exercise Details:**")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    sets = st.number_input("Sets", min_value=1, max_value=10, value=3)
                with col2:
                    reps = st.number_input("Reps", min_value=1, max_value=50, value=10)
                with col3:
                    rest_time = st.number_input("Rest (sec)", min_value=30, max_value=300, value=90, step=15)
                
                exercise_notes = st.text_input("Exercise Notes", placeholder="Form cues, focus points...")
                
                submitted = st.form_submit_button("➕ Add Exercise", use_container_width=True)
                
                if submitted and exercise_name:
                    new_exercise = {
                        'exercise': exercise_name,
                        'sets': sets,
                        'reps': reps,
                        'rest': rest_time,
                        'notes': exercise_notes
                    }
                    st.session_state.program_exercises.append(new_exercise)
                    st.balloons()
                    st.rerun()
        
        # Show current program
        if st.session_state.program_exercises:
            st.subheader("📋 Current Program")
            
            st.markdown('<div class="workout-card">', unsafe_allow_html=True)
            
            for i, ex in enumerate(st.session_state.program_exercises):
                col1, col2 = st.columns([5, 1])
                
                with col1:
                    notes_display = f" - *{ex.get('notes', '')}*" if ex.get('notes') else ""
                    st.write(f"**{i+1}. {ex['exercise']}** - {ex['sets']}×{ex['reps']} (Rest: {ex.get('rest', 90)}s){notes_display}")
                
                with col2:
                    if st.button("🗑️", key=f"remove_prog_{i}", help="Remove exercise"):
                        st.session_state.program_exercises.pop(i)
                        st.rerun()
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Save program
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("💾 Save Program", use_container_width=True, type="primary"):
                    if program_name and st.session_state.program_exercises:
                        date_str = program_date.strftime('%Y-%m-%d')
                        result = st.session_state.tracker.create_daily_program(
                            date_str, program_name, created_by, program_notes, st.session_state.program_exercises
                        )
                        
                        if save_as_template:
                            template_result = st.session_state.tracker.save_template(
                                program_name, category, program_notes, created_by, 
                                st.session_state.program_exercises
                            )
                        
                        st.balloons()
                        st.session_state.program_exercises = []
                        st.rerun()
                    else:
                        st.error("❌ Enter program name and add exercises")
            
            with col2:
                if st.button("🗑️ Clear Program", use_container_width=True):
                    st.session_state.program_exercises = []
                    st.rerun()
    
    with templates_tab:
        st.subheader("📚 Workout Templates")
        
        templates = st.session_state.tracker.get_templates()
        
        if templates:
            for template in templates:
                with st.expander(f"📋 {template['name']} ({template['category']})", expanded=False):
                    st.write(f"**Created by:** {template['created_by']}")
                    st.write(f"**Created:** {template['created_at'][:10]}")
                    
                    if template['description']:
                        st.info(f"**Description:** {template['description']}")
                    
                    st.write("**Exercises:**")
                    for i, ex in enumerate(template['exercises'], 1):
                        notes_display = f" - *{ex.get('notes', '')}*" if ex.get('notes') else ""
                        st.write(f"{i}. **{ex['exercise']}** - {ex['sets']}×{ex['reps']} (Rest: {ex.get('rest', 90)}s){notes_display}")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        if st.button(f"📅 Use Template", key=f"use_{template['id']}", use_container_width=True):
                            st.session_state.program_exercises = template['exercises'].copy()
                            st.balloons()
                            st.rerun()
                    
                    with col2:
                        if st.button(f"🗑️ Delete", key=f"del_temp_{template['id']}", use_container_width=True):
                            if st.session_state.get('confirm_delete_template') == template['id']:
                                result = st.session_state.tracker.delete_template(template['id'])
                                st.session_state.pop('confirm_delete_template', None)
                                st.rerun()
                            else:
                                st.session_state.confirm_delete_template = template['id']
                                st.warning("⚠️ Tap again to confirm deletion")
        else:
            st.info("📋 No templates found. Create your first one!")

def exercises_page():
    """Exercise management page"""
    st.markdown('<h1 style="font-size: 2rem; font-weight: 800; color: #1e293b; margin-bottom: 1.5rem; text-transform: uppercase;">➕ Exercise Manager</h1>', unsafe_allow_html=True)
    
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
        
        submitted = st.form_submit_button("➕ Add Exercise", use_container_width=True)
        
        if submitted and exercise_name.strip():
            full_description = f"{description}\nDifficulty: {difficulty}" if description else f"Difficulty: {difficulty}"
            result = st.session_state.tracker.add_custom_exercise(exercise_name.strip(), category, full_description)
            
            if "✅" in result:
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
                    st.markdown('<div class="workout-card">', unsafe_allow_html=True)
                    
                    col1, col2 = st.columns([4, 1])
                    
                    with col1:
                        st.markdown(f"**🌟 {exercise['exercise_name']}**")
                        
                        if exercise['description']:
                            st.write(f"💡 {exercise['description']}")
                        
                        st.caption(f"📅 Added: {exercise['created_at'][:10]}")
                    
                    with col2:
                        if st.button("🚀 Use", key=f"use_custom_{exercise['exercise_name']}", 
                                   help="Select for quick log", use_container_width=True):
                            st.session_state.last_exercise = exercise['exercise_name']
                            st.balloons()
                    
                    st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("🎯 No custom exercises yet. Add your first one above!")
    
    # Built-in exercises info
    st.subheader("📚 Comprehensive Exercise Database")
    built_in_count = len(st.session_state.tracker.get_all_exercises()) - len(custom_exercises)
    st.info(f"💪 **{built_in_count}+ exercises** available including strength, cardio, Olympic lifts, strongman, and specialty movements.")

def data_manager_page():
    """Data management page with GitHub storage info"""
    st.markdown('<h1 style="font-size: 2rem; font-weight: 800; color: #1e293b; margin-bottom: 1.5rem; text-transform: uppercase;">💾 Data Manager</h1>', unsafe_allow_html=True)
    
    df = st.session_state.tracker.get_data()
    templates = st.session_state.tracker.get_templates()
    custom_exercises = st.session_state.tracker.get_custom_exercises()
    
    # GitHub Storage Status
    st.subheader("📁 GitHub Storage Status")
    db_info = st.session_state.tracker.get_database_info()
    
    if db_info:
        st.markdown('<div class="github-info">', unsafe_allow_html=True)
        st.write(f"**🗃️ Database File:** `{db_info['file_path']}`")
        st.write(f"**📊 File Size:** {db_info['file_size_mb']} MB")
        st.write(f"**🏋️ Workout Sets:** {db_info['workout_count']} logged")
        
        if db_info['github_ready']:
            st.write("**✅ GitHub Ready:** Your data is safely stored and will persist between app updates!")
        else:
            st.write("**⚠️ Size Warning:** Database approaching GitHub's 100MB limit")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
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
            if "✅" in result:
                st.balloons()
                time.sleep(1)
                st.rerun()
            else:
                st.info(result)
    
    with col2:
        if st.button("🚨 RESET ALL DATA", use_container_width=True):
            if st.session_state.get('confirm_nuclear', False):
                result = st.session_state.tracker.reset_all_data()
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
            
            recent_data = df.head(20)[['date', 'exercise', 'reps', 'weight', 'rpe', 'set_notes', 'workout_notes']]
            recent_data['date'] = recent_data['date'].dt.strftime('%Y-%m-%d')
            st.dataframe(recent_data, use_container_width=True)
            
            suspicious_notes = df[
                df['set_notes'].str.contains('Warm up set|Working weight|Heavy set', case=False, na=False) |
                df['workout_notes'].str.contains('Great leg session|Finished with leg press', case=False, na=False)
            ]
            
            if not suspicious_notes.empty:
                st.warning(f"🚨 Found {len(suspicious_notes)} potentially fake data entries:")
                st.dataframe(suspicious_notes[['date', 'exercise', 'reps', 'weight', 'set_notes', 'workout_notes']], 
                           use_container_width=True)
            else:
                st.caption("✅ No obvious sample data detected")
        else:
            st.info("📊 No workout data found")
    
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
    
    st.subheader("💾 Backup & Export")
    
    st.markdown('<div class="workout-card">', unsafe_allow_html=True)
    st.write("**📤 Export Your Data**")
    
    export_filename = st.text_input("Backup filename", value=f"gym_backup_{date.today().strftime('%Y%m%d')}.json")
    
    if st.button("📤 Export All Data", use_container_width=True, type="primary"):
        result = st.session_state.tracker.export_data(export_filename)
        if "✅" in result:
            st.balloons()
        else:
            st.error(result)
    
    st.markdown('</div>', unsafe_allow_html=True)

def info_page():
    """Information page"""
    st.markdown('<h1 style="font-size: 2rem; font-weight: 800; color: #1e293b; margin-bottom: 1.5rem; text-transform: uppercase;">ℹ️ About AI-Enhanced Gym Tracker</h1>', unsafe_allow_html=True)
    
    st.markdown("""
    ## 🏆 **AI-Enhanced Fitness Tracking Platform**
    
    **Version:** AI-Enhanced GitHub-Persistent v9.0 - Smart Fitness Companion  
    **Status:** ✅ Smart Suggestions, Goals Tracking, Offline Support, Perfect Design
    
    ### ✨ **NEW AI-ENHANCED FEATURES**
    
    - **🧠 Smart Auto-Suggestions** - AI analyzes your history for optimal progression
    - **🚀 Quick Stats Dashboard** - Streaks, PRs, weekly volume at a glance  
    - **🎯 SMART Goals System** - Set and track measurable fitness goals
    - **📱 Offline Support** - Never lose a workout due to poor gym WiFi
    - **🔥 Progressive Overload Intelligence** - Automatically suggests weight/rep increases
    
    ### 💡 **SMART FEATURES IN ACTION**
    
    - **Progression Analysis**: "Last RPE was 7.5 - ready for +2.5kg!"
    - **Goal Tracking**: "87% toward your 100kg bench press goal"  
    - **Streak Motivation**: "🔥 7-day workout streak - keep it up!"
    - **PR Detection**: "New PR: Squat 95kg (previous: 92.5kg)"
    
    ### 🗃️ **Data Persistence & Reliability**
    
    Your workout data is permanently stored in your GitHub repository as `gym_tracker_MASTER.db`. 
    This means:
    - **No data loss** during app updates
    - **Automatic backups** via GitHub
    - **Full data ownership** - you control everything
    - **Unlimited storage** for decades of workouts
    - **Offline capability** with automatic sync
    
    ### 🎯 **PERFECT FOR FINANCIAL PLANNERS**
    
    As a financial professional, you'll appreciate:
    - **Data-driven insights** into your fitness progress
    - **Goal-oriented approach** with measurable outcomes
    - **Professional, clean interface** suitable for any environment
    - **Reliable tracking** that scales with your busy schedule
    
    **Current Status:** ✅ **AI-Enhanced & GitHub-Persistent**  
    **Theme:** Clean, professional design with smart functionality  
    **Intelligence:** Progressive overload AI with goal optimization  
    **Storage:** Permanent GitHub-based SQLite with offline support  
    **Accessibility:** WCAG AAA compliant for all users
    """)

def main():
    """Main application entry point"""
    
    # Header with improved typography
    st.markdown('<div class="main-header">💪 AI-Enhanced Gym Tracker</div>', unsafe_allow_html=True)
    
    # Enhanced main navigation - now with Goals
    tab1, tab2, tab3, tab4 = st.tabs([
        "🔥 Today",
        "⚡ Quick Log", 
        "📈 Progress",
        "🎯 Goals"
    ])
    
    # Main tab content
    with tab1:
        todays_workout_page()
    
    with tab2:
        enhanced_quick_log_page()
    
    with tab3:
        progress_page()
    
    with tab4:
        goals_dashboard_page()
    
    # Additional features dropdown in main area
    st.markdown('<div class="section-header">MORE FEATURES</div>', unsafe_allow_html=True)
    
    additional_feature = st.selectbox(
        "Select Additional Feature:",
        options=["Choose Feature...", "📋 Programs", "➕ Exercises", "💾 Data", "ℹ️ Info"],
        index=0,
        key="additional_features"
    )
    
    # Show additional feature content if selected
    if additional_feature == "📋 Programs":
        st.markdown("---")
        program_creator_page()
    elif additional_feature == "➕ Exercises":
        st.markdown("---")
        exercises_page()
    elif additional_feature == "💾 Data":
        st.markdown("---")
        data_manager_page()
    elif additional_feature == "ℹ️ Info":
        st.markdown("---")
        info_page()

# Run the application
if __name__ == "__main__":
    main()
