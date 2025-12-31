from flask import Flask, request, jsonify
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
import gspread
from google.oauth2.service_account import Credentials
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Twilio setup
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_WHATSAPP_NUMBER = os.getenv('TWILIO_WHATSAPP_NUMBER')
client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# Google Sheets setup
SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
creds = Credentials.from_service_account_file(os.getenv('GOOGLE_CREDENTIALS_PATH'), scopes=SCOPES)
gc = gspread.authorize(creds)
sheet = gc.open_by_key(os.getenv('GOOGLE_SHEETS_ID')).sheet1

# COMMERCE COACHING COURSES
COURSES = {
    '1': {'name': 'CA Foundation', 'fee': '₹25,000', 'timing': '7AM-10AM, 6PM-9PM'},
    '2': {'name': 'CA Intermediate', 'fee': '₹35,000', 'timing': '6AM-9AM, 5PM-8PM'},
    '3': {'name': 'CMA Foundation', 'fee': '₹22,000', 'timing': '8AM-11AM, 4PM-7PM'},
    '4': {'name': 'Class 11th Commerce', 'fee': '₹18,000', 'timing': '9AM-12PM'},
    '5': {'name': 'Class 12th Commerce', 'fee': '₹20,000', 'timing': '3PM-6PM'},
}

# Conversation state
user_state = {}

def welcome_message():
    return """👋 नमस्ते! 

💼 **Commerce Excellence Academy** में आपका स्वागत!

📚 **हमारे Top Courses:**

1️⃣ CA Foundation
2️⃣ CA Intermediate 
3️⃣ CMA Foundation
4️⃣ Class 11th Commerce
5️⃣ Class 12th Commerce

अपना course number भेजें 👉"""

def course_details(course_id):
    if course_id in COURSES:
        course = COURSES[course_id]
        return f"""✅ **{course['name']}**

💰 **Full Course Fee:** {course['fee']}
⏰ **Batch Timing:** {course['timing']}
📖 **100% Syllabus Coverage**
✅ **Weekly Tests + Doubt Classes**
📱 **Live + Recorded Classes**
🎯 **100+ Selections Every Year**

क्या interested हैं?
1️⃣ हाँ, enrollment के लिए contact करें
2️⃣ और details चाहिए
3️⃣ दूसरे courses देखें"""

@app.route('/whatsapp', methods=['POST'])
def whatsapp_webhook():
    incoming_msg = request.values.get('Body', '').strip()
    from_number = request.values.get('From', '')
    
    phone = from_number.replace('whatsapp:', '')
    
    if phone not in user_state:
        user_state[phone] = {'step': 'welcome'}
    
    state = user_state[phone]
    response = MessagingResponse()
    msg = response.message()
    
    if state['step'] == 'welcome':
        msg.body(welcome_message())
        state['step'] = 'course_select'
    
    elif state['step'] == 'course_select':
        if incoming_msg in COURSES:
            state['course'] = incoming_msg
            msg.body(course_details(incoming_msg))
            state['step'] = 'course_reply'
        else:
            msg.body("❌ कृपया 1-5 में से कोई एक number चुनें")
    
    elif state['step'] == 'course_reply':
        if incoming_msg == '1':
            msg.body("✨ **बहुत अच्छा decision!**\n\n👤 अपना पूरा नाम भेजें:")
            state['step'] = 'name'
        elif incoming_msg == '3':
            msg.body(welcome_message())
            state['step'] = 'course_select'
        else:
            msg.body("1 (हाँ) या 3 (वापस) चुनें")
    
    elif state['step'] == 'name':
        state['name'] = incoming_msg
        msg.body("📧 Email ID भेजें:\n(example: student@gmail.com)")
        state['step'] = 'email'
    
    elif state['step'] == 'email':
        state['email'] = incoming_msg
        msg.body("📱 Phone number भेजें:\n(9876543210)")
        state['step'] = 'phone'
    
    elif state['step'] == 'phone':
        state['phone'] = incoming_msg
        
        # SAVE TO GOOGLE SHEETS 🚀
        row = [
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            state['name'],
            state['phone'],
            state['email'],
            COURSES[state['course']]['name'],
            COURSES[state['course']]['fee'],
            COURSES[state['course']]['timing'],
            "NEW LEAD"
        ]
        sheet.append_row(row)
        print(f"✅ NEW LEAD SAVED: {state['name']} - {COURSES[state['course']]['name']}")
        
        msg.body(f"""🎉 **धन्यवाद {state['name']} जी!**

✅ **आपकी जानकारी save हो गई:**

👤 **Name:** {state['name']}
📧 **Email:** {state['email']}
📱 **Phone:** {state['phone']}
📚 **Course:** {COURSES[state['course']]['name']}
💰 **Fees:** {COURSES[state['course']]['fee']}
⏰ **Timing:** {COURSES[state['course']]['timing']}

📞 **हमारा counselor 2 घंटे में contact करेगा!**

💼 **Commerce Excellence Academy**
*CA | CMA | 11th-12th Commerce*""")
        
        # Reset for next conversation
        user_state[phone] = {'step': 'welcome'}
    
    return str(response)

@app.route('/broadcast', methods=['POST'])
def broadcast():
    data = request.get_json()
    numbers = data.get('numbers', [])
    message = data.get('message', '')
    
    results = []
    for number in numbers:
        try:
            client.messages.create(
                from_=TWILIO_WHATSAPP_NUMBER,
                to=number,
                body=message
            )
            results.append({'number': number, 'status': 'sent'})
            print(f"📤 Broadcast sent to {number}")
        except Exception as e:
            results.append({'number': number, 'status': 'failed', 'error': str(e)})
    
    return jsonify({'sent': len([r for r in results if r['status'] == 'sent']), 'total': len(numbers), 'results': results})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
