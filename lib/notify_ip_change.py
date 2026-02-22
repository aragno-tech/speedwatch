import os
import requests

from speedwatch_lib import send_email, RECIPIENTS

IP_STORE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'var', 'currentip')


def get_public_ip():
    return requests.get('https://api.ipify.org').text


def update_ip_store(ip_addr, ip_store_path):
    with open(ip_store_path, 'w') as f:
        f.write(ip_addr)


def has_public_ip_changed(ip_store_path, recipients):
    ip_addr = get_public_ip()
    if os.path.isfile(ip_store_path):
        with open(ip_store_path, 'r') as f:
            if f.read() != ip_addr:
                update_ip_store(ip_addr, ip_store_path)
                text = "Your new IP is: " + str(ip_addr)
                print(text)
                send_email("IP Address Change", text, recipients)
    else:
        update_ip_store(ip_addr, ip_store_path)


if __name__ == "__main__":
    has_public_ip_changed(IP_STORE_PATH, RECIPIENTS)
