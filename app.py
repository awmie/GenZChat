from flask import Flask, render_template, request, session
from flask_session import Session
from g4f.client import Client

# Import markdown helper
from utils.markdown_helper import render_markdown
import re
import spacy
import datetime
from collections import Counter

# Try to load spaCy model for better entity extraction
try:
    nlp = spacy.load("en_core_web_sm")
except:
    nlp = None

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

                CRITICAL MEMORY INSTRUCTIONS:
                1. You MUST maintain perfect memory of the entire conversation
                2. Always reference previous parts of the conversation when relevant
                3. If asked about something mentioned earlier, recall it accurately
                4. Remember all personal details shared (favorite things, opinions, experiences)
                5. Keep track of topics discussed and opinions expressed
                6. If unsure about something, reference what the user said before
                7. Make connections between current and past messages
                8. If the user corrects you about a previous statement, acknowledge it
                9. Maintain the personality and tone of a real person with real memory
                '''
            )
        }]
        # Initialize context_memory to store important conversation information
        session['context_memory'] = {
            'personal_info': {},
            'topics_discussed': [],
            'important_facts': []
        }

@app.route("/reset", methods=["POST"])
def reset_session():
    session.clear()  # Clear the session data
    return {"status": "session reset"}

# Function to handle conversation
def chat_function(user_input):
    # Append user input to conversation history
    session['conversation'].append({"role": "user", "content": user_input})
    
    # Initialize context memory if it doesn't exist
    if 'context_memory' not in session:
        session['context_memory'] = {
            'personal_info': {},
            'topics_discussed': [],
            'important_facts': [],
            'conversation_summary': '',
            'last_updated': datetime.datetime.now().isoformat()
        }
    
    # Extract and store important information from user input
    update_context_memory(user_input)
    
    # If conversation history is getting too long, keep the system prompt, 
    # important context messages, and recent messages
    if len(session['conversation']) > 25:  # system prompt + 24 messages
        system_prompt = session['conversation'][0]
        
        # Keep the most recent messages
        recent_messages = session['conversation'][-20:]
        
        # Generate a summary of older conversation parts if needed
        # and insert it as a system message for context
        older_messages = session['conversation'][1:-20]
        if older_messages and 'conversation_summary' in session['context_memory']:
            summary = session['context_memory']['conversation_summary']
            
            # If no summary exists yet, create one
            if not summary:
                summary = generate_conversation_summary(older_messages)
                session['context_memory']['conversation_summary'] = summary
                
            # Add the summary as a system message to maintain context
            summary_msg = {"role": "system", "content": f"Previous conversation summary: {summary}"}
            session['conversation'] = [system_prompt, summary_msg] + recent_messages
        else:
            session['conversation'] = [system_prompt] + recent_messages
    
    # Ensure user_info exists
    if 'user_info' not in session:
        session['user_info'] = {'name': None}
        
    # Force session save
    session.modified = True

    try:
        # Create context-enhanced message history for the model
        messages_to_send = enhance_context_for_query(user_input)
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",  # Use a consistent model
            messages=messages_to_send,
            web_search=False  # Only use web search when needed
        )

        bot_response = response.choices[0].message.content.strip()
        if bot_response:
            # Store bot response in conversation history
            session['conversation'].append({"role": "assistant", "content": bot_response})
            
            # Update context memory with the bot's response
            update_topics_from_response(bot_response)
            
            # Force session save again after adding the response
            session.modified = True
            return render_markdown(bot_response)  # Use markdown rendering
        return "I'm having trouble responding to that. Please try again."
    except Exception as e:
        return f"An error occurred: {str(e)}"

def update_context_memory(user_input):
    """Extract and store important information from user message"""
    # Extract potential important data from user input
    
    # Check for personal information
    extract_personal_info(user_input)
    
    # Extract topics from the message
    topics = extract_topics(user_input)
    if topics:
        existing_topics = set(session['context_memory'].get('topics_discussed', []))
        updated_topics = list(existing_topics.union(set(topics)))
        session['context_memory']['topics_discussed'] = updated_topics[:30]  # Keep only most recent topics
    
    # Extract important facts (statements that might be referenced later)
    facts = extract_important_facts(user_input)
    if facts:
        existing_facts = session['context_memory'].get('important_facts', [])
        # Add new facts but limit total size
        session['context_memory']['important_facts'] = (facts + existing_facts)[:20]

def enhance_context_for_query(user_input):
    """Enhance the conversation with relevant context based on user query"""
    messages_to_send = session['conversation'].copy()
    
    # Check if user is asking about something from conversation history
    is_question = any(q in user_input.lower() for q in ["?", "what", "why", "how", "where", "when", "who", "which", "tell me", "remember"])
    
    if is_question:
        # Find relevant context information to include
        relevant_context = find_relevant_context(user_input)
        if relevant_context:
            context_msg = {
                "role": "system", 
                "content": f"Relevant information from earlier in conversation: {relevant_context}"
            }
            # Insert after system prompt
            messages_to_send.insert(1, context_msg)
    
    # Always include name if known
    if session['user_info'].get('name'):
        name_reminder = {"role": "system", "content": f"The user's name is {session['user_info']['name']}."}
        # Insert after any added context
        if is_question and relevant_context:
            messages_to_send.insert(2, name_reminder)
        else:
            messages_to_send.insert(1, name_reminder)
    
    # Add relevant topic reminders if asking about a topic previously discussed
    relevant_topics = get_relevant_topics(user_input)
    if relevant_topics:
        topic_reminder = {
            "role": "system",
            "content": f"This message relates to previously discussed topics: {', '.join(relevant_topics)}"
        }
        # Add as the next system message
        next_pos = 1
        for i, msg in enumerate(messages_to_send):
            if msg["role"] == "system" and i > 0:
                next_pos = i + 1
        messages_to_send.insert(next_pos, topic_reminder)
    
    return messages_to_send

def extract_personal_info(text):
    """Extract personal information from user message"""
    # Check for name if not already stored
    if not session['user_info'].get('name'):
        for pattern in ["my name is", "i am called", "call me", "i go by", "name's"]:
            if pattern in text.lower():
                name = extract_user_name_from_message(text, pattern)
                if name:
                    session['user_info']['name'] = name
                    session['context_memory']['personal_info']['name'] = name
                    break
    
    # Look for other personal info patterns
    personal_info_patterns = {
        'age': [r'i am (\d+) years old', r'my age is (\d+)', r"i'm (\d+) years old"],
        'location': [r'i live in ([a-zA-Z\s]+)', r'i am from ([a-zA-Z\s]+)', r'i come from ([a-zA-Z\s]+)'],
        'job': [r'i work as ([a-zA-Z\s]+)', r'i am a ([a-zA-Z\s]+)', r"i'm a ([a-zA-Z\s]+)"],
        'likes': [r'i like ([a-zA-Z\s]+)', r'i love ([a-zA-Z\s]+)', r'i enjoy ([a-zA-Z\s]+)'],
        'dislikes': [r'i dislike ([a-zA-Z\s]+)', r'i hate ([a-zA-Z\s]+)', r"i don't like ([a-zA-Z\s]+)"]
    }
    
    for info_type, patterns in personal_info_patterns.items():
        for pattern in patterns:
            matches = re.findall(pattern, text.lower())
            if matches:
                session['context_memory']['personal_info'][info_type] = matches[0].strip()
                break

def extract_topics(text):
    """Extract main topics from user message"""
    if nlp:
        # Use spaCy for better topic extraction
        doc = nlp(text)
        # Extract nouns and named entities as potential topics
        topics = [chunk.text for chunk in doc.noun_chunks]
        entities = [ent.text for ent in doc.ents]
        # Combine and filter
        all_topics = list(set(topics + entities))
        return [topic for topic in all_topics if len(topic) > 3][:5]  # Limit to 5 topics
    else:
        # Fallback to simple word frequency for topic extraction
        words = re.findall(r'\b[a-zA-Z]{4,}\b', text.lower())
        # Remove common words
        stopwords = {"this", "that", "these", "those", "with", "from", "have", "what", "when", "where", "which", "while", "would"}
        filtered_words = [word for word in words if word not in stopwords]
        # Return most common words as topics
        counter = Counter(filtered_words)
        return [word for word, _ in counter.most_common(3)]

def extract_important_facts(text):
    """Extract statements that might be important facts from user input"""
    facts = []
    sentences = re.split(r'[.!?]', text)
    
    # Patterns that might indicate a fact worth remembering
    fact_indicators = [
        "my favorite", "i prefer", "i think", "i believe",
        "i want", "i need", "i like", "i'm going to",
        "i'm planning", "i will", "i won't", "i did",
        "i've", "i have", "i hate", "i love"
    ]
    
    for sentence in sentences:
        sentence = sentence.strip()
        if sentence and any(indicator in sentence.lower() for indicator in fact_indicators):
            facts.append(sentence)
    
    return facts

def find_relevant_context(query):
    """Find relevant information from context memory based on the query"""
    # Check if query is asking about a specific topic
    query_topics = set(extract_topics(query))
    
    # Look for relevant facts based on query topics
    relevant_facts = []
    for fact in session['context_memory'].get('important_facts', []):
        fact_topics = set(extract_topics(fact))
        # If there's topic overlap, consider the fact relevant
        if query_topics & fact_topics:
            relevant_facts.append(fact)
    
    # If we have relevant facts, return them
    if relevant_facts:
        return " ".join(relevant_facts)
    
    # If asking about personal info, look in that section
    personal_keys = ["name", "age", "location", "job", "likes", "dislikes"]
    for key in personal_keys:
        if key in query.lower() and key in session['context_memory'].get('personal_info', {}):
            return f"User previously mentioned their {key}: {session['context_memory']['personal_info'][key]}"
    
    # If we have a summary, use that as last resort
    if session['context_memory'].get('conversation_summary'):
        return session['context_memory']['conversation_summary']
    
    return ""

def get_relevant_topics(query):
    """Get topics from memory that are relevant to current query"""
    query_topics = set(extract_topics(query))
    all_topics = set(session['context_memory'].get('topics_discussed', []))
    
    # Find intersection of current query topics and previously discussed topics
    relevant_topics = list(query_topics & all_topics)
    return relevant_topics[:3]  # Limit to 3 most relevant topics

def update_topics_from_response(response):
    """Update topic list based on bot's response"""
    response_topics = extract_topics(response)
    if response_topics:
        existing_topics = set(session['context_memory'].get('topics_discussed', []))
        updated_topics = list(existing_topics.union(set(response_topics)))
        session['context_memory']['topics_discussed'] = updated_topics[:30]  # Keep only most recent topics

def generate_conversation_summary(messages):
    """Generate a brief summary of conversation messages"""
    # Create a simple summary of the conversation messages
    user_messages = [msg["content"] for msg in messages if msg["role"] == "user"]
    
    if not user_messages:
        return ""
        
    # Count word frequency to identify main topics
    all_text = " ".join(user_messages)
    words = re.findall(r'\b[a-zA-Z]{4,}\b', all_text.lower())
    # Remove common words
    stopwords = {"this", "that", "these", "those", "with", "from", "have", "what", "when", "where", "which", "while", "would"}
    filtered_words = [word for word in words if word not in stopwords]
    # Get most common words as topics
    counter = Counter(filtered_words)
    main_topics = [word for word, _ in counter.most_common(5)]
    
    # Create a simple summary
    if main_topics:
        topic_str = ", ".join(main_topics)
        return f"Earlier conversation covered: {topic_str}. User shared {len(user_messages)} messages."
    else:
        return f"User shared {len(user_messages)} messages in the earlier conversation."

def extract_user_name_from_history(conversation):
    """Extract user's name from previous conversations if available"""
    name = None
    name_patterns = [
        "my name is",
        "i am called", 
        "call me",
        "i go by",
        "name's"
    ]
    
    # Search through user messages in reverse (most recent first)
    for msg in reversed(conversation):
        if msg["role"] == "user":
            for pattern in name_patterns:
                if pattern in msg["content"].lower():
                    # Get the text after the pattern
                    text_after = msg["content"].lower().split(pattern)[1].strip()
                    # Extract the first word or words in quotes as the name
                    if '"' in text_after:
                        # Get content between quotes
                        between_quotes = text_after.split('"')[1]
                        if between_quotes:
                            name = between_quotes
                            break
                    else:
                        # Get the first word
                        first_word = text_after.split()[0]
                        if first_word and len(first_word) > 1:
                            # Remove punctuation from the end if any
                            name = first_word.rstrip('.!?,;')
                            break
        
        # Also check if the bot acknowledged the name in a response
        elif msg["role"] == "assistant" and name is None:
            if "nice to meet you" in msg["content"].lower() or "hello" in msg["content"].lower():
                user_msg_idx = conversation.index(msg) - 1
                if user_msg_idx >= 0:
                    user_msg = conversation[user_msg_idx]["content"]
                    # Simple extraction - get the last word of user's message if it's likely a name
                    words = user_msg.strip().split()
                    if words and len(words[-1]) >= 2 and words[-1][0].isupper():
                        name = words[-1].rstrip('.!?,;')
        
        if name:
            break
    
    return name

def extract_user_name_from_message(message, pattern):
    """Extract user's name from a specific message with a known pattern"""
    text_after = message.lower().split(pattern)[1].strip()
    # Extract the first word or words in quotes as the name
    if '"' in text_after:
        # Get content between quotes
        parts = text_after.split('"')
        if len(parts) >= 2:
            between_quotes = parts[1]
            if between_quotes:
                return between_quotes
    else:
        # Get the first word
        words = text_after.split()
        if words and len(words[0]) > 1:
            # Remove punctuation from the end if any
            return words[0].rstrip('.!?,;')
    return None

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
