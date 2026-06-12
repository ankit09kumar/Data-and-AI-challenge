from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
import json
from functools import wraps

# Import database models
from models import db, User, JobDescription, Candidate, Application
# Import NLP parsing tools
from nlp_utils import (
    extract_text_from_pdf,
    extract_text_from_docx,
    extract_contact_info,
    extract_skills,
    extract_experience_years,
    match_candidate_to_job
)

app = Flask(__name__)
app.secret_key = 'super_secret_candidate_discovery_key_129837'

# Database Configuration (SQLite)
db_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'candidate_discovery.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# File Upload Configuration
UPLOAD_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB limit
ALLOWED_EXTENSIONS = {'pdf', 'docx'}

# Initialize Database
db.init_app(app)

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Helper function to check file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Create DB Tables on Startup
with app.app_context():
    db.create_all()

# Authentication Decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# --- Authentication Routes ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['username'] = user.username
            flash('Welcome back, Recruiter!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password.', 'danger')
            
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
        if existing_user:
            flash('Username or Email already registered.', 'danger')
            return redirect(url_for('register'))
            
        hashed_password = generate_password_hash(password, method='scrypt')
        new_user = User(username=username, email=email, password_hash=hashed_password)
        
        try:
            db.session.add(new_user)
            db.session.commit()
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error occurred: {e}', 'danger')
            
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    flash('Logged out successfully.', 'info')
    return redirect(url_for('login'))

# --- Dashboard & Analytics Routes ---

@app.route('/')
@login_required
def dashboard():
    total_candidates = Candidate.query.count()
    total_jobs = JobDescription.query.count()
    total_applications = Application.query.count()
    
    # Calculate average match score
    apps = Application.query.all()
    avg_score = round(sum(app.match_score for app in apps) / len(apps), 1) if apps else 0.0
    
    # Get recent applications
    recent_applications = Application.query.order_by(Application.created_at.desc()).limit(5).all()
    
    return render_template(
        'dashboard.html',
        total_candidates=total_candidates,
        total_jobs=total_jobs,
        total_applications=total_applications,
        avg_score=avg_score,
        recent_applications=recent_applications
    )

@app.route('/api/analytics')
@login_required
def analytics_api():
    # 1. Score Distribution
    apps = Application.query.all()
    distributions = {"0-20": 0, "20-40": 0, "40-60": 0, "60-80": 0, "80-100": 0}
    for app in apps:
        score = app.match_score
        if score < 20: distributions["0-20"] += 1
        elif score < 40: distributions["20-40"] += 1
        elif score < 60: distributions["40-60"] += 1
        elif score < 80: distributions["60-80"] += 1
        else: distributions["80-100"] += 1

    # 2. Top Extracted Skills
    candidates = Candidate.query.all()
    skill_counts = {}
    for cand in candidates:
        if cand.skills_extracted:
            skills = [s.strip() for s in cand.skills_extracted.split(',') if s.strip()]
            for skill in skills:
                skill_counts[skill] = skill_counts.get(skill, 0) + 1
    
    # Sort skills and get top 8
    top_skills = sorted(skill_counts.items(), key=lambda x: x[1], reverse=True)[:8]
    top_skills_labels = [item[0] for item in top_skills]
    top_skills_values = [item[1] for item in top_skills]

    # 3. Application status breakdown
    status_counts = {}
    for app in apps:
        status_counts[app.status] = status_counts.get(app.status, 0) + 1

    return jsonify({
        'distributions_labels': list(distributions.keys()),
        'distributions_values': list(distributions.values()),
        'top_skills_labels': top_skills_labels,
        'top_skills_values': top_skills_values,
        'status_labels': list(status_counts.keys()),
        'status_values': list(status_counts.values())
    })

# --- Job Management Routes ---

@app.route('/jobs')
@login_required
def list_jobs():
    jobs = JobDescription.query.order_by(JobDescription.created_at.desc()).all()
    return render_template('jobs.html', jobs=jobs)

