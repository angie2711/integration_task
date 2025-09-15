# paymob_checkout.py
import os
import time
import uuid
import requests
from dotenv import load_dotenv

load_dotenv("example.env")

# Env variables (set these in your .env)
PAYMOB_API_KEY = os.getenv("PAYMOB_API_KEY")          # for /api/auth/tokens
PAYMOB_SECRET_KEY = os.getenv("PAYMOB_SECRET_KEY")    # sk_test_... used for Intention API (Authorization: Token ...)
PAYMOB_PUBLIC_KEY = os.getenv("PAYMOB_PUBLIC_KEY")    # public key (for unifiedcheckout URL)
PAYMOB_INTEGRATION_ID = os.getenv("PAYMOB_INTEGRATION_ID")  # integration id (for payment_keys or intention)
PAYMOB_IFRAME_ID = os.getenv("PAYMOB_IFRAME_ID")      # iframe id (for old flow)
PAYMOB_NOTIFICATION_URL = os.getenv("PAYMOB_NOTIFICATION_URL")
PAYMOB_REDIR_URL = os.getenv("PAYMOB_REDIRECTION_URL")

AUTH_TOKENS_URL = "https://accept.paymob.com/api/auth/tokens"
ORDERS_URL = "https://accept.paymob.com/api/ecommerce/orders"
PAYMENT_KEYS_URL = "https://accept.paymob.com/api/acceptance/payment_keys"
INTENTION_URL = "https://accept.paymob.com/v1/intention/"

def auth_token():
    """Get auth token (used in older Paymob flow). Requires PAYMOB_API_KEY."""
    if not PAYMOB_API_KEY:
        raise RuntimeError("PAYMOB_API_KEY not set in environment")
    resp = requests.post(AUTH_TOKENS_URL, json={"api_key": PAYMOB_API_KEY})
    resp.raise_for_status()
    return resp.json().get("token")


def create_order(auth_token, amount_cents=10000, items=None):
    """Create an order (old ecommerce flow). Returns order_id."""
    headers = {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}
    payload = {
        "delivery_needed": False,
        "amount_cents": int(amount_cents),
        "currency": "EGP",
        "items": items or []
    }
    resp = requests.post(ORDERS_URL, json=payload, headers=headers)
    resp.raise_for_status()
    return resp.json().get("id")


def create_intention_demo():

    if not PAYMOB_SECRET_KEY:
        raise RuntimeError("PAYMOB_SECRET_KEY not set in environment")

    url = INTENTION_URL
    headers = {
        "Authorization": f"Token {PAYMOB_SECRET_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "amount": 2000,
        "currency": "EGP",
        "payment_methods": [158],
        "items": [
            {
                "name": "Item name",
                "amount": 2000,
                "description": "Item description",
                "quantity": 1
            }
        ],
        "billing_data": {
            "apartment": "dumy",
            "first_name": "ala",
            "last_name": "zain",
            "street": "dumy",
            "building": "dumy",
            "phone_number": "+92345xxxxxxxx",
            "city": "dumy",
            "country": "dumy",
            "email": "ali@gmail.com",
            "floor": "dumy",
            "state": "dumy"
        },
        "extras": {"ee": 22},
        "special_reference": "phe4sjw11q-1xxxxxxxxx",
        "expiration": 3600,
        "notification_url": "https://webhook.site/dabe4968-5xxxxxxxxxxxxxxxxxxxxxx",
        "redirection_url": "https://www.google.com/"
    }

    try:
        resp = requests.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}


def get_payment_key(auth_token, order_id, amount_cents=10000, billing_data=None, integration_id=None):
    """Request a payment_key for iframe (old flow). Returns token string."""
    headers = {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}
    integration_id = integration_id or PAYMOB_INTEGRATION_ID
    if not integration_id:
        raise RuntimeError("integration_id not set (env PAYMOB_INTEGRATION_ID)")
    payload = {
        "auth_token": auth_token,
        "amount_cents": int(amount_cents),
        "expiration": 3600,
        "order_id": order_id,
        "billing_data": billing_data or {
            "apartment": "803",
            "email": "test@example.com",
            "floor": "42",
            "first_name": "Test",
            "last_name": "User",
            "street": "Test Street",
            "building": "803",
            "phone_number": "+201234567890",
            "shipping_method": "PKG",
            "postal_code": "01898",
            "city": "Cairo",
            "country": "EG",
            "state": "Cairo"
        },
        "currency": "EGP",
        "integration_id": int(integration_id)
    }
    resp = requests.post(PAYMENT_KEYS_URL, json=payload, headers=headers)
    resp.raise_for_status()
    return resp.json().get("token")


def create_intention(amount=10000, currency="EGP", payment_methods="5266025", items="iphone",
                     billing_data=None, notification_url=None, redirection_url=None,
                     merchant_order_id=None, extras=None, expiration=3600, special_reference=None):
    """
    Create a Payment Intention (new flow). Returns the full response JSON.
    Uses PAYMOB_SECRET_KEY in Authorization header (Token <secret>).
    """
    if not PAYMOB_SECRET_KEY:
        raise RuntimeError("PAYMOB_SECRET_KEY not set in environment")

    # prepare defaults
    merchant_order_id = merchant_order_id or f"morder-{int(time.time())}-{uuid.uuid4().hex[:6]}"
    payment_methods = payment_methods or ([int(PAYMOB_INTEGRATION_ID)] if PAYMOB_INTEGRATION_ID else [])
    payload = {
        "amount": int(amount),   # intention uses amount in base currency (check your PDF / docs) — PDF showed 2000 etc.
        "currency": currency,
        "merchant_order_id": merchant_order_id,
        "integration_id": int(PAYMOB_INTEGRATION_ID) if PAYMOB_INTEGRATION_ID else None,
        "payment_methods": payment_methods,
        "items": items or [],
        "billing_data": billing_data or {},
        "expiration": expiration
    }
    if extras:
        payload["extras"] = extras
    if special_reference:
        payload["special_reference"] = special_reference
    if notification_url or PAYMOB_NOTIFICATION_URL:
        payload["notification_url"] = notification_url or PAYMOB_NOTIFICATION_URL
    if redirection_url or PAYMOB_REDIR_URL:
        payload["redirection_url"] = redirection_url or PAYMOB_REDIR_URL

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Token {PAYMOB_SECRET_KEY}"
    }
    resp = requests.post(INTENTION_URL, json=payload, headers=headers)
    resp.raise_for_status()
    return resp.json()