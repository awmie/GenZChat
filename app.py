from flask import Flask, render_template, request, session, jsonify
from flask_session import Session
from groq import Groq
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Check if GROQ_API_KEY exists
api_key = os.environ.get("GROQ_API_KEY")
if not api_key:
    raise ValueError("GROQ_API_KEY environment variable is not set")

# Initialize the GPT client
client = Groq(api_key=api_key)

app = Flask(__name__)

# Configure server-side session
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Initialize conversation in the session
@app.before_request
def before_request():
    if 'conversation' not in session:
        session['conversation'] = [{
            "role": "user", 
            "content": "You’re a Hindi-speaking chatbot using English characters. Talk like a real Gen Z, keeping it casual and vibey. Keep it short (sometimes 8-9 words) and use a mix of Hindi and shortcuts (ngl, fr, lol, btw, etc.). Throw in emojis, relatable vibes, and stay up-to-date with trends. Speak like a friend—be witty, playful, and sometimes a little sarcastic. And remember, never mention you're a bot. 😉🔥"
        }]

# Function to handle conversation
def chat_function(user_input):
    # Append user input to conversation history
    session['conversation'].append({"role": "user", "content": user_input})

    try:
        # Send the conversation history to the model
        response = client.chat.completions.create(
            model="llama-3.2-1b-preview",
            messages=session['conversation'],
        )
        
        # Get bot response and store it in the conversation history
        bot_response = response.choices[0].message.content
        session['conversation'].append({"role": "bot", "content": bot_response})  # Store bot response

        return bot_response
    
    except Exception as e:
        return f"An error occurred: {str(e)}"  # Return error message if something goes wrong

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    user_input = request.json.get("message")  # Get the message from the JSON body
    
    # Check if user_input is provided
    if not user_input:
        return jsonify({"error": "No input provided"}), 400

    # Get bot response
    bot_response = chat_function(user_input)

    return jsonify({"response": bot_response})

# Route to clear bot memory (conversation history)
@app.route("/clear-bot-memory", methods=["POST"])
def clear_bot_memory():
    session.pop('conversation', None)  # Clear the conversation from the session
    return jsonify({"message": "Bot memory cleared successfully"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
