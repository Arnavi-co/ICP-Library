import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import os

# --- Database Connection ---
DB_FILE = 'library.db'

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

# --- Authentication ---
def check_login(username, password):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM librarians WHERE username = ? AND password = ?", (username, password))
    user = c.fetchone()
    conn.close()
    return user is not None

# --- Page Config ---
st.set_page_config(page_title="ICP College Library", layout="wide")

# --- Session State ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'username' not in st.session_state:
    st.session_state['username'] = None

# --- Login Screen ---
if not st.session_state['logged_in']:
    st.title("🔐 ICP College Library Login")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            if check_login(username, password):
                st.session_state['logged_in'] = True
                st.session_state['username'] = username
                st.success("Login Successful!")
                st.rerun()
            else:
                st.error("Invalid Credentials")
    st.info("Default Login: admin / admin123")
    st.stop()

# --- Main Interface ---
st.title(f"📚 ICP College Library - {st.session_state['username']}")

# Sidebar Navigation
menu = st.sidebar.selectbox("Menu", ["Dashboard", "Search Student", "Issue Book", "Return Book", "Add Student", "Add Book", "Logout"])

conn = get_db()

# --- 1. Dashboard ---
if menu == "Dashboard":
    st.header("📊 Library Overview")
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM books")
    total_books = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM books WHERE status = 'Available'")
    available = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM borrowings WHERE return_date IS NULL")
    issued = c.fetchone()[0]
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Books", total_books)
    col2.metric("Available", available)
    col3.metric("Issued", issued)
    
    st.subheader("Overdue Books")
    today = datetime.now().strftime("%Y-%m-%d")
    c.execute('''SELECT b.title, s.name, br.due_date, br.id 
                 FROM borrowings br 
                 JOIN books b ON br.book_accession_no = b.accession_no 
                 JOIN students s ON br.student_id = s.id 
                 WHERE br.return_date IS NULL AND br.due_date < ?''', (today,))
    overdue = c.fetchall()
    if overdue:
        df = pd.DataFrame(overdue, columns=["Book", "Student", "Due Date", "ID"])
        st.dataframe(df)
    else:
        st.success("No overdue books!")

# --- 2. Search Student ---
elif menu == "Search Student":
    st.header("🔍 Search Student")
    search_name = st.text_input("Enter Student Name")
    if search_name:
        c = conn.cursor()
        c.execute("SELECT * FROM students WHERE name LIKE ?", (f"%{search_name}%",))
        students = c.fetchall()
        if students:
            for s in students:
                st.subheader(f"Student: {s['name']}")
                st.write(f"**Mobile:** {s['mobile']} | **Class:** {s['class_name']} | **Age:** {s['age']}")
                
                # Show Borrowings
                c.execute('''SELECT b.title, br.issue_date, br.due_date, br.return_date, br.fine_amount 
                             FROM borrowings br 
                             JOIN books b ON br.book_accession_no = b.accession_no 
                             WHERE br.student_id = ?''', (s['id'],))
                history = c.fetchall()
                if history:
                    st.write("**Borrowing History**")
                    df = pd.DataFrame(history, columns=["Book", "Issue Date", "Due Date", "Return Date", "Fine"])
                    st.dataframe(df)
                else:
                    st.write("No borrowing history.")
        else:
            st.warning("Student not found.")

# --- 3. Issue Book ---
elif menu == "Issue Book":
    st.header("📖 Issue Book")
    c = conn.cursor()
    
    # Get Available Books
    c.execute("SELECT accession_no, title FROM books WHERE status = 'Available'")
    books = c.fetchall()
    book_options = {b['accession_no']: f"{b['title']} ({b['accession_no']})" for b in books}
    
    # Get Students
    c.execute("SELECT id, name FROM students")
    students = c.fetchall()
    student_options = {s['id']: s['name'] for s in students}
    
    col1, col2 = st.columns(2)
    with col1:
        selected_book = st.selectbox("Select Book", list(book_options.keys()))
        selected_student = st.selectbox("Select Student", list(student_options.keys()))
    with col2:
        issue_date = st.date_input("Issue Date", datetime.now())
        due_date = st.date_input("Due Date", datetime.now() + timedelta(days=14))
    
    if st.button("Issue Book"):
        if selected_book and selected_student:
            try:
                c.execute("UPDATE books SET status = 'Issued' WHERE accession_no = ?", (selected_book,))
                c.execute('''INSERT INTO borrowings (student_id, book_accession_no, issue_date, due_date, return_date) 
                             VALUES (?, ?, ?, ?, NULL)''',
                             (selected_student, selected_book, issue_date.strftime("%Y-%m-%d"), due_date.strftime("%Y-%m-%d")))
                conn.commit()
                st.success("Book Issued Successfully!")
            except Exception as e:
                st.error(f"Error: {e}")
        else:
            st.warning("Please select both book and student.")

