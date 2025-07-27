from flask import Flask, render_template, request, redirect, url_for, session, flash,g
import sqlite3
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'your_secret_key'
DATABASE = 'library.db'

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(error):
    db = g.pop('db', None)
    if db is not None:
        db.close()

# -------------------- LOGIN --------------------
@app.route('/')
def home():
    return redirect(url_for('welcome'))

# ------------------- Welcome Page -------------------
@app.route('/welcome')
def welcome():
    return render_template('welcome.html')

# ------------------- Member Login -------------------
@app.route('/member_login', methods=['GET', 'POST'])
def member_login():
    if request.method == 'POST':
        email = request.form['email']
        conn = sqlite3.connect('library.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM members WHERE email = ?", (email,))
        member = cursor.fetchone()
        conn.close()

        if member:
            session['member_email'] = email
            return redirect(url_for('member_dashboard'))
        else:
            flash("Invalid email", "danger")
            return render_template('member_login.html')

    return render_template('member_login.html')

# ------------------- Member Dashboard -------------------
@app.route('/member_dashboard')
def member_dashboard():
    if 'member_email' not in session:
        return redirect(url_for('member_login'))

    email = session['member_email']
    conn = sqlite3.connect('library.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM members WHERE email = ?", (email,))
    member = cursor.fetchone()

    if not member:
        return redirect(url_for('member_logout'))

    member_id, member_name = member

    cursor.execute("""
        SELECT books.title, books.author, issue.issue_date, issue.return_date
        FROM issue
        JOIN books ON issue.book_id = books.id
        WHERE issue.member_id = ? AND issue.returned = 0
    """, (member_id,))
    issued_books = cursor.fetchall()
    conn.close()

    return render_template('member_dashboard.html', member_name=member_name, issued_books=issued_books)


# ------------------- Logout -------------------
@app.route('/member_logout')
def member_logout():
    session.pop('member_email', None)
    return redirect(url_for('member_login'))



@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form['password']
        if password == 'admin123':
            session['admin'] = True
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid password', 'danger')
    return render_template('login.html')



@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully", "info")
    return redirect(url_for('login'))



# -------------------- DASHBOARDS --------------------
@app.route('/dashboard')
def dashboard():
    if 'admin' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html')


# -------------------- BOOKS --------------------a


@app.route('/books')
def books():
    search_query = request.args.get('search', '')
    conn = get_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    if search_query:
        cursor.execute("SELECT * FROM books WHERE title LIKE ? OR author LIKE ? OR category LIKE ?",
                       (f'%{search_query}%', f'%{search_query}%', f'%{search_query}%'))
    else:
        cursor.execute("SELECT * FROM books")

    books = cursor.fetchall()
    conn.close()
    return render_template('books.html', books=books, search_query=search_query)


@app.route('/delete_book/<int:book_id>', methods=['POST'])
def delete_book(book_id):
    conn = get_db()
    conn.execute("DELETE FROM books WHERE id=?", (book_id,))
    conn.commit()
    return redirect(url_for('books'))

@app.route('/add_book', methods=['GET', 'POST'])
def add_book():
    if request.method == 'POST':
        title = request.form['title']
        author = request.form['author']
        category = request.form['category']
        total_copies = request.form['total_copies']

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO books (title, author, category, total_copies)
            VALUES (?, ?, ?, ?)
        ''', (title, author, category, total_copies))
        conn.commit()
        conn.close()
        return redirect(url_for('books'))

    return render_template('add_book.html')


@app.route('/edit_book/<int:book_id>', methods=['GET', 'POST'])
def edit_book(book_id):
    conn = get_db()
    cur = conn.cursor()
    
    if request.method == 'POST':
        title = request.form['title']
        author = request.form['author']
        category = request.form['category']
        total_copies = request.form['total_copies']

        cur.execute('''
            UPDATE books
            SET title=?, author=?, category=?, total_copies=?
            WHERE id=?
        ''', (title, author, category, total_copies, book_id))

        conn.commit()
        flash("Book updated successfully!", "success")  # Flash confirmation
        return redirect(url_for('books'))

    cur.execute("SELECT * FROM books WHERE id=?", (book_id,))
    book = cur.fetchone()
    return render_template('edit_book.html', book=book)


@app.route('/issued_books')
def issued_books():
    conn = get_db()
    cur = conn.cursor()
    
    query = request.args.get('q', '').strip()
    
    if query:
        cur.execute("""
            SELECT issue.id, issue.issue_date, issue.return_date, 
                   members.name AS member_name, books.title AS book_title, books.author
            FROM issue 
            JOIN members ON issue.member_id = members.id
            JOIN books ON issue.book_id = books.id
            WHERE issue.returned = 0 AND (
                members.name LIKE ? OR
                books.title LIKE ?
            )
        """, (f"%{query}%", f"%{query}%"))
    else:
        cur.execute("""
            SELECT issue.id, issue.issue_date, issue.return_date, 
                   members.name AS member_name, books.title AS book_title, books.author
            FROM issue 
            JOIN members ON issue.member_id = members.id
            JOIN books ON issue.book_id = books.id
            WHERE issue.returned = 0
        """)
    
    issued = cur.fetchall()
    return render_template('issued_books.html', issued=issued)

@app.route('/member_issued_books')
def member_issued_books():
    if 'member_email' not in session:
        return redirect(url_for('member_login'))

    email = session['member_email']
    conn = get_db()
    cur = conn.cursor()

    # Get member ID based on email
    cur.execute("SELECT id FROM members WHERE email = ?", (email,))
    member = cur.fetchone()
    if not member:
        conn.close()
        return "Member not found"

    member_id = member['id']

    # Fetch books issued to this member that are not returned
    cur.execute("""
        SELECT books.title, books.author, issue.issue_date, issue.return_date
        FROM issue
        JOIN books ON issue.book_id = books.id
        WHERE issue.member_id = ? AND issue.returned = 0
    """, (member_id,))
    books = cur.fetchall()
    conn.close()

    return render_template("member_books.html", books=books)


# -------------------- MEMBERS --------------------

@app.route('/members')
def members():
    search = request.args.get('search', '')
    conn = get_db()
    cur = conn.cursor()

    if search:
        cur.execute("SELECT * FROM members WHERE name LIKE ? OR email LIKE ?", 
                    (f'%{search}%', f'%{search}%'))
    else:
        cur.execute("SELECT * FROM members")
        
    members = cur.fetchall()
    return render_template('members.html', members=members, search=search)


@app.route('/add_member', methods=['GET', 'POST'])
def add_member():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        conn = get_db()
        conn.execute("INSERT INTO members (name,email,phone) VALUES (?, ?, ?)", (name, email, phone))
        conn.commit()
        return redirect(url_for('members'))
    return render_template('add_member.html')


@app.route('/edit_member/<int:member_id>', methods=['GET', 'POST'])
def edit_member(member_id):
    conn = get_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        
        cursor.execute('''
            UPDATE members
            SET name = ?, email = ?, phone = ?
            WHERE id = ?
        ''', (name, email, phone, member_id))

        conn.commit()  # 💡 Don't forget this!
        conn.close()
        return redirect(url_for('members'))  # Go back to members list

    cursor.execute('SELECT * FROM members WHERE id = ?', (member_id,))
    member = cursor.fetchone()
    conn.close()
    return render_template('edit_member.html', member=member)


@app.route('/delete_member/<int:member_id>')
def delete_member(member_id):
    conn = get_db()
    conn.execute("DELETE FROM members WHERE id=?", (member_id,))
    conn.commit()
    return redirect(url_for('members'))

# -------------------- ISSUE / RETURN --------------------
'''@app.route('/issue', methods=['GET', 'POST'])
def issue_book():
    conn = get_db()
    cur = conn.cursor()
    if request.method == 'POST':
        book_id = request.form['book_id']
        member_id = request.form['member_id']
        issue_date = datetime.now().date()
        return_date = issue_date + timedelta(days=14)
        cur.execute("INSERT INTO issue (book_id, member_id, issue_date, return_date, returned) VALUES (?, ?, ?, ?, 0)",
                    (book_id, member_id, issue_date, return_date))
        conn.commit()
        return redirect(url_for('issue_book'))
    cur.execute("SELECT * FROM books")
    books = cur.fetchall()
    cur.execute("SELECT * FROM members")
    members = cur.fetchall()
    cur.execute("""
        SELECT issue.id, issue.issue_date, issue.return_date, members.name as member_name, books.title as book_title, books.author
        FROM issue JOIN members ON issue.member_id = members.id
        JOIN books ON issue.book_id = books.id
        WHERE issue.returned=0
    """)
    issues = cur.fetchall()
    return render_template('issue.html', books=books, members=members,issues=issues)'''

@app.route('/issue_book', methods=['GET', 'POST'])
def issue_book():
    conn = get_db()
    cur = conn.cursor()

    if request.method == 'POST':
        member_id = request.form['member_id']
        book_id = request.form['book_id']
        issue_date = request.form['issue_date']
        return_date = request.form['return_date']

        # Insert into issue table
        cur.execute("""
            INSERT INTO issue (member_id, book_id, issue_date, return_date, returned)
            VALUES (?, ?, ?, ?, 0)
        """, (member_id, book_id, issue_date, return_date))

        # Mark book as unavailable
        cur.execute("UPDATE books SET available = 0 WHERE id = ?", (book_id,))
        conn.commit()
        conn.close()
        return redirect(url_for('issued_books'))

    # On GET: load members and books
    cur.execute("SELECT * FROM members")
    members = cur.fetchall()
    cur.execute("SELECT * FROM books")
    books = cur.fetchall()
    conn.close()
    return render_template('issue.html', members=members, books=books)


@app.route('/return', methods=['GET', 'POST'])
def return_book_page():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT issue.id, issue.issue_date, issue.return_date, members.name as member_name, books.title as book_title, books.author
        FROM issue JOIN members ON issue.member_id = members.id
        JOIN books ON issue.book_id = books.id
        WHERE issue.returned=0
    """)
    issues = cur.fetchall()
    return render_template('return.html', issues=issues)


@app.route('/return_book/<int:issue_id>', methods=['POST'])
def return_book(issue_id):
    conn = get_db()
    cur = conn.cursor()
    
    cur.execute("UPDATE issue SET returned = 1 WHERE id = ?", (issue_id,))
    conn.commit()
    conn.close()
    
    return redirect(url_for('issued_books'))


# -------------------- EXTRAS --------------------

@app.route('/reports')
def reports():
    conn = sqlite3.connect('library.db')
    c = conn.cursor()

    c.execute('SELECT COUNT(*) FROM books')
    total_books = c.fetchone()[0]

    c.execute('SELECT COUNT(*) FROM members')
    total_members = c.fetchone()[0]

    c.execute('SELECT COUNT(*) FROM issue')
    total_issued = c.fetchone()[0]

    # Get recently issued books (last 5)
    c.execute('''
        SELECT members.name, books.title, issue.issue_date, issue.return_date
        FROM issue
        JOIN members ON issue.member_id = members.id
        JOIN books ON issue.book_id = books.id
        ORDER BY issue.issue_date DESC
        LIMIT 5
    ''')
    recent = c.fetchall()

    conn.close()

    # Structure data into dictionaries for Jinja
    recent_issues = [
        {
            'member': {'name': r[0]},
            'book': {'title': r[1]},
            'issue_date': datetime.strptime(r[2], "%Y-%m-%d"),
            'return_date': datetime.strptime(r[3], "%Y-%m-%d")
        }
        for r in recent
    ]

    return render_template('reports.html', total_books=total_books,
                           total_members=total_members, total_issued=total_issued,
                           recent_issues=recent_issues)


@app.route('/returned_books')
def returned_books():
    conn = sqlite3.connect('library.db')
    c = conn.cursor()
    c.execute("SELECT * FROM returned_books ORDER BY return_date DESC")
    returned = c.fetchall()
    conn.close()
    return render_template('return.html', returned=returned)


@app.route('/fines')
def fines():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT members.name, books.title, issue.return_date
        FROM issue 
        JOIN books ON books.id = issue.book_id
        JOIN members ON members.id = issue.member_id
        WHERE issue.returned=0
    """)
    today = datetime.now().date()
    results = []
    for row in cur.fetchall():
        due = datetime.strptime(row['return_date'], "%Y-%m-%d").date()
        fine = (today - due).days * 5 if today > due else 0
        results.append((row['name'], row['title'], row['return_date'], fine))
    return render_template('fines.html', fines=results)

@app.route('/search', methods=['GET', 'POST'])
def search():
    results = []
    if request.method == 'POST':
        keyword = request.form['keyword']
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT * FROM books WHERE title LIKE ? OR author LIKE ?", 
                    (f'%{keyword}%', f'%{keyword}%'))
        results = cur.fetchall()
    return render_template('search.html', results=results)

@app.route('/change_password', methods=['GET', 'POST'])
def change_password():
    if request.method == 'POST':
        old = request.form['old_password']
        new = request.form['new_password']
        if old == 'admin123':
            # In production, save to file or env; hardcoded for now
            flash("Password changed (not persisted in demo)", "success")
        else:
            flash("Incorrect old password", "danger")
    return render_template('change_password.html')

if __name__ == '__main__':
    app.run(debug=True)
