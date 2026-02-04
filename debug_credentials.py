import requests
import json
import logging

# Configuration
SSO_BASE = "https://sso.sg.cropin.in/auth/realms/"
API_BASE = "https://cloud.cropin.in"
TENANT = "asp"
USERNAME = "2022280601"
PASSWORD = "123123123"

logging.basicConfig(level=logging.INFO)

def get_token():
    token_url = f"{SSO_BASE}{TENANT}/protocol/openid-connect/token"
    payload = {
        "grant_type": "password",
        "username": USERNAME,
        "password": PASSWORD,
        "client_id": "resource_server",
        "client_secret": "resource_server",
        "scope": "openid"
    }
    
    logging.info(f"Authenticating against {token_url}...")
    try:
        resp = requests.post(token_url, data=payload)
        resp.raise_for_status()
        token = resp.json().get('access_token')
        logging.info("Authentication Success.")
        return token
    except Exception as e:
        logging.error(f"Authentication Failed: {e}")
        if resp:
            logging.error(f"Response: {resp.text}")
        return None

def check_crops(token):
    url = f"{API_BASE}/services/farm/api/crops?size=1000"
    headers = {"Authorization": f"Bearer {token}"}
    
    logging.info(f"Fetching crops from {url}...")
    try:
        resp = requests.get(url, headers=headers)
        resp.raise_for_status()
        crops = resp.json()
        logging.info(f"Fetched {len(crops)} crops.")
        
        brinjal_variations = []
        all_names = []
        
        for crop in crops:
            name = crop.get('name') or ""
            all_names.append(name)
            if "brinjal" in name.lower():
                brinjal_variations.append(f"Found: '{name}' (ID: {crop.get('id')})")
        
        if brinjal_variations:
            print("\n✅ MATCHES FOUND for 'Brinjal':")
            for m in brinjal_variations:
                print(m)
        else:
            print("\n❌ NO MATCHES FOUND for 'Brinjal'.")
            print("First 10 crop names found:")
            print(all_names[:10])
            
    except Exception as e:
        logging.error(f"Failed to fetch crops: {e}")
        if resp:
            logging.error(f"Response: {resp.text}")

if __name__ == "__main__":
    token = get_token()
    if token:
        check_crops(token)