@app.route('/jobs/add', methods=['GET', 'POST'])
@login_required
def add_job():
    if request.method == 'POST':
        title = request.form.get('title')
        department = request.form.get('department')
        description = request.form.get('description')
        requirements_raw = request.form.get('requirements_raw')
        skills_required = request.form.get('skills_required') # Comma-separated
        experience_years_required = request.form.get('experience_years_required')
        
        # Clean skills required (lowercase and trim whitespace)
        cleaned_skills = ",".join([s.strip().lower() for s in skills_required.split(',') if s.strip()])
        
        try:
            exp_val = int(experience_years_required or 0)
        except ValueError:
            exp_val = 0
            
        new_job = JobDescription(
            title=title,
            department=department,
            description=description,
            requirements_raw=requirements_raw,
            skills_required=cleaned_skills,
            experience_years_required=exp_val
        )
        
        try:
            db.session.add(new_job)
            db.session.commit()
            flash(f"Job Listing '{title}' added successfully!", 'success')
            return redirect(url_for('list_jobs'))
        except Exception as e:
            db.session.rollback()
            flash(f"Error adding job: {e}", 'danger')
            
    return render_template('add_job.html')

@app.route('/jobs/delete/<int:job_id>', methods=['POST'])
@login_required
def delete_job(job_id):
    job = JobDescription.query.get_or_4_0_4(job_id)
    try:
        db.session.delete(job)
        db.session.commit()
        flash('Job description deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting job: {e}', 'danger')
    return redirect(url_for('list_jobs'))

# --- Resume Upload & NLP Processing ---

@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload_resumes():
    jobs = JobDescription.query.all()
    if not jobs:
        flash('Please create a Job Description first before uploading resumes.', 'warning')
        return redirect(url_for('add_job'))
        
    if request.method == 'POST':
        job_id = request.form.get('job_id')
        uploaded_files = request.files.getlist('resumes')
        
        if not job_id:
            flash('Please select a target Job Description.', 'danger')
            return redirect(url_for('upload_resumes'))
            
        job = JobDescription.query.get(job_id)
        if not job:
            flash('Target Job Description not found.', 'danger')
            return redirect(url_for('upload_resumes'))
            
        success_count = 0
        error_count = 0
        
        for file in uploaded_files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                # Ensure unique filename to prevent collisions
                unique_filename = f"{os.urandom(8).hex()}_{filename}"
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                file.save(file_path)
                
                # Extract text based on file format
                text = ""
                if unique_filename.lower().endswith('.pdf'):
                    text = extract_text_from_pdf(file_path)
                elif unique_filename.lower().endswith('.docx'):
                    text = extract_text_from_docx(file_path)
                    
                if not text.strip():
                    error_count += 1
                    continue
                    
                # Extract Candidate Details using NLP utils
                name, email, phone = extract_contact_info(text)
                # If name heuristic failed, use the original file name
                if name == "Unknown Candidate":
                    name = filename.rsplit('.', 1)[0].replace('_', ' ').replace('-', ' ').title()
                    
                skills = extract_skills(text)
                experience = extract_experience_years(text)
                
                # Check if Candidate already exists by Email
                candidate = None
                if email:
                    candidate = Candidate.query.filter_by(email=email).first()
                    
                if not candidate:
                    candidate = Candidate(
                        name=name,
                        email=email,
                        phone=phone,
                        experience_years=experience,
                        skills_extracted=",".join(skills),
                        parsed_text=text,
                        resume_path=unique_filename
                    )
                    db.session.add(candidate)
                    db.session.flush() # Secure Candidate ID before linking
                else:
                    # Update existing candidate details
                    candidate.name = name
                    candidate.phone = phone
                    candidate.experience_years = max(candidate.experience_years, experience)
                    
                    # Merge skills
                    existing_skills = [s.strip().lower() for s in (candidate.skills_extracted or "").split(',') if s.strip()]
                    merged_skills = list(set(existing_skills).union(set(skills)))
                    candidate.skills_extracted = ",".join(merged_skills)
                    candidate.parsed_text = text
                    candidate.resume_path = unique_filename
                
                # Match candidate against the targeted Job Description
                match_score, skill_score, experience_score, semantic_score, match_details = match_candidate_to_job(candidate, job)
                
                # Create or update application entry
                application = Application.query.filter_by(candidate_id=candidate.id, job_id=job.id).first()
                if not application:
                    application = Application(
                        candidate_id=candidate.id,
                        job_id=job.id,
                        match_score=match_score,
                        skill_score=skill_score,
                        experience_score=experience_score,
                        semantic_score=semantic_score,
                        match_details=match_details,
                        status='Screened'
                    )
                    db.session.add(application)
                else:
                    # Overwrite scores with latest parsing
                    application.match_score = match_score
                    application.skill_score = skill_score
                    application.experience_score = experience_score
                    application.semantic_score = semantic_score
                    application.match_details = match_details
                    
                success_count += 1
            else:
                error_count += 1
                
        try:
            db.session.commit()
            if success_count > 0:
                flash(f"Successfully processed {success_count} resume(s).", 'success')
            if error_count > 0:
                flash(f"Failed to process {error_count} file(s). Ensure they are valid PDF or DOCX formats.", 'warning')
            return redirect(url_for('list_candidates', job_id=job.id))
        except Exception as e:
            db.session.rollback()
            flash(f"Database error saving profiles: {e}", 'danger')
            
    return render_template('upload.html', jobs=jobs)

