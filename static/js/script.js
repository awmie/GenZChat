const form = document.getElementById('chat-form');
const chatBox = document.getElementById('chat-box');
const messageInput = document.getElementById('message');
const emojiBtn = document.getElementById('emoji-btn');
const emojiPicker = document.getElementById('emoji-picker');
const toggleButton = document.getElementById('dark-mode-toggle');
const body = document.body;

// Function to hide emoji picker
function hideEmojiPicker() {
    emojiPicker.style.display = 'none';
}

// Initialize the emoji picker using EmojiMart
document.addEventListener('DOMContentLoaded', () => {
    try {
        const pickerOptions = {
            onEmojiSelect: (emoji) => {
                messageInput.value += emoji.native; // Append the selected emoji to the input
            }
        };
        const picker = new EmojiMart.Picker(pickerOptions);
        emojiPicker.appendChild(picker); // Append emoji picker to the container

        // Toggle visibility of emoji picker when emoji button is clicked
        emojiBtn.addEventListener('click', (event) => {
            event.stopPropagation(); // Prevent immediate dismissal
            emojiPicker.style.display = emojiPicker.style.display === 'none' || emojiPicker.style.display === '' ? 'block' : 'none';
        });

        // Hide the emoji picker if clicking outside of it or on the message input field
        document.addEventListener('click', (event) => {
            if (!emojiPicker.contains(event.target) && event.target !== emojiBtn) {
                hideEmojiPicker();
            }
        });

        // Prevent click inside the emoji picker from hiding it
        emojiPicker.addEventListener('click', (event) => {
            event.stopPropagation();
        });

    } catch (error) {
        console.error('Error initializing emoji picker:', error);
    }
});

// Function to scroll to the bottom of the chat box
function scrollToBottom() {
    setTimeout(() => {
        chatBox.scrollTop = chatBox.scrollHeight;
    }, 100); // Adding a slight delay ensures the DOM has updated
}

// Add an event listener to the form to handle message submission
form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const userMessage = messageInput.value;
    messageInput.value = '';

    // Display user message in the chat box
    chatBox.innerHTML += `<div class="text-right mb-2"><span class="bg-blue-300 p-3 rounded-lg inline-block">${userMessage}</span></div>`;

    // Auto-scroll to the bottom after the user sends a message
    scrollToBottom();

    // Send the message to the server
    try {
        const response = await fetch('/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ message: userMessage }),
        });

        const data = await response.json();

        // Display the bot response
        chatBox.innerHTML += `<div class="text-left mb-2"><span class="bg-gray-200 p-3 rounded-lg inline-block">${data.response || "No response from bot."}</span></div>`;

        // Auto-scroll to the bottom after receiving the bot's response
        scrollToBottom();

    } catch (error) {
        console.error('Error sending message:', error);
        chatBox.innerHTML += `<div class="text-left mb-2"><span class="bg-red-200 p-3 rounded-lg inline-block">Error sending message!</span></div>`;

        // Auto-scroll to the bottom if an error occurs
        scrollToBottom();
    }
});

// Check for existing dark mode preference in local storage
if (localStorage.getItem('dark-mode') === 'enabled') {
    body.classList.add('dark-mode');
    toggleButton.textContent = 'Light Mode';  // Update button text
}

toggleButton.addEventListener('click', () => {
    body.classList.toggle('dark-mode');

    if (body.classList.contains('dark-mode')) {
        localStorage.setItem('dark-mode', 'enabled');
        toggleButton.textContent = 'Light Mode';  // Update button text
    } else {
        localStorage.setItem('dark-mode', 'disabled');
        toggleButton.textContent = 'Dark Mode';  // Update button text
    }
});
