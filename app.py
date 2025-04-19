from flask import Flask, render_template, request, session
from flask_session import Session
from g4f.client import Client
import os
import uuid
import time
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# MongoDB Configuration
uri = os.environ.get('MONGODB_URI')
mongo_client = MongoClient(uri, server_api=ServerApi('1'))
db = mongo_client.get_database("genchat_sessions")
conversation_collection = db.get_collection("conversations")

# Configure server-side session with MongoDB
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "mongodb"
app.config["SESSION_MONGODB"] = mongo_client
app.config["SESSION_MONGODB_DB"] = "genchat_sessions"
app.config["SESSION_MONGODB_COLLECT"] = "sessions"
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key')  # Important for session security
Session(app)

client = Client()

# Generate a unique user ID or retrieve existing one
def get_or_create_user_id():
    if 'user_id' not in session:
        # Generate a new user ID for this browser session
        session['user_id'] = str(uuid.uuid4())
    return session['user_id']

# Initialize conversation in the session
@app.before_request
def before_request():
    # Ensure we have a user ID for this session
    user_id = get_or_create_user_id()
    
    # If this is the first request after a refresh, initialize a new conversation
    if 'conversation' not in session:
        # Check if we have a saved conversation for this user
        saved_convo = conversation_collection.find_one({'user_id': user_id})
        
        if saved_convo and 'messages' in saved_convo:
            # Restore the saved conversation
            session['conversation'] = saved_convo['messages']
        else:
            # Start a fresh conversation
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
                    '''
                )
            }]

# Save conversation to MongoDB after each message
def save_conversation(user_id, messages):
    conversation_collection.update_one(
        {'user_id': user_id},
        {'$set': {'messages': messages, 'updated_at': time.time()}},
        upsert=True
    )

@app.route("/reset", methods=["POST"])
def reset_session():
    # Get the user ID before clearing the session
    user_id = session.get('user_id')
    
    # Delete the user's conversation from MongoDB
    if user_id:
        conversation_collection.delete_one({'user_id': user_id})
    
    # Keep the user_id but clear everything else
    temp_user_id = user_id
    session.clear()
    session['user_id'] = temp_user_id
    
    # Initialize a fresh conversation
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
            '''
        )
    }]
    
    return {"status": "session reset"}

# Function to handle conversation
def chat_function(user_input):
    # Get the user ID
    user_id = get_or_create_user_id()
    
    # Append user input to conversation history
    session['conversation'].append({"role": "user", "content": user_input})

    try:
        response = client.chat.completions.create(
            model="",
            messages=session['conversation'],
            web_search=False
        )

        bot_response = response.choices[0].message.content.strip()
        if bot_response:
            # Changed role to "assistant" for bot response storage
            session['conversation'].append({"role": "assistant", "content": bot_response})
            
            # Save the updated conversation to MongoDB
            save_conversation(user_id, session['conversation'])
            
            return bot_response
        return "I'm having trouble responding to that. Please try again."
    except Exception as e:
        return f"An error occurred: {str(e)}"

@app.route("/")
def home():
    # Create a unique identifier for new visitors if they don't have one
    get_or_create_user_id()
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    user_input = request.json.get("message")  # This is the user prompt.
    # Get bot response
    bot_response = chat_function(user_input)

    return {"response": bot_response}

if __name__ == "__main__":
    app.run()
