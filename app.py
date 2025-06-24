import hashlib
# import mysql.connector
from flask import Flask, request, redirect, url_for, render_template, session, jsonify
from decimal import Decimal
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Database connection setup
# db_config = {
#     "host": "localhost",
#     "user": "root",
#     "password": "",
#     "database": "ebdb"
# }

# First page to show
@app.route('/')
def home():
    return render_template('login.html')

# Route for handling user login
@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']

    hashed_password = hashlib.sha256(password.encode()).hexdigest()

    # Connect to the database
    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor(dictionary=True)

    # Query to check user credentials
    query = "SELECT * FROM user WHERE username = %s AND password = %s"
    cursor.execute(query, (username, hashed_password))
    user = cursor.fetchone()

    if user:
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        update_login_query = "UPDATE user SET last_login = %s WHERE user_id = %s"
        cursor.execute(update_login_query, (current_time, user['user_id']))
        
        log_query = "INSERT INTO user_logs (user_id, action) VALUES (%s, 'login')"
        cursor.execute(log_query, (user['user_id'],))
        connection.commit()

        session['username'] = user['username']
        session['role'] = user['role']

        cursor.close()
        connection.close()

        # Redirect based on role
        if user['role'] == 'Admin':
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('emp_dashboard'))
    else:
        cursor.close()
        connection.close()
        return render_template('message.html', message="Invalid credentials, please try again.", redirect_url='/')
    
# Route for forgot password
@app.route('/forgot_pass', methods=['GET',' POST'])
def forgot_password():
    return render_template('frgt_pass.html')

@app.route('/forgot_pass_submit', methods=['POST'])
def forgot_pass_submit():
    username = request.form['username']

    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor(dictionary=True)

    query = "SELECT * FROM user WHERE username = %s"
    cursor.execute(query, (username,))
    user = cursor.fetchone()

    cursor.close()
    connection.close()

    if not user:
        return render_template('message.html', message="Username does not exist.", redirect_url='/forgot_pass')

    session['forgot_username'] = username
    return redirect(url_for('security_questions', username=username))

@app.route('/security_questions')
def security_questions():
    return render_template('question.html')

@app.route('/verify_security_questions', methods=['POST'])
def verify_security_questions():
    username = request.form['username']
    answer1 = request.form['answer1'].strip().lower()
    answer2 = request.form['answer2'].strip().lower()

    # Security question answers
    correct_answer1 = "blue"
    correct_answer2 = "iphone"

    if answer1 == correct_answer1 and answer2 == correct_answer2:
        return redirect(url_for('reset_password', username=username))
    else:
        return render_template('message.html', message="Incorrect answers.", redirect_url=url_for('security_questions', username=username))
    
@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'GET':
        username=request.args.get('username')
        return render_template('reset_pass.html', username=username)
    
    username = request.form['username']
    new_password = request.form['new_password']
    confirm_password = request.form['confirm_password']

    if new_password != confirm_password:
        return render_template('message.html', message="Passwords do not match.", redirect_url=url_for('reset_password', username=username))
    
    hashed_password = hashlib.sha256(new_password.encode()).hexdigest()

    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor()

    query = "UPDATE user SET password = %s WHERE username = %s"
    cursor.execute(query, (hashed_password, username))
    connection.commit()

    cursor.close()
    connection.close()

    return render_template('message.html', message="Password Successfully Reset", redirect_url='/')
    
# Route for admin page
@app.route('/admin')
def admin_dashboard():
    if 'username' in session and session['role'] == 'Admin':
        return render_template('admin.html', username=session['username'])
    return redirect(url_for('home'))

# Route for employee page
@app.route('/employee')
def emp_dashboard():
    if 'username' in session and session['role'] == 'Employee':
        return render_template('emp.html', username=session['username'])
    return redirect(url_for('home'))

# Registration page from Admin panel
@app.route('/register')
def register_page():
    if 'username' in session and session['role'] == 'Admin':
        return render_template('register.html')
    return redirect(url_for('home'))