# --- Candidate Directory Routes ---

@app.route('/candidates')
@login_required
def list_candidates():
    job_id = request.args.get('job_id')
    min_score = request.args.get('min_score')
    min_exp = request.args.get('min_exp')
    search_query = request.args.get('search')
    sort_by = request.args.get('sort', 'score_desc')
    
    query = db.session.query(Application).join(Candidate).join(JobDescription)
    
    # Filter by Job Description
    if job_id:
        query = query.filter(Application.job_id == int(job_id))
    # Filter by Minimum Match Score
    if min_score:
        query = query.filter(Application.match_score >= float(min_score))
    # Filter by Minimum Experience Years
    if min_exp:
        query = query.filter(Candidate.experience_years >= float(min_exp))
    # Filter by Text Search (name, email, skills)
    if search_query:
        search_filter = f"%{search_query}%"
        query = query.filter(
            (Candidate.name.like(search_filter)) | 
            (Candidate.email.like(search_filter)) | 
            (Candidate.skills_extracted.like(search_filter))
        )
        
    # Sort Logic
    if sort_by == 'score_desc':
        query = query.order_by(Application.match_score.desc())
    elif sort_by == 'score_asc':
        query = query.order_by(Application.match_score.asc())
    elif sort_by == 'exp_desc':
        query = query.order_by(Candidate.experience_years.desc())
    elif sort_by == 'name_asc':
        query = query.order_by(Candidate.name.asc())
        
    applications = query.all()
    jobs = JobDescription.query.all()
    
    return render_template(
        'candidates.html',
        applications=applications,
        jobs=jobs,
        selected_job=int(job_id) if job_id else None,
        min_score=min_score,
        min_exp=min_exp,
        search_query=search_query,
        sort_by=sort_by
    )

@app.route('/candidates/<int:cand_id>')
@login_required
def candidate_detail(cand_id):
    # Fetch Candidate
    candidate = Candidate.query.get_or_4_0_4(cand_id)
    # Get current active application context (optional URL param)
    job_id = request.args.get('job_id')
    
    application = None
    if job_id:
        application = Application.query.filter_by(candidate_id=candidate.id, job_id=int(job_id)).first()
        
    # Fallback to candidate's first application if no job context specified
    if not application and candidate.applications:
        application = candidate.applications[0]
        
    match_details = {}
    if application and application.match_details:
        try:
            match_details = json.loads(application.match_details)
        except json.JSONDecodeError:
            pass
            
    return render_template(
        'candidate_detail.html',
        candidate=candidate,
        application=application,
        match_details=match_details
    )

@app.route('/candidates/delete/<int:cand_id>', methods=['POST'])
@login_required
def delete_candidate(cand_id):
    candidate = Candidate.query.get_or_4_0_4(cand_id)
    
    # Delete associated resume file if it exists
    if candidate.resume_path:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], candidate.resume_path)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                print(f"Error removing physical resume file: {e}")
                
    try:
        db.session.delete(candidate)
        db.session.commit()
        flash('Candidate profile deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting candidate: {e}', 'danger')
        
    return redirect(url_for('list_candidates'))

@app.route('/applications/update_status/<int:app_id>', methods=['POST'])
@login_required
def update_application_status(app_id):
    application = Application.query.get_or_4_0_4(app_id)
    status = request.form.get('status')
    
    if status in ['Screened', 'Shortlisted', 'Interviewing', 'Rejected', 'Hired']:
        application.status = status
        try:
            db.session.commit()
            flash('Application status updated successfully.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating status: {e}', 'danger')
    else:
        flash('Invalid status option selected.', 'danger')
        
    return redirect(url_for('candidate_detail', cand_id=application.candidate_id, job_id=application.job_id))

if __name__ == '__main__':
    app.run(debug=True, port=5000)
