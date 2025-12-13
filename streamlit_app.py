import streamlit as st
import google.generativeai as genai
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# --- PAGE SETUP ---
st.set_page_config(page_title="Powerbuilder App", page_icon="💪")
st.title("💪 The Powerbuilder App")
st.caption("Custom AI Coaching for Gym A & Gym B")

# --- GET API KEY ---
try:
    api_key = st.secrets["GEMINI_API_KEY"]
except:
    st.error("No API Key found in secrets.toml")
    st.stop()

# --- HELPER FUNCTION: GET HISTORY ---
def get_recent_history():
    """Fetches the last 5 logs from Google Sheets to give the AI context."""
    try:
        # Connect to Google Sheets
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_dict = st.secrets["service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        
        # Open the Sheet
        sheet = client.open("Powerbuilder Data").sheet1
        
        # Get all data and slice the last 5 rows
        all_values = sheet.get_all_values()
        
        if len(all_values) < 2:
            return "No previous history found."
            
        # Skip header, take last 5
        recent_rows = all_values[1:][-5:]
        
        history_text = ""
        for row in recent_rows:
            # Row format: [Date, Gym, Workout, Log]
            # We construct a string like: "On 2025-12-12 (Workout A): V-Squat 300x10..."
            if len(row) >= 4:
                history_text += f"- On {row[0]} ({row[2]}): {row[3]}\n"
        
        return history_text

    except Exception as e:
        return f"Could not fetch history (Error: {e})"

# --- THE BRAIN (SYSTEM PROMPT) ---
system_instruction = """
ROLE: You are an expert strength coach for a 6 foot 3 inch, 215lb male (ISD). Goal: Powerbuilder physique.
CONSTRAINTS:
1. Injury: WEAK right shoulder. MAX 75lbs on Pectoral Fly.
2. Structure: ALWAYS prescribe exactly 3 working sets per exercise.
3. Reps: Default to 10-12 reps for Compounds, 12-15 for Isolations (unless history dictates otherwise).
4. Format: "Exercise Name: 3 Sets of [Reps] at [Weight]".
5. Safety: If NO history exists for an exercise, prescribe a conservative warm-up weight (e.g., 50% of bodyweight) rather than guessing heavy.

EQUIPMENT & SPLITS:
- Workout A (Gym A - Hammer Strength & Free Weights):
    1. V-Squat Machine (Heavy Quad Focus)
    2. Hammer Strength Flat Press (Max strength. Aim for 140+ lbs)
    3. Hammer Strength Shoulder Press (Front Delts)
    4. Hammer Strength Iso-Lat Chest/Back (Width Focus)
    5. Leg Extension (Isolation)
    6. Hammer Curls (Brachialis)
    7. DB French Press (Tricep Mass)
    8. Back Extension (Spinal Erectors)
    9. Abdominal Machine

- Workout B (Gym B - Aesthetics/Upper Shelf):
    1. Incline DB Press
    2. Lat Pulldown (Cable)
    3. Lateral Raise Machine (Drop sets allowed)
    4. Leg Press
    5. Pectoral Fly Machine (MAX 75 lbs)
    6. Tricep Rope Pushdown
    7. Bicep Curl Machine
    8. Calf Raise (On Leg Press)
    9. Ab Crunch Bench

- Workout C (Gym B - Volume/Width):
    1. Incline Press Machine
    2. Lat Pulldown (Cable)
    3. Lateral Raise Machine
    4. Leg Press
    5. Pectoral Fly Machine (MAX 75 lbs)
    6. Tricep Rope Pushdown
    7. Bicep Curl Machine
    8. Calf Raise (On Leg Press)
    9. Ab Crunch Bench

YOUR JOB:
1. READ the "Recent History" provided in the prompt.
2. COMPARE the last logged weight for specific exercises to the current plan.
3. CALCULATE the new target weight (Progressive Overload). If they hit the goal, add 5-10lbs. If they failed, hold or reduce.
4. GENERATE the dashboard.
"""

# --- THE USER INTERFACE ---
gym_choice = st.selectbox("Where are you?", ["Gym A (Hammer Strength)", "Gym B (Cables)"])
workout_choice = st.selectbox("Which Workout?", ["Workout A", "Workout B", "Workout C"])
user_notes = st.text_input("Any specific notes for today? (Optional)")

# --- THE GENERATE BUTTON ---
if st.button("Generate My Workout"):
    try:
        # 1. Fetch History Automatically
        with st.spinner("Checking your past workouts..."):
            past_history = get_recent_history()
        
        # 2. Configure the Brain
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.5-flash", system_instruction=system_instruction)
        
        # 3. Create the Prompt
        user_prompt = f"""
        CONTEXT:
        - Current Location: {gym_choice}
        - Current Workout: {workout_choice}
        - User's Specific Notes Today: {user_notes}
        
        RECENT HISTORY (From Database):
        {past_history}
        
        TASK:
        Create today's dashboard. Look at the history above to determine the weights.
        """
        
        # 4. Get the Answer
        with st.spinner("Coach is calculating weights..."):
            response = model.generate_content(user_prompt)
            st.markdown(response.text)
            
    except Exception as e:
        st.error(f"Error: {e}")

# --- LOGGING SECTION ---
st.divider()
st.subheader("📝 Live Workout Log")
st.caption("Enter results here (e.g., 'V-Squat: 315x10'). This saves to your permanent database.")

session_data = st.text_area("Session Results:", height=150)

if st.button("Save to Google Sheets"):
    if not session_data:
        st.error("Please type something first!")
    else:
        try:
            scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
            creds_dict = st.secrets["service_account"]
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
            client = gspread.authorize(creds)
            sheet = client.open("Powerbuilder Data").sheet1
            
            today_date = datetime.now().strftime("%Y-%m-%d")
            row_data = [today_date, gym_choice, workout_choice, session_data]
            sheet.append_row(row_data)
            
            st.success("✅ Saved! The app will remember this next time.")
            
        except Exception as e:
            st.error(f"Error saving to sheets: {e}")