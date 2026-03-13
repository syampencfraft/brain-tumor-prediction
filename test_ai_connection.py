import socket
import sys

def check_dns(hostname):
    print(f"Checking DNS for {hostname}...")
    try:
        addr = socket.gethostbyname(hostname)
        print(f"Successfully resolved {hostname} to {addr}")
        return True
    except socket.gaierror as e:
        print(f"DNS Resolution failed for {hostname}: {e}")
        return False

def check_connection(hostname, port=443):
    print(f"Checking connection to {hostname}:{port}...")
    try:
        socket.create_connection((hostname, port), timeout=10)
        print(f"Successfully connected to {hostname}:{port}")
        return True
    except Exception as e:
        print(f"Connection failed to {hostname}:{port}: {e}")
        return False

if __name__ == "__main__":
    target = "generativelanguage.googleapis.com"
    dns_ok = check_dns(target)
    conn_ok = check_connection(target)
    
    if not dns_ok or not conn_ok:
        print("\n--- Troubleshooting ---")
        print("1. Check if your internet connection is active.")
        print("2. If you're using a VPN or proxy, ensure it's configured correctly.")
        print("3. Try flushing your DNS cache: run `ipconfig /flushdns` in cmd.")
        print("4. Check if a firewall is blocking Python's access to the internet.")
        sys.exit(1)
    else:
        print("\nEverything looks fine from a network perspective.")
