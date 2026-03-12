import pandas as pd
import sqlite3
import os

DB_FILE = 'library.db'

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # 1. Create Books Table
    c.execute('''CREATE TABLE IF NOT EXISTS books (
        accession_no TEXT PRIMARY KEY,
        title TEXT,
        author TEXT,
        publisher TEXT,
        year INTEGER,
        pages INTEGER,
        cost REAL,
        bill_number TEXT,
        source TEXT,
        status TEXT DEFAULT 'Available'
    )''')
    
    # 2. Create Students Table
    c.execute('''CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        dob TEXT,
        mobile TEXT,
        class_name TEXT,
        age INTEGER
    )''')
    
    # 3. Create Borrowings Table (Loans & Fines)
    c.execute('''CREATE TABLE IF NOT EXISTS borrowings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER,
        book_accession_no TEXT,
        issue_date TEXT,
        due_date TEXT,
        return_date TEXT,
        fine_amount REAL DEFAULT 0,
        FOREIGN KEY(student_id) REFERENCES students(id),
        FOREIGN KEY(book_accession_no) REFERENCES books(accession_no)
    )''')
    
    # 4. Create Librarian Table
    c.execute('''CREATE TABLE IF NOT EXISTS librarians (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT
    )''')
    
    # Insert Default Librarian (Username: admin, Password: admin123)
    c.execute("INSERT OR IGNORE INTO librarians (username, password) VALUES ('admin', 'admin123')")
    
    conn.commit()
    conn.close()
    print("Database initialized successfully.")

def import_excel():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    try:
        # Import Books
        if os.path.exists('books.xlsx'):
            df_books = pd.read_excel('books.xlsx')
            # Map columns to DB
            df_books = df_books.rename(columns={
                'accession no': 'accession_no',
                'bill number and date': 'bill_number',
                'source of supply': 'source',
                'date of birth': 'dob' # Just in case
            })
            # Drop duplicates based on accession_no
            df_books = df_books.drop_duplicates(subset=['accession_no'])
            
            for _, row in df_books.iterrows():
                c.execute('''INSERT OR IGNORE INTO books 
                    (accession_no, title, author, publisher, year, pages, cost, bill_number, source, status) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Available')''',
                    (row.get('accession_no'), row.get('title'), row.get('author'), 
                     row.get('publisher'), row.get('year'), row.get('pages'), 
                     row.get('cost'), row.get('bill_number'), row.get('source')))
            print(f"Imported {len(df_books)} books.")

        # Import Students
        if os.path.exists('students.xlsx'):
            df_students = pd.read_excel('students.xlsx')
            df_students = df_students.drop_duplicates(subset=['name'])
            
            for _, row in df_students.iterrows():
                c.execute('''INSERT OR IGNORE INTO students 
                    (name, dob, mobile, class_name, age) 
                    VALUES (?, ?, ?, ?, ?)''',
                    (row.get('name'), row.get('dob'), row.get('mobile'), 
                     row.get('class'), row.get('age')))
            print(f"Imported {len(df_students)} students.")
            
    except Exception as e:
        print(f"Error importing data: {e}")
    
    conn.commit()
    conn.close()
    print("Data import complete.")

if __name__ == "__main__":
    init_db()
    import_excel()