# importing Flask application factory function from the app package
from app import create_app

# creates an instance of the Flask app by calling the factory function
# this allows better modularity & easier configuration management
app = create_app()

# this block makes sure the app runs only when this script is executed directly and not when imported
if __name__ == "__main__":
    app.run(debug=True)
