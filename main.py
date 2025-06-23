import os
import random, string
from datetime import datetime
from functools import wraps
from database.db import Database
from flask.views import MethodView
from flask import Flask, render_template, redirect, url_for, flash, session, request, send_from_directory
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from flask_bootstrap import Bootstrap5
from wtforms import StringField, SubmitField, SelectField, PasswordField
from wtforms.validators import DataRequired, Length
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
from pdf import PDFGenerator, ResultPDFGenerator
from collections import defaultdict
from pymysql.err import IntegrityError


load_dotenv()
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY")
Bootstrap5(app)


db = Database("localhost", "root", "", "voting_db")

DEFAULT_PHOTO = "default.jpg"
UPLOAD_FOLDER = os.path.join("static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


class CandidateForm(FlaskForm):
    fullname = StringField("Full name", validators=[DataRequired()])
    class_name = StringField("Class", validators=[DataRequired()])
    gender = SelectField("Gender", choices=["Male", "Female"])
    photo = FileField("Photo", validators=[FileAllowed(['jpg', 'jpeg', 'png'], 'Images Files Only!')])
    position = SelectField("Aspiring Position", coerce=int, validators=[DataRequired()])
    submit = SubmitField("Submit")

class ChangePasswordForm(FlaskForm):
    current_pwd = PasswordField("Current Password", validators=[DataRequired(), Length(min=7)])
    new_pwd = PasswordField("New Password", validators=[DataRequired(), Length(min=7, message="Password must be at least 7 characters long")])
    c_new_pwd = PasswordField("Confirm New Password", validators=[DataRequired(), Length(min=7, message="Password must match")])
    submit = SubmitField("Update")


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


# Voter's routes
class VotersLoginView(MethodView):
    def get(self):
        return render_template("index.html")
    

    def post(self):
        vote_code = request.form["vote_code"].strip().upper()

        result = db.read("voting_codes", {"code": vote_code})
        if result:
            if result[0][2] == "Yes":
                flash("This code has already been used", "danger")
                return redirect(url_for("index"))
            session["voter_code"] = vote_code
            return redirect(url_for("vote"))
        else:
            flash("Invalid Vote Code!", "danger")
            return redirect(url_for("index"))
    

class VoteView(MethodView):
    decorators = [voter_required]

    def get(self):
        positions = db.read("positions")
        candidates = db.read("candidates")

        grouped = defaultdict(list)

        for c in candidates:
            candidate_dict = {
                "id": c[0],
                "name": c[1],
                "position_id": c[5],
                "photo_url": c[4]
            }
            grouped[candidate_dict["position_id"]].append(candidate_dict)

        results_data = []
        for p in positions:
            results_data.append({
                "position": {
                    "id": p[0],
                    "name": p[1]
                },
                "candidates": grouped.get(p[0], [])
            })

        return render_template("vote.html", results_data=results_data)
    

    def post(self):
        voter_code = session.get("voter_code")

        voting_code = db.read("voting_codes", clause={"code": voter_code})     
        voting_code_id = voting_code[0][0]
       
        positions = db.read("positions")
        votes_to_insert = []

        for position in positions:
            position_id = position[0]
            form_field = f"vote_{position_id}"
            candidate_id = request.form.get(form_field)

            if not candidate_id:
                continue

            candidates = db.read("candidates", clause={"id": candidate_id, "position_id": position_id})
            if not candidates:
                flash("Invalid candidate selection.", "danger")
                return redirect(url_for("vote"))

            columns = ["voting_code_id", "candidate_id", "position_id", "timestamp"]
            values = [
                voting_code_id,
                candidate_id,
                position_id,
                datetime.now()
            ]
            votes_to_insert.append(values)

        try:
            for vote in votes_to_insert:
                db.insert("votes", columns, vote)

                candidate_id = vote[1]
                current_vote = db.read("candidates", clause={"id": candidate_id})
                new_total = current_vote[0][-1] + 1
                db.update("candidates", {"total_votes": new_total}, {"id": candidate_id})

            session.pop("voter_code", None)
            session["voted"] = True
            db.update("voting_codes", {"has_voted": "Yes"}, {"code": voter_code})
            return redirect(url_for("thank_you"))
        except Exception as e:
            flash("An error occurred while submitting your votes. Please try again.", "danger")
            return redirect(url_for("vote"))
    

class ThankYouView(MethodView):

    def get(self):
        if not session.get("voted"):
            flash("Access denied. Please vote first.", "danger")
            return redirect(url_for("index"))

        session.pop("voted", None)
        return render_template("thank_you.html")



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

        result = db.read("voting_codes")
        used_codes = 0
        for row in result:
            if row[2] == "Yes":
                used_codes += 1

        if total_codes > 0:
            vote_percent = round((used_codes / total_codes) * 100)
        else:
            vote_percent = 0

        active_session = db.read("election_sessions", clause={"active": 1})
        is_active = bool(active_session)

        return render_template(
            "dashboard.html", 
            total_candidates=total_candidates, 
            total_positions=total_positions,
            total_codes=total_codes,
            used_codes=used_codes,
            vote_percent=vote_percent,
            is_active=is_active
        )
    
    def post(self):
        action = request.form.get("action")
        if action == "reset":
            db.delete_all("votes")
            db.delete_all("candidates")
            db.delete_all("positions")
            db.delete_all("voting_codes")
            db.delete_all("final_results")
            db.update("election_sessions", {"active": 0}, {"active": 1})

            flash("System has been fully reset.", "success")
            return redirect(url_for("dashboard"))
        
        if action == "close":
            session = db.read("election_sessions", clause={"active": 1})
            if not session:
                flash("No active election session.", "danger")
                return redirect(url_for("dashboard"))

            session_id = session[0][0]
            positions = db.read("positions")
            candidates = db.read("candidates")

            grouped = defaultdict(list)

            for c in candidates:
                candidate_id = c[0]
                position_id = c[5]
                total_votes = c[6]
                grouped[position_id].append((candidate_id, total_votes))

            for position_id, candidate_list in grouped.items():
                sorted_candidates = sorted(candidate_list, key=lambda x: x[1], reverse=True)

                for rank, (candidate_id, votes) in enumerate(sorted_candidates, start=1):
                    columns = ["session_id", "candidate_id", "position_id", "total_votes", "rank"]
                    values = [session_id, candidate_id, position_id, votes, rank]
                    db.insert("final_results", columns, values)

            db.update("election_sessions", {"active": 0}, {"id": session_id})
            flash("Election closed and results saved.", "success")
            return redirect(url_for("final_results"))
    

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
            try:
                codes = db.read("voting_codes")
                if not codes:
                    flash("Cannot reset, no codes generated yet.", "info")
                    return redirect(url_for("generate_codes"))

                db.delete_all("voting_codes")
                session["generated"] = False
                flash("All voting codes have been reset.", "info")
                db.update("election_sessions", {"active": 0}, {"active": 1})
                return redirect(url_for("generate_codes"))

            except IntegrityError as e:
                if e.args[0] == 1451:
                    flash("Reset blocked. They are already used to vote.", "danger")
                else:
                    flash("An unexpected database error occurred.", "danger")
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

            current_year = datetime.now().year
            session_name = f"{current_year} elections"
            db.update("election_sessions", {"active": 0}, {"active": 1})

            existing_session = db.read("election_sessions", clause={"name": session_name})
            if existing_session:
                session_id = existing_session[0][0]
                db.update("election_sessions", {"active": 1}, {"id": session_id})
            else:
                db.insert("election_sessions", ["name", "active"], [session_name, 1])

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
            try:
                candidate_id = request.form.get("candidate_id")
                if candidate_id:
                    db.delete("candidates", {"id": int(candidate_id)})
                    flash("Candidate deleted successfully!", "success")
                else:
                    flash("Invalid candidate ID", "danger")
            except IntegrityError as e:
                if e.args[0] == 1451:
                    flash("Deletion blocked. They already have votes recorded.", "danger")
                else:
                    flash("An unexpected database error occurred.", "danger")
            
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

        votes_per_position = defaultdict(int)
        for c in candidates:
            position_id = c[5]
            total_votes = c[6]
            votes_per_position[position_id] += total_votes

        for c in candidates:
            candidate_id, full_name, class_name, gender, photo_url, position_id, total_votes = c

            position_total = votes_per_position[position_id] or 1
            percentage = round((total_votes / position_total) * 100)

            grouped_candidates[position_id].append({
                "id": candidate_id,
                "full_name": full_name,
                "class_name": class_name,
                "gender": gender,
                "photo_url": photo_url,
                "position_id": position_id,
                "total_votes": total_votes,
                "position_name": positions_dict.get(position_id, "Unknown"),
                "percentage": percentage
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
    

class FinalResultsView(MethodView):
    def _get_final_results(self):
        session = db.read("election_sessions", clause={"active": 0})
        if not session:
            return None, []

        latest_session = sorted(session, key=lambda x: x[0], reverse=True)[0]
        session_id = latest_session[0]
        results = db.read("final_results", clause={"session_id": session_id})
        positions = db.read("positions")
        candidates = db.read("candidates")

        position_map = {p[0]: p[1] for p in positions}
        candidate_map = {c[0]: c for c in candidates}

        final_results = []
        for r in results:
            _, _, candidate_id, position_id, votes, rank, _ = r
            # if rank not in (1, 2):
            #     continue
            candidate = candidate_map.get(candidate_id)
            if not candidate:
                continue
            final_results.append((
                candidate[1],
                candidate[2],
                candidate[3],
                candidate[4],
                position_map.get(position_id, "Unknown"),
                votes,
                rank
            ))

        return session_id, final_results

    def get(self):
        session_id, results = self._get_final_results()
        if session_id is None:
            flash("Cannot view final results until elections are closed!.", "info")
            return redirect(url_for("dashboard"))

        grouped = defaultdict(list)
        for r in results:
            full_name, class_name, gender, photo, position_name, votes, rank = r
            grouped[position_name].append({
                "full_name": full_name,
                "class_name": class_name,
                "photo": photo,
                "votes": votes,
                "rank": rank,
                "position_name": position_name
            })

        for position in grouped:
            grouped[position].sort(key=lambda x: x["rank"])

        return render_template("final_results.html", grouped_results=grouped)

    def post(self):
        action = request.form.get("action")
        if action == "download_results":
            _, results = self._get_final_results()

            os.makedirs("static/results", exist_ok=True)
            top_two = [r for r in results if r[6] in (1, 2)]
            filepath = "static/results/election_winners.pdf"
            pdf = ResultPDFGenerator(top_two)
            pdf.generate(filepath)
            return send_from_directory("static/results", "election_winners.pdf", as_attachment=True)

        
class ChangePasswordView(MethodView):
    decorators = [login_required]

    def get(self):
        form = ChangePasswordForm()
        return render_template("update_password.html", form=form)


    def post(self):
        form = ChangePasswordForm()
        name = session.get("name", "admin")

        if form.validate_on_submit():
            current_pwd = form.current_pwd.data
            new_pwd = form.new_pwd.data
            c_new_pwd = form.c_new_pwd.data


            if new_pwd != c_new_pwd:
                flash("New passwords do not match.", "danger")
                return render_template("update_password.html", form=form)

            user = db.read("admin", {"username": name}, columns=["password"])
            if not user:
                flash("Admin not found.", "danger")
                return render_template("update_password.html", form=form)

            stored_password = user[0][0]

            if not check_password_hash(stored_password, current_pwd):
                flash("Incorrect current password.", "danger")
                return render_template("update_password.html", form=form)

            hashed_password = generate_password_hash(new_pwd, method='pbkdf2:sha256', salt_length=16)
            db.update("admin", {"password": hashed_password}, {"username": name})

            flash("Password updated successfully.", "success")

        return render_template("update_password.html", form=form)


@app.route("/logout")
@login_required
def logout():
    session.pop("logged_in", None)
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))



# registers
app.add_url_rule("/", view_func=VotersLoginView.as_view("index"))
app.add_url_rule("/vote", view_func=VoteView.as_view("vote"))
app.add_url_rule("/thank-you", view_func=ThankYouView.as_view("thank_you"))
app.add_url_rule("/admin/login", view_func=AdminLoginView.as_view("login"))
app.add_url_rule("/admin/dashboard", view_func=DashboardView.as_view("dashboard"))
app.add_url_rule("/admin/generate-codes", view_func=CodeView.as_view("generate_codes"))
app.add_url_rule("/admin/positions", view_func=PositionsView.as_view("positions"))
app.add_url_rule("/admin/add-candidates", view_func=AddCandidatesView.as_view("add_candidates"))
app.add_url_rule("/admin/candidates", view_func=CandidateView.as_view("candidates"))
app.add_url_rule("/admin/edit-candidate/<int:candidate_id>", view_func=EditCandidateView.as_view("edit_candidate"))
app.add_url_rule("/admin/results", view_func=ResultsView.as_view("results"))
app.add_url_rule("/admin/final-results", view_func=FinalResultsView.as_view("final_results"))
app.add_url_rule("/change-password", view_func=ChangePasswordView.as_view("change_password"))


if __name__ == "__main__":
    app.run(debug=True)