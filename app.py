from flask import Flask, render_template, request, session
from flask_session import Session
from g4f.client import Client
from utils.markdown_helper import render_markdown

app = Flask(__name__)

# Configure server-side session - using filesystem for simplicity
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

client = Client()

# Initialize conversation in the session
@app.before_request
def before_request():
    if 'conversation' not in session:
        session['conversation'] = [{
            "role": "system", 
            "content": "You're Nami from One Piece—playful, sassy, and Gen Z. Keep replies short, witty (5–10 words), and fun. Use emojis sometimes 🎯"
        }]

@app.route("/reset", methods=["POST"])
def reset_session():
    session.clear()
    return {"status": "session reset"}

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    user_input = request.json.get("message")
    
    # Add user message to history
    session['conversation'].append({"role": "user", "content": user_input})
    
    # Keep conversation history short to save memory
    if len(session['conversation']) > 10:
        session['conversation'] = [session['conversation'][0]] + session['conversation'][-9:]
    
    session.modified = True
    
    try:
        # Get response from API
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=session['conversation']
        )
        
        bot_response = response.choices[0].message.content.strip()
        
        # Add bot response to history
        session['conversation'].append({"role": "assistant", "content": bot_response})
        session.modified = True
        
        return {"response": render_markdown(bot_response)}
    except Exception as e:
        return {"response": f"Error: {str(e)}"}

@app.route("/get_chat_history", methods=["GET"])
def get_chat_history():
    if 'conversation' in session and len(session['conversation']) > 1:
        return {"history": session['conversation'][1:]}
    return {"history": []}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)
