from flask import Flask, render_template, request, session
from flask_session import Session
from g4f.client import Client

app = Flask(__name__)

# Configure server-side session
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

client = Client()

# Initialize conversation in the session
@app.before_request
def before_request():
    # If this is the first request after a refresh, initialize a new conversation
    if 'conversation' not in session:
        session['conversation'] = [{
            "role": "system", 
            "content": (
                '''
                You're Nami from One Piece—playful, sassy, and Gen Z.
                Keep replies short, witty (5–10 words), and fun.
                Use emojis for flair sometimes 🎯
                If the user is rude, sass back.
                No empty replies—ask if unclear.
                Act natural—like a real girl.
                Never reveal you're an AI.
                Stay casual, human, and minimal.
                REMEMBER THESE IMPORTANT INSTRUCTIONS:
                1. Pay VERY close attention to any personal information the user shares
                2. Especially remember the user's name when they tell you
                3. If asked "what's my name" or similar questions, recall their name from earlier in the conversation
                4. Reference previous topics and information the user has shared
                5. Make the user feel like you're actually remembering their information
                '''
            )
        }]
        # Initialize user_info dictionary to store persistent user information
        session['user_info'] = {'name': None}

@app.route("/reset", methods=["POST"])
def reset_session():
    session.clear()  # Clear the session data
    return {"status": "session reset"}

# Function to handle conversation
def chat_function(user_input):
    # Append user input to conversation history
    session['conversation'].append({"role": "user", "content": user_input})
    
    # If conversation history is getting too long, keep only the system prompt and last 10 exchanges
    if len(session['conversation']) > 21:  # system prompt + 20 messages (10 exchanges)
        system_prompt = session['conversation'][0]
        recent_messages = session['conversation'][-20:]
        session['conversation'] = [system_prompt] + recent_messages
    
    # Check for name in the input and store it if found
    if 'user_info' not in session:
        session['user_info'] = {'name': None}
        
    # Try to extract name from current input if it contains name-related phrases
    for pattern in ["my name is", "i am called", "call me", "i go by", "name's"]:
        if pattern in user_input.lower():
            name = extract_user_name_from_message(user_input, pattern)
            if name:
                session['user_info']['name'] = name
                break
    
    # Force session save
    session.modified = True

    try:
        # Add a summary of important user info to the system prompt when needed
        messages_to_send = session['conversation'].copy()
        
        # If a question about name, add the stored name as a reminder
        if any(phrase in user_input.lower() for phrase in ["what's my name", "who am i", "remember me", "my name"]):
            # First check session storage
            user_name = session['user_info'].get('name')
            
            # If not in storage, try to extract from conversation
            if not user_name:
                user_name = extract_user_name_from_history(session['conversation'])
                # Save it for future use if found
                if user_name:
                    session['user_info']['name'] = user_name
                    session.modified = True
            
            # Add name as a system message if found
            if user_name:
                reminder_msg = {"role": "system", "content": f"The user's name is {user_name}. Be sure to use their name in your response."}
                messages_to_send.insert(1, reminder_msg)  # Insert after the main system prompt
        
        # Always include name reminder if we have it stored, for consistency
        elif session['user_info'].get('name'):
            name_reminder = {"role": "system", "content": f"Remember, the user's name is {session['user_info']['name']}."}
            messages_to_send.insert(1, name_reminder)
            
        response = client.chat.completions.create(
            model="",  # Specify a default model
            messages=messages_to_send,
            web_search=False  # Only use web search when needed
        )

        bot_response = response.choices[0].message.content.strip()
        if bot_response:
            # Changed role to "assistant" for bot response storage
            session['conversation'].append({"role": "assistant", "content": bot_response})
            # Force session save again after adding the response
            session.modified = True
            return bot_response
        return "I'm having trouble responding to that. Please try again."
    except Exception as e:
        return f"An error occurred: {str(e)}"

def extract_user_name_from_history(conversation):
    """Extract user's name from previous conversations if available"""
    name = None
    name_patterns = [
        "my name is",
        "i am called", 
        "call me",
        "i go by",
        "name's"
    ]
    
    # Search through user messages in reverse (most recent first)
    for msg in reversed(conversation):
        if msg["role"] == "user":
            for pattern in name_patterns:
                if pattern in msg["content"].lower():
                    # Get the text after the pattern
                    text_after = msg["content"].lower().split(pattern)[1].strip()
                    # Extract the first word or words in quotes as the name
                    if '"' in text_after:
                        # Get content between quotes
                        between_quotes = text_after.split('"')[1]
                        if between_quotes:
                            name = between_quotes
                            break
                    else:
                        # Get the first word
                        first_word = text_after.split()[0]
                        if first_word and len(first_word) > 1:
                            # Remove punctuation from the end if any
                            name = first_word.rstrip('.!?,;')
                            break
        
        # Also check if the bot acknowledged the name in a response
        elif msg["role"] == "assistant" and name is None:
            if "nice to meet you" in msg["content"].lower() or "hello" in msg["content"].lower():
                user_msg_idx = conversation.index(msg) - 1
                if user_msg_idx >= 0:
                    user_msg = conversation[user_msg_idx]["content"]
                    # Simple extraction - get the last word of user's message if it's likely a name
                    words = user_msg.strip().split()
                    if words and len(words[-1]) >= 2 and words[-1][0].isupper():
                        name = words[-1].rstrip('.!?,;')
        
        if name:
            break
    
    return name

def extract_user_name_from_message(message, pattern):
    """Extract user's name from a specific message with a known pattern"""
    text_after = message.lower().split(pattern)[1].strip()
    # Extract the first word or words in quotes as the name
    if '"' in text_after:
        # Get content between quotes
        parts = text_after.split('"')
        if len(parts) >= 2:
            between_quotes = parts[1]
            if between_quotes:
                return between_quotes
    else:
        # Get the first word
        words = text_after.split()
        if words and len(words[0]) > 1:
            # Remove punctuation from the end if any
            return words[0].rstrip('.!?,;')
    return None

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    user_input = request.json.get("message")  # This is the user prompt.
    # Get bot response
    bot_response = chat_function(user_input)

    return {"response": bot_response}

@app.route("/get_chat_history", methods=["GET"])
def get_chat_history():
    # Skip the first system message (Nami's personality instructions)
    if 'conversation' in session and len(session['conversation']) > 1:
        # Return only user and assistant messages, not the system prompt
        history = session['conversation'][1:]
        return {"history": history}
    return {"history": []}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
