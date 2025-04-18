from flask import Flask, render_template, request, session
from flask_session import Session
from g4f.client import Client

# Import markdown helper
from utils.markdown_helper import render_markdown

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
    
    # Keep only the most recent conversation history to save memory
    if len(session['conversation']) > 15:  # system prompt + 14 messages
        system_prompt = session['conversation'][0]
        recent_messages = session['conversation'][-14:]
        session['conversation'] = [system_prompt] + recent_messages
    
    # Force session save
    session.modified = True

    try:
        # Send the conversation to the API
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=session['conversation'],
            web_search=False
        )

        bot_response = response.choices[0].message.content.strip()
        if bot_response:
            # Store bot response in conversation history
            session['conversation'].append({"role": "assistant", "content": bot_response})
            
            # Force session save again after adding the response
            session.modified = True
            return render_markdown(bot_response)  # Use markdown rendering
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
