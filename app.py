from flask import Flask, render_template, request, redirect, url_for, flash
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from werkzeug.utils import secure_filename
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'
UPLOAD_FOLDER = 'static/uploads/'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB limit

# Ensure the upload folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def get_db_connection():
    conn = psycopg2.connect(
        dbname='school_db',
        user='postgres',
        password='4321',
        host='localhost'
    )
    return conn

def create_tables():
    conn = get_db_connection()
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()

    # Create classes table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS classes (
            class_id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    ''')

    # Create student table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS student (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            email VARCHAR(255) NOT NULL,
            address TEXT,
            class_id INT REFERENCES classes(class_id),
            image VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    ''')

    cur.close()
    conn.close()

@app.route('/')
def home():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        SELECT s.id, s.name, s.email, s.created_at, c.name AS class_name, s.image 
        FROM student s
        JOIN classes c ON s.class_id = c.class_id
        ORDER BY s.created_at DESC;
    ''')
    students = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('index.html', students=students)

@app.route('/create', methods=('GET', 'POST'))
def create():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM classes;')
    classes = cur.fetchall()
    cur.close()

    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        address = request.form['address']
        class_id = request.form['class_id']
        image = request.files.get('image')

        if not name:
            flash('Name is required!', 'error')
        else:
            filename = None
            if image and image.filename:
                if image.filename.rsplit('.', 1)[1].lower() in {'jpg', 'png'}:
                    filename = secure_filename(image.filename)
                    image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    image.save(image_path)
                    flash(f'File saved to {image_path}', 'info')
                else:
                    flash('Invalid image format! Only jpg and png are allowed.', 'error')

            cur = conn.cursor()
            cur.execute('''
                INSERT INTO student (name, email, address, class_id, image)
                VALUES (%s, %s, %s, %s, %s)
            ''', (name, email, address, class_id, filename))
            conn.commit()
            cur.close()
            conn.close()
            return redirect(url_for('home'))

    return render_template('create.html', classes=classes)

@app.route('/view/<int:id>')
def view(id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        SELECT s.name, s.email, s.address, s.created_at, c.name AS class_name, s.image
        FROM student s
        JOIN classes c ON s.class_id = c.class_id
        WHERE s.id = %s;
    ''', (id,))
    student = cur.fetchone()
    cur.close()
    conn.close()
    return render_template('view.html', student=student)

@app.route('/edit/<int:id>', methods=('GET', 'POST'))
def edit(id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM classes;')
    classes = cur.fetchall()

    cur.execute('SELECT * FROM student WHERE id = %s;', (id,))
    student = cur.fetchone()
    cur.close()

    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        address = request.form['address']
        class_id = request.form['class_id']
        image = request.files.get('image')

        if not name:
            flash('Name is required!', 'error')
        else:
            filename = None
            if image and image.filename:
                if image.filename.rsplit('.', 1)[1].lower() in {'jpg', 'png'}:
                    filename = secure_filename(image.filename)
                    image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    image.save(image_path)
                    flash(f'File saved to {image_path}', 'info')
                else:
                    flash('Invalid image format! Only jpg and png are allowed.', 'error')

            cur = conn.cursor()
            cur.execute('''
                UPDATE student SET name = %s, email = %s, address = %s, class_id = %s, image = %s
                WHERE id = %s;
            ''', (name, email, address, class_id, filename, id))
            conn.commit()
            cur.close()
            conn.close()
            return redirect(url_for('home'))

    return render_template('edit.html', student=student, classes=classes)

@app.route('/delete/<int:id>', methods=('POST',))
def delete(id):
    conn = get_db_connection()
    cur = conn.cursor()

    # Delete the image from the server
    cur.execute('SELECT image FROM student WHERE id = %s;', (id,))
    image = cur.fetchone()[0]
    if image:
        try:
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], image)
            os.remove(image_path)
            flash(f'File removed from {image_path}', 'info')
        except FileNotFoundError:
            flash('File not found for removal.', 'warning')

    # Delete the student record
    cur.execute('DELETE FROM student WHERE id = %s;', (id,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('home'))

@app.route('/classes', methods=('GET', 'POST'))
def manage_classes():
    conn = get_db_connection()
    cur = conn.cursor()

    if request.method == 'POST':
        name = request.form['name']
        if not name:
            flash('Class name is required!', 'error')
        else:
            cur.execute('INSERT INTO classes (name) VALUES (%s);', (name,))
            conn.commit()
            return redirect(url_for('manage_classes'))

    cur.execute('SELECT * FROM classes ORDER BY created_at DESC;')
    classes = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('classes.html', classes=classes)

@app.route('/classes/delete/<int:id>', methods=('POST',))
def delete_class(id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('DELETE FROM classes WHERE class_id = %s;', (id,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('manage_classes'))

if __name__ == '__main__':
    create_tables()  # Create tables on startup
    app.run(debug=True)
