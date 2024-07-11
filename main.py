from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import requests
from requests.auth import HTTPBasicAuth
import json
import os
from dotenv import load_dotenv
from datetime import datetime
import base64

# Initializing the FastAPI Application
app = FastAPI()

load_dotenv()

# Safaricom Api credentials
consumer_key = os.getenv('CONSUMER_KEY')
consumer_secret = os.getenv('CONSUMER_SECRET')
base_url = os.getenv('BASE_URL')

# Function to get access token
def access_token():
    mpesa_auth_url = 'https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials'
    data = (requests.get(mpesa_auth_url, auth=HTTPBasicAuth(consumer_key, consumer_secret))).json()
    return data['access_token']

# Creating home route
@app.get('/')
def home():
    return "Welcome to the safaricom access token generator"

# Creating access token route
@app.get('/access_token')
def token():
    data = access_token()
    return data

# Registering urls
@app.get('/register_urls')
def register():
    mpesa_endpoint = "https://sandbox.safaricom.co.ke/mpesa/c2b/v1/registerurl"
    headers = {"Authorization": f"Bearer {access_token()}"}
    response_data = requests.post(
        mpesa_endpoint,
        json={
            "ShortCode": "600997",
            "ResponseType": "Completed",
            "ConfirmationURL": f"{base_url}/c2b/confirm",
            "ValidationURL": f"{base_url}/c2b/validation"
        },
        headers=headers
    )
    return response_data.json()

@app.post('/c2b/confirm')
async def confirm(request: Request):
    data = await request.json()
    with open('confirm.json', 'a') as file:
        json.dump(data, file)
        file.write('\n')
    return JSONResponse(content={"ResultCode": 0, "ResultDesc": "Accepted"}, status_code=200)

@app.post('/c2b/validation')
async def validation(request: Request):
    data = await request.json()
    with open('validation.json', 'a') as file:
        json.dump(data, file)
        file.write('\n')
    return JSONResponse(content={"ResultCode": 0, "ResultDesc": "Accepted"}, status_code=200)

# Simulating transaction
@app.get('/simulate')
def simulate():
    mpesa_endpoint = 'https://sandbox.safaricom.co.ke/mpesa/c2b/v1/simulate'
    headers = {"Authorization": f"Bearer {access_token()}"}
    request_body = {
        "ShortCode": 600998,
        "CommandID": "CustomerPayBillOnline",
        "Amount": 1,
        "Msisdn": 254708374149,
        "BillRefNumber": "Test",
    }
    simulate_response = requests.post(mpesa_endpoint, json=request_body, headers=headers)
    return simulate_response.json()

# Initiate Mpesa express request
#/pay?phone=&amount
@app.get('/pay')
def MpesaExpress(amount: str, phone: str):
    endpoint = 'https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest'
    headers = {"Authorization": f"Bearer {access_token()}"}
    Timestamp = datetime.now()
    times = Timestamp.strftime("%Y%m%d%H%M%S")
    password = "174379" + "bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919" + times
    password = base64.b64encode(password.encode('utf-8')).decode('utf-8')

    data = {
        "BusinessShortCode": "174379",
        "Password": password,
        "Timestamp": times,
        "TransactionType": "CustomerPayBillOnline",
        "PartyA": phone,
        "PartyB": "174379",
        "PhoneNumber": phone,
        "CallBackURL": base_url,    
        "AccountReference": "Test",    
        "TransactionDesc": "Test",
        "Amount": amount
    }

    res = requests.post(endpoint, json=data, headers=headers)
    return res.json()

# Consume M-PESA express callback
@app.post('/lmno-callback')
async def incoming(request: Request):
    data = await request.json()
    print(data)
    return "ok"

@app.post("/mpesa/callback")
async def mpesa_callback(request: Request):
    if not request.url.scheme == "https":
        return JSONResponse(status_code=400, content={"error": "HTTPS required"})

    try:
        payload = await request.json()
    except ValueError:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON"})

    # Print the received callback data
    print("Received M-Pesa Callback:")
    print(json.dumps(payload, indent=2))

# FastAPI doesn't require the if __name__ == '__main__' block for running the app
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)