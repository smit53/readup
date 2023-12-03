from flask import Flask, jsonify, render_template, request, redirect, url_for, session, flash
import mysql.connector
import math
import secrets
import pymysql
from .config import RDSConfig

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

db_config = {
    'user': RDSConfig.USERNAME,
    'password': RDSConfig.PASSWORD,
    'host': RDSConfig.ENDPOINT,
    'port': RDSConfig.PORT,
    'database': RDSConfig.DATABASE_NAME
}

conn = pymysql.connect(**db_config)
cursor = conn.cursor(dictionary=True)

@app.route('/')
def index():
    return render_template('index.html')

def get_books(page=1, per_page=20):
    offset = (page - 1) * per_page
    cursor.execute(f'SELECT * FROM books LIMIT {per_page} OFFSET {offset}')
    books = cursor.fetchall()
    return books
    
def get_book_by_id(book_id, user_id=None):
    cursor.execute('SELECT * FROM Books WHERE book_id = %s', (book_id,))
    book = cursor.fetchone()

    if user_id:
        cursor.execute('SELECT * FROM Bookmarks WHERE user_id = %s AND book_id = %s', (user_id, book_id))
        bookmark_info = cursor.fetchone()
        book['is_bookmarked'] = bool(bookmark_info)

    return book

def get_total_books():
    cursor.execute('SELECT COUNT(*) as total_books FROM books')
    result = cursor.fetchone()

    return result['total_books']

def is_user_logged_in():
    return 'user_id' in session

# Make the is_user_logged_in function available to all templates
@app.context_processor
def inject_user_status():
    return dict(is_user_logged_in=is_user_logged_in)

# Define custom functions
def custom_max(a, b):
    return max(a, b)

def custom_min(a, b):
    return min(a, b)

def get_books(page=1, per_page=20, user_id=None):
    offset = (page - 1) * per_page
    cursor.execute(f'SELECT b.*, bm.user_id IS NOT NULL as is_bookmarked FROM books b LEFT JOIN bookmarks bm ON b.book_id = bm.book_id AND bm.user_id = %s LIMIT {per_page} OFFSET {offset}', (user_id,))
    books = cursor.fetchall()
    return books

# Pass the custom functions to the Jinja2 environment
app.jinja_env.globals.update(custom_max=custom_max, custom_min=custom_min)

@app.route('/explore')
def explore():
    if not is_user_logged_in():
        flash('Please log in to access this page.', 'error')
        return redirect(url_for('login'))
    
    per_page = 20
    page = request.args.get('page', 1, type=int)
    total_books = get_total_books()
    total_pages = math.ceil(total_books / per_page)

    user_id = session.get('user_id')  # Get user_id from the session if available

    books = get_books(page=page, per_page=per_page, user_id=user_id)

    return render_template('explore.html', books=books, page=page, total_pages=total_pages, user_id=user_id)


def get_user_bookmarks(user_id):
    cursor.execute('SELECT book_id FROM Bookmarks WHERE user_id = %s', (user_id,))
    bookmarks = set(row['book_id'] for row in cursor.fetchall())
    return bookmarks

@app.route('/bookmark/<int:book_id>')
def bookmark(book_id):
    if not is_user_logged_in():
        flash('Please log in to bookmark a book.', 'error')
        return redirect(url_for('login'))

    user_id = session['user_id']

    # Check if the bookmark already exists
    cursor.execute('SELECT * FROM Bookmarks WHERE user_id = %s AND book_id = %s', (user_id, book_id))
    existing_bookmark = cursor.fetchone()

    if existing_bookmark:
        # Remove the bookmark
        cursor.execute('DELETE FROM Bookmarks WHERE user_id = %s AND book_id = %s', (user_id, book_id))
        conn.commit()
        flash('Bookmark removed successfully!', 'success')
    else:
        # Add the bookmark
        cursor.execute('INSERT INTO Bookmarks (user_id, book_id) VALUES (%s, %s)', (user_id, book_id))
        conn.commit()
        flash('Bookmarked successfully!', 'success')

    # Redirect back to the same page after bookmarking
    referrer = request.referrer
    return redirect(referrer)

