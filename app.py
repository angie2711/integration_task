# app.py
import os
from flask import Flask, render_template, redirect, jsonify, request
from dotenv import load_dotenv
import paymob_checkout

load_dotenv()

app = Flask(__name__)

# Home (renders templates/pay.html)
@app.route("/")
def home():
    return render_template("pay.html")


# Old flow: auth -> order -> payment_key -> iframe
@app.route("/pay")
def pay():
    try:
        auth_token = paymob_checkout.auth_token()
        order_id = paymob_checkout.create_order(auth_token, amount_cents=10000)
        payment_key = paymob_checkout.get_payment_key(auth_token, order_id, amount_cents=10000)

        iframe_id = os.getenv("PAYMOB_IFRAME_ID") or paymob_checkout.PAYMOB_IFRAME_ID
        if not iframe_id:
            return "Missing IFRAME ID configuration", 500

        iframe_url = f"https://accept.paymob.com/api/acceptance/iframes/{iframe_id}?payment_token={payment_key}"
        return redirect(iframe_url)
    except Exception as e:
        return f"Error during pay flow: {str(e)}", 500


# New Intention API route (POST)
@app.route("/create-intention", methods=["POST"])
def create_intention_route():
    try:
        data = request.get_json() or {}
        amount = data.get("amount", 10000)
        payment_methods = data.get("payment_methods")  # a list of ints (e.g., [158])
        items = data.get("items")
        billing_data = data.get("billing_data")
        notification_url = data.get("notification_url")
        redirection_url = data.get("redirection_url")
        merchant_order_id = data.get("merchant_order_id")

        resp = paymob_checkout.create_intention(
            amount=amount,
            payment_methods=payment_methods,
            items=items,
            billing_data=billing_data,
            notification_url=notification_url,
            redirection_url=redirection_url,
            merchant_order_id=merchant_order_id
        )

        # if client_secret exists, build unifiedcheckout URL
        client_secret = resp.get("client_secret")
        public_key = os.getenv("PAYMOB_PUBLIC_KEY")
        if client_secret and public_key:
            unified = f"https://accept.paymob.com/unifiedcheckout/?publicKey={public_key}&clientSecret={client_secret}"
            return jsonify({"checkout_url": unified, "intention_response": resp})
        return jsonify(resp)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/demo-intention", methods=["GET"])
def demo_intention():
    try:
        resp = paymob_checkout.create_intention_demo()
        return jsonify(resp)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Redirect/callback after payment (customer-facing)
@app.route("/payment_callback", methods=["GET", "POST"])
def payment_callback():
    # Paymob may redirect with params — here we simply show a confirmation placeholder
    return "Payment processed (customer redirect). Check server webhook for final status."


# Webhook: Paymob will POST here (server-to-server)
@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        payload = request.get_data()
        data = request.get_json(silent=True)

        # Simple signature check (adjust header name & method according to Paymob docs)
        signature = request.headers.get("X-Signature") or request.headers.get("X-Callback-Signature")
        secret = os.getenv("PAYMOB_SECRET_KEY")
        if signature and secret:
            import hmac, hashlib, base64
            computed = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
            # NOTE: Paymob may send signature in different formats; check docs and adapt.
            if not hmac.compare_digest(computed, signature):
                # allow base64(hex) variations if necessary (example)
                try:
                    b64 = base64.b64encode(bytes.fromhex(computed)).decode()
                    if not hmac.compare_digest(b64, signature):
                        return jsonify({"error": "invalid signature"}), 401
                except Exception:
                    return jsonify({"error": "invalid signature"}), 401

        # Process notification (store in DB, update order status, etc.)
        print("Webhook payload:", data)
        return jsonify({"received": True}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400


if __name__ == "__main__":
    app.run(debug=True)