import requests
r = requests.get("http://localhost:8000/api/forecast/TATASTEEL.NS")
print("Status:", r.status_code)
print("Text:", r.text)
