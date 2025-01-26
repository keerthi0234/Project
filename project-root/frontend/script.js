// Predefined credentials for testing (change these to what you're using)
const validCredentials = {
    email: "user@example.com",  // Correct email
    password: "password123"     // Correct password
};

// Handle the form submission
document.getElementById('login-form').addEventListener('submit', function(e) {
    e.preventDefault();  // Prevent form from submitting normally
    
    // Get the values from the form inputs
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;

    // Log the values to ensure they are being captured correctly
    console.log("Entered email:", email);
    console.log("Entered password:", password);

    // Check if the credentials are correct
    if (email === validCredentials.email && password === validCredentials.password) {
        console.log("Login successful!");
        
        // Store login state in localStorage
        localStorage.setItem("loggedIn", "true");

        // Redirect to main page after successful login
        window.location.href = "http://127.0.0.1:5500/frontend/index.html";
    } else {
        console.log("Invalid credentials!");

        // Display error message if credentials are incorrect
        alert("Incorrect email or password. Please try again.");
    }
});
