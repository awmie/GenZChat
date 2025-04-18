from flask import Flask, render_template, request, jsonify
from g4f.client import Client
import os
import json
import traceback
from utils.markdown_helper import render_markdown

app = Flask(__name__)

# Simple in-memory chat history (since filesystem sessions don't work well in serverless)
chat_history = {}

client = Client()

@app.route("/reset", methods=["POST"])
def reset_session():
    request_id = request.headers.get('X-Request-ID', 'default')
    if request_id in chat_history:
        del chat_history[request_id]
    return {"status": "session reset"}

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    try:
        user_input = request.json.get("message")
        request_id = request.headers.get('X-Request-ID', 'default')
        
        # Initialize conversation history if needed
        if request_id not in chat_history:
            chat_history[request_id] = [{
                "role": "system", 
                "content": "You're Nami from One Piece—playful, sassy, and Gen Z. Keep replies short, witty (5–10 words), and fun. Use emojis sometimes 🎯"
            }]
        
        # Add user message to history
        chat_history[request_id].append({"role": "user", "content": user_input})
        
        # Keep conversation history short to save memory
        if len(chat_history[request_id]) > 10:
            chat_history[request_id] = [chat_history[request_id][0]] + chat_history[request_id][-9:]
        
        # Get response from API
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=chat_history[request_id]
        )
        
        bot_response = response.choices[0].message.content.strip()
        
        # Add bot response to history
        chat_history[request_id].append({"role": "assistant", "content": bot_response})
        
        return {"response": render_markdown(bot_response)}
    except Exception as e:
        error_detail = traceback.format_exc()
        print(f"Error in chat endpoint: {str(e)}\n{error_detail}")
        return {"response": f"Sorry, I encountered an error. Please try again later."}, 500

@app.route("/get_chat_history", methods=["GET"])
def get_chat_history():
    request_id = request.headers.get('X-Request-ID', 'default')
    if request_id in chat_history and len(chat_history[request_id]) > 1:
        return {"history": chat_history[request_id][1:]}
    return {"history": []}

# Vercel requires a serverless function handler
def handler(event, context):
    return app(event, context)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5001)))
