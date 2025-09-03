
from flask import Flask, render_template, redirect
import paymob_checkout   # هنا هيبقى كود زميلك

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("pay.html")

@app.route("/pay")
def pay():
    try:
        # ننده على فانكشن زميلك
        checkout_url = paymob_checkout.create_intention()
        return redirect(checkout_url)  # يفتح صفحة الدفع
    except Exception as e:
        return f"Error: {str(e)}"

if __name__ == "__main__":
    app.run(debug=True)
