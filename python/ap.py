import hashlib
import mysql.connector
from flask import Flask, request, jsonify, redirect, url_for, render_template


app = Flask(__name__, template_folder='../html', static_folder='../html/static')

# Database connection setup
db_config = {
    "host": "localhost",
    "user": "root",
    "password": "",
    "database": "ebdb"
}

# Route for handling the registration form submission
@app.route('/register', methods=['POST'])
def register_user():
    try:
        # Get form data
        fname = request.form['fname']
        lname = request.form['lname']
        contacts = request.form['contacts']
        username = request.form['user']
        password = request.form['pass']
        role = request.form['role']

        hashed_password = hashlib.sha256(password.encode()).hexdigest()

        # Connect to the database
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()

        # Insert the data into the user table
        query = """
            INSERT INTO user (firstName, lastName, contacts, username, password, role)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        values = (fname, lname, contacts, username, hashed_password, role)

        # cursor.execute(query, (fname, lname, contacts, username, password, role))
        cursor.execute(query, values)
        connection.commit()

        cursor.close()
        connection.close()

        return jsonify({"message": "User registered successfully!"}), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Route for rendering the registration form
@app.route('/')
def registration_form():
    return render_template('emp_reg.html')  # Use the updated HTML file name
    
if __name__ == '__main__':
    app.run(debug=True)
    
# # Route for rendering the registration form (optional)
# @app.route('/')
# def registration_form():
#     return render_template('emp_reg.html')

# # Route to display the login page (GET request)
# @app.route('/login', methods=['GET'])
# def login_page():
#     return render_template('login.html')

# # Route for handling user login
# @app.route('/login', methods=['POST'])
# def login_user():
#     try:
#         username = request.form['username']
#         password = request.form['password']

#         hashed_password = hashlib.sha256(password.encode()).hexdigest()

#         # Connect to the database
#         connection = mysql.connector.connect(**db_config)
#         cursor = connection.cursor()

#         # Query to check user credentials
#         query = "SELECT password, role FROM user WHERE username = %s"
#         cursor.execute(query, (username,))
#         result = cursor.fetchone()

#         cursor.close()
#         connection.close()

#         # Check if user exists and password matches
#         if result and result[0] == hashed_password:
#             role = result[1]
#             if role == "Admin":
#                 return redirect(url_for('admin_page'))
#             elif role == "Employee":
#                 return redirect(url_for('employee_page'))
#             else:
#                 return "Invalid role, Contact administrator.", 403
            
#         return "Invalid username or password", 401
    
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500
# # Route for admin page
# @app.route('/admin')
# def admin_page():
#     return render_template('admin.html')

# # Route for employee page
# @app.route('/employee')
# def employee_page():
#     return render_template('emp.html')

