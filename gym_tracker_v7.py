```python
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
import sqlite3
import numpy as np
import json
import time

# --- GymTracker Data Layer ---
class GymTracker:
    def __init__(self, db_name='gym_tracker_MASTER.db'):
        self.db_name = db_name
        self.init_database()

    def init_database(self):
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
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        for i, set_data in enumerate(sets_data, 1):
            cursor.execute(
                '''INSERT INTO workouts (date, exercise, set_number, reps, weight, rpe, set_notes, workout_notes)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                (date_str, exercise, i, set_data['reps'], set_data['weight'], set_data.get('rpe'), set_data.get('set_notes', ''), workout_notes)
            )
        conn.commit()
        conn.close()
        return f"✅ Logged {len(sets_data)} sets for {exercise}"

    def quick_log(self, exercise, reps, weight, rpe=None, set_notes="", workout_notes="", date_str=None):
        if date_str is None:
            date_str = date.today().strftime('%Y-%m-%d')
        return self.log_workout(date_str, exercise, [{'reps': reps, 'weight': weight, 'rpe': rpe, 'set_notes': set_notes}], workout_notes)

    def delete_set(self, set_id):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM workouts WHERE id = ?', (set_id,))
        rows = cursor.rowcount
        conn.commit()
        conn.close()
        return "✅ Set deleted!" if rows > 0 else "❌ Set not found!"

    def get_daily_workout(self, date_str):
        conn = sqlite3.connect(self.db_name)
        try:
            df = pd.read_sql_query(
                '''SELECT id, exercise, set_number, reps, weight, rpe, set_notes, workout_notes, created_at
                   FROM workouts WHERE date = ? ORDER BY exercise, set_number''',
                conn, params=(date_str,)
            )
        except Exception:
            df = pd.DataFrame()
        conn.close()
        return df

    def add_custom_exercise(self, exercise_name, category="Custom", description=""):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        try:
            cursor.execute(
                'INSERT INTO custom_exercises (exercise_name, category, description) VALUES (?, ?, ?)',
                (exercise_name, category, description)
            )
            conn.commit()
            result = f"✅ Added: {exercise_name}"
        except sqlite3.IntegrityError:
            result = f"❌ Exercise '{exercise_name}' already exists!"
        conn.close()
        return result

    def save_template(self, template_name, category, description, created_by, exercises_list, is_public=False):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        exercises_json = json.dumps(exercises_list)
        try:
            cursor.execute(
                'INSERT INTO workout_templates (template_name, category, description, created_by, exercises, is_public) VALUES (?, ?, ?, ?, ?, ?)',
                (template_name, category, description, created_by, exercises_json, int(is_public))
            )
            conn.commit()
            result = f"✅ Template '{template_name}' saved!"
        except sqlite3.IntegrityError:
            result = f"❌ Template '{template_name}' already exists!"
        conn.close()
        return result

    def get_templates(self, category=None, created_by=None):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        query = 'SELECT * FROM workout_templates WHERE 1=1'
        params = []
        if category:
            query += ' AND category = ?'; params.append(category)
        if created_by:
            query += ' AND created_by = ?'; params.append(created_by)
        query += ' ORDER BY created_at DESC'
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        templates = []
        for row in rows:
            templates.append({
                'id': row[0], 'name': row[1], 'category': row[2], 'description': row[3],
                'created_by': row[4], 'exercises': json.loads(row[5]), 'is_public': bool(row[6]),
                'created_at': row[7], 'last_used': row[8]
            })
        return templates

    def delete_template(self, template_id):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM workout_templates WHERE id = ?', (template_id,))
        rows = cursor.rowcount
        conn.commit()
        conn.close()
        return "✅ Template deleted!" if rows > 0 else "❌ Template not found!"

    def get_all_exercises(self):
        built_in = [
            'Bench Press','Squat','Deadlift','Overhead Press','Barbell Row','Incline Bench Press',
            'Machine Shoulder Press','Lat Pulldown','Pull-ups','Hack Squat','Leg Press','Romanian Deadlift',
            'Hip Thrust','Leg Curl','Leg Extension','Calf Raises','Bicep Curls','Tricep Pushdown','Dips',
            'Lateral Raises','Face Pulls','Bulgarian Split Squats','Walking Lunges','Close Grip Bench Press',
            'Wide Grip Pulldown','T-Bar Row','Hammer Curls','Chest Supported Row','Front Squat','Military Press','Chin Up'
        ]
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('SELECT exercise_name FROM custom_exercises ORDER BY exercise_name')
        custom = [r[0] for r in cursor.fetchall()]
        conn.close()
        return sorted(set(built_in + custom))

    def get_custom_exercises(self):
        conn = sqlite3.connect(self.db_name)
        try:
            df = pd.read_sql_query(
                'SELECT exercise_name, category, description, created_at FROM custom_exercises ORDER BY created_at DESC',
                conn
            )
        except Exception:
            df = pd.DataFrame()
        conn.close()
        return df

    def get_data(self):
        conn = sqlite3.connect(self.db_name)
        try:
            df = pd.read_sql_query('SELECT * FROM workouts ORDER BY date DESC, exercise, set_number', conn)
            if not df.empty:
                df['date'] = pd.to_datetime(df['date'])
        except Exception:
            df = pd.DataFrame()
        conn.close()
        return df

    def get_exercise_stats(self, exercise):
        df = self.get_data()
        if df.empty or exercise not in df['exercise'].values:
            return None
        ex = df[df['exercise'] == exercise]
        daily = ex.groupby('date').agg({'weight':['max','mean'],'reps':['sum','mean'],'set_number':'count'}).round(2)
        daily.columns = ['max_weight','avg_weight','total_reps','avg_reps','total_sets']
        daily['volume'] = ex.groupby('date').apply(lambda x:(x['reps']*x['weight']).sum())
        daily.reset_index(inplace=True)
        return {
            'daily_stats': daily,
            'max_weight': ex['weight'].max(),
            'total_volume': (ex['reps']*ex['weight']).sum(),
            'total_sets': len(ex),
            'workout_count': ex['date'].nunique(),
            'avg_rpe': ex['rpe'].mean() if ex['rpe'].notna().any() else 0
        }

    def clean_sample_data(self):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        patterns = [
            "Warm up set, felt good","Working weight","Heavy set, good depth",
            "Full range of motion","Great leg session! Gym was quiet, felt strong.",
            "Finished with leg press, good pump"
        ]
        deleted = 0
        for p in patterns:
            cursor.execute('DELETE FROM workouts WHERE set_notes LIKE ? OR workout_notes LIKE ?', (f'%{p}%',f'%{p}%'))
            deleted += cursor.rowcount
        cursor.execute("DELETE FROM workouts WHERE exercise='Hack Squat' AND weight IN (80.0,90.0,100.0) AND reps IN (12,10,8)
```
