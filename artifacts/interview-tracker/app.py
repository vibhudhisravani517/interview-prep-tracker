import os
import uuid
import bcrypt
from functools import wraps
from flask import Flask, render_template, redirect, url_for, request, flash, jsonify, session, abort, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SESSION_SECRET', 'dev-secret-key-change-me')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///interview_tracker.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'uploads', 'notes')
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'webp', 'heic', 'heif'}
MAX_IMAGE_BYTES = 12 * 1024 * 1024  # 12 MB
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

db = SQLAlchemy(app)

CATEGORIES = [
    {'id': 'aptitude', 'label': 'Aptitude', 'icon': '🧮', 'color': 'blue'},
    {'id': 'programming', 'label': 'Programming', 'icon': '💻', 'color': 'green'},
    {'id': 'data_structures', 'label': 'Data Structures', 'icon': '🌳', 'color': 'purple'},
    {'id': 'mock_interviews', 'label': 'Mock Interviews', 'icon': '🎤', 'color': 'orange'},
]

TASK_STATUSES = [
    {'id': 'pending',     'label': 'Pending',     'color': 'gray'},
    {'id': 'in_progress', 'label': 'In Progress', 'color': 'blue'},
    {'id': 'completed',   'label': 'Completed',   'color': 'green'},
]


# ── Models ───────────────────────────────────────────────────────────────────

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.LargeBinary, nullable=False)
    role = db.Column(db.String(20), nullable=False, default='student')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    tasks = db.relationship('UserTask', backref='owner', lazy=True, cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

    def check_password(self, password):
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash)


class Topic(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(50), nullable=False)
    priority = db.Column(db.String(20), default='medium')
    completed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)


class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    topic_id = db.Column(db.Integer, db.ForeignKey('topic.id'), nullable=False)
    content = db.Column(db.Text, nullable=False, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint('user_id', 'topic_id', name='uq_user_topic_note'),)


class NoteImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    topic_id = db.Column(db.Integer, db.ForeignKey('topic.id'), nullable=False)
    filename = db.Column(db.String(200), nullable=False)
    original_name = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class UserTask(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    topic = db.Column(db.String(200), nullable=True)
    due_date = db.Column(db.Date, nullable=True)
    priority = db.Column(db.String(20), default='medium')
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def is_overdue(self):
        return (self.due_date and self.due_date < date.today()
                and self.status != 'completed')


# ── Auth helpers ──────────────────────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login', next=request.path))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login', next=request.path))
        if session.get('user_role') != 'admin':
            flash('Admin access required.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated


def current_user():
    if 'user_id' in session:
        return db.session.get(User, session['user_id'])
    return None


@app.context_processor
def inject_user():
    return {'current_user': current_user()}


# ── Auth routes ───────────────────────────────────────────────────────────────

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')
        role = request.form.get('role', 'student')

        if not email or not password or not confirm:
            flash('All fields are required.', 'error')
            return render_template('register.html', form_data=request.form)
        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'error')
            return render_template('register.html', form_data=request.form)
        if password != confirm:
            flash('Passwords do not match.', 'error')
            return render_template('register.html', form_data=request.form)
        if role not in ('student', 'admin'):
            role = 'student'
        if User.query.filter_by(email=email).first():
            flash('An account with that email already exists.', 'error')
            return render_template('register.html', form_data=request.form)

        user = User(email=email, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        session['user_id'] = user.id
        session['user_email'] = user.email
        session['user_role'] = user.role
        flash('Welcome! Your account has been created.', 'success')
        return redirect(url_for('dashboard'))

    return render_template('register.html', form_data={})


@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        next_url = request.form.get('next', '')

        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['user_email'] = user.email
            session['user_role'] = user.role
            flash('Welcome back!', 'success')
            return redirect(next_url or url_for('dashboard'))

        flash('Invalid email or password.', 'error')
        return render_template('login.html', form_email=email, next_url=next_url)

    next_url = request.args.get('next', '')
    return render_template('login.html', form_email='', next_url=next_url)


@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


# ── Admin routes ──────────────────────────────────────────────────────────────

@app.route('/admin')
@admin_required
def admin_panel():
    students = User.query.filter_by(role='student').order_by(User.created_at.desc()).all()
    topic_stats = get_stats()

    student_data = []
    for s in students:
        task_total = UserTask.query.filter_by(user_id=s.id).count()
        task_done  = UserTask.query.filter_by(user_id=s.id, status='completed').count()
        student_data.append({
            'user': s,
            'task_total': task_total,
            'task_done': task_done,
            'task_pct': round(task_done / task_total * 100) if task_total else 0,
        })

    admin_count = User.query.filter_by(role='admin').count()
    return render_template('admin.html',
                           student_data=student_data,
                           topic_stats=topic_stats,
                           categories=CATEGORIES,
                           admin_count=admin_count)


@app.route('/admin/delete/<int:user_id>', methods=['POST'])
@admin_required
def admin_delete_user(user_id):
    user = db.session.get(User, user_id)
    if not user:
        abort(404)
    if user.id == session['user_id']:
        flash('You cannot delete your own account.', 'error')
        return redirect(url_for('admin_panel'))
    email = user.email
    db.session.delete(user)
    db.session.commit()
    flash(f'Account "{email}" has been deleted.', 'info')
    return redirect(url_for('admin_panel'))


# ── Task Manager routes ───────────────────────────────────────────────────────

@app.route('/tasks')
@login_required
def task_list():
    uid = session['user_id']
    status_filter   = request.args.get('status', 'all')
    priority_filter = request.args.get('priority', 'all')

    query = UserTask.query.filter_by(user_id=uid)
    if status_filter != 'all':
        query = query.filter_by(status=status_filter)
    if priority_filter != 'all':
        query = query.filter_by(priority=priority_filter)

    tasks = query.order_by(UserTask.due_date.asc().nullslast(), UserTask.created_at.desc()).all()

    counts = {
        'all':         UserTask.query.filter_by(user_id=uid).count(),
        'pending':     UserTask.query.filter_by(user_id=uid, status='pending').count(),
        'in_progress': UserTask.query.filter_by(user_id=uid, status='in_progress').count(),
        'completed':   UserTask.query.filter_by(user_id=uid, status='completed').count(),
    }
    today = date.today()
    return render_template('tasks.html', tasks=tasks, counts=counts,
                           active_status=status_filter, active_priority=priority_filter,
                           statuses=TASK_STATUSES, today=today)


@app.route('/tasks/add', methods=['GET', 'POST'])
@login_required
def add_task():
    if request.method == 'POST':
        title    = request.form.get('title', '').strip()
        topic    = request.form.get('topic', '').strip()
        due_raw  = request.form.get('due_date', '').strip()
        priority = request.form.get('priority', 'medium')
        status   = request.form.get('status', 'pending')

        if not title:
            flash('Task title is required.', 'error')
            return render_template('add_task.html', form_data=request.form, statuses=TASK_STATUSES)

        due_date = None
        if due_raw:
            try:
                due_date = datetime.strptime(due_raw, '%Y-%m-%d').date()
            except ValueError:
                flash('Invalid date format.', 'error')
                return render_template('add_task.html', form_data=request.form, statuses=TASK_STATUSES)

        task = UserTask(user_id=session['user_id'], title=title, topic=topic,
                        due_date=due_date, priority=priority, status=status)
        db.session.add(task)
        db.session.commit()
        flash(f'Task "{title}" added!', 'success')
        return redirect(url_for('task_list'))

    return render_template('add_task.html', form_data={}, statuses=TASK_STATUSES)


@app.route('/tasks/edit/<int:task_id>', methods=['GET', 'POST'])
@login_required
def edit_task(task_id):
    task = UserTask.query.filter_by(id=task_id, user_id=session['user_id']).first_or_404()

    if request.method == 'POST':
        title    = request.form.get('title', '').strip()
        topic    = request.form.get('topic', '').strip()
        due_raw  = request.form.get('due_date', '').strip()
        priority = request.form.get('priority', 'medium')
        status   = request.form.get('status', 'pending')

        if not title:
            flash('Task title is required.', 'error')
            return render_template('edit_task.html', task=task, statuses=TASK_STATUSES)

        due_date = None
        if due_raw:
            try:
                due_date = datetime.strptime(due_raw, '%Y-%m-%d').date()
            except ValueError:
                flash('Invalid date format.', 'error')
                return render_template('edit_task.html', task=task, statuses=TASK_STATUSES)

        task.title    = title
        task.topic    = topic
        task.due_date = due_date
        task.priority = priority
        task.status   = status
        db.session.commit()
        flash('Task updated!', 'success')
        return redirect(url_for('task_list'))

    return render_template('edit_task.html', task=task, statuses=TASK_STATUSES)


@app.route('/tasks/delete/<int:task_id>', methods=['POST'])
@login_required
def delete_task(task_id):
    task = UserTask.query.filter_by(id=task_id, user_id=session['user_id']).first_or_404()
    db.session.delete(task)
    db.session.commit()
    flash('Task deleted.', 'info')
    return redirect(url_for('task_list'))


@app.route('/tasks/status/<int:task_id>', methods=['POST'])
@login_required
def update_task_status(task_id):
    task = UserTask.query.filter_by(id=task_id, user_id=session['user_id']).first_or_404()
    new_status = request.json.get('status')
    if new_status in ('pending', 'in_progress', 'completed'):
        task.status = new_status
        db.session.commit()
    return jsonify({'status': task.status, 'id': task.id})


# ── Notes routes ─────────────────────────────────────────────────────────────

@app.route('/notes')
@login_required
def notes_page():
    uid = session['user_id']
    # Collect all topic IDs the user has ANY note text or image for
    all_notes_q = Note.query.filter_by(user_id=uid).order_by(Note.updated_at.desc()).all()
    image_rows = NoteImage.query.filter_by(user_id=uid).order_by(NoteImage.created_at.asc()).all()

    note_map   = {n.topic_id: n for n in all_notes_q}
    images_map = {}
    for img in image_rows:
        images_map.setdefault(img.topic_id, []).append({
            'id': img.id,
            'url': url_for('static', filename='uploads/notes/' + img.filename),
            'name': img.original_name,
        })

    # Active topic IDs = has text content OR has images
    active_ids = set(
        tid for tid, n in note_map.items() if n.content.strip()
    ) | set(images_map.keys())

    topics_map = {}
    if active_ids:
        topics_map = {t.id: t for t in Topic.query.filter(Topic.id.in_(active_ids)).all()}

    notes_by_category = {cat['id']: [] for cat in CATEGORIES}
    for tid in active_ids:
        topic = topics_map.get(tid)
        if not topic or topic.category not in notes_by_category:
            continue
        notes_by_category[topic.category].append({
            'note':   note_map.get(tid),
            'topic':  topic,
            'images': images_map.get(tid, []),
        })
    # Sort each category by topic title
    for cat_id in notes_by_category:
        notes_by_category[cat_id].sort(key=lambda x: x['topic'].title)

    all_topics = Topic.query.order_by(Topic.category, Topic.title).all()
    has_notes = any(len(v) > 0 for v in notes_by_category.values())
    return render_template('notes.html', notes_by_category=notes_by_category,
                           categories=CATEGORIES, all_topics=all_topics, has_notes=has_notes)


@app.route('/notes/save/<int:topic_id>', methods=['POST'])
@login_required
def save_note(topic_id):
    topic = Topic.query.get_or_404(topic_id)
    uid = session['user_id']
    content = request.json.get('content', '').strip()

    note = Note.query.filter_by(user_id=uid, topic_id=topic_id).first()
    if note:
        note.content = content
        note.updated_at = datetime.utcnow()
    else:
        note = Note(user_id=uid, topic_id=topic_id, content=content)
        db.session.add(note)
    db.session.commit()
    return jsonify({
        'saved': True,
        'topic_id': topic_id,
        'updated_at': note.updated_at.strftime('%b %d, %Y %H:%M'),
    })


@app.route('/notes/delete/<int:topic_id>', methods=['POST'])
@login_required
def delete_note(topic_id):
    uid = session['user_id']
    note = Note.query.filter_by(user_id=uid, topic_id=topic_id).first()
    if note:
        db.session.delete(note)
        db.session.commit()
    flash('Note deleted.', 'info')
    return redirect(url_for('notes_page'))


@app.route('/notes/get/<int:topic_id>')
@login_required
def get_note(topic_id):
    uid = session['user_id']
    note = Note.query.filter_by(user_id=uid, topic_id=topic_id).first()
    images = NoteImage.query.filter_by(user_id=uid, topic_id=topic_id)\
                            .order_by(NoteImage.created_at.asc()).all()
    imgs = [{'id': i.id, 'url': url_for('static', filename='uploads/notes/' + i.filename),
             'name': i.original_name} for i in images]
    return jsonify({'content': note.content if note else '', 'topic_id': topic_id, 'images': imgs})


# ── Image upload routes ───────────────────────────────────────────────────────

def _allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/notes/upload/<int:topic_id>', methods=['POST'])
@login_required
def upload_note_image(topic_id):
    Topic.query.get_or_404(topic_id)
    uid = session['user_id']

    if 'image' not in request.files:
        return jsonify({'error': 'No file sent'}), 400

    f = request.files['image']
    if not f or f.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    if not _allowed_file(f.filename):
        return jsonify({'error': 'File type not allowed. Use JPG, PNG, GIF or WebP.'}), 400

    # Read into memory to check size before saving
    data = f.read()
    if len(data) > MAX_IMAGE_BYTES:
        return jsonify({'error': 'Image too large (max 12 MB)'}), 400

    ext = f.filename.rsplit('.', 1)[1].lower()
    if ext in ('heic', 'heif'):
        ext = 'jpg'  # browser-display compatible rename
    unique_name = f"{uid}_{topic_id}_{uuid.uuid4().hex}.{ext}"
    save_path = os.path.join(UPLOAD_FOLDER, unique_name)
    with open(save_path, 'wb') as out:
        out.write(data)

    img = NoteImage(user_id=uid, topic_id=topic_id,
                    filename=unique_name,
                    original_name=secure_filename(f.filename)[:200])
    db.session.add(img)

    # Ensure a Note row exists (so the card appears even with no text yet)
    note = Note.query.filter_by(user_id=uid, topic_id=topic_id).first()
    if not note:
        note = Note(user_id=uid, topic_id=topic_id, content='')
        db.session.add(note)

    db.session.commit()

    return jsonify({
        'id': img.id,
        'url': url_for('static', filename='uploads/notes/' + unique_name),
        'name': img.original_name,
    })


@app.route('/notes/image/delete/<int:image_id>', methods=['POST'])
@login_required
def delete_note_image(image_id):
    uid = session['user_id']
    img = NoteImage.query.filter_by(id=image_id, user_id=uid).first_or_404()
    path = os.path.join(UPLOAD_FOLDER, img.filename)
    if os.path.exists(path):
        os.remove(path)
    db.session.delete(img)
    db.session.commit()
    return jsonify({'deleted': True, 'id': image_id})


# ── Stats helper ──────────────────────────────────────────────────────────────

def get_stats():
    stats = {}
    total = 0
    total_done = 0
    for cat in CATEGORIES:
        done  = Topic.query.filter_by(category=cat['id'], completed=True).count()
        count = Topic.query.filter_by(category=cat['id']).count()
        total += count
        total_done += done
        stats[cat['id']] = {
            'total': count, 'completed': done, 'pending': count - done,
            'percent': round(done / count * 100) if count else 0,
        }
    stats['overall'] = {
        'total': total, 'completed': total_done, 'pending': total - total_done,
        'percent': round(total_done / total * 100) if total else 0,
    }
    return stats


# ── Prep-topic routes ─────────────────────────────────────────────────────────

@app.route('/')
@login_required
def dashboard():
    stats = get_stats()
    recent = Topic.query.order_by(Topic.created_at.desc()).limit(5).all()
    uid = session['user_id']
    upcoming_tasks = (UserTask.query
                      .filter_by(user_id=uid)
                      .filter(UserTask.status != 'completed')
                      .order_by(UserTask.due_date.asc().nullslast())
                      .limit(4).all())
    return render_template('dashboard.html', categories=CATEGORIES, stats=stats,
                           recent=recent, upcoming_tasks=upcoming_tasks, today=date.today())


@app.route('/topics')
@login_required
def topics():
    category = request.args.get('category', 'all')
    status   = request.args.get('status', 'all')
    priority = request.args.get('priority', 'all')

    query = Topic.query
    if category != 'all':
        query = query.filter_by(category=category)
    if status == 'completed':
        query = query.filter_by(completed=True)
    elif status == 'pending':
        query = query.filter_by(completed=False)
    if priority != 'all':
        query = query.filter_by(priority=priority)

    all_topics = query.order_by(Topic.created_at.desc()).all()
    stats = get_stats()

    uid = session['user_id']
    topic_ids = [t.id for t in all_topics]
    notes_map = {}
    if topic_ids:
        user_notes = Note.query.filter(
            Note.user_id == uid,
            Note.topic_id.in_(topic_ids)
        ).all()
        notes_map = {n.topic_id: n for n in user_notes}

    return render_template('topics.html', topics=all_topics, categories=CATEGORIES,
                           active_category=category, active_status=status,
                           active_priority=priority, stats=stats, notes_map=notes_map)


@app.route('/add', methods=['GET', 'POST'])
@login_required
def add_topic():
    if request.method == 'POST':
        title       = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        category    = request.form.get('category', '')
        priority    = request.form.get('priority', 'medium')

        if not title or not category:
            flash('Title and category are required.', 'error')
            return render_template('add_topic.html', categories=CATEGORIES, form_data=request.form)

        topic = Topic(title=title, description=description, category=category, priority=priority)
        db.session.add(topic)
        db.session.commit()
        flash(f'Topic "{title}" added successfully!', 'success')
        return redirect(url_for('topics', category=category))

    prefill_category = request.args.get('category', '')
    return render_template('add_topic.html', categories=CATEGORIES,
                           prefill_category=prefill_category, form_data={})


@app.route('/edit/<int:topic_id>', methods=['GET', 'POST'])
@login_required
def edit_topic(topic_id):
    topic = Topic.query.get_or_404(topic_id)
    if request.method == 'POST':
        title       = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        category    = request.form.get('category', '')
        priority    = request.form.get('priority', 'medium')

        if not title or not category:
            flash('Title and category are required.', 'error')
            return render_template('edit_topic.html', topic=topic, categories=CATEGORIES)

        topic.title = title; topic.description = description
        topic.category = category; topic.priority = priority
        db.session.commit()
        flash('Topic updated successfully!', 'success')
        return redirect(url_for('topics'))

    return render_template('edit_topic.html', topic=topic, categories=CATEGORIES)


@app.route('/toggle/<int:topic_id>', methods=['POST'])
@login_required
def toggle_topic(topic_id):
    topic = Topic.query.get_or_404(topic_id)
    topic.completed = not topic.completed
    topic.completed_at = datetime.utcnow() if topic.completed else None
    db.session.commit()
    return jsonify({'completed': topic.completed, 'id': topic.id})


@app.route('/delete/<int:topic_id>', methods=['POST'])
@login_required
def delete_topic(topic_id):
    topic = Topic.query.get_or_404(topic_id)
    db.session.delete(topic)
    db.session.commit()
    flash('Topic deleted.', 'info')
    return redirect(url_for('topics'))


@app.route('/progress')
@login_required
def progress():
    stats = get_stats()
    by_category = {}
    for cat in CATEGORIES:
        by_category[cat['id']] = {
            'meta': cat,
            'topics': Topic.query.filter_by(category=cat['id']).order_by(Topic.completed, Topic.priority).all(),
            'stats': stats[cat['id']],
        }
    return render_template('progress.html', categories=CATEGORIES, by_category=by_category, stats=stats)


@app.route('/api/stats')
@login_required
def api_stats():
    return jsonify(get_stats())


# ── Seed data ─────────────────────────────────────────────────────────────────

def seed_data():
    if Topic.query.count() == 0:
        samples = [
            Topic(title='Number Series & Sequences', category='aptitude', priority='high'),
            Topic(title='Profit & Loss Problems', category='aptitude', priority='medium'),
            Topic(title='Time & Work Calculations', category='aptitude', priority='medium'),
            Topic(title='Probability Basics', category='aptitude', priority='low'),
            Topic(title='Python Basics & OOP', category='programming', priority='high'),
            Topic(title='Array Manipulation', category='programming', priority='high'),
            Topic(title='String Processing Techniques', category='programming', priority='medium'),
            Topic(title='Recursion & Backtracking', category='programming', priority='high',
                  completed=True, completed_at=datetime.utcnow()),
            Topic(title='Arrays & Linked Lists', category='data_structures', priority='high'),
            Topic(title='Binary Trees & BST', category='data_structures', priority='high'),
            Topic(title='Graphs & BFS/DFS', category='data_structures', priority='medium'),
            Topic(title='Hash Maps & Sets', category='data_structures', priority='high',
                  completed=True, completed_at=datetime.utcnow()),
            Topic(title='Technical Round 1 Practice', category='mock_interviews', priority='high'),
            Topic(title='HR Interview Questions', category='mock_interviews', priority='medium'),
            Topic(title='System Design Overview', category='mock_interviews', priority='low'),
        ]
        db.session.bulk_save_objects(samples)
        db.session.commit()


with app.app_context():
    db.create_all()
    seed_data()


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
