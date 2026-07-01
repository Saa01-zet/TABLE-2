import sqlite3
from flask import Flask, request, jsonify, render_template, session, redirect
from flask_cors import CORS
from functools import wraps
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key_here_change_this_in_production'
CORS(app)


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'message': 'Необходимо авторизоваться'}), 401
        return f(*args, **kwargs)

    return decorated_function


def get_db_connection():
    conn = sqlite3.connect('users.db')
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()

    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
    ''')

    conn.execute('''
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    conn.commit()
    conn.close()


@app.route('/')
def index():
    return redirect('/login')


@app.route('/register')
def register_page():
    return render_template('register.html')


@app.route('/login')
def login_page():
    return render_template('login.html')


@app.route('/profile')
def profile_page():
    if 'user_id' not in session:
        return redirect('/login')
    return render_template('profile.html')


@app.route('/edit_profile')
def edit_profile_page():
    if 'user_id' not in session:
        return redirect('/login')
    return render_template('edit_profile.html')


@app.route('/notes')
def notes_page():
    if 'user_id' not in session:
        return redirect('/login')
    return render_template('notes.html')


@app.route('/create_note')
def create_note_page():
    if 'user_id' not in session:
        return redirect('/login')
    return render_template('create_note.html')


@app.route('/view_note')
def view_note_page():
    if 'user_id' not in session:
        return redirect('/login')
    return render_template('view_note.html')


@app.route('/edit_note')
def edit_note_page():
    if 'user_id' not in session:
        return redirect('/login')
    return render_template('edit_note.html')


@app.route('/api/register', methods=['POST'])
def register():
    try:
        data = request.json
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '').strip()

        if not username or not email or not password:
            return jsonify({'message': 'Все поля должны быть заполнены'}), 400

        if len(password) < 6:
            return jsonify({'message': 'Пароль должен содержать не менее 6 символов'}), 400

        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()

        if user:
            conn.close()
            return jsonify({'message': 'Пользователь уже зарегистрирован'}), 400

        conn.execute(
            'INSERT INTO users (username, email, password) VALUES (?, ?, ?)',
            (username, email, password)
        )
        conn.commit()
        conn.close()

        return jsonify({'message': 'Регистрация выполнена успешно'}), 201

    except Exception as e:
        return jsonify({'message': f'Ошибка: {str(e)}'}), 500


@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.json
        email = data.get('email', '').strip()
        password = data.get('password', '').strip()

        if not email or not password:
            return jsonify({'message': 'Все поля должны быть заполнены'}), 400

        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        conn.close()

        if not user:
            return jsonify({'message': 'Неверный email или пароль'}), 401

        if user['password'] != password:
            return jsonify({'message': 'Неверный email или пароль'}), 401

        session['user_id'] = user['id']
        session['username'] = user['username']
        session['email'] = user['email']

        return jsonify({
            'message': 'Добро пожаловать!',
            'user': {
                'id': user['id'],
                'username': user['username'],
                'email': user['email']
            }
        }), 200

    except Exception as e:
        return jsonify({'message': f'Ошибка: {str(e)}'}), 500


@app.route('/api/profile', methods=['GET'])
@login_required
def get_profile():
    try:
        user_id = session.get('user_id')
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
        conn.close()

        if not user:
            return jsonify({'message': 'Пользователь не найден'}), 404

        return jsonify({
            'id': user['id'],
            'username': user['username'],
            'email': user['email']
        }), 200

    except Exception as e:
        return jsonify({'message': f'Ошибка: {str(e)}'}), 500


@app.route('/api/profile', methods=['PUT'])
@login_required
def update_profile():
    try:
        data = request.json
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        user_id = session.get('user_id')

        if not username or not email:
            return jsonify({'message': 'Все поля должны быть заполнены'}), 400

        conn = get_db_connection()

        existing_user = conn.execute(
            'SELECT * FROM users WHERE email = ? AND id != ?',
            (email, user_id)
        ).fetchone()

        if existing_user:
            conn.close()
            return jsonify({'message': 'Этот email уже используется другим пользователем'}), 400

        conn.execute(
            'UPDATE users SET username = ?, email = ? WHERE id = ?',
            (username, email, user_id)
        )
        conn.commit()
        conn.close()

        session['username'] = username
        session['email'] = email

        return jsonify({
            'message': 'Профиль успешно обновлен',
            'user': {
                'id': user_id,
                'username': username,
                'email': email
            }
        }), 200

    except Exception as e:
        return jsonify({'message': f'Ошибка: {str(e)}'}), 500


