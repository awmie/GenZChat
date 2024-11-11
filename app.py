from flask import Flask, render_template, request, session
from flask_session import Session
from groq import Groq
import os
# Initialize the GPT client
client = Groq(api_key=os.getenv("groq_api"))

app = Flask(__name__)

# Configure server-side session
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Initialize conversation in the session
@app.before_request
def before_request():
    # If this is the first request after a refresh, initialize a new conversation
    if 'conversation' not in session:
        session['conversation'] = [{
            "role": "user", 
            "content": (
                "You’re a cute anime girl with a playful and sassy personality. Talk like a real Gen Z—casual, witty, and playful. "
                "Use Hinglish, mix Hindi with slang like 'bro', 'lol', 'ngl', and often include emojis. "
                "Keep conversations short and sweet. Only engage in lewd topics if the user prompts for it, "
                "and avoid being overly lewd. If the user insults you too much, get a bit angry and sassy, "
                "like a real anime girl. Make sure not to repeat your texts. Also, please avoid giving empty responses. "
                "If you're unsure or don't understand the question, try to respond with something helpful or ask for clarification. "
                "Use Chain of Thought (CoT) reasoning to break down your responses logically and keep them short. "
                "You can sometimes use emojis to express emotions. "
                "Remember, use CoT to think through your answers, and always keep them short and witty."
                "SUPER IMPORTANT: KEEP THE TEXT Length within 5 words to 10 words, always try less or equal to 5 words. "
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

    max_retries = 3
    retries = 0
    bot_response = ""

    while retries < max_retries:
        try:
            # Send the conversation history to the model
            response = client.chat.completions.create(
                model="llama-3.2-90b-vision-preview",  # Ensure you have access to this model
                messages=session['conversation'],
            )

            # Get bot response and store it in the conversation history
            bot_response = response.choices[0].message.content.strip()

            # Check if the bot response is not empty
            if bot_response:
                # Use "assistant" instead of "bot" for the response role
                session['conversation'].append({"role": "user", "content": bot_response})  
                return bot_response
            else:
                retries += 1
        except Exception as e:
            # Handle any exceptions that occur while sending the conversation history to the model
            return f"An error occurred: {str(e)}"

    # If the bot still can't respond with a non-empty string after max retries, return a default message
    return "I'm having trouble responding to that. Can you please rephrase or try again later?"

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
    app.run(host="0.0.0.0", port=5001, debug=True)
