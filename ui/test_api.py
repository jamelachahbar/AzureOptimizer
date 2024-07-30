import requests

# Define the API endpoint
url = 'http://127.0.0.1:5000/api/run'

# Define the payload
payload = {
    'mode': 'dry-run',
    'all_subscriptions': True,
    'use_adls': False
}

# Send the POST request
response = requests.post(url, json=payload)

# Print the response
print(response.json())