# --- 4. Return Book ---
elif menu == "Return Book":
    st.header("🔄 Return Book")
    c = conn.cursor()
    c.execute('''SELECT br.id, b.title, s.name, br.due_date, br.issue_date 
                 FROM borrowings br 
                 JOIN books b ON br.book_accession_no = b.accession_no 
                 JOIN students s ON br.student_id = s.id 
                 WHERE br.return_date IS NULL''')
    active_loans = c.fetchall()
    
    if active_loans:
        loan_options = {l['id']: f"{l['title']} - {l['name']} (Due: {l['due_date']})" for l in active_loans}
        selected_loan = st.selectbox("Select Active Loan", list(loan_options.keys()))
        
        if selected_loan:
            loan = next(l for l in active_loans if l['id'] == selected_loan)
            return_date = st.date_input("Return Date", datetime.now())
            
            if st.button("Confirm Return"):
                fine = 0
                if return_date > datetime.strptime(loan['due_date'], "%Y-%m-%d").date():
                    days_overdue = (return_date - datetime.strptime(loan['due_date'], "%Y-%m-%d").date()).days
                    fine = days_overdue * 10 # 10 currency units per day
                    st.warning(f"Overdue by {days_overdue} days. Fine: {fine}")
                
                c.execute("UPDATE books SET status = 'Available' WHERE accession_no = (SELECT book_accession_no FROM borrowings WHERE id = ?)", (selected_loan,))
                c.execute("UPDATE borrowings SET return_date = ?, fine_amount = ? WHERE id = ?", 
                          (return_date.strftime("%Y-%m-%d"), fine, selected_loan))
                conn.commit()
                st.success("Book Returned Successfully!")
    else:
        st.info("No active loans to return.")

# --- 5. Add Student ---
elif menu == "Add Student":
    st.header("➕ Add New Student")
    with st.form("add_student"):
        name = st.text_input("Name")
        dob = st.date_input("Date of Birth")
        mobile = st.text_input("Mobile Number")
        class_name = st.text_input("Class")
        age = st.number_input("Age", min_value=1)
        submitted = st.form_submit_button("Add Student")
        if submitted:
            c = conn.cursor()
            c.execute("INSERT INTO students (name, dob, mobile, class_name, age) VALUES (?, ?, ?, ?, ?)",
                      (name, dob.strftime("%Y-%m-%d"), mobile, class_name, age))
            conn.commit()
            st.success("Student Added!")

# --- 6. Add Book ---
elif menu == "Add Book":
    st.header("➕ Add New Book")
    with st.form("add_book"):
        accession = st.text_input("Accession No")
        title = st.text_input("Title")
        author = st.text_input("Author")
        publisher = st.text_input("Publisher")
        year = st.number_input("Year")
        pages = st.number_input("Pages")
        cost = st.number_input("Cost")
        bill = st.text_input("Bill Number")
        source = st.text_input("Source of Supply")
        submitted = st.form_submit_button("Add Book")
        if submitted:
            c = conn.cursor()
            c.execute("INSERT INTO books (accession_no, title, author, publisher, year, pages, cost, bill_number, source, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Available')",
                      (accession, title, author, publisher, year, pages, cost, bill, source))
            conn.commit()
            st.success("Book Added!")

# --- 7. Logout ---
elif menu == "Logout":
    st.session_state['logged_in'] = False
    st.session_state['username'] = None
    st.success("Logged Out")
    st.rerun()

conn.close()