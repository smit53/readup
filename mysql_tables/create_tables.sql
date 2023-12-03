Create Database library;

CREATE TABLE Books (
    book_id INT AUTO_INCREMENT PRIMARY KEY,            -- Unique identifier for each book
    title VARCHAR(255) NOT NULL,           -- Title of the book 
    authors VARCHAR(255),                  -- Authors of the book
    original_publication_year INTEGER,     -- Year of original publication
    language_code VARCHAR(10),             -- Language code of the book
    average_rating FLOAT,                  -- Average rating of the book
    ratings_count INTEGER,                 -- Number of ratings for the book
    image_url VARCHAR(255)                 -- URL for the book cover image
);

CREATE TABLE Users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,          -- Unique identifier for each user
    username VARCHAR(255) UNIQUE,        -- User's username (unique constraint)
	first_name VARCHAR(255),			 -- User's first name 
    last_name VARCHAR(255),              -- User's last name
    email VARCHAR(255) UNIQUE,           -- User's email address (unique constraint)
	dob DATE NOT NULL, 					 -- user date of birth (not null constraint)
    registration_date DATE default null,     -- Date when the user registered (not null constraint)
	last_updated DATE NOT NULL			 -- Date last when user details updated (not null constraint)
);

-- Create a trigger to update registration_date and last_updated columns on each insert or update
CREATE TRIGGER update_dates
BEFORE INSERT ON Users
FOR EACH ROW
SET NEW.registration_date = COALESCE(NEW.registration_date, CURDATE()),
    NEW.last_updated = COALESCE(NEW.last_updated, CURDATE());
    
CREATE TRIGGER update_last_updated
BEFORE UPDATE ON Users
FOR EACH ROW
SET NEW.last_updated = CURDATE();

CREATE TABLE UserCredentials (
    user_id INTEGER PRIMARY KEY,         -- Reference to Users table
    password VARCHAR(255) NOT NULL,     -- Hashed password (not null constraint)
    FOREIGN KEY (user_id) REFERENCES Users(user_id)  -- Foreign key referencing Users table
);

CREATE TABLE Bookmarks (
    bookmark_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    book_id INT,
    FOREIGN KEY (user_id) REFERENCES Users(user_id),
    FOREIGN KEY (book_id) REFERENCES Books(book_id),
    UNIQUE KEY unique_user_book (user_id, book_id)
);
