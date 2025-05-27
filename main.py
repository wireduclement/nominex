import os
from datetime import datetime, timezone
from functools import wraps
from database.db import Database
from flask.views import MethodView
from flask import Flask, render_template, redirect, url_for, flash, session, request
from werkzeug.security import check_password_hash
from dotenv import load_dotenv
import random, string


load_dotenv()
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY")


db = Database("localhost", "root", "", "voting_db")


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("logged_in"):
            flash("You must log in to access that page.", "info")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


def generate_codes(length=10):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))


def vote_quantity(count):
    codes = []
    for _ in range(count):
        code = generate_codes()
        codes.append(code)
    return codes


class HomeView(MethodView):
    def get(self):
        return render_template("index.html") 
    

class VoteView(MethodView):
    def get(self):
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


class DashboardView(MethodView):
    decorators = [login_required] 

    def get(self):
        return render_template("dashboard.html")
    

class CodeView(MethodView):
    decorators = [login_required]

    def get(self):
        generated_codes = db.read("voting_codes")
        return render_template("vote_codes.html", generated_codes=generated_codes)
    
    def post(self):
        action = request.form.get("action")

        if action == "reset":
            db.delete_all("voting_codes")
            session["generated"] = False
            flash("All voting codes has been reset.", "info")
            return redirect(url_for("generate_codes"))
        
        if session.get("generated"):
            flash("Codes already generated. Please reset first.", "info")
            return redirect(url_for("generate_codes"))
        
        quantity = request.form.get("voting_codes", type=int)
        if not quantity or quantity <= 0:
            flash("Please enter a valid number", "info")
            return redirect(url_for("generate_codes"))
        
        codes = vote_quantity(quantity)
        for code in codes:
            timestamp = datetime.now()
            db.insert("voting_codes", ["code", "has_voted", "created_at"], [code, "No", timestamp])
        
        session["generated"] = True
        flash(f"{quantity} code(s) generated successfully!", "success")
        return redirect(url_for("generate_codes"))
    

class PositionsView(MethodView):
    decorators = [login_required]

    def get(self):
        return render_template("positions.html")
    

class CandidatesView(MethodView):
    decorators = [login_required]

    def get(self):
        return render_template("candidates.html")
    

class ResultsView(MethodView):

    decorators = [login_required]
    def get(self):
        return render_template("results.html")


@app.route("/logout")
@login_required
def logout():
    session.pop("logged_in", None)
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))



# registers
app.add_url_rule("/", view_func=HomeView.as_view("index"))
app.add_url_rule("/vote", view_func=VoteView.as_view("vote"))
app.add_url_rule("/admin/login", view_func=LoginView.as_view("login"))
app.add_url_rule("/admin/dashboard", view_func=DashboardView.as_view("dashboard"))
app.add_url_rule("/admin/generate-codes", view_func=CodeView.as_view("generate_codes"))
app.add_url_rule("/admin/positions", view_func=PositionsView.as_view("positions"))
app.add_url_rule("/admin/candidates", view_func=CandidatesView.as_view("candidates"))
app.add_url_rule("/admin/results", view_func=ResultsView.as_view("results"))


if __name__ == "__main__":
    app.run(debug=True)