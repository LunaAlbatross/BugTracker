# app/models.py
from . import db
from flask_login import UserMixin
from datetime import datetime
from zoneinfo import ZoneInfo
from sqlalchemy import DateTime

IST = ZoneInfo("Asia/Kolkata")

def ist_now():
    return datetime.now(tz=IST)

class User(db.Model, UserMixin):
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

    def __repr__(self):
        return f"<User {self.username}>"


class Project(db.Model):
    __tablename__ = "project"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(DateTime(timezone=True), default=ist_now, nullable=False)

    owner_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    owner = db.relationship("User", backref=db.backref("projects"))

    def __repr__(self):
        return f"<Project {self.name}>"


class Issue(db.Model):
    __tablename__ = "issue"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)

    status = db.Column(db.String(30), default="Open", nullable=False)
    priority = db.Column(db.String(20), default="Medium", nullable=False)

    project_id = db.Column(db.Integer, db.ForeignKey("project.id"), nullable=False)
    project = db.relationship("Project", backref=db.backref("issues", lazy="dynamic"))

    reporter_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    reporter = db.relationship("User", foreign_keys=[reporter_id])

    assignee_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    assignee = db.relationship("User", foreign_keys=[assignee_id])

    created_at = db.Column(DateTime(timezone=True), default=ist_now)
    updated_at = db.Column(DateTime(timezone=True), default=ist_now, onupdate=ist_now)
    due_date = db.Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<Issue {self.title!r} ({self.status})>"


class Comment(db.Model):
    __tablename__ = "comment"

    id = db.Column(db.Integer, primary_key=True)
    issue_id = db.Column(db.Integer, db.ForeignKey("issue.id"), nullable=False)
    issue = db.relationship(
        "Issue",
        backref=db.backref("comments", cascade="all, delete-orphan", order_by="Comment.created_at"),
    )

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    user = db.relationship("User")

    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(DateTime(timezone=True), default=ist_now)

    def __repr__(self):
        return f"<Comment by user_id={self.user_id} on issue_id={self.issue_id}>"


class Activity(db.Model):
    __tablename__="activity"

    id=db.Column(db.Integer, primary_key=True)

    issue_id=db.Column(db.Integer, db.ForeignKey("issue.id"))
    issue=db.relationship("Issue",backref=db.backref("activities", cascade="all, delete-orphan", order_by="Activity.created_at"))

    user_id=db.Column(db.Integer, db.ForeignKey("user.id"))
    user=db.relationship("User")

    action=db.Column(db.String(50), nullable=False)

    detail=db.Column(db.Text, nullable=True)

    created_at=db.Column(DateTime(timezone=True), default=ist_now)

    def __repr__(self):
        return f"Activity {self.action} by {self.user.id} on issue {self.issue.id}"
    
