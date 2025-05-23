import os
from functools import wraps
from database.db import Database
from flask.views import MethodView
from flask import Flask, render_template, redirect, url_for, flash, session, request
from werkzeug.security import check_password_hash
from dotenv import load_dotenv


load_dotenv()
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY")


db = Database("localhost", "root", "", "voting_db")

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("logged_in"):
            flash("You must log in to access this page.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


@app.route("/")
def homepage():
    return render_template("index.html")  


@app.route("/vote")
def vote():
    return render_template("vote.html")


class LoginView(MethodView):
    def get(self):
        return render_template("admin.html")
    

    def post(self):
        username = request.form["username"]
        password = request.form["password"]

        result = db.read("admin", clause={"username": username}, columns=["password"])

        if result:
            stored_password = result[0][0]
            
            if check_password_hash(stored_password, password):
                session["logged_in"] = True
                return redirect(url_for("dashboard"))
            else:
                flash("Invalid username or password, please try again.", "danger")
                return redirect(url_for("login"))
        else:
            flash("Admin info not found", "danger")

        return render_template("admin.html")


@app.route("/admin/dashboard")
def dashboard():
    return render_template("dashboard.html")





# registers
app.add_url_rule("/admin/login", view_func=LoginView.as_view("login"))


if __name__ == "__main__":
    app.run(debug=True)