# app/routes.py
from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

from .models import User, Project, Issue, Comment, Activity
from . import db

main = Blueprint("main", __name__)


@main.route("/")
def home():
    return render_template("home.html")


@main.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        confirm = request.form.get("confirm")

        if not username or not email or not password or not confirm:
            flash("All fields are required.", "error")
            return redirect(url_for("main.register"))

        if password != confirm:
            flash("Passwords do not match.", "error")
            return redirect(url_for("main.register"))

        existing = User.query.filter((User.username == username) | (User.email == email)).first()
        if existing:
            flash("Username or email already exists.", "error")
            return redirect(url_for("main.register"))

        hashed = generate_password_hash(password)
        user = User(username=username, email=email, password_hash=hashed)
        db.session.add(user)
        db.session.commit()

        flash("Account created successfully. You can login now.", "success")
        return redirect(url_for("main.login"))

    return render_template("register.html")


@main.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        user = User.query.filter_by(email=email).first()
        if not user or not check_password_hash(user.password_hash, password):
            flash("Invalid email or password.", "error")
            return redirect(url_for("main.login"))

        login_user(user)
        flash("Logged in successfully.", "success")
        return redirect(url_for("main.dashboard"))

    return render_template("login.html")


@main.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out successfully.", "success")
    return redirect(url_for("main.login"))


@main.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html", user=current_user)


@main.route("/projects")
@login_required
def projects_list():
    projects = Project.query.order_by(Project.created_at.desc()).all()
    return render_template("projects/list.html", projects=projects)


@main.route("/projects/new", methods=["GET", "POST"])
@login_required
def project_create():
    if request.method == "POST":
        name = request.form.get("name")
        description = request.form.get("description")

        if not name:
            flash("Project name is required.", "error")
            return redirect(url_for("main.project_create"))

        existing = Project.query.filter_by(name=name).first()
        if existing:
            flash("Project with this name already exists.", "error")
            return redirect(url_for("main.project_create"))

        project = Project(name=name, description=description, owner=current_user)
        db.session.add(project)
        db.session.commit()

        flash("Project created successfully.", "success")
        return redirect(url_for("main.projects_list"))

    return render_template("projects/new.html")


@main.route("/projects/<int:project_id>/issues")
@login_required
def project_issues(project_id):
    project = Project.query.get_or_404(project_id)

    status = request.args.get("status",type=str)
    priority = request.args.get("priority",type=str)
    assignee = request.args.get("assignee",type=str)
    q = request.args.get("q",type=str)
    page = request.args.get("page", 1, type=int)
    per_page = 20

    query=Issue.query.filter(Issue.project_id==project.id)

    if status:
        query=query.filter(Issue.status==status)
    if priority:
        query=query.filter(Issue.priority==priority)
    if assignee:
        if assignee=="unassigned":
            query=query.filter(Issue.assignee_id.is_(None))
        else:
            try:
                query=query.filter(Issue.assignee_id==int(assignee))
            except ValueError:
                query=query.filter(False)
    if q:
        query=query.filter(Issue.title.ilike(f"%{q}%")) 

    query=query.order_by(Issue.created_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    issues = pagination.items

    statuses = ["Open", "In Progress", "Resolved", "Closed"]
    priorities = ["Low", "Medium", "High", "Critical"]

    users = User.query.order_by(User.username).all()

    return render_template(
        "issues/list.html",
        project=project,
        issues=issues,
        pagination=pagination,
        statuses=statuses,
        priorities=priorities,
        users=users,
        current_filters={"status": status, "priority": priority, "assignee": assignee, "q": q},
    )


@main.route("/projects/<int:project_id>/issues/new", methods=["GET", "POST"])
@login_required
def issue_create(project_id):
    project = Project.query.get_or_404(project_id)

    if request.method == "POST":
        title = request.form.get("title")
        description = request.form.get("description")
        priority = request.form.get("priority") or "Medium"
        due_date_raw = request.form.get("due_date")

        if not title:
            flash("Title is required.", "error")
            return redirect(url_for("main.issue_create", project_id=project_id))

        issue = Issue(
            title=title,
            description=description,
            priority=priority,
            project_id=project.id,
            reporter_id=current_user.id,
        )

        if due_date_raw:
            try:
                issue.due_date = datetime.strptime(due_date_raw, "%Y-%m-%d")
            except ValueError:
                flash("Invalid due date format. Use YYYY-MM-DD.", "error")
                return redirect(url_for("main.issue_create", project_id=project_id))

        db.session.add(issue)
        db.session.flush()

        activity=Activity(issue_id=issue.id,user_id=current_user.id,action="Created",detail=f"Issue '{issue.title}' created.")
        db.session.add(activity)
        db.session.commit()

        flash("Issue created", "success")
        return redirect(url_for("main.project_issues", project_id=project_id))

    return render_template("issues/new.html", project=project)


@main.route("/issues/<int:issue_id>", methods=["GET", "POST"])
@login_required
def issue_detail(issue_id):
    issue = Issue.query.get_or_404(issue_id)

    if request.method == "POST":
        content = request.form.get("content")
        if not content:
            flash("Content cannot be empty.", "error")
            return redirect(url_for("main.issue_detail", issue_id=issue_id))

        comment = Comment(issue_id=issue_id, user_id=current_user.id, content=content)
        db.session.add(comment)

        snippet=(comment.content[:50]+"...") if len(comment.content or "")>50 else comment.content or ""
        activity=Activity(issue_id=issue.id,user_id=current_user.id,action="Commented",detail=snippet)
        db.session.add(activity)

        db.session.commit()

        flash("Comment added", "success")
        return redirect(url_for("main.issue_detail", issue_id=issue_id))

    return render_template("issues/detail.html", issue=issue)


@main.route("/issues/<int:issue_id>/edit", methods=["GET", "POST"])
@login_required
def issue_edit(issue_id):
    issue=Issue.query.get_or_404(issue_id)
    project=issue.project

    allowed=( current_user.id == issue.reporter_id or current_user.id == project.owner_id or (issue.assignee_id is not None and current_user.id==issue).assignee_id)

    if not allowed:
        flash("You are not authorized to edit this issue.","error")
        return redirect(url_for("main.issue_detail",issue_id=issue_id))
    
    if request.method == "POST":
        old_title = issue.title
        old_description = issue.description or ""
        old_priority = issue.priority
        old_status = issue.status
        old_assignee_id = issue.assignee_id
        old_due_date = issue.due_date

  
        old_assignee_name = None
        if old_assignee_id:
            old_assignee = User.query.get(old_assignee_id)
            old_assignee_name = old_assignee.username if old_assignee else f"id:{old_assignee_id}"

        title = request.form.get("title")
        description = request.form.get("description") or ""
        priority = request.form.get("priority") or "Medium"
        status = request.form.get("status") or issue.status
        assignee_id_raw = request.form.get("assignee_id")
        due_date_raw = request.form.get("due_date")

        if not title:
            flash("Title is required.", "error")
            return redirect(url_for("main.issue_edit", issue_id=issue.id))

        new_assignee_id = None
        new_assignee_name = None
        if assignee_id_raw:
            try:
                new_assignee_id = int(assignee_id_raw)
                new_assignee = User.query.get(new_assignee_id)
                new_assignee_name = new_assignee.username if new_assignee else f"id:{new_assignee_id}"
            except ValueError:
                flash("Invalid assignee ID.", "error")
                return redirect(url_for("main.issue_edit", issue_id=issue.id))

        # parse due date
        new_due_date = None
        if due_date_raw:
            try:
                new_due_date = datetime.strptime(due_date_raw, "%Y-%m-%d")
            except ValueError:
                flash("Invalid due date format. Use YYYY-MM-DD.", "error")
                return redirect(url_for("main.issue_edit", issue_id=issue.id))

        issue.title = title
        issue.description = description
        issue.priority = priority
        issue.status = status
        issue.assignee_id = new_assignee_id
        issue.due_date = new_due_date

        changes = []
        if old_title != issue.title:
            changes.append(f"title: '{old_title}' -> '{issue.title}'")
        if old_description != issue.description:
            changes.append("description: (changed)")
        if old_priority != issue.priority:
            changes.append(f"priority: {old_priority} -> {issue.priority}")
        # compare datetimes carefully (None handling)
        if (old_due_date and new_due_date and str(old_due_date) != str(new_due_date)) or (bool(old_due_date) != bool(new_due_date)):
            changes.append(f"due_date: {old_due_date or 'None'} -> {new_due_date or 'None'}")
        if old_status != issue.status:
            changes.append(f"status: {old_status} -> {issue.status}")
        # assignee name change
        if old_assignee_id != new_assignee_id:
            changes.append(f"assignee: {old_assignee_name or 'Unassigned'} -> {new_assignee_name or 'Unassigned'}")

        db.session.add(issue)

        detail_text = "; ".join(changes) if changes else "No changes made."
        activity = Activity(
            issue_id=issue.id,
            user_id=current_user.id,
            action="Updated",
            detail=detail_text
        )
        db.session.add(activity)
        db.session.commit()

        flash("Issue updated.", "success")
        return redirect(url_for("main.issue_detail", issue_id=issue.id))

    
    #if method is GET
    users=User.query.order_by(User.username).all()
    statuses=["Open","In Progress","Resolved","Closed"]
    priorities=["Low","Medium","High","Critical"]

    return render_template(
                           "issues/edit.html",
                           issue=issue,
                           users=users,
                           statuses=statuses,
                           priorities=priorities
                        )