@app.route('/api/logout', methods=['POST'])
def logout():
    try:
        session.clear()
        return jsonify({'message': 'Вы успешно вышли из аккаунта'}), 200
    except Exception as e:
        return jsonify({'message': f'Ошибка: {str(e)}'}), 500



@app.route('/api/notes', methods=['GET'])
@login_required
def get_notes():
    try:
        user_id = session.get('user_id')
        search = request.args.get('search', '').strip()

        conn = get_db_connection()

        if search:
            notes = conn.execute(
                'SELECT * FROM notes WHERE user_id = ? AND title LIKE ? ORDER BY created_at DESC',
                (user_id, f'%{search}%')
            ).fetchall()
        else:
            notes = conn.execute(
                'SELECT * FROM notes WHERE user_id = ? ORDER BY created_at DESC',
                (user_id,)
            ).fetchall()

        conn.close()

        result = []
        for note in notes:
            result.append({
                'id': note['id'],
                'title': note['title'],
                'content': note['content'],
                'created_at': note['created_at']
            })

        return jsonify(result), 200

    except Exception as e:
        return jsonify({'message': f'Ошибка: {str(e)}'}), 500


@app.route('/api/notes', methods=['POST'])
@login_required
def create_note():
    try:
        data = request.json
        title = data.get('title', '').strip()
        content = data.get('content', '').strip()
        user_id = session.get('user_id')

        if not title or not content:
            return jsonify({'message': 'Все поля должны быть заполнены'}), 400

        created_at = datetime.now().strftime('%d.%m.%Y %H:%M')

        conn = get_db_connection()
        conn.execute(
            'INSERT INTO notes (title, content, user_id, created_at) VALUES (?, ?, ?, ?)',
            (title, content, user_id, created_at)
        )
        conn.commit()
        conn.close()

        return jsonify({'message': 'Заметка успешно создана'}), 201

    except Exception as e:
        return jsonify({'message': f'Ошибка: {str(e)}'}), 500


@app.route('/api/note', methods=['GET'])
@login_required
def get_note():
    try:
        note_id = request.args.get('id')
        user_id = session.get('user_id')

        if not note_id:
            return jsonify({'message': 'ID заметки не указан'}), 400

        conn = get_db_connection()
        note = conn.execute(
            'SELECT * FROM notes WHERE id = ? AND user_id = ?',
            (note_id, user_id)
        ).fetchone()
        conn.close()

        if not note:
            return jsonify({'message': 'Заметка не найдена'}), 404

        return jsonify({
            'id': note['id'],
            'title': note['title'],
            'content': note['content'],
            'created_at': note['created_at']
        }), 200

    except Exception as e:
        return jsonify({'message': f'Ошибка: {str(e)}'}), 500


@app.route('/api/note', methods=['PUT'])
@login_required
def update_note():
    try:
        data = request.json
        note_id = data.get('id')
        title = data.get('title', '').strip()
        content = data.get('content', '').strip()
        user_id = session.get('user_id')

        if not note_id:
            return jsonify({'message': 'ID заметки не указан'}), 400

        if not title or not content:
            return jsonify({'message': 'Все поля должны быть заполнены'}), 400

        conn = get_db_connection()

        note = conn.execute(
            'SELECT * FROM notes WHERE id = ? AND user_id = ?',
            (note_id, user_id)
        ).fetchone()

        if not note:
            conn.close()
            return jsonify({'message': 'Заметка не найдена'}), 404

        conn.execute(
            'UPDATE notes SET title = ?, content = ? WHERE id = ? AND user_id = ?',
            (title, content, note_id, user_id)
        )
        conn.commit()
        conn.close()

        return jsonify({'message': 'Заметка успешно обновлена'}), 200

    except Exception as e:
        return jsonify({'message': f'Ошибка: {str(e)}'}), 500


@app.route('/api/note', methods=['DELETE'])
@login_required
def delete_note():
    try:
        note_id = request.args.get('id')
        user_id = session.get('user_id')

        if not note_id:
            return jsonify({'message': 'ID заметки не указан'}), 400

        conn = get_db_connection()

        note = conn.execute(
            'SELECT * FROM notes WHERE id = ? AND user_id = ?',
            (note_id, user_id)
        ).fetchone()

        if not note:
            conn.close()
            return jsonify({'message': 'Заметка не найдена'}), 404

        conn.execute(
            'DELETE FROM notes WHERE id = ? AND user_id = ?',
            (note_id, user_id)
        )
        conn.commit()
        conn.close()

        return jsonify({'message': 'Заметка успешно удалена'}), 200

    except Exception as e:
        return jsonify({'message': f'Ошибка: {str(e)}'}), 500


if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)