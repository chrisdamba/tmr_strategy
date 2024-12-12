from flask import Flask

app = Flask(__name__)

@app.route("/")
def home():
    return "Welcome to the trading dashboard. Authenticate at https://localhost:5055 first."

# Add more routes for orders, portfolio, etc.
