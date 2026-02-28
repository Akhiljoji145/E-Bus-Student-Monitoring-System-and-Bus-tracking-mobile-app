import requests
import json

def send_push_notification(tokens, title, message, data=None):
    """
    Send push notifications to multiple Expo push tokens.
    """
    url = "https://exp.host/--/api/v2/push/send"
    headers = {
        "host": "exp.host",
        "accept": "application/json",
        "accept-encoding": "gzip, deflate",
        "content-type": "application/json"
    }
    
    # Ensure tokens is a list
    if isinstance(tokens, str):
        tokens = [tokens]
    
    # Filter out empty tokens
    valid_tokens = [t for t in tokens if t]
    
    if not valid_tokens:
        return False

    payload = []
    for token in valid_tokens:
        payload.append({
            "to": token,
            "title": title,
            "body": message,
            "data": data or {},
            "sound": "default"
        })

    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"Error sending push notification: {e}")
        return False
