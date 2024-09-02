import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Configure email settings
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587
EMAIL_USERNAME = 'projecttestfunny@gmail.com'
EMAIL_PASSWORD = 'oxge rqwe tdpn utaf' # App Password
EMAIL_RECEIVER = 'projecttestfunny@gmail.com' # To send it to the same address

@app.route('/', methods=['GET', 'POST'])
def user_report():
    
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        subject = request.form['subject']
        message = request.form['message']
        
        # Create the email
        msg = MIMEMultipart()
        msg['From'] = EMAIL_USERNAME
        msg['To'] = EMAIL_RECEIVER
        msg['Subject'] = f"Report from {name}: {subject}"
        
        # Add the message body
        body = f"Name: {name}\nEmail: {email}\n\nMessage:\n{message}"
        msg.attach(MIMEText(body, 'plain'))
        
        # Send the email
        try:
            server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
            server.starttls()
            server.login(EMAIL_USERNAME, EMAIL_PASSWORD)
            server.sendmail(EMAIL_USERNAME, EMAIL_RECEIVER, msg.as_string())
            server.quit()
            
            flash("Your report has been sent successfully.", "success")
        except Exception as e:
            flash(f"Failed to send the report: {str(e)}", "error")
    
    return render_template('user_report.html')

if __name__ == '__main__':
    app.run(debug=True)
