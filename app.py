from flask import Flask, render_template, session, request, redirect
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.secret_key = "mysecretkey"

# -----------------------
# MySQL Configuration
# -----------------------

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = os.environ.get("DB_PASSWORD", "Vaishnavi@00")
app.config['MYSQL_DB'] = 'quiz_db'

mysql = MySQL(app)

# -----------------------
# HOME ROUTE (Redirect to Login)
# -----------------------

@app.route('/')
def home():
    return redirect('/register')

@app.route('/testdb')
def test_db():
    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT 1")
        return "Database Connected Successfully!"
    except Exception as e:
        return str(e)

# -----------------------
# USER AUTH
# -----------------------

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])

        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO users(name, email, password) VALUES(%s, %s, %s)",
                    (name, email, password))
        mysql.connection.commit()
        cur.close()

        return redirect('/login')

    return render_template("register.html")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = cur.fetchone()

        if user and check_password_hash(user[3], password):
            session['user_id'] = user[0]
            session['username'] = user[1]
            return redirect('/dashboard')
        else:
            return "Invalid Email or Password"

    return render_template("login.html")

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

# -----------------------
# QUIZ
# -----------------------

@app.route('/quiz/<domain>', methods=['GET', 'POST'])
def quiz(domain):
    if 'user_id' not in session:
        return redirect('/login')

    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM questions WHERE domain=%s", (domain,))
    questions = cur.fetchall()

    if request.method == 'POST':
        score = 0

        for q in questions:
            question_id = str(q[0])
            selected_answer = request.form.get(question_id)

            if selected_answer == q[6]:
                score += 1

        total_questions = len(questions)
        percentage = round((score / total_questions) * 100, 2) if total_questions > 0 else 0

        cur.execute("INSERT INTO results(user_id, score) VALUES(%s, %s)",
                    (session['user_id'], score))
        mysql.connection.commit()

        return render_template("result.html",
                               score=score,
                               total=total_questions,
                               percentage=percentage)

    return render_template("quiz.html", questions=questions)

# -----------------------
# LEADERBOARD
# -----------------------

@app.route('/leaderboard')
def leaderboard():
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT users.name, results.score
        FROM results
        JOIN users ON users.id = results.user_id
        ORDER BY results.score DESC
    """)
    data = cur.fetchall()
    return render_template("leaderboard.html", data=data)

# -----------------------
# ADMIN
# -----------------------

@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM admin WHERE username=%s AND password=%s",
                    (username, password))
        admin = cur.fetchone()

        if admin:
            session['admin'] = admin[1]
            return redirect('/admin_dashboard')
        else:
            return "Invalid Admin Credentials"

    return render_template("admin_login.html")

@app.route('/admin_dashboard')
def admin_dashboard():
    if 'admin' not in session:
        return redirect('/admin_login')

    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM questions")
    questions = cur.fetchall()

    return render_template("admin_dashboard.html", questions=questions)

@app.route('/add_question', methods=['GET', 'POST'])
def add_question():
    if 'admin' not in session:
        return redirect('/admin_login')

    if request.method == 'POST':
        domain = request.form.get('domain')
        question = request.form['question']
        option1 = request.form['option1']
        option2 = request.form['option2']
        option3 = request.form['option3']
        option4 = request.form['option4']
        answer = request.form['answer']

        cur = mysql.connection.cursor()
        cur.execute("""
            INSERT INTO questions(question, option1, option2, option3, option4, answer, domain)
            VALUES(%s, %s, %s, %s, %s, %s, %s)
        """, (question, option1, option2, option3, option4, answer, domain))

        mysql.connection.commit()
        return redirect('/admin_dashboard')

    return render_template("add_question.html")

@app.route('/delete_question/<int:id>')
def delete_question(id):
    if 'admin' not in session:
        return redirect('/admin_login')

    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM questions WHERE id=%s", (id,))
    mysql.connection.commit()

    return redirect('/admin_dashboard')

@app.route('/edit_question/<int:id>', methods=['GET','POST'])
def edit_question(id):
    if 'admin' not in session:
        return redirect('/admin_login')

    cur = mysql.connection.cursor()

    if request.method == 'POST':
        domain = request.form['domain']
        question = request.form['question']
        option1 = request.form['option1']
        option2 = request.form['option2']
        option3 = request.form['option3']
        option4 = request.form['option4']
        answer = request.form['answer']

        cur.execute("""
            UPDATE questions 
            SET question=%s,
                option1=%s,
                option2=%s,
                option3=%s,
                option4=%s,
                answer=%s,
                domain=%s
            WHERE id=%s
        """, (question, option1, option2, option3, option4,
              answer, domain, id))

        mysql.connection.commit()
        return redirect('/admin_dashboard')

    # GET request (load existing data)
    cur.execute("SELECT * FROM questions WHERE id=%s", (id,))
    question_data = cur.fetchone()

    return render_template("edit_question.html",
                           question=question_data)

@app.route('/select_domain')
def select_domain():
    if 'user_id' not in session:
        return redirect('/login')

    return render_template("select_domain.html")

@app.route('/dashboard')
def dashboard():
    if 'user_id' in session:
        return redirect('/select_domain')
    else:
        return redirect('/login')
    
@app.route('/instructions/<domain>')
def instructions(domain):
    if 'user_id' not in session:
        return redirect('/login')

    return render_template("instructions.html", domain=domain)

# -----------------------

if __name__ == "__main__":
    app.run(debug=True)