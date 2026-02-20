import smtplib
from email.mime.text import MIMEText
import subprocess
import socket
import requests
import os
import os.path
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env'))
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

recipients = ["recipient@example.com"]
ipstorepath = "/home/netmon/mylib/currentip"

def send_email(subject, body, recipients, sender=EMAIL_SENDER, password=EMAIL_PASSWORD):
    hostname = socket.gethostname()
    body = body + "\n\nFrom: " + hostname
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = ', '.join(recipients)
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp_server:
       smtp_server.login(sender, password)
       smtp_server.sendmail(sender, recipients, msg.as_string())
    print("Message sent!")

def get_public_ip():
    response = requests.get('https://api.ipify.org').text
    return response

def updateipstore(ipaddr, ipstorepath):
    #Writes Current IP Address to the IP Store file
    currentip = open(ipstorepath, 'w')
    currentip.write(ipaddr)
    currentip.truncate()
    currentip.close()

def has_public_ip_changed(ipstorepath, recipients):
    ipaddr = get_public_ip()
    if os.path.isfile(ipstorepath): #test if IP Store file exists
        currentip = open(ipstorepath, 'r+') #Open IP Store file for reading
        if currentip.read() != ipaddr: #Check if IP Address received is the same what is stored in IP Store file. Code below will run if currentip does not equal IP address received from IPIFY
            currentip.close()
            updateipstore(ipaddr, ipstorepath)
            text = "Your new IP is: " + str(ipaddr)
            print(text)
            send_email("IP Address Change", text,  recipients)
            #sendnewip(ipaddr, toaddress, fromaddress, smtpserver) #Send email with new IP Address
    else: #Runs if IP Store file doesn't exist
        updateipstore(ipaddr, ipstorepath) #Used to create IP store file

has_public_ip_changed(ipstorepath, recipients)
