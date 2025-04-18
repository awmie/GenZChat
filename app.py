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
                '''
            )
        }]

@app.route("/reset", methods=["POST"])
def reset_session():
    session.clear()  # Clear the session data
    return {"status": "session reset"}

# Function to handle conversation
def chat_function(user_input):
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
            return bot_response
        return "I'm having trouble responding to that. Please try again."
    except Exception as e:
        return f"An error occurred: {str(e)}"

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    user_input = request.json.get("message")  # This is the user prompt.
    # Get bot response
    bot_response = chat_function(user_input)

    return {"response": bot_response}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
