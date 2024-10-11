document.getElementById('message-form').addEventListener('submit', function(event) {
    event.preventDefault();
    const messageInput = document.getElementById('message');
    const message = messageInput.value;

    // Create a new message element and add it to the message container
    const messageContainer = document.querySelector('.message-container');
    const messageElement = document.createElement('div');
    messageElement.textContent = message;
    messageElement.classList.add('message');
    messageContainer.appendChild(messageElement);

    // Clear the input
    messageInput.value = '';

    // Scroll to the bottom
    messageContainer.scrollTop = messageContainer.scrollHeight;
});
