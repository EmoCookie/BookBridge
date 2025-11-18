import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime


# establishing a connection to SQLite database & configuring it
# to return rows as dictionaries (column access by name)
def get_db_connection():
    conn = sqlite3.connect("app/database.db")
    conn.row_factory = sqlite3.Row  # allows column access by name
    return conn


# creating 'users' table to store basic user information
def create_user_table():
    conn = get_db_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            age INTEGER NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
    """
    )
    conn.commit()
    conn.close()


# creating 'user_profiles' table to store extended profile info
def create_user_profile_table():
    conn = get_db_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS user_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            username TEXT,
            profile_picture TEXT,
            bio TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """
    )
    conn.commit()
    conn.close()


# creating the 'friend_requests' table to manage friend request data
def create_friend_requests_table():
    conn = get_db_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS friend_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER NOT NULL,
            receiver_id INTEGER NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
    )
    conn.commit()
    conn.close()


# creating 'book_listings' table for books posted by users
def create_book_listings_table():
    conn = get_db_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS book_listings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            genre TEXT NOT NULL,
            condition TEXT NOT NULL,
            image_filename TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """
    )
    conn.commit()
    conn.close()


# creating 'messages' table for buyer-seller communication
def create_messages_table():
    conn = get_db_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER NOT NULL,
            receiver_id INTEGER NOT NULL,
            book_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (sender_id) REFERENCES users(id),
            FOREIGN KEY (receiver_id) REFERENCES users(id),
            FOREIGN KEY (book_id) REFERENCES book_listings(id)
        )
    """
    )
    conn.commit()
    conn.close()


# creating 'community_posts' table if it doesn't already exist
def create_community_posts_table():
    conn = get_db_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS community_posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            genre TEXT NOT NULL,
            image_filename TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """
    )
    conn.commit()
    conn.close()


# creating 'comments' table if it doesn't already exist
def create_comments_table():
    conn = get_db_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (post_id) REFERENCES community_posts(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """
    )
    conn.commit()
    conn.close()


# creates tables in the database.
# each function ensures the table is created only if it doesn't exist
create_user_table()
create_user_profile_table()
create_book_listings_table()
create_messages_table()
create_community_posts_table()
create_comments_table()
create_friend_requests_table()


# user manageent functions
# registers a new user by inserting their details to the 'users' table
def register_user(first_name, last_name, age, email, password):
    conn = get_db_connection()
    hashed_pw = generate_password_hash(password)
    conn.execute(
        """
        INSERT INTO users (first_name, last_name, age, email, password)
        VALUES (?, ?, ?, ?, ?)
    """,
        (first_name, last_name, age, email, hashed_pw),
    )
    conn.commit()
    conn.close()


# gets a user by their email address
def get_user_by_email(email):
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()
    return user


# gets a user by their user ID
def get_user_by_id(user_id):
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return user


# validating user credentials by checking email & password hash
def validate_login(email, password):
    user = get_user_by_email(email)  # retrieves user record by email
    if user and check_password_hash(
        user["password"], password
    ):  # verify hashed password
        return True  # login valid
    return False  # login failed


# Saves user's profile (username, bio, and profile picture)
def save_user_profile(user_id, username, bio, profile_picture):
    conn = get_db_connection()
    # checks if the profile already exists
    existing = conn.execute(
        "SELECT * FROM user_profiles WHERE user_id = ?", (user_id,)
    ).fetchone()

    if existing:
        # updates the existing profile
        conn.execute(
            """
            UPDATE user_profiles SET username = ?, bio = ?, profile_picture = ?
            WHERE user_id = ?
        """,
            (username, bio, profile_picture, user_id),
        )
    else:
        # creates a new profile entry
        conn.execute(
            """
            INSERT INTO user_profiles (user_id, username, bio, profile_picture)
            VALUES (?, ?, ?, ?)
        """,
            (user_id, username, bio, profile_picture),
        )

    conn.commit()
    conn.close()


# retrieves a user's profile based on their user ID
def get_user_profile(user_id):
    conn = get_db_connection()
    profile = conn.execute(
        "SELECT * FROM user_profiles WHERE user_id = ?", (user_id,)
    ).fetchone()
    conn.close()
    return profile


# adding a new book listing for a user
def add_book_listing(user_id, title, author, genre, condition, image_filename):
    conn = get_db_connection()
    conn.execute(
        """
        INSERT INTO book_listings (user_id, title, author, genre, condition, image_filename)
        VALUES (?, ?, ?, ?, ?, ?)
    """,
        (user_id, title, author, genre, condition, image_filename),
    )
    conn.commit()
    conn.close()


# retrieving all book listings created by a specific user
def get_book_listings_by_user(user_id):
    conn = get_db_connection()
    books = conn.execute(
        "SELECT * FROM book_listings WHERE user_id = ?", (user_id,)
    ).fetchall()
    conn.close()
    return books


# retrieving all book listings and the seller's full name
def get_book_listings_with_seller():
    conn = get_db_connection()
    results = conn.execute(
        """
        SELECT bl.*, u.first_name || ' ' || u.last_name AS seller_name
        FROM book_listings bl
        JOIN users u ON bl.user_id = u.id
    """
    ).fetchall()
    conn.close()
    return results


# storing a message sent from one user to another related to a book
def send_message(sender_id, receiver_id, book_id, message):
    conn = get_db_connection()
    conn.execute(
        """
        INSERT INTO messages (sender_id, receiver_id, book_id, message)
        VALUES (?, ?, ?, ?)
        """,
        (sender_id, receiver_id, book_id, message),
    )
    conn.commit()
    conn.close()


# retrieving all messages received by a specific user including sender info & book details
def get_messages_for_user(user_id):
    conn = get_db_connection()
    messages = conn.execute(
        """
        SELECT m.*, u.first_name AS sender_name, b.title AS book_title, b.image_filename
        FROM messages m
        JOIN users u ON m.sender_id = u.id
        JOIN book_listings b ON m.book_id = b.id
        WHERE m.receiver_id = ?
        ORDER BY timestamp DESC
        """,
        (user_id,),
    ).fetchall()
    conn.close()
    return messages


# creating messages table if it doesn't already exist
def create_messages_table():
    conn = get_db_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER NOT NULL,
            receiver_id INTEGER NOT NULL,
            book_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (sender_id) REFERENCES users(id),
            FOREIGN KEY (receiver_id) REFERENCES users(id),
            FOREIGN KEY (book_id) REFERENCES book_listings(id)
        )
    """
    )
    conn.commit()
    conn.close()


# inseting a new message into the messages table
def send_message(sender_id, receiver_id, book_id, message):
    conn = get_db_connection()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        """
        INSERT INTO messages (sender_id, receiver_id, book_id, message, timestamp)
        VALUES (?, ?, ?, ?, ?)
    """,
        (sender_id, receiver_id, book_id, message, timestamp),
    )
    conn.commit()
    conn.close()


# getting the latest conversation threads for a user (grouped by book & sender)
def get_conversations_for_user(user_id):
    conn = get_db_connection()
    conversations = conn.execute(
        """
        SELECT m.*, b.title AS book_title, b.image_filename, u.first_name AS sender_name
        FROM messages m
        JOIN book_listings b ON m.book_id = b.id
        JOIN users u ON m.sender_id = u.id
        WHERE m.receiver_id = ?
        GROUP BY m.book_id, m.sender_id
        ORDER BY m.timestamp DESC
    """,
        (user_id,),
    ).fetchall()
    conn.close()
    return conversations


# getting the full chat history between two users for a specific book
def get_chat_history(user1_id, user2_id, book_id):
    conn = get_db_connection()
    history = conn.execute(
        """
        SELECT m.*, u.first_name AS sender_name
        FROM messages m
        JOIN users u ON m.sender_id = u.id
        WHERE ((sender_id = ? AND receiver_id = ?) OR (sender_id = ? AND receiver_id = ?))
        AND book_id = ?
        ORDER BY m.timestamp
    """,
        (user1_id, user2_id, user2_id, user1_id, book_id),
    ).fetchall()
    conn.close()
    return history


# getting a user record by ID
def get_user_by_id(user_id):
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return user


# getting a book listing by ID
def get_book_by_id(book_id):
    conn = get_db_connection()
    book = conn.execute(
        "SELECT * FROM book_listings WHERE id = ?", (book_id,)
    ).fetchone()
    conn.close()
    return book


# getting all messages exchanged between two users regarding a specific book
def get_messages_between_users(user1_id, user2_id, book_id):
    conn = get_db_connection()
    messages = conn.execute(
        """
        SELECT m.*, u.first_name AS sender_name
        FROM messages m
        JOIN users u ON m.sender_id = u.id
        WHERE ((m.sender_id = ? AND m.receiver_id = ?) OR (m.sender_id = ? AND m.receiver_id = ?))
          AND m.book_id = ?
        ORDER BY m.timestamp ASC
    """,
        (user1_id, user2_id, user2_id, user1_id, book_id),
    ).fetchall()
    conn.close()
    return messages
