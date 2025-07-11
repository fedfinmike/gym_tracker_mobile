--- app_original.py
+++ app_fixed.py
@@
-import streamlit as st
-import pandas as pd
-import matplotlib.pyplot as plt
-import seaborn as sns
-import plotly.express as px
-import plotly.graph_objects as go
+import streamlit as st
+import pandas as pd
+import matplotlib.pyplot as plt
+import plotly.graph_objects as go
 from datetime import datetime, date, timedelta
 import sqlite3
-import numpy as np
-import json
-import time
+import numpy as np
+import json
+import time
@@ st.set_page_config(
 )

-# Professional CSS Styling
+# Professional CSS Styling (updated for submit-button styling)
 st.markdown("""
 <style>
@@
-    .stButton > button[kind="primary"] {
-        background: linear-gradient(135deg, #1e40af 0%, #3b82f6 100%);
-        border: 1px solid #3b82f6;
-        color: white;
-        font-weight: 600;
-        height: 3.5rem;
-    }
-    .stButton > button[kind="primary"]:hover {
-        background: linear-gradient(135deg, #1d4ed8 0%, #2563eb 100%);
-        box-shadow: 0 4px 16px rgba(59, 130, 246, 0.4);
-    }
+    /* Style form submit buttons (type="submit") */
+    .stButton > button[type="submit"] {
+        background: linear-gradient(135deg, #1e40af 0%, #3b82f6 100%);
+        border: 1px solid #3b82f6;
+        color: white;
+        font-weight: 600;
+        height: 3.5rem;
+    }
+    .stButton > button[type="submit"]:hover {
+        background: linear-gradient(135deg, #1d4ed8 0%, #2563eb 100%);
+        box-shadow: 0 4px 16px rgba(59, 130, 246, 0.4);
+    }
@@ def enhanced_quick_log_page():
-        submitted = st.form_submit_button("🚀 LOG SET", use_container_width=True, type="primary")
+        submitted = st.form_submit_button("🚀 LOG SET", use_container_width=True)
@@ def enhanced_quick_log_page():
     if not daily_workout.empty:
         exercises_done = daily_workout['exercise'].unique()
@@
         for exercise_name in exercises_done:
             exercise_sets = daily_workout[daily_workout['exercise'] == exercise_name]
             total_volume = (exercise_sets['reps'] * exercise_sets['weight']).sum()
@@
             for _, set_row in exercise_sets.iterrows():
-                with col1:
-                    notes_display = f" - *{set_row['set_notes']}*" if set_row['set_notes'] else ""
-                    rpe_emoji = "🟢" if set_row['rpe'] <= 7 else "🟡" if set_row['rpe'] <= 8 else "🔴"
-                    st.markdown(f'<div class="set-item">Set {set_row["set_number"]}: {set_row["reps"]} reps @ {set_row["weight"]}kg {rpe_emoji}RPE:{set_row["rpe"]}{notes_display}</div>',
-                               unsafe_allow_html=True)
+                with col1:
+                    notes_display = f" - *{set_row['set_notes']}*" if set_row['set_notes'] else ""
+                    # Handle missing RPE gracefully
+                    rpe_value = set_row['rpe']
+                    if pd.notnull(rpe_value):
+                        if rpe_value <= 7:
+                            rpe_emoji = "🟢"
+                        elif rpe_value <= 8:
+                            rpe_emoji = "🟡"
+                        else:
+                            rpe_emoji = "🔴"
+                        rpe_display = f"RPE:{int(rpe_value)}"
+                    else:
+                        rpe_emoji = ""
+                        rpe_display = ""
+                    st.markdown(
+                        f'<div class="set-item">'
+                        f'Set {set_row["set_number"]}: {set_row["reps"]} reps @ {set_row["weight"]}kg '
+                        f'{rpe_emoji}{rpe_display}{notes_display}'
+                        f'</div>',
+                        unsafe_allow_html=True
+                    )
