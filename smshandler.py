from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
# from flask_ngrok import run_with_ngrok

app = Flask(__name__)
# run_with_ngrok(app)  # Exposes the app using ngrok

@app.route("/sms", methods=['POST'])
def sms_reply():
    """Handles incoming SMS from Twilio and responds with a generic message."""
    incoming_msg = request.form.get('Body', '')
    sender = request.form.get('From', '')

    print(f"Received message: {incoming_msg} from {sender}")

    # Respond with a generic message
    response = MessagingResponse()
    response.message("Thanks for reaching out and using Salus AI! Please interact with Salus at this URL:  https://salus-ai.lovable.app/ .")
    
    print (str(response))

    return str(response)

if __name__ == "__main__":
    app.run()
