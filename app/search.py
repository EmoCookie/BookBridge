# importing necessary libraries
import string
import numpy as np
from sklearn.feature_extraction.text import (
    TfidfVectorizer,
)  # for converting text to numerical vectors
from sklearn.metrics.pairwise import (
    cosine_similarity,
)  # for computing similarity between vectors
from fuzzywuzzy import fuzz  # for fuzzy matching to handle typos or approximate matches

from nltk.corpus import stopwords  # common words to be filtered out
from nltk.stem import WordNetLemmatizer  # to reduce words to their base form
from nltk.tokenize import word_tokenize  # to split text into individual words

from app.models import get_db_connection  # function to connect to SQLite DB

# global variables to cache the TF-IDF vectors & book data for efficiency
cached_vectors = None  # stores the TF-IDF vectors for all books
cached_books = None  # stores all book records from the database
vectorizer = None  # TF-IDF vectorizer instance

# NLTK setup processing
stop_words = set(stopwords.words("english"))  # english stopwords for filtering
lemmatizer = WordNetLemmatizer()  # lemmatizer instance


def preprocess_text(text):
    """clean & preprocess input text for lowercase, remove punctuation & stopwords & lemmatize"""
    text = text.lower().translate(str.maketrans("", "", string.punctuation))
    tokens = word_tokenize(text)
    return " ".join(
        [lemmatizer.lemmatize(word) for word in tokens if word not in stop_words]
    )


def get_all_book_listings():
    """retrieving all book listings from the database"""
    conn = get_db_connection()
    results = conn.execute("SELECT * FROM book_listings").fetchall()
    conn.close()
    return results


def build_search_index():
    """building & caching TF-IDF vectors for all books in the database to improve search speed & accuracy"""
    global cached_vectors, cached_books, vectorizer

    all_books = get_all_book_listings()
    cached_books = all_books  # caches the original books for later lookup
    # combining relevant fields for each book into a single string for vectorization
    combined_texts = [
        preprocess_text(
            f"{book['title']} {book['author']} {book['genre']} {book['condition']}"
        )
        for book in all_books
    ]
    # creating TF-IDF vectors for all book entries
    vectorizer = TfidfVectorizer()
    cached_vectors = vectorizer.fit_transform(combined_texts)


def fuzzy_score(query, book):
    """fuzzy match score between query & combined book info using the FuzzyWuzzy partial_ratio."""
    book_text = f"{book['title']} {book['author']} {book['genre']}"
    return fuzz.partial_ratio(query.lower(), book_text.lower()) / 100


def search_books_ml(query):
    # hybrid search combining TF-IDF cosine similarity, fuzzy matching & returning a list of books ranked by relevance
    global cached_vectors, cached_books, vectorizer
    # builds index if not already cached
    if cached_vectors is None or cached_books is None:
        build_search_index()
    # preprocess the query & get its vector
    processed_query = preprocess_text(query)
    query_vector = vectorizer.transform([processed_query])
    similarities = cosine_similarity(query_vector, cached_vectors).flatten()

    top_matches = []  # lists to store relevant results
    for i, book in enumerate(cached_books):
        tfidf_score = similarities[i]  # similarity based on meaning
        fuzzy = fuzzy_score(query, book)  # similarity based on character match

        # weighted combination of both scores
        combined_score = (0.75 * tfidf_score) + (0.25 * fuzzy)
        # applying threshold to filter out irrelevant results
        if combined_score > 0.3:
            book_dict = dict(book)  # converts SQLite Row to dictionary
            book_dict["score"] = round(combined_score, 3)
            top_matches.append(book_dict)
    # sorting results by relevance
    top_matches.sort(key=lambda x: x["score"], reverse=True)
    return top_matches