@app.route('/mylist')
def my_list():
    if not is_user_logged_in():
        flash('Please log in to access your list.', 'error')
        return redirect(url_for('login'))

    user_id = session['user_id']

    # Fetch only the bookmarked books from the database for the logged-in user
    cursor.execute('SELECT * FROM bookmarks bm JOIN books b ON b.book_id = bm.book_id WHERE bm.user_id = %s;', (user_id,))
    books = cursor.fetchall()

    # Provide default values for page and total_pages
    page = 1
    total_pages = 1

    return render_template('my_list.html', books=books, page=page, total_pages=total_pages)

@app.route('/toggle_bookmark/<int:book_id>')
def toggle_bookmark(book_id):
    if not is_user_logged_in():
        flash('Please log in to bookmark a book.', 'error')
        return redirect(url_for('login'))

    user_id = session['user_id']

    # Check if the bookmark already exists
    cursor.execute('SELECT * FROM Bookmarks WHERE user_id = %s AND book_id = %s', (user_id, book_id))
    existing_bookmark = cursor.fetchone()

    if existing_bookmark:
        # Remove the bookmark
        cursor.execute('DELETE FROM Bookmarks WHERE user_id = %s AND book_id = %s', (user_id, book_id))
        conn.commit()
        # flash('Bookmark removed successfully!', 'success')
    else:
        # Add the bookmark
        cursor.execute('INSERT INTO Bookmarks (user_id, book_id) VALUES (%s, %s)', (user_id, book_id))
        conn.commit()
        # flash('Bookmarked successfully!', 'success')

    return redirect(request.referrer)

@app.route('/book/<int:book_id>')
def book_details(book_id):
    if not is_user_logged_in():
        flash('Please log in to access this page.', 'error')
        return redirect(url_for('login'))
    user_id = session['user_id']
    book = get_book_by_id(book_id,user_id)

    if book:
        return render_template('book_details.html', book=book)
    else:
        # Redirect to explore page if the book is not found
        return redirect(url_for('explore'))

@app.route('/search', methods=['GET', 'POST'])
def search():
    if is_user_logged_in():
        user_id = session['user_id']
        if request.method == 'POST':
            search_query = request.form.get('search_query')
            cursor.execute('SELECT b.*, CASE WHEN bm.user_id = %s THEN 1 ELSE 0 END AS is_bookmarked FROM books b LEFT JOIN bookmarks bm ON b.book_id = bm.book_id WHERE title LIKE %s OR authors LIKE %s;', (user_id, f'%{search_query}%', f'%{search_query}%'))
            search_results = cursor.fetchall()

            if not search_results:
                flash('No results found. Please try a different search query.', 'info')
                return redirect(url_for('search'))

            return render_template('search_results.html', search_results=search_results, query=search_query)
        
        return render_template('search.html')
    else:
        flash('Please log in to use the search functionality.', 'error')
        return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = get_user_by_username(username)

        if user and username == user['username'] and user['password'] == password:
            session['user_id'] = user['user_id']
            # flash('Login successful', 'success')

            # Check if there's an intended page to redirect to after login
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            else:
                return redirect(url_for('explore'))  # Redirect to explore page after successful login

        else:
            flash('Invalid username or password', 'error')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('Logout successful', 'success')
    return redirect(url_for('login'))


