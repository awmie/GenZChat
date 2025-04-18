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
                IMPORTANT: Remember the entire conversation history and refer back to it in your responses when relevant.
                If the user mentions something from earlier in the conversation, acknowledge it.
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
    
    # If conversation history is getting too long, keep only the system prompt and last 10 exchanges
    if len(session['conversation']) > 21:  # system prompt + 20 messages (10 exchanges)
        system_prompt = session['conversation'][0]
        recent_messages = session['conversation'][-20:]
        session['conversation'] = [system_prompt] + recent_messages
        # Force session save
        session.modified = True

    try:
        response = client.chat.completions.create(
            model="",
            messages=session['conversation'],
            web_search=True
        )

        bot_response = response.choices[0].message.content.strip()
        if bot_response:
            # Changed role to "assistant" for bot response storage
            session['conversation'].append({"role": "assistant", "content": bot_response})
            # Force session save
            session.modified = True
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
