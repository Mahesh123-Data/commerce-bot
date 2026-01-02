from flask import Flask, request, jsonify
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Debug logging
DEBUG_FILE = '/tmp/bot_debug.log'

def log_debug(msg):
    try:
        with open(DEBUG_FILE, 'a') as f:
            f.write(f"[{datetime.now()}] {msg}\n")
        sys.stderr.write(f"[DEBUG] {msg}\n")
        sys.stderr.flush()
    except Exception as e:
        sys.stderr.write(f"Log error: {e}\n")
        sys.stderr.flush()

# Twilio setup
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_WHATSAPP_NUMBER = os.getenv('TWILIO_WHATSAPP_NUMBER')
client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# COMMERCE COURSES
COURSES = {
    '1': {'name': 'CA Foundation', 'fee': '₹25,000'},
    '2': {'name': 'CA Intermediate', 'fee': '₹35,000'},
    '3': {'name': 'CMA Foundation', 'fee': '₹22,000'},
    '4': {'name': 'Class 11th Commerce', 'fee': '₹18,000'},
    '5': {'name': 'Class 12th Commerce', 'fee': '₹20,000'},
}

user_state = {}

def welcome():
    return """👋 नमस्ते! 

💼 **Commerce Excellence Academy**

📚 Top Courses:
1️⃣ CA Foundation
2️⃣ CA Intermediate 
3️⃣ CMA Foundation
4️⃣ Class 11th Commerce
5️⃣ Class 12th Commerce

Number bhejo 👉"""

@app.route('/whatsapp', methods=['POST'])
def whatsapp():
    msg = request.values.get('Body', '').strip()
    phone = request.values.get('From', '').replace('whatsapp:', '')
    
    log_debug(f"MSG_RECEIVED: phone={phone}, msg={msg}")
    
    if phone not in user_state:
        user_state[phone] = {'step': 'welcome'}
        log_debug(f"NEW_USER: {phone}")
    
    state = user_state[phone]
    log_debug(f"CURRENT_STEP: {state['step']}")
    
    resp = MessagingResponse()
    rmsg = resp.message()
    
    if state['step'] == 'welcome':
        log_debug("STEP: welcome")
        rmsg.body(welcome())
        state['step'] = 'course'
    
    elif state['step'] == 'course':
        log_debug(f"STEP: course, msg={msg}")
        if msg in COURSES:
            state['course'] = msg
            course = COURSES[msg]
            rmsg.body(f"""✅ **{course['name']}**
💰 Fee: {course['fee']}

1️⃣ Interested
3️⃣ Back""")
            state['step'] = 'reply'
            log_debug(f"COURSE_SELECTED: {course['name']}")
        else:
            rmsg.body("1-5 choose karo")
    
    elif state['step'] == 'reply':
        log_debug(f"STEP: reply, msg={msg}")
        if msg == '1':
            rmsg.body("👤 Name bhejo:")
            state['step'] = 'name'
        elif msg == '3':
            rmsg.body(welcome())
            state['step'] = 'course'
    
    elif state['step'] == 'name':
        log_debug(f"STEP: name, name={msg}")
        state['name'] = msg
        rmsg.body("📧 Email:")
        state['step'] = 'email'
    
    elif state['step'] == 'email':
        log_debug(f"STEP: email, email={msg}")
        state['email'] = msg
        rmsg.body("📱 Phone:")
        state['step'] = 'phone'
    
    elif state['step'] == 'phone':
        log_debug(f"STEP: phone, phone_input={msg}")
        state['phone'] = msg
        course = COURSES[state['course']]
        
        log_debug(f"PHONE_STEP_DATA: name={state.get('name')}, email={state.get('email')}, phone={msg}, course={course['name']}")
        
        # Save to Google Sheets
        try:
            log_debug("SHEETS_INIT: Starting gspread import")
            import gspread
            from google.oauth2.service_account import Credentials
            
            SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
            log_debug("SHEETS_AUTH: Loading credentials.json")
            
            creds = Credentials.from_service_account_file('./credentials.json', scopes=SCOPES)
            gc = gspread.authorize(creds)
            
            sheet_id = os.getenv('GOOGLE_SHEETS_ID')
            log_debug(f"SHEETS_OPENING: sheet_id={sheet_id}")
            
            sheet = gc.open_by_key(sheet_id).sheet1
            
            status = "Interested"
            notes = f"Course: {course['name']}"
            row = [
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                phone,
                state['name'],
                state['email'],
                state['phone'],
                course['name'],
                course['fee'],
                status,
                notes
            ]
            
            log_debug(f"SHEETS_APPEND: row={row}")
            sheet.append_row(row)
            log_debug(f"SHEETS_SUCCESS: Lead saved for {state['name']}")
            
        except Exception as e:
            log_debug(f"SHEETS_ERROR: {type(e).__name__}: {str(e)}")
        
        log_debug("SHEETS_BLOCK_COMPLETE")
        
        rmsg.body(f"""✅ **Thank you {state['name']}**!

Course: {course['name']}
Email: {state['email']}
Phone: {state['phone']}

Counselor call karega! 📞""")
        state['step'] = 'welcome'
    
    return str(resp)

@app.route('/broadcast', methods=['POST'])
def broadcast():
    data = request.get_json()
    numbers = data.get('numbers', [])
    message = data.get('message', '')
    
    for number in numbers:
        client.messages.create(from_=TWILIO_WHATSAPP_NUMBER, to=number, body=message)
    
    return jsonify({'status': 'sent'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