def get_user_by_username(username):
    cursor.execute('select u.user_id, u.username, uc.password from usercredentials uc join users u on uc.user_id = u.user_id where u.username = %s', (username,))
    return cursor.fetchone()
    
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username').lower()
        password = request.form.get('password')
        first_name = request.form.get('first_name').capitalize()
        last_name = request.form.get('last_name').capitalize()
        email = request.form.get('email').lower()
        dob = request.form.get('dob')  # Assuming you have a date of birth field

        # Check if the username is already taken
        if get_user_by_username(username):
            flash('Username is already taken. Please choose another.', 'error')
        else:
            # Insert the new user into the Users table
            cursor.execute('INSERT INTO Users (username, first_name, last_name, email, dob) VALUES (%s, %s, %s, %s, %s)',
                           (username, first_name, last_name, email, dob))
            conn.commit()

            # Get the user_id of the newly inserted user
            cursor.execute('SELECT user_id FROM Users WHERE username = %s', (username,))
            user_id = cursor.fetchone()['user_id']

            # Insert user credentials into the UserCredentials table
            cursor.execute('INSERT INTO UserCredentials (user_id, password) VALUES (%s, %s)', (user_id, password))
            conn.commit()

            flash('Signup successful. Please log in.', 'success')
            return redirect(url_for('login'))

    return render_template('signup.html')

@app.route('/profile')
def profile():
    if is_user_logged_in():
        user_id = session['user_id']
        
        # Fetch user details from the Users table
        cursor.execute('SELECT * FROM Users WHERE user_id = %s', (user_id,))
        user = cursor.fetchone()

        return render_template('profile.html', user=user)
    else:
        flash('Please log in to access your profile.', 'error')
        return redirect(url_for('login'))

@app.route('/update_profile', methods=['GET', 'POST'])
def update_profile():
    if is_user_logged_in():
        user_id = session['user_id']

        if request.method == 'POST':
            # Get updated details from the form
            updated_first_name = request.form.get('updated_first_name')
            updated_last_name = request.form.get('updated_last_name')
            updated_email = request.form.get('updated_email')

            # Check if nothing is being updated
            if not any([updated_first_name, updated_last_name, updated_email]):
                flash('No changes made. Please update at least one field.', 'info')
                return redirect(url_for('update_profile'))

            # Update the user details in the Users table for non-empty fields
            update_query = 'UPDATE Users SET'
            update_values = []

            if updated_first_name:
                update_query += ' first_name = %s,'
                update_values.append(updated_first_name.capitalize())

            if updated_last_name:
                update_query += ' last_name = %s,'
                update_values.append(updated_last_name.capitalize())

            if updated_email:
                update_query += ' email = %s,'
                update_values.append(updated_email.lower())

            # Remove the trailing comma and add the WHERE clause
            update_query = update_query.rstrip(',')
            update_query += ' WHERE user_id = %s'

            # Append user_id to the update_values list
            update_values.append(user_id)

            # Execute the update query
            cursor.execute(update_query, tuple(update_values))
            conn.commit()

            flash('Profile updated successfully.', 'success')
            return redirect(url_for('profile'))

        return render_template('update_profile.html')
    else:
        flash('Please log in to access your profile.', 'error')
        return redirect(url_for('login'))

@app.route('/change_password', methods=['GET', 'POST'])
def change_password():
    if is_user_logged_in():
        user_id = session['user_id']

        if request.method == 'POST':
            # Get the current and new passwords from the form
            current_password = request.form.get('current_password')
            new_password = request.form.get('new_password')
            confirm_password = request.form.get('confirm_password')

            # Validate the current password (you may want to enhance this validation)
            cursor.execute('SELECT password FROM UserCredentials WHERE user_id = %s', (user_id,))
            stored_password = cursor.fetchone()['password']

            if not stored_password == current_password:
                flash('Incorrect current password. Please try again.', 'error')
                return redirect(url_for('change_password'))

            if not new_password == confirm_password:
                flash('Passwords dont match, Try again!', 'error')
                return redirect(url_for('change_password'))

            # Update the password in the UserCredentials table
            hashed_new_password = new_password
            cursor.execute('UPDATE UserCredentials SET password = %s WHERE user_id = %s',
                           (hashed_new_password, user_id))
            conn.commit()

            flash('Password changed successfully.', 'success')
            return redirect(url_for('logout'))

        return render_template('change_password.html')
    else:
        flash('Please log in to change your password.', 'error')
        return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)