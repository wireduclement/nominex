import os
from datetime import datetime
from functools import wraps
from database.db import Database
from flask.views import MethodView
from flask import Flask, render_template, redirect, url_for, flash, session, request, send_from_directory
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from flask_bootstrap import Bootstrap5
from wtforms import StringField, SubmitField, SelectField
from wtforms.validators import DataRequired
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import random, string
from pdf import PDFGenerator
from collections import defaultdict


load_dotenv()
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY")
Bootstrap5(app)


db = Database("localhost", "root", "", "voting_db")

DEFAULT_PHOTO = "default.png"
UPLOAD_FOLDER = os.path.join("static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


class CandidateForm(FlaskForm):
    fullname = StringField("Full name", validators=[DataRequired()])
    class_name = StringField("Class", validators=[DataRequired()])
    gender = SelectField("Gender", choices=["Male", "Female"])
    photo = FileField("Photo", validators=[FileAllowed(['jpg', 'jpeg', 'png'], 'Images Files Only!')])
    position = SelectField("Aspiring Position", coerce=int, validators=[DataRequired()])
    submit = SubmitField("Submit")


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("logged_in"):
            flash("You must log in to access that page.", "info")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


def voter_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "voter_code" not in session:
            flash("Please enter your vote code to continue.", "info")
            return redirect(url_for("index"))
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


class VotersLoginView(MethodView):
    def get(self):
        return render_template("index.html") 
    

    def post(self):
        vote_code = request.form["vote_code"].strip().upper()

        result = db.read("voting_codes")
        matched = False
        for row in result:
            if vote_code in row:
                matched = True
                break

        if matched:
            session["voter_code"] = vote_code
            return redirect(url_for("vote"))
        else:
            flash("Invalid Code!", "danger")
            return redirect(url_for("index"))
    

# Voter's routes
class VoteView(MethodView):
    # decorators = [voter_required]

    def get(self):
        return render_template("vote.html")


# Admin routes
class AdminLoginView(MethodView):
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
        total_candidates = db.count_rows("candidates")
        total_positions = db.count_rows("positions")
        total_codes = db.count_rows("voting_codes")
        return render_template(
            "dashboard.html", 
            total_candidates=total_candidates, 
            total_positions=total_positions,
            total_codes=total_codes
        )
    

class CodeView(MethodView):
    decorators = [login_required]

    def get(self):
        page = int(request.args.get("page", 1))
        per_page = 25
        offset = (page - 1) * per_page

        generated_codes = db.read("voting_codes")
        total = len(generated_codes)
        paginated_codes = generated_codes[offset:offset + per_page]

        total_pages = (total + per_page - 1) // per_page

        return render_template("vote_codes.html", generated_codes=paginated_codes, total_pages=total_pages, current_page=page)
    
    def post(self):
        action = request.form.get("action")

        if action == "reset":
            codes = db.read("voting_codes")
            if not codes:
                flash("Cannot reset, no codes generated yet.", "info")
                return redirect(url_for("generate_codes"))
            
            db.delete_all("voting_codes")
            session["generated"] = False
            flash("All voting codes has been reset.", "info")
            return redirect(url_for("generate_codes"))
        
        elif action == "download":
            codes = db.read("voting_codes")
            if not codes:
                flash("No codes available for download.", "info")
                return redirect(url_for("generate_codes"))
            
            os.makedirs("static/codes", exist_ok=True)
            filepath = "static/codes/voting_codes.pdf"
            pdf = PDFGenerator()
            pdf.add_codes(codes)
            pdf.output(filepath)
            return send_from_directory("static/codes", "voting_codes.pdf", as_attachment=True)
        

        elif action == "generate":
            codes = db.read("voting_codes")
            if codes:
                flash("Codes already generated. Reset if you want to regenerate!", "info")
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
        
        flash("Invalid action", "danger")
        return redirect(url_for("generate_codes"))
    

class PositionsView(MethodView):
    decorators = [login_required]

    def get(self, edit_id=None):
        created_positions = db.read("positions")
        return render_template("positions.html", created_positions=created_positions, edit_id=edit_id)
    
    def post(self):
        action = request.form.get("action")

        if action == "create_position":
            position = request.form.get("positions")
            if position:
                db.insert("positions", ["name"], [position])
                flash("Position created successfully!", "success")
            return redirect(url_for("positions"))
        
        if action == "delete_position":
            position_id = request.form.get("position_id")
            if position_id:
                db.delete("positions", {"id": int(position_id)})
                flash("Position deleted successfully!", "success")
            else:
                flash("Invalid position ID", "danger")
            return redirect(url_for("positions"))
        
        if action == "edit_position":
            position_id = request.form.get("position_id")
            return self.get(edit_id=int(position_id))

        if action == "update_position":
            position_id = request.form.get("position_id")
            new_name = request.form.get("new_name")
            if position_id and new_name:
                db.update("positions", {"name": new_name}, {"id": int(position_id)})
                flash("Position updated successfully!", "success")
            return redirect(url_for("positions"))
        
        return redirect(url_for("positions"))


class AddCandidatesView(MethodView):
    decorators = [login_required]

    def get(self):
        form = CandidateForm()

        positions = db.read("positions")
        form.position.choices = [(p[0], p[1]) for p in positions]

        return render_template("add_candidates.html", form=form)
    
    def post(self):
        form = CandidateForm()

        positions = db.read("positions")
        form.position.choices = [(p[0], p[1]) for p in positions]

        if form.validate_on_submit():
            photo_file = form.photo.data
            if photo_file and photo_file.filename:
                filename = secure_filename(photo_file.filename)
                filepath = os.path.join(UPLOAD_FOLDER, filename)
                photo_file.save(filepath)
            else:
                filename = DEFAULT_PHOTO
        
            photo_path = os.path.join("uploads", filename)
                
            columns = ["full_name", "class_name", "gender", "photo_url", "position_id"]
            values = [
                form.fullname.data,
                form.class_name.data,
                form.gender.data,
                photo_path,
                form.position.data,
            ]
            db.insert("candidates", columns, values)

            flash("Candidate added successfully!", "success")
            return redirect(url_for("candidates"))
        
        return render_template("add_candidates.html", form=form)
        

class CandidateView(MethodView):
    decorators = [login_required]
    
    def get(self):
        candidates = db.read("candidates")
        positions = dict(db.read("positions"))

        joined_candidates = []
        for c in candidates:
            candidate_dict = {
                "id": c[0],
                "photo_url": c[4],
                "full_name": c[1],
                "gender": c[3],
                "class_name": c[2],
                "position": positions.get(c[5], "Unknown")
            }
            joined_candidates.append(candidate_dict)
        return render_template("candidates.html", candidates=joined_candidates)
    

class EditCandidateView(MethodView):
    decorators = [login_required]

    def get(self, candidate_id):
        form = CandidateForm()

        positions = db.read("positions")
        form.position.choices = [(p[0], p[1]) for p in positions]

        candidate = db.read("candidates", {"id": candidate_id})
        if candidate:
            form.fullname.data = candidate[0][1]
            form.class_name.data = candidate[0][2]
            form.gender.data = candidate[0][3]
            form.photo.data = candidate[0][4]
            form.position.data = candidate[0][5]
        else:
            flash("Candidate not found!", "danger")
            return redirect(url_for("candidates"))

        return render_template("edit_candidate.html", form=form, candidate_id=candidate_id)
    
    def post(self, candidate_id=None):
        form = CandidateForm()

        positions = db.read("positions")
        form.position.choices = [(p[0], p[1]) for p in positions]
        action = request.form.get("action")

        if action == "update_candidate" and candidate_id:
            if form.validate_on_submit():
                photo_file = form.photo.data
                if photo_file and photo_file.filename:
                    filename = secure_filename(photo_file.filename)
                    filepath = os.path.join(UPLOAD_FOLDER, filename)
                    photo_file.save(filepath)
                    photo_path = os.path.join("uploads", filename)
                else:
                    photo_path = db.read("candidates", {"id": candidate_id})[0][4]
            
                db.update(
                    "candidates", 
                    {
                        "full_name": form.fullname.data,
                        "class_name": form.class_name.data,
                        "gender": form.gender.data,
                        "photo_url": photo_path,
                        "position_id": int(form.position.data)
                    },
                    {"id": candidate_id}
                )
                flash("Candidate updated successfully!", "success")
                return redirect(url_for("candidates"))
            
        if action == "delete_candidate":
            candidate_id = request.form.get("candidate_id")
            if candidate_id:
                db.delete("candidates", {"id": int(candidate_id)})
                flash("Candidate deleted successfully!", "success")
            else:
                flash("Invalid candidate ID", "danger")
            return redirect(url_for("candidates"))
            
        flash("Form submission error.", "danger")
        return render_template("edit_candidate.html", form=form, candidate_id=candidate_id)
    

class ResultsView(MethodView):
    decorators = [login_required]

    def get(self):
        total_positions = db.count_rows("positions")
        total_candidates = db.count_rows("candidates")

        positions = db.read("positions") 
        candidates = db.read("candidates") 

        positions_dict = dict(positions)

        grouped_candidates = defaultdict(list)
        for c in candidates:
            candidate_id, full_name, class_name, gender, photo_url, position_id = c
            grouped_candidates[position_id].append({
                "id": candidate_id,
                "full_name": full_name,
                "class_name": class_name,
                "gender": gender,
                "photo_url": photo_url,
                "position_id": position_id,
                "position_name": positions_dict.get(position_id, "Unknown"),
                "percentage": random.randint(5, 95)
            })

        results_data = []
        for pos_id, candidates_list in grouped_candidates.items():
            results_data.append({
                "position": {
                    "id": pos_id,
                    "name": positions_dict.get(pos_id, "Unknown")
                },
                "candidates": candidates_list
            })

        return render_template(
            "results.html", 
            total_positions=total_positions,
            total_candidates=total_candidates,
            results_data=results_data
        )


@app.route("/logout")
@login_required
def logout():
    session.pop("logged_in", None)
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))



# registers
app.add_url_rule("/", view_func=VotersLoginView.as_view("index"))
app.add_url_rule("/vote", view_func=VoteView.as_view("vote"))
app.add_url_rule("/admin/login", view_func=AdminLoginView.as_view("login"))
app.add_url_rule("/admin/dashboard", view_func=DashboardView.as_view("dashboard"))
app.add_url_rule("/admin/generate-codes", view_func=CodeView.as_view("generate_codes"))
app.add_url_rule("/admin/positions", view_func=PositionsView.as_view("positions"))
app.add_url_rule("/admin/add-candidates", view_func=AddCandidatesView.as_view("add_candidates"))
app.add_url_rule("/admin/candidates", view_func=CandidateView.as_view("candidates"))
app.add_url_rule("/admin/edit-candidate/<int:candidate_id>", view_func=EditCandidateView.as_view("edit_candidate"))
app.add_url_rule("/admin/results", view_func=ResultsView.as_view("results"))


if __name__ == "__main__":
    app.run(debug=True)