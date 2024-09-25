from flask import Flask, render_template, request, session
from flask_session import Session
from g4f.client import Client
from g4f.Provider import HuggingChat

# Initialize the GPT client
client = Client(provider=HuggingChat)

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
            "content": "You are a chatbot that talks in Hindi but uses English characters. Don't reveal you are a bot. Keep your replies short sometimes 8-9 words if needed. Use shortcuts like u, ngl, fr, etc. Be casual and informal."
        }]

# Function to handle conversation
def chat_function(user_input):
    # Append user input to conversation history
    session['conversation'].append({"role": "user", "content": user_input})

    # Send the conversation history to the model
    response = client.chat.completions.create(
        model="meta-llama",
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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
