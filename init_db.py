import sqlite3

conn = sqlite3.connect('library.db')
cursor = conn.cursor()

# Drop existing tables if needed (optional for clean init)
cursor.execute("DROP TABLE IF EXISTS books")
cursor.execute("DROP TABLE IF EXISTS members")
cursor.execute("DROP TABLE IF EXISTS issue")

# Create books table
cursor.execute('''
    CREATE TABLE books (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        author TEXT NOT NULL,
        category TEXT,
        available INTEGER DEFAULT 1,
        total_copies INTEGER DEFAULT 1
    )
''')

# Create members table
cursor.execute('''
    CREATE TABLE members (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT,
        phone TEXT
    )
''')

# Create issue table
cursor.execute('''
    CREATE TABLE issue (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        book_id INTEGER,
        member_id INTEGER,
        issue_date TEXT,
        return_date TEXT,
        returned INTEGER DEFAULT 0,
        FOREIGN KEY (book_id) REFERENCES books(id),
        FOREIGN KEY (member_id) REFERENCES members(id)
    )
''')
cursor.execute(''' 
    CREATE TABLE IF NOT EXISTS returns (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        member_name TEXT,
        book_title TEXT,
        author TEXT,
        issue_date TEXT,
        due_date TEXT,
        return_date TEXT
    )
''')


conn.commit()
conn.close()

print("Initialized database with tables in 'library.db'")
