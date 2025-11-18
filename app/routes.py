# import necessary modules & functions
import os
from datetime import datetime
from app.models import get_db_connection
from werkzeug.utils import secure_filename
from app.search import search_books_ml
from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    current_app,
)

# import custom database helper functions from models.py file
from app.models import (
    get_user_by_email,
    register_user,
    validate_login,
    save_user_profile,
    get_user_profile,
    get_book_listings_by_user,
    add_book_listing,
    send_message,
    get_messages_for_user,
)

# defining a Blueprint named 'main' to organize routes
main = Blueprint("main", __name__)


# route for homepage
@main.route("/")
def home():
    return render_template("index.html")


# route for 'My Account' page
@main.route("/myaccount")
def my_account():
    if "user" not in session:  # user not logged in
        return render_template("account.html", logged_in=False)

    user_id = session["user"]["id"]
    listings = get_book_listings_by_user(user_id)
    user_profile = get_user_profile(user_id)
    messages = get_messages_for_user(user_id)

    # getting friend requests (joining with user_profiles to get username & profile pic)
    conn = get_db_connection()
    friend_requests = conn.execute(
        """
        SELECT fr.id, u.id AS sender_id, up.username, up.profile_picture, fr.created_at
        FROM friend_requests fr
        JOIN users u ON fr.sender_id = u.id
        JOIN user_profiles up ON u.id = up.user_id
        WHERE fr.receiver_id = ? AND fr.status = 'pending'
        """,
        (user_id,),
    ).fetchall()
    conn.close()

    # converts each row to a dict & parse `created_at`
    friend_requests = [
        {
            **dict(row),
            "created_at": datetime.strptime(row["created_at"], "%Y-%m-%d %H:%M:%S"),
        }
        for row in friend_requests
    ]

    return render_template(
        "account.html",
        logged_in=True,
        user=session["user"],
        first_name=session["user"]["first_name"],
        listings=listings,
        user_profile=user_profile,
        messages=messages,
        friend_requests=friend_requests,  # pass to template
    )


# static page route for 'Communities'
@main.route("/communities")
def communities():
    # get genre parameter from the query string
    genre = request.args.get("genre")
    conn = get_db_connection()

    posts = []  # list to store retrieved posts
    comments_by_post = {}  # dictionary to group comments by post ID

    if genre:
        # getting all posts matching the genre (case-insensitive) & author names
        posts = conn.execute(
            """
            SELECT community_posts.*, users.first_name, users.last_name
            FROM community_posts
            JOIN users ON community_posts.user_id = users.id
            WHERE LOWER(community_posts.genre) = LOWER(?)
            ORDER BY community_posts.created_at DESC
            """,
            (genre,),
        ).fetchall()

        # extracting post IDs to fetch related comments
        post_ids = [post["id"] for post in posts]
        if post_ids:
            # dynamically build placeholders for SQL query based on number of posts
            placeholders = ",".join("?" for _ in post_ids)
            # get all comments related to the selected posts with commenter name
            comments = conn.execute(
                f"""
                SELECT c.*, u.id AS commenter_id, u.first_name || ' ' || u.last_name AS commenter_name
                FROM comments c
                JOIN users u ON c.user_id = u.id
                WHERE c.post_id IN ({placeholders})
                ORDER BY c.created_at ASC
                """,
                post_ids,
            ).fetchall()

            # group comments by post_id
            for comment in comments:
                comments_by_post.setdefault(comment["post_id"], []).append(comment)

    conn.close()
    # render the communities page with the filtered posts & their comments
    return render_template(
        "communities.html", posts=posts, comments_by_post=comments_by_post
    )


# route to create a new community post
@main.route("/communities/create", methods=["GET", "POST"])
def create_post():
    # checks if user is logged in
    if "user" not in session:
        return redirect(url_for("main.login"))

    if request.method == "POST":
        # get form data submitted by the user
        title = request.form["title"]
        content = request.form["content"]
        genre = request.form["genre"]
        image = request.files.get("image")

        filename = None
        # if an image was uploaded then save it to the uploads folder
        if image and image.filename:
            filename = secure_filename(image.filename)
            image.save(os.path.join("app/static/uploads", filename))

        # get current user info using their email
        user = get_user_by_email(session["user"]["email"])

        # insert the new post into the database
        conn = get_db_connection()
        conn.execute(
            """
            INSERT INTO community_posts (user_id, title, content, genre, image_filename)
            VALUES (?, ?, ?, ?, ?)
        """,
            (user["id"], title, content, genre, filename),
        )
        conn.commit()
        conn.close()

        # redirect to the community page filtered by the selected genre
        return redirect(url_for("main.communities", genre=genre))

    # render the post creation form
    return render_template("create_post.html")


