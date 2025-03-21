import os
import logging
from flask import Flask, render_template, request, jsonify
from groq import Groq
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
load_dotenv()

app = Flask(__name__)

try:
    client = Groq(api_key="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")
    logger.info("Successfully initialized Groq client")
except Exception as e:
    logger.error(f"Failed to initialize Groq client: {e}")
    client = None


chat_history = []
feedback_list = []

#dummy data
dummy_data = {
    "1234567890": {
        "name": "Rahul Sharma",
        "credit_card_no": "5123-4567-8912-3456",
        "phone_no": "9876543210",
        "email": "rahul.sharma@example.com",
        "status": "active",
        "card_type": "HDFC Infinia Metal",
        "last_payment": "₹15,000",
        "due_date": "25th monthly",
        "cvv": "***",  
        "expiry": "12/2025",
        "billing_address": "12-B, MG Road, Mumbai"
    },
    "9876543210": {
        "name": "Priya Patel",
        "credit_card_no": "4024-0071-2345-6789",
        "phone_no": "8765432109",
        "email": "priya.patel@example.com",
        "status": "blocked",
        "card_type": "HDFC Regalia Gold",
        "last_payment": "₹22,500",
        "due_date": "5th monthly",
        "cvv": "***",
        "expiry": "09/2026",
        "billing_address": "45/A, Koramangala, Bangalore"
    },
    "1122334455": {
        "name": "Amit Verma",
        "credit_card_no": "3782-8224-6310-005",
        "phone_no": "7654321098",
        "email": "amit.verma@example.com",
        "status": "expired",
        "card_type": "HDFC MoneyBack+",
        "last_payment": "₹8,000",
        "due_date": "15th monthly",
        "cvv": "***",
        "expiry": "03/2024",
        "billing_address": "9th Cross, Hyderabad"
    }
}

def call_llm(query):
    """Handle generic queries with LLM"""
    if not client:
        return default_assistance()
    
    try:
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": """You are HDFC Bank's official assistant. Provide 
                accurate information about banking services. For account-specific issues, 
                always direct users to official channels. Be concise and professional."""},
                {"role": "user", "content": f"HDFC Query: {query}"}
            ],
            model="llama-3.2-3b-preview",
            temperature=0.3,
            max_tokens=256
        )
        llm_response = response.choices[0].message.content
        return f"{llm_response}\n\n{default_assistance()}"
    
    except Exception as e:
        logger.error(f"LLM Error: {e}")
        return default_assistance()

def default_assistance():
    """Standard assistance message"""
    return """For immediate help:
📞 Call: 1800-202-6161 (24/7)
🌐 Visit: https://www.hdfcbank.com
📱 Use Mobile Banking App"""

def validate_account_details(user_input, account):
    """Check if provided details match account"""
    input_lower = user_input.lower()
    
    checks = [
        ("phone number", account["phone_no"]),
        ("email", account["email"]),
        ("last payment", account["last_payment"].lower()),
        ("due date", account["due_date"].lower()),
        ("billing address", account["billing_address"].lower())
    ]
    
    for field, value in checks:
        if field in input_lower and value in input_lower:
            return True
    return False

def process_message(message):
    message = message.lower().strip()
    logger.info(f"Processing: {message}")

    # 1. Check for account recovery flow
    recovery_keywords = [
        'forgot', 'remember', 'lost card',
        'details', 'retrieve', 'recover'
    ]
    if any(keyword in message for keyword in recovery_keywords):
        return handle_account_recovery(message)
    
    # 2. Check if account number is provided
    if any(acc_no in message for acc_no in dummy_data.keys()):
        account_no = next((acc_no for acc_no in dummy_data.keys() if acc_no in message), None)
        if account_no:
            return handle_account_specific_query(account_no, message)
    
    # 3. Check for card not working scenarios
    card_issue_keywords = [
        'not working', 'declined', 'blocked', 
        'transaction failed', 'card issue'
    ]
    if any(keyword in message for keyword in card_issue_keywords):
        return handle_card_issues(message)
    
    # 4. Generic queries
    return call_llm(message)

def handle_account_specific_query(account_no, message):
    """Handle queries where account number is provided"""
    account = dummy_data.get(account_no)
    if not account:
        return "Account number not found. Please try again or visit nearest branch."
    
    # Check for card issues
    card_issue_keywords = [
        'not working', 'declined', 'blocked', 
        'transaction failed', 'card issue'
    ]
    if any(keyword in message for keyword in card_issue_keywords):
        return handle_card_issues(message, account_no)
    
    # Default response for account-specific queries
    return (f"Thank you, {account['name']}. How can I assist you with your {account['card_type']}?\n"
            f"Your card is currently {account['status']}.\n"
            f"Last payment: {account['last_payment']} (Due: {account['due_date']})\n\n"
            "For further assistance:\n"
            "📞 Call: 1800-202-6161\n"
            "🌐 Visit: https://www.hdfcbank.com")

def handle_card_issues(message, account_no=None):
    """Handle predefined card issues"""
    solutions = {
        'blocked': "Your card was temporarily blocked for security. Please visit "
                   "https://hdfc.cardreactivate.com or call 1800-202-6161.",
        'expired': "Your card has expired. New card already dispatched to: "
                   f"{dummy_data['1122334455']['billing_address']}",
        'active': "Your card appears active. Please check:\n"
                  "1. Available balance\n2. Expiry date\n3. Merchant POS terminal",
        'default': "For card issues, please:\n"
                   "1. Check https://hdfc.cardstatus.com\n"
                   "2. Visit nearest branch\n"
                   "3. Call 24/7 helpline"
    }
    
    if account_no:
        status = dummy_data[account_no]['status']
        return solutions.get(status, solutions['default'])
    
    return "For card assistance, please provide your registered mobile number or account number."

def handle_account_recovery(message):
    """Multi-step account recovery with proper matching"""
    # Check if we're already in recovery flow
    last_resp = chat_history[-1]['bot'].lower() if chat_history else ""
    
    # Step 1: Initial recovery request
    if 'recovery' not in last_resp:
        return ("Let's help recover your account. Please share any of these:\n"
                "📱 Last 4 digits of registered mobile\n"
                "📧 Email address\n"
                "💳 Last payment amount\n"
                "🏠 Part of billing address")
    
    # Step 2: Validate provided details
    for account_no, account in dummy_data.items():
        # Check mobile last 4 digits
        if message.strip().isdigit() and len(message.strip()) == 4:
            if message.strip() == account['phone_no'][-4:]:
                return generate_recovery_response(account)
        
        # Check email
        if '@' in message and message.strip().lower() == account['email'].lower():
            return generate_recovery_response(account)
        
        # Check last payment
        if 'payment' in last_resp and message.strip().lower() == account['last_payment'].lower():
            return generate_recovery_response(account)
        
        # Check billing address
        if any(word.lower() in account['billing_address'].lower() 
               for word in message.split() if len(word) > 3):
            return generate_recovery_response(account)
    
    # If no match found
    return ("The details you provided don't match our records. Please try again with:\n"
            "1. Exact last 4 digits of registered mobile\n"
            "2. Complete email address\n"
            "3. Full billing address\n"
            "4. Exact last payment amount")

def generate_recovery_response(account):
    """Generate account recovery response with masked details"""
    masked_card = '****-****-****-' + account['credit_card_no'][-4:]
    masked_phone = '*******' + account['phone_no'][-3:]
    
    return (f"Account verified! Here are your details:\n\n"
            f"👤 Name: {account['name']}\n"
            f"💳 Card: {masked_card}\n"
            f"📱 Phone: {masked_phone}\n"
            f"📧 Email: {account['email']}\n"
            f"🏠 Billing Address: {account['billing_address']}\n\n"
            f"Your {account['card_type']} is currently {account['status']}.\n"
            f"Last payment: {account['last_payment']} (Due: {account['due_date']})\n\n"
            "For further assistance:\n"
            "📞 Call: 1800-202-6161\n"
            "🌐 Visit: https://www.hdfcbank.com")


@app.route('/')
def home():
    return render_template('index.html')

@app.route('/chatbot')
def chatbot():
    return render_template('chatbot.html')

@app.route('/handle_chat', methods=['POST'])
def handle_chat():
    user_message = request.form['message']
    response = process_message(user_message)
    chat_history.append({'user': user_message, 'bot': response})
    return jsonify({'response': response})

if __name__ == '__main__':
    app.run(debug=True)
