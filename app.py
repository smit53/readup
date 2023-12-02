from flask import Flask, render_template, request, redirect, url_for
import mysql.connector
import math

app = Flask(__name__)

db_config = {
    'user': 'root',
    'password': 'root',
    'host': '127.0.0.1',
    'port': 3306,
    'database': 'readup',
    'raise_on_warnings': True
}

conn = mysql.connector.connect(**db_config)
cursor = conn.cursor(dictionary=True)

@app.route('/')
def index():
    return render_template('index.html')

def get_books(page=1, per_page=20):
    offset = (page - 1) * per_page
    cursor.execute(f'SELECT * FROM books LIMIT {per_page} OFFSET {offset}')
    books = cursor.fetchall()
    return books
    
def get_book_by_id(book_id):
    cursor.execute(f'SELECT * FROM books WHERE book_id = {book_id}')
    book = cursor.fetchone()
    return book

def get_total_books():
    cursor.execute('SELECT COUNT(*) as total_books FROM books')
    result = cursor.fetchone()

    return result['total_books']

# Define custom functions
def custom_max(a, b):
    return max(a, b)

def custom_min(a, b):
    return min(a, b)

# Pass the custom functions to the Jinja2 environment
app.jinja_env.globals.update(custom_max=custom_max, custom_min=custom_min)

@app.route('/explore')
def explore():
    per_page = 20
    page = request.args.get('page', 1, type=int)
    total_books = get_total_books()
    total_pages = math.ceil(total_books / per_page)

    books = get_books(page=page, per_page=per_page)

    return render_template('explore.html', books=books, page=page, total_pages=total_pages)


@app.route('/book/<int:book_id>')
def book_details(book_id):
    book = get_book_by_id(book_id)

    if book:
        return render_template('book_details.html', book=book)
    else:
        # Redirect to explore page if the book is not found
        return redirect(url_for('explore'))

@app.route('/search')
def search():
    return render_template('search.html')

@app.route('/search_results', methods=['GET'])
def search_results():
    query = request.args.get('query', '')
    
    # Perform a search based on the query (customize this based on your needs)
    cursor.execute('SELECT * FROM books WHERE title LIKE %s OR authors LIKE %s', (f'%{query}%', f'%{query}%'))
    search_results = cursor.fetchall()

    return render_template('search_results.html', query=query, results=search_results)


if __name__ == '__main__':
    app.run(debug=True)