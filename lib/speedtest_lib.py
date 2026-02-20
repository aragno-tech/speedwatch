import smtplib
from email.mime.text import MIMEText
import subprocess
import socket
import requests
import os.path

recipients = ["recipient@example.com"]
ipstorepath = "/home/netmon/mylib/currentip"

def writefile(str, filepath):
    #Writes str to file
    file = open(filepath, 'a')
    file.write(str)
    file.close()

def writelog(str):
    #Writes str to log
    writefile(str.rstrip() + "\n", "/home/netmon/log/speed.log")

