import os
import sys
import subprocess
import webbrowser # <--- ADD THIS IMPORT
import time       # <--- ADD THIS IMPORT
import xlsxwriter

# This part is crucial for making the executable work correctly.
if getattr(sys, 'frozen', False):
    base_path = sys._MEIPASS
else:
    base_path = os.path.dirname(os.path.abspath(__file__))

# Construct the full path to the admin script
admin_script_path = os.path.join(base_path, "1_👑_Admin.py")

# The command to run the Streamlit app
command = [
    "streamlit", "run", admin_script_path,
    "--server.headless", "true",
    "--server.port", "8501"
]

# Run the command in a non-blocking way
subprocess.Popen(command)

# --- THIS IS THE NEW PART ---
# Give the server a moment to start up
time.sleep(3)

# Now, tell the OS to open the default web browser to the correct URL
webbrowser.open("http://localhost:8501")