# route to handle comment submission for community posts
@main.route("/communities/comment", methods=["POST"])
def add_comment():
    # require user to be logged in to comment
    if "user" not in session:
        flash("Please log in to comment.", "warning")
        return redirect(url_for("main.login"))

    # get comment data from the form
    post_id = request.form["post_id"]
    content = request.form["content"]

    # insert the comment into the database
    conn = get_db_connection()
    conn.execute(
        """
        INSERT INTO comments (post_id, user_id, content)
        VALUES (?, ?, ?)
        """,
        (post_id, session["user"]["id"], content),
    )
    conn.commit()
    conn.close()

    flash("Comment added successfully!", "success")
    # redirect back to the communities page and preserving the genre filter if it exists
    return redirect(url_for("main.communities", genre=request.args.get("genre", "")))


# static page route for 'About'
@main.route("/about")
def about():
    return render_template("about.html")


# route for user login
@main.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        # retrieves form data
        email = request.form["email"]
        password = request.form["password"]
        # validates login credentials
        if validate_login(email, password):
            # fetches user details from database
            user = get_user_by_email(email)
            # stores user info in session that is used for login state
            session["user"] = {
                "id": user["id"],
                "email": user["email"],
                "first_name": user["first_name"],
            }
            # redirects to user's account page after successful login
            return redirect(url_for("main.my_account"))
        else:
            # shows error message if login failed
            flash("Invalid email or password", "danger")

    # renders login page for GET requests or after a failed login
    return render_template("login.html")


# route for user registration
@main.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        # retrieves registration form data
        first = request.form["first_name"]
        last = request.form["last_name"]
        age = request.form["age"]
        email = request.form["email"]
        password = request.form["password"]

        # checks if user already exists
        if get_user_by_email(email):
            flash("An account with this email already exists.", "danger")
            return redirect(url_for("main.register"))

        # registering a new user
        register_user(first, last, int(age), email, password)
        # flash success message & redirect to login
        flash("Registration successful. Please log in.", "success")
        return redirect(url_for("main.login"))

    return render_template("register.html")


# route for logging out
@main.route("/logout")
def logout():
    # removes 'user' data from session
    session.pop("user", None)
    # shows logout message
    flash("You have been logged out.", "info")
    # clears all session data including flashed messages
    session.clear()
    # redirects back to login page
    return redirect(url_for("main.login"))


# route to handle profile update form
@main.route("/update_profile", methods=["POST"])
def update_profile():
    # ensures the user is logged in
    if "user" not in session:
        flash("Please log in to update your profile.", "warning")
        return redirect(url_for("main.login"))

    # gets the current user ID from session
    user_id = session["user"]["id"]
    # gets form data
    username = request.form["username"]
    bio = request.form["bio"]
    profile_pic = request.files.get("profile_picture")
    # save uploaded profile picture if present
    filename = None
    if profile_pic and profile_pic.filename != "":
        filename = secure_filename(profile_pic.filename)
        profile_pic.save(os.path.join(current_app.config["UPLOAD_FOLDER"], filename))

    # save profile data to database
    save_user_profile(user_id, username, bio, filename)
    # shows success message & redirects
    flash("Profile updated!", "success")
    return redirect(url_for("main.my_account"))


# route to view another user's profile
@main.route("/profile/<int:user_id>")
def view_profile(user_id):
    conn = get_db_connection()
    # fetches profile data of the user being viewed
    user_profile = conn.execute(
        "SELECT * FROM user_profiles WHERE user_id = ?", (user_id,)
    ).fetchone()
    # fetches all book listings of that user
    books = conn.execute(
        "SELECT * FROM book_listings WHERE user_id = ?", (user_id,)
    ).fetchall()
    conn.close()

    # gets the currently logged-in user's ID
    current_user_id = session.get("user_id")
    # checks if the logged-in user is friends with the viewed user
    is_friend = check_if_friends(current_user_id, user_id)
    # checks if the current user has received a friend request from the viewed user
    friend_request_sent = check_if_friend_request_received(current_user_id, user_id)
    # checks if a friend request is already pending from current user to the viewed user
    request_pending = check_if_request_pending(current_user_id, user_id)

    # renders the profile page with relevant data
    return render_template(
        "profile.html",
        user_profile=user_profile,
        books=books,
        is_friend=is_friend,
        friend_request_sent=friend_request_sent,
        request_pending=request_pending,
    )


# checks if two users are friends
def check_if_friends(current_user_id, user_id):
    conn = get_db_connection()
    # query the database for friend request between the two users with 'accepted' status
    friendship = conn.execute(
        """
        SELECT * FROM friend_requests
        WHERE (
            (sender_id = ? AND receiver_id = ?)
            OR (sender_id = ? AND receiver_id = ?)
        )
        AND status = 'accepted'
        """,
        (current_user_id, user_id, user_id, current_user_id),
    ).fetchone()
    conn.close()
    # returns True if friendship exists or False otherwise
    return friendship is not None


# checks if the current user has received a friend request from another user
def check_if_friend_request_received(current_user, other_user):
    conn = get_db_connection()
    # checks if other_user has sent a friend request to current_user
    request = conn.execute(
        "SELECT * FROM friend_requests WHERE sender_id = ? AND receiver_id = ?",
        (other_user, current_user),
    ).fetchone()
    conn.close()
    # returns True if a request is found
    return request is not None


# checks if the current user has already sent a friend request to another user
def check_if_request_pending(current_user, other_user):
    conn = get_db_connection()
    # checks if current_user has sent a friend request to other_user
    request = conn.execute(
        "SELECT * FROM friend_requests WHERE sender_id = ? AND receiver_id = ?",
        (current_user, other_user),
    ).fetchone()
    conn.close()
    # returns True if a request exists
    return request is not None


# route to send a friend request to a user
@main.route("/send_friend_request/<int:user_id>", methods=["POST"])
def send_friend_request(user_id):
    # gets the ID of the currently logged-in user from the session
    sender_id = session.get("user", {}).get("id")
    # ensures the sender is logged in & not sending a request to themselves
    if sender_id and sender_id != user_id:
        conn = get_db_connection()
        # inserts a new pending friend request into the database
        conn.execute(
            "INSERT INTO friend_requests (sender_id, receiver_id, status) VALUES (?, ?, ?)",
            (sender_id, user_id, "pending"),  # ✅ Ensure status is set
        )
        conn.commit()
        conn.close()
    # redirects to the viewed user's profile page
    return redirect(url_for("main.view_profile", user_id=user_id))


# route to decline a received friend request
@main.route("/decline_friend_request/<int:request_id>", methods=["POST"])
def decline_friend_request(request_id):
    # gets the ID of the currently logged-in user
    current_user_id = session.get("user", {}).get("id")
    # redirects to login page if the user is not logged in
    if not current_user_id:
        return redirect(url_for("main.login"))

    conn = get_db_connection()
    # deletes the friend request only if the logged-in user is the receiver
    conn.execute(
        "DELETE FROM friend_requests WHERE id = ? AND receiver_id = ?",
        (request_id, current_user_id),
    )
    conn.commit()
    conn.close()

    # redirects back to the 'My Account' page after declining
    return redirect(url_for("main.my_account"))


# route to accept a friend request
@main.route("/accept_friend_request/<int:request_id>", methods=["POST"])
def accept_friend_request(request_id):
    current_user_id = session.get("user", {}).get("id")
    # redirects to login if user is not logged in
    if not current_user_id:
        return redirect(url_for("main.login"))

    conn = get_db_connection()

    # updates the friend request status to 'accepted'
    conn.execute(
        "UPDATE friend_requests SET status = 'accepted' WHERE id = ? AND receiver_id = ?",
        (request_id, current_user_id),
    )
    conn.commit()
    conn.close()

    # redirects to My Account after accepting
    return redirect(url_for("main.my_account"))


# route to list a new book
@main.route("/list_book", methods=["POST"])
def list_book():
    # ensures user is logged in before listing a book
    if "user" not in session:
        flash("Please log in to list a book.", "warning")
        return redirect(url_for("main.login"))

    # gets form data
    title = request.form["title"]
    author = request.form["author"]
    genre = request.form["genre"]
    condition = request.form["condition"]
    image = request.files.get("book_image")

    # saves uploaded book image if present
    filename = None
    if image and image.filename != "":
        filename = secure_filename(image.filename)
        image.save(os.path.join(current_app.config["UPLOAD_FOLDER"], filename))

    # saves book listing in database
    add_book_listing(session["user"]["id"], title, author, genre, condition, filename)
    flash("Book listed successfully!", "success")
    return redirect(url_for("main.my_account"))


# route to delete a book listing
@main.route("/delete_listing/<int:listing_id>", methods=["POST"])
def delete_listing(listing_id):
    if "user" not in session:
        return redirect(url_for("main.login"))

    conn = get_db_connection()

    # deletes listing only if it belongs to the logged-in user
    conn.execute(
        """
        DELETE FROM book_listings
        WHERE id = ?
        AND user_id = (SELECT id FROM users WHERE email = ?)
    """,
        (listing_id, session["user"].get("email")),
    )

    conn.commit()
    conn.close()
    return redirect(url_for("main.my_account"))


# route to handle book search using ML/NLP
@main.route("/search")
def search_books():
    query = request.args.get("query", "")
    # Call custom search function. TF-IDF + fuzzy match
    results = search_books_ml(query)
    # renders search results page
    return render_template("results.html", query=query, results=results)


# route to send message from account page
@main.route("/send_message", methods=["POST"])
def send_message_route():
    if "user" not in session:
        flash("Please log in to send a message.", "warning")
        return redirect(url_for("main.login"))

    # extracts message details from form
    sender_id = session["user"]["id"]
    receiver_id = request.form["receiver_id"]
    book_id = request.form["book_id"]
    message = request.form["message"]

    # saves message in database
    send_message(sender_id, receiver_id, book_id, message)
    flash("Message sent successfully!", "success")
    return redirect(url_for("main.my_account"))


# route to delete a message
@main.route("/delete_message/<int:message_id>", methods=["POST"])
def delete_message(message_id):
    if "user" not in session:
        return redirect(url_for("main.login"))

    conn = get_db_connection()
    # allows deletion if user is either the sender or receiver
    conn.execute(
        """
        DELETE FROM messages
        WHERE id = ?
        AND (sender_id = (SELECT id FROM users WHERE email = ?) OR receiver_id = (SELECT id FROM users WHERE email = ?))
    """,
        (message_id, session["user"]["email"], session["user"]["email"]),
    )
    conn.commit()
    conn.close()

    return redirect(url_for("main.my_account"))


# chat route
@main.route("/chat/<int:buyer_id>/<int:book_id>")
def chat(buyer_id, book_id):
    if "user" not in session:
        return redirect(url_for("main.login"))

    current_user_id = session["user"]["id"]
    conn = get_db_connection()

    # retrieves messages for the given book & users
    messages = conn.execute(
        """
        SELECT * FROM messages
        WHERE book_id = ?
          AND ((sender_id = ? AND receiver_id = ?) OR (sender_id = ? AND receiver_id = ?))
        ORDER BY timestamp ASC
        """,
        (book_id, current_user_id, buyer_id, buyer_id, current_user_id),
    ).fetchall()

    # gets book title
    book = conn.execute(  # get book & buyer details for display
        "SELECT title FROM book_listings WHERE id = ?", (book_id,)
    ).fetchone()
    book_title = book["title"] if book else "Book"

    # gets buyer name
    buyer = conn.execute(
        "SELECT first_name FROM users WHERE id = ?", (buyer_id,)
    ).fetchone()
    buyer_name = buyer["first_name"] if buyer else "User"

    conn.close()

    # renders chat template with conversation history
    return render_template(
        "chat.html",
        buyer_id=buyer_id,
        book_id=book_id,
        buyer_name=buyer_name,
        book_title=book_title,
        messages=messages,
        current_user_id=current_user_id,
    )


# route to send a message from chat page
@main.route("/chat/send_message", methods=["POST"])
def send_chat_message():
    if "user" not in session:
        return redirect(url_for("main.login"))

    # extract message details from form
    sender_id = session["user"]["id"]
    receiver_id = request.form["receiver_id"]
    book_id = request.form["book_id"]
    message = request.form["message"]

    # saves message & redirect back to chat page
    send_message(sender_id, receiver_id, book_id, message)
    return redirect(url_for("main.chat", buyer_id=receiver_id, book_id=book_id))