# Employee registration
@app.route('/register_emp', methods=['GET','POST'])
def register_emp():
    if request.method == 'GET':
        if 'username' in session and session['role'] == 'Admin':
            return render_template('emp_reg.html')
        return redirect(url_for('home'))
        
    try:
        # Get form data
        fname = request.form['fname']
        lname = request.form['lname']
        contacts = request.form['contacts']
        username = request.form['user']
        password = request.form['pass']
        role = request.form['role']

        hashed_password = hashlib.sha256(password.encode()).hexdigest()

        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()

        # Insert the data into the user table
        query = """
            INSERT INTO user (firstName, lastName, contacts, username, password, role)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        values = (fname, lname, contacts, username, hashed_password, role)

        cursor.execute(query, values)
        connection.commit()

        cursor.close()
        connection.close()

        return redirect(url_for('register_emp'))
    
    except Exception as e:
        return f"Error: {e}"
    
# Product registration
@app.route('/register_prod', methods=['GET','POST'])
def register_prod():
    if request.method == 'GET':
        if 'username' in session and session['role'] == 'Admin':
            return render_template('prd_reg.html')
        return redirect(url_for('home'))
        
    try:
        # Get form data
        prod_id = request.form['prod_id']
        prod_name = request.form['prod_name']
        stock = request.form['stock']
        price = request.form['price']
        category = request.form['category']

        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()

        # Insert the data into the user table
        query = """
            INSERT INTO prod (prod_id, prod_name, stock, price, category)
            VALUES (%s, %s, %s, %s, %s)
        """
        values = (prod_id, prod_name, stock, price, category)

        cursor.execute(query, values)
        connection.commit()

        cursor.close()
        connection.close()

        return redirect(url_for('register_prod'))
    
    except Exception as e:
        return f"Error: {e}"

# Inventory page
@app.route('/inventory')
def inventory_page():
    if 'username' in session:
        try:
            search_query = request.args.get('search', '')

            connection = mysql.connector.connect(**db_config)
            cursor = connection.cursor(dictionary=True)

            if search_query:
                query = "SELECT * FROM prod WHERE prod_name LIKE %s OR category LIKE %s"
                cursor.execute(query, ('%' + search_query + '%', '%' + search_query + '%'))
            else:
                query = "SELECT * FROM prod"
                cursor.execute(query)

            products = cursor.fetchall()

            # Add stock status for each product
            for product in products:
                stock = product['stock']
                if stock <= 15:
                    product['status'] = 'Low Stock'
                elif stock >= 30:
                    product['status'] = 'Over Stock'
                else:
                    product['status'] = 'Normal'

            cursor.close()
            connection.close()

            # Pass products to the template
            return render_template('inventory.html', products=products)

        except Exception as e:
            return f"Error: {e}"
        
    return redirect(url_for('home'))

# Inventory page for Employee
@app.route('/inventory_emp')
def inventory_emp():
    if 'username' in session:
        try:
            search_query = request.args.get('search', '')

            connection = mysql.connector.connect(**db_config)
            cursor = connection.cursor(dictionary=True)

            if search_query:
                query = "SELECT * FROM prod WHERE prod_name LIKE %s OR category LIKE %s"
                cursor.execute(query, ('%' + search_query + '%', '%' + search_query + '%'))
            else:
                query = "SELECT * FROM prod"
                cursor.execute(query)

            products = cursor.fetchall()

            # Add stock status for each product
            for product in products:
                stock = product['stock']
                if stock <= 15:
                    product['status'] = 'Low Stock'
                elif stock >= 50:
                    product['status'] = 'Over Stock'
                else:
                    product['status'] = 'Normal'

            cursor.close()
            connection.close()

            # Pass products to the template
            return render_template('emp_inv.html', products=products)

        except Exception as e:
            return f"Error: {e}"
        
    return redirect(url_for('home'))

# Sales page from Admin panel
@app.route('/sales')
def sales_page():
    if 'username' in session and session['role'] == 'Admin':
        return render_template('sales.html')
    return redirect(url_for('home'))

# Customer Page
@app.route('/customer_page', methods=['POST', 'GET'])
def customer_page():
    if request.method == 'POST':
        session['customer_name'] = request.form['customer']
        session['email'] = request.form['email']
        session['contacts'] = request.form['contacts']
        session['age'] = request.form.get('age') or None
        session['birthdate'] = request.form.get('birthdate') or None
        session['sex'] = request.form.get('sex') or None
        session['tel_no'] = request.form.get('tel_no') or None
        session['street'] = request.form.get('street') or None
        session['city'] = request.form.get('city') or None
        session['zip'] = request.form.get('zip') or None

        return redirect(url_for('order_page'))
    
    return render_template('customer.html')

# Order Page
@app.route('/order_page', methods=['GET', 'POST'])
def order_page():
    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor(dictionary=True)

    if request.method == 'POST':
        data = request.get_json()
        print("Received order data", data)

        if not data or len(data) == 0:
            return jsonify({"error": "Invalid data"}), 400

        if request.method == 'POST':
            data = request.get_json()
            print("Received order data", data)

            if not data or len(data) == 0:
                return jsonify({"error": "Invalid data"}), 400

            # Initialize if not already
            if 'order_list' not in session:
                session['order_list'] = []

            # Build a lookup map of existing items
            existing_items = {item['prod_id']: item for item in session['order_list']}

            connection = mysql.connector.connect(**db_config)
            cursor = connection.cursor(dictionary=True)

            for item in data:
                prod_id = item['prod_id']
                quantity = int(item['quantity'])

                cursor.execute("SELECT * FROM prod WHERE prod_id = %s", (prod_id,))
                product = cursor.fetchone()
                if not product:
                    continue

                if product['stock'] <= 0:
                    return jsonify({"error": f"{product['prod_name']} is out of stock."}), 400
                if quantity > product['stock']:
                    return jsonify({"error": f"Only {product['stock']} item(s) of {product['prod_name']} available."}), 400

                if prod_id in existing_items:
                    # Update quantity and total
                    existing_items[prod_id]['quantity'] += quantity
                    existing_items[prod_id]['total_price'] = existing_items[prod_id]['quantity'] * existing_items[prod_id]['unit_price']
                else:
                    # Add new item
                    existing_items[prod_id] = {
                        'prod_id': prod_id,
                        'prod_name': product['prod_name'],
                        'quantity': quantity,
                        'unit_price': float(product['price']),
                        'total_price': float(product['price']) * quantity
                    }

            session['order_list'] = list(existing_items.values())
            session['order_total'] = sum(item['total_price'] for item in session['order_list'])

            cursor.close()
            connection.close()

            return jsonify({"message": "Order received", "redirect": "/checkout_page"})
    else:
        if 'order_list' not in session:
            session['order_list'] = []

        cursor.execute("SELECT prod_id, prod_name, stock, price, category FROM prod")
        products = cursor.fetchall()
        cursor.close()
        connection.close()
        return render_template('order.html', products=products)
    
@app.route('/check_existing_order')
def check_existing_order():
    exists = 'order_list' in session and len(session['order_list']) > 0
    return jsonify({'exists': exists})

# Checkout Page
@app.route('/checkout_page')
def checkout_page():
    order_list = session.get('order_list', [])
    total_cash_payment = sum(item['quantity'] * item['unit_price'] for item in order_list)
    return render_template('checkout.html', order_list=order_list, total_cash_payment=total_cash_payment)

# Save all data
@app.route('/submit_checkout', methods=['POST'])
def submit_checkout():
    customer_name = request.form.get('customer_name')
    email = request.form.get('email')
    contacts = request.form.get('contacts')
    total_amount = request.form.get('total_amount')
    payment_amount = float(request.form.get('payment', 0))
    change_amount = float(request.form.get('change', 0))
    age = request.form.get('age')
    birthdate = request.form.get('birthdate')
    sex = request.form.get('sex')
    tel_no = request.form.get('tel_no')
    street = request.form.get('street')
    city = request.form.get('city')
    zip_code = request.form.get('zip')

    # Multiple values (for each product row)
    prod_ids = request.form.getlist('prod_id')
    if not prod_ids:
        return "Cannot checkout with an empty table.", 400
    
    quantities = request.form.getlist('quantity')
    unit_prices = request.form.getlist('unit_price')

    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor()

    try:
        insert_customer = """
            INSERT INTO customer 
            (customer_name, email, contacts, age, birthdate, sex, tel_no, street, city, zip)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(insert_customer, (customer_name, email, contacts, age, birthdate, sex,
            tel_no, street, city, zip_code))
        customer_id = cursor.lastrowid

        insert_order = """
            INSERT INTO orders (customer_id, order_date, total_amount, payment_amount, change_amount)
            VALUES (%s, NOW(), %s, %s, %s)
        """
        cursor.execute(insert_order, (customer_id, total_amount, payment_amount, change_amount))
        order_id = cursor.lastrowid

        for i in range(len(prod_ids)):
            prod_id = prod_ids[i]
            quantity = int(quantities[i])
            unit_price = float(unit_prices[i])
            total_price = quantity * unit_price

            insert_checkout = """
                INSERT INTO checkout (order_id, product_id, quantity, unit_price, total_price)
                VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(insert_checkout, (order_id, prod_id, quantity, unit_price, total_price))

            update_stock = """
                UPDATE prod
                SET stock = stock - %s
                WHERE prod_id = %s AND stock >= %s
            """
            cursor.execute(update_stock, (quantity, prod_id, quantity))

        connection.commit()
        session['latest_order_id'] = order_id
        session.pop('order_list', None)
        return redirect(url_for('receipt_page'))

    except Exception as e:
        connection.rollback()
        return f"Error during checkout: {e}"

    finally:
        cursor.close()
        connection.close()

@app.route('/remove_checkout_item/<int:prod_id>', methods=['POST'])
def remove_checkout_item(prod_id):
    order_list = session.get('order_list', [])
    updated_list = [item for item in order_list if int(item['prod_id']) != prod_id]
    session['order_list'] = updated_list
    session['order_total'] = sum(item['quantity'] * item['unit_price'] for item in updated_list)
    return jsonify(success=True, new_total=session['order_total'])

@app.route('/receipt')
def receipt_page():
    order_id = session.get('latest_order_id')
    if not order_id:
        return redirect(url_for('sales_page'))

    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor(dictionary=True)

    # Get order info
    cursor.execute("""
        SELECT o.order_id, o.order_date, o.total_amount, o.payment_amount, o.change_amount,
           c.customer_name, c.email, c.contacts
        FROM orders o
        JOIN customer c ON o.customer_id = c.customer_id
        WHERE o.order_id = %s
    """, (order_id,))
    order_info = cursor.fetchone()

    # Compute VAT
    vat_rate = 0.12
    total_amount = float(order_info['total_amount'])
    vatable_sales = round(total_amount / (1 + vat_rate), 2)
    vat_amount = round(total_amount - vatable_sales, 2)

    order_info['vatable_sales'] = vatable_sales
    order_info['vat_amount'] = vat_amount

    # Get item details
    cursor.execute("""
        SELECT p.prod_name, ch.quantity, ch.unit_price, ch.total_price
        FROM checkout ch
        JOIN prod p ON ch.product_id = p.prod_id
        WHERE ch.order_id = %s
    """, (order_id,))
    items = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template('receipt.html', order=order_info, items=items)

# Sales page from Employee
@app.route('/sales_emp')
def sales_emp():
    if 'username' in session and session['role'] == 'Employee':
        return render_template('emp_sale.html')
    return redirect(url_for('home'))

@app.route('/customer_emp', methods=['POST', 'GET'])
def customer_emp():
    if request.method == 'POST':
        session['customer_name'] = request.form['customer']
        session['email'] = request.form['email']
        session['contacts'] = request.form['contacts']
        session['age'] = request.form.get('age') or None
        session['birthdate'] = request.form.get('birthdate') or None
        session['sex'] = request.form.get('sex') or None
        session['tel_no'] = request.form.get('tel_no') or None
        session['street'] = request.form.get('street') or None
        session['city'] = request.form.get('city') or None
        session['zip'] = request.form.get('zip') or None

        return redirect(url_for('order_emp'))
    
    return render_template('emp_customer.html')

@app.route('/order_emp', methods=['GET','POST'])
def order_emp():
    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor(dictionary=True)

    if request.method == 'POST':
        data = request.get_json()
        print("Recieved order data", data)

        if not data or len(data) == 0:
            return jsonify({"error": "Invalid data"}), 400

        if request.method == 'POST':
            data = request.get_json()
            print("Received order data", data)

            if not data or len(data) == 0:
                return jsonify({"error": "Invalid data"}), 400

            # Initialize if not already
            if 'order_list' not in session:
                session['order_list'] = []

            # Build a lookup map of existing items
            existing_items = {item['prod_id']: item for item in session['order_list']}

            connection = mysql.connector.connect(**db_config)
            cursor = connection.cursor(dictionary=True)

            for item in data:
                prod_id = item['prod_id']
                quantity = int(item['quantity'])

                cursor.execute("SELECT * FROM prod WHERE prod_id = %s", (prod_id,))
                product = cursor.fetchone()
                if not product:
                    continue

                if product['stock'] <= 0:
                    return jsonify({"error": f"{product['prod_name']} is out of stock."}), 400
                if quantity > product['stock']:
                    return jsonify({"error": f"Only {product['stock']} item(s) of {product['prod_name']} available."}), 400

                if prod_id in existing_items:
                    # Update quantity and total
                    existing_items[prod_id]['quantity'] += quantity
                    existing_items[prod_id]['total_price'] = existing_items[prod_id]['quantity'] * existing_items[prod_id]['unit_price']
                else:
                    # Add new item
                    existing_items[prod_id] = {
                        'prod_id': prod_id,
                        'prod_name': product['prod_name'],
                        'quantity': quantity,
                        'unit_price': float(product['price']),
                        'total_price': float(product['price']) * quantity
                    }

            session['order_list'] = list(existing_items.values())
            session['order_total'] = sum(item['total_price'] for item in session['order_list'])

            cursor.close()
            connection.close()

            return jsonify({"message": "Order received", "redirect": "/checkout_page"})
    else:
        if 'order_list' not in session:
            session['order_list'] = []

        cursor.execute("SELECT prod_id, prod_name, stock, price, category FROM prod")
        products = cursor.fetchall()
        cursor.close()
        connection.close()
        return render_template('emp_purchase.html', products=products)

@app.route('/checkout_emp')
def checkout_emp():
    order_list = session.get('order_list', [])
    total_cash_payment = sum(item['quantity'] * item['unit_price'] for item in order_list)
    return render_template('emp_checkout.html', order_list=order_list, total_cash_payment=total_cash_payment)

@app.route('/submit_checkout_emp', methods=['POST'])
def submit_checkout_emp():
    customer_name = request.form.get('customer_name')
    email = request.form.get('email')
    contacts = request.form.get('contacts')
    total_amount = request.form.get('total_amount')
    payment_amount = float(request.form.get('payment', 0))
    change_amount = float(request.form.get('change', 0))
    age = request.form.get('age')
    birthdate = request.form.get('birthdate')
    sex = request.form.get('sex')
    tel_no = request.form.get('tel_no')
    street = request.form.get('street')
    city = request.form.get('city')
    zip_code = request.form.get('zip')

    prod_ids = request.form.getlist('prod_id')
    if not prod_ids:
        return "Cannot checkout with an empty table.", 400
    
    quantities = request.form.getlist('quantity')
    unit_prices = request.form.getlist('unit_price')

    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor()

    try:
        insert_customer = """
            INSERT INTO customer 
            (customer_name, email, contacts, age, birthdate, sex, tel_no, street, city, zip)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(insert_customer, (customer_name, email, contacts, age, birthdate, sex,
            tel_no, street, city, zip_code))
        customer_id = cursor.lastrowid

        insert_order = """
            INSERT INTO orders (customer_id, order_date, total_amount, payment_amount, change_amount)
            VALUES (%s, NOW(), %s, %s, %s)
        """
        cursor.execute(insert_order, (customer_id, total_amount, payment_amount, change_amount))
        order_id = cursor.lastrowid

        for i in range(len(prod_ids)):
            prod_id = prod_ids[i]
            quantity = int(quantities[i])
            unit_price = float(unit_prices[i])
            total_price = quantity * unit_price

            insert_checkout = """
                INSERT INTO checkout (order_id, product_id, quantity, unit_price, total_price)
                VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(insert_checkout, (order_id, prod_id, quantity, unit_price, total_price))

            update_stock = """
                UPDATE prod
                SET stock = stock - %s
                WHERE prod_id = %s AND stock >= %s
            """
            cursor.execute(update_stock, (quantity, prod_id, quantity))

        connection.commit()
        session['latest_order_id'] = order_id
        session.pop('order_list', None)
        return redirect(url_for('receipt_emp'))

    except Exception as e:
        connection.rollback()
        return f"Error during checkout: {e}"

    finally:
        cursor.close()
        connection.close()

@app.route('/receipt_emp')
def receipt_emp():
    order_id = session.get('latest_order_id')
    if not order_id:
        return redirect(url_for('sales_emp'))

    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor(dictionary=True)

    cursor.execute("""
        SELECT o.order_id, o.order_date, o.total_amount, o.payment_amount, o.change_amount,
           c.customer_name, c.email, c.contacts
        FROM orders o
        JOIN customer c ON o.customer_id = c.customer_id
        WHERE o.order_id = %s
    """, (order_id,))
    order_info = cursor.fetchone()

    vat_rate = 0.12
    total_amount = float(order_info['total_amount'])
    vatable_sales = round(total_amount / (1 + vat_rate), 2)
    vat_amount = round(total_amount - vatable_sales, 2)

    order_info['vatable_sales'] = vatable_sales
    order_info['vat_amount'] = vat_amount

    cursor.execute("""
        SELECT p.prod_name, ch.quantity, ch.unit_price, ch.total_price
        FROM checkout ch
        JOIN prod p ON ch.product_id = p.prod_id
        WHERE ch.order_id = %s
    """, (order_id,))
    items = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template('emp_receipt.html', order=order_info, items=items)

# Maintenance page from Admin panel
@app.route('/maintenance')
def maintenance_page():
    if 'username' in session and session['role'] == 'Admin':
        return render_template('maintenance.html')
    return redirect(url_for('home'))

# Add page from Admin panel
@app.route('/add_emp')
def add_emp():
    if 'username' in session:
        try:
            search_query = request.args.get('search', '').strip()

            connection = mysql.connector.connect(**db_config)
            cursor = connection.cursor(dictionary=True)

            if search_query:
                query = """
                    SELECT user_id, firstname, lastname, role, username
                    FROM user
                    WHERE firstname LIKE %s OR lastname LIKE %s OR username LIKE %s
                """
                like_pattern = f"%{search_query}%"
                cursor.execute(query, (like_pattern, like_pattern, like_pattern))
            else:
                query = "SELECT user_id, firstname, lastname, role, username FROM user"
                cursor.execute(query)

            users = cursor.fetchall()

            for user in users:
                user['full_name'] = f"{user['firstname']} {user['lastname']}"

            cursor.close()
            connection.close()

            return render_template('add_emp.html', users=users)

        except Exception as e:
            return f"Error: {e}"
        
    return redirect(url_for('home'))

# Edit page from Admin panel
@app.route('/edit')
def edit_page():
    if 'username' in session and session['role'] == 'Admin':
        return render_template('edit.html')
    return redirect(url_for('home'))

@app.route('/edit_emp')
def edit_emp():
    if 'username' in session:
        try:
            search_query = request.args.get('search', '').strip()

            connection = mysql.connector.connect(**db_config)
            cursor = connection.cursor(dictionary=True)

            if search_query:
                query = """
                    SELECT user_id, firstname, lastname, role, username
                    FROM user
                    WHERE firstname LIKE %s OR lastname LIKE %s OR username LIKE %s
                """
                like_pattern = f"%{search_query}%"
                cursor.execute(query, (like_pattern, like_pattern, like_pattern))
            else:
                query = "SELECT user_id, firstname, lastname, role, username FROM user"
                cursor.execute(query)

            users = cursor.fetchall()

            for user in users:
                user['full_name'] = f"{user['firstname']} {user['lastname']}"

            cursor.close()
            connection.close()

            return render_template('edit_emp.html', users=users)

        except Exception as e:
            return f"Error: {e}"
        
    return redirect(url_for('home'))

@app.route('/edit_prod')
def edit_prod():
    if 'username' in session:
        try:
            search_query = request.args.get('search', '')

            connection = mysql.connector.connect(**db_config)
            cursor = connection.cursor(dictionary=True)

            if search_query:
                query = "SELECT * FROM prod WHERE prod_name LIKE %s OR category LIKE %s"
                cursor.execute(query, ('%' + search_query + '%', '%' + search_query + '%'))
            else:
                query = "SELECT * FROM prod"
                cursor.execute(query)

            products = cursor.fetchall()

            cursor.close()
            connection.close()

            return render_template('edit_prod.html', products=products)

        except Exception as e:
            return f"Error: {e}"
        
    return redirect(url_for('home'))

# Report page from Admin panel
@app.route('/report')
def report_page():
    if 'username' in session and session['role'] == 'Admin':
        return render_template('report.html')
    return redirect(url_for('home'))

@app.route('/order_details')
def order_details():
    if 'username' in session:
        try:
            search_query = request.args.get('search', '').strip()

            connection = mysql.connector.connect(**db_config)
            cursor = connection.cursor(dictionary=True)

            if search_query:
                # SQL with WHERE clause for filtering
                query = """
                    SELECT o.order_id, c.customer_name, c.email, c.contacts, o.order_date, o.total_amount
                    FROM `orders` o
                    JOIN customer c ON o.customer_id = c.customer_id
                    WHERE c.customer_name LIKE %s OR c.email LIKE %s OR CAST(c.contacts AS CHAR) LIKE %s
                """
                like_pattern = f"%{search_query}%"
                cursor.execute(query, (like_pattern, like_pattern, like_pattern))
            else:
                # Normal query with no search filter
                query = """
                    SELECT o.order_id, c.customer_name, c.email, c.contacts, o.order_date, o.total_amount
                    FROM `orders` o
                    JOIN customer c ON o.customer_id = c.customer_id
                """
                cursor.execute(query)

            order_details = cursor.fetchall()

            for order in order_details:
                order['date'] = order['order_date'].strftime('%B %#d, %Y')

            cursor.close()
            connection.close()

            return render_template('ord_dtls.html', order_details=order_details)

        except Exception as e:
            return f"Error: {e}"
        
    return redirect(url_for('home'))

@app.route('/user_logs')
def user_logs():
    if 'username' in session:
        try:
            search_query = request.args.get('search', '').strip()

            connection = mysql.connector.connect(**db_config)
            cursor = connection.cursor(dictionary=True)

            if search_query:
                query = """
                    SELECT ul.log_id, ul.timestamp, ul.action, u.username, 
                        CONCAT(u.firstname, ' ', u.lastname) AS full_name
                    FROM user_logs ul
                    JOIN user u ON ul.user_id = u.user_id
                    WHERE u.firstname LIKE %s OR u.lastname LIKE %s OR u.username LIKE %s
                    ORDER BY ul.timestamp ASC
                """
                like_pattern = f"%{search_query}%"
                cursor.execute(query, (like_pattern, like_pattern, like_pattern))
            else:
                query = """
                    SELECT ul.log_id, ul.timestamp, ul.action, u.username, 
                        CONCAT(u.firstname, ' ', u.lastname) AS full_name
                    FROM user_logs ul
                    JOIN user u ON ul.user_id = u.user_id
                    ORDER BY ul.timestamp ASC
                """
                cursor.execute(query)

            user_logs = cursor.fetchall()

            for log in user_logs:
                log['date'] = log['timestamp'].strftime('%B %#d, %Y')
                log['time'] = log['timestamp'].strftime('%I:%M %p').lower()
                log['log_status'] = log['action'].capitalize()

            cursor.close()
            connection.close()

            return render_template('user_logs.html', user_logs=user_logs)

        except Exception as e:
            return f"Error: {e}"
        
    return redirect(url_for('home'))

# Help page from Admin panel
@app.route('/help')
def help_page():
    if 'username' in session and session['role'] == 'Admin':
        return render_template('help.html')
    return redirect(url_for('home'))

# About page from Admin panel
@app.route('/about')
def about_page():
    if 'username' in session and session['role'] == 'Admin':
        return render_template('about.html')
    return redirect(url_for('home'))

# Help page from Employee panel
@app.route('/help_emp')
def help_emp():
    if 'username' in session and session['role'] == 'Employee':
        return render_template('emp_help.html')
    return redirect(url_for('home'))

# About page from Employee panel
@app.route('/about_emp')
def about_emp():
    if 'username' in session and session['role'] == 'Employee':
        return render_template('emp_about.html')
    return redirect(url_for('home'))

# Logout Route
@app.route('/logout')
def logout():
    username = session.get('username')

    if username:
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor(dictionary=True)

        cursor.execute("SELECT user_id FROM user WHERE username = %s", (username,))
        user = cursor.fetchone()

        if user:
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            update_logout_query = "UPDATE user SET last_logout = %s WHERE user_id = %s"
            cursor.execute(update_logout_query, (current_time, user['user_id']))
            
            log_query = "INSERT INTO user_logs (user_id, action) VALUES (%s, 'logout')"
            cursor.execute(log_query, (user['user_id'],))
            connection.commit()

        cursor.close()
        connection.close()

    session.clear()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)