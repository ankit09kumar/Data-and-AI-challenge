from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class JobDescription(db.Model):
    __tablename__ = 'job_descriptions'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    department = db.Column(db.String(80), nullable=False)
    description = db.Column(db.Text, nullable=False)
    requirements_raw = db.Column(db.Text, nullable=True)
    skills_required = db.Column(db.String(500), nullable=False) # Comma-separated list of skills (lowercase)
    experience_years_required = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship with applications
    applications = db.relationship('Application', back_populates='job', cascade="all, delete-orphan")

class Candidate(db.Model):
    __tablename__ = 'candidates'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=True)
    phone = db.Column(db.String(50), nullable=True)
    location = db.Column(db.String(120), nullable=True)
    experience_years = db.Column(db.Float, default=0.0)
    skills_extracted = db.Column(db.Text, nullable=True) # Comma-separated skills (lowercase)
    education_raw = db.Column(db.Text, nullable=True)
    resume_path = db.Column(db.String(256), nullable=False)
    parsed_text = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship with applications
    applications = db.relationship('Application', back_populates='candidate', cascade="all, delete-orphan")

class Application(db.Model):
    __tablename__ = 'applications'
    id = db.Column(db.Integer, primary_key=True)
    candidate_id = db.Column(db.Integer, db.ForeignKey('candidates.id'), nullable=False)
    job_id = db.Column(db.Integer, db.ForeignKey('job_descriptions.id'), nullable=False)
    match_score = db.Column(db.Float, default=0.0) # Combined score (0-100)
    skill_score = db.Column(db.Float, default=0.0) # Skill match score (0-100)
    experience_score = db.Column(db.Float, default=0.0) # Experience match score (0-100)
    semantic_score = db.Column(db.Float, default=0.0) # Cosine similarity score (0-100)
    match_details = db.Column(db.Text, nullable=True) # JSON string of match analysis (matched skills, missing skills, etc.)
    status = db.Column(db.String(50), default='Screened') # Screened, Shortlisted, Interviewing, Rejected, Hired
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    candidate = db.relationship('Candidate', back_populates='applications')
    job = db.relationship('JobDescription', back_populates='applications')
