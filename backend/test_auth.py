
import os
import requests
from dotenv import load_dotenv

load_dotenv()

supabase_url = os.getenv("SUPABASE_URL")
anon_key = os.getenv("SUPABASE_ANON_KEY")

email = input("Test user email: ")
password = input("Test user password: ")

response = requests.post(
    f"{supabase_url.rstrip('/')}/auth/v1/token?grant_type=password",
    headers={
        "apikey": anon_key,
        "Content-Type": "application/json",
    },
    json={
        "email": email,
        "password": password,
    },
    timeout=20,
)

if response.status_code == 200:
    data = response.json()
    print("Login successful!")
    print("Access token:")
    print(data["access_token"])
else:
    print("Login failed:", response.status_code, response.text)
