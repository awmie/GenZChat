from flask import Flask, render_template, request, session
from flask_session import Session
from groq import Groq
import os
# Initialize the GPT client
client = Groq(api_key=os.environ["GROQ_API_KEY"])

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

    # Send the conversation history to the model
    response = client.chat.completions.create(
        model="llama-3.2-90b-vision-preview",
        messages=session['conversation'],
    )

    # Get bot response and store it in the conversation history
    bot_response = response.choices[0].message.content
    session['conversation'].append({"role": "bot", "content": bot_response})  # Store bot response

    return bot_response

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    user_input = request.json.get("message")  # Get the message from the JSON body

    # Get bot response
    bot_response = chat_function(user_input)

    return {"response": bot_response}

# Route to clear bot memory (conversation history)
@app.route("/clear-bot-memory", methods=["POST"])
def clear_bot_memory():
    session.pop('conversation', None)  # Clear the conversation from the session
    return {"message": "Bot memory cleared successfully"}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
