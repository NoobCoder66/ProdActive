import hashlib
import os
import csv
import io
import mysql.connector
import math
from flask import Flask, request, flash, redirect, url_for, render_template, session, jsonify, send_file, make_response
from decimal import Decimal
from datetime import datetime
from functools import wraps
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)
app.secret_key = 'your_secret_key'

def nocache(view):
    @wraps(view)
    def no_cache(*args, **kwargs):
        response = make_response(view(*args, **kwargs))
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response
    return no_cache

def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("MYSQLHOST"),
        user=os.getenv("MYSQLUSER"),
        password=os.getenv("MYSQLPASSWORD"),
        database=os.getenv("MYSQLDATABASE"),
        port=int(os.getenv("MYSQLPORT"))
    )


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
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

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
        conn.commit()

        session['username'] = user['username']
        session['role'] = user['role']

        cursor.close()
        cursor.close()

        # Redirect based on role
        if user['role'] == 'Admin':
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('emp_dashboard'))
    else:
        cursor.close()
        conn.close()
        return render_template('message.html', message="Invalid credentials, please try again.", redirect_url='/')
    
# Route for forgot password
@app.route('/forgot_pass', methods=['GET',' POST'])
@nocache
def forgot_password():
    return render_template('frgt_pass.html')

@app.route('/forgot_pass_submit', methods=['POST'])
@nocache
def forgot_pass_submit():
    username = request.form['username']

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    query = "SELECT * FROM user WHERE username = %s"
    cursor.execute(query, (username,))
    user = cursor.fetchone()

    cursor.close()
    conn.close()

    if not user:
        return render_template('message.html', message="Username does not exist.", redirect_url='/forgot_pass')

    session['forgot_username'] = username
    return redirect(url_for('security_questions', username=username))

@app.route('/security_questions')
@nocache
def security_questions():
    return render_template('question.html')

@app.route('/verify_security_questions', methods=['POST'])
@nocache
def verify_security_questions():
    username = request.form['username']
    answer1 = request.form['answer1'].strip().lower()
    answer2 = request.form['answer2'].strip().lower()

    # Security question answers
    correct_answer1 = "technological institute of the philippines"
    correct_answer2 = "eboutique"

    if answer1 == correct_answer1 and answer2 == correct_answer2:
        return redirect(url_for('reset_password', username=username))
    else:
        return render_template('message.html', message="Incorrect answers.", redirect_url=url_for('security_questions', username=username))
    
@app.route('/reset_password', methods=['GET', 'POST'])
@nocache
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

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    query = "UPDATE user SET password = %s WHERE username = %s"
    cursor.execute(query, (hashed_password, username))
    conn.commit()

    cursor.close()
    conn.close()

    return render_template('message.html', message="Password Successfully Reset", redirect_url='/')
    
# Route for admin page
@app.route('/admin')
@nocache
def admin_dashboard():
    if 'username' in session and session['role'] == 'Admin':
        return render_template('admin.html', username=session['username'])
    return redirect(url_for('home'))

# Route for employee page
@app.route('/employee')
@nocache
def emp_dashboard():
    if 'username' in session and session['role'] == 'Employee':
        return render_template('emp.html', username=session['username'])
    return redirect(url_for('home'))

# Registration page from Admin panel
@app.route('/register')
@nocache
def register_page():
    if 'username' in session and session['role'] == 'Admin':
        return render_template('register.html')
    return redirect(url_for('home'))

# Employee registration
@app.route('/register_emp', methods=['GET','POST'])
@nocache
def register_emp():
    if request.method == 'GET':
        if 'username' in session and session['role'] == 'Admin':
            return render_template('emp_reg.html')
        return redirect(url_for('home'))
        
    try:
        # Get form data
        fname = request.form['fname']
        lname = request.form['lname']
        email = request.form['email']
        contacts = request.form['contacts']
        username = request.form['user']
        password = request.form['pass']
        role = request.form['role']

        hashed_password = hashlib.sha256(password.encode()).hexdigest()

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Insert the data into the user table
        query = """
            INSERT INTO user (firstName, lastName, email, contacts, username, password, role)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        values = (fname, lname, email, contacts, username, hashed_password, role)

        cursor.execute(query, values)
        conn.commit()

        cursor.close()
        conn.close()

        return redirect(url_for('register_emp'))
    
    except Exception as e:
        return f"Error: {e}"
    
# Product registration
@app.route('/register_prod', methods=['GET','POST'])
@nocache
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

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Insert the data into the user table
        query = """
            INSERT INTO prod (prod_id, prod_name, stock, price, category)
            VALUES (%s, %s, %s, %s, %s)
        """
        values = (prod_id, prod_name, stock, price, category)

        cursor.execute(query, values)
        conn.commit()

        cursor.close()
        conn.close()

        return redirect(url_for('register_prod'))
    
    except Exception as e:
        return f"Error: {e}"

@app.route('/inventory')
@nocache
def inventory_page():
    if 'username' in session:
        try:
            search_query = request.args.get('search', '')

            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            if search_query:
                cursor.execute("""
                    SELECT * FROM prod 
                    WHERE prod_name LIKE %s OR category LIKE %s
                """, ('%' + search_query + '%', '%' + search_query + '%'))
            else:
                cursor.execute("SELECT * FROM prod")
            products = cursor.fetchall()

            # Fetch demand per product from checkout table
            cursor.execute("""
                SELECT product_id, SUM(quantity) as total_demand
                FROM checkout
                WHERE order_id IS NOT NULL
                GROUP BY product_id
            """)
            demand_data = cursor.fetchall()
            demand_map = {d['product_id']: d['total_demand'] for d in demand_data}

            # EOQ calculation per product
            for product in products:
                prod_id = product['prod_id']
                stock = product['stock']
                if prod_id in demand_map:
                    annual_demand = demand_map[prod_id]
                else:
                    annual_demand = 1

                # ordering_cost = product['ordering_cost']
                # holding_cost = product['holding_cost']

                try:
                    eoq = math.sqrt((2 * annual_demand * product['ordering_cost']) / product['holding_cost'])
                except ZeroDivisionError:
                    eoq = 0

                product['eoq'] = round(eoq)

                if prod_id not in demand_map:
                    product['status'] = 'Unsold Product'
                elif stock <= eoq:
                    product['status'] = 'Low Stock'
                else:
                    product['status'] = 'Normal'

            cursor.close()
            conn.close()
            return render_template('inventory.html', products=products)

        except Exception as e:
            return f"Error: {e}"

    return redirect(url_for('home'))

@app.route('/inventory_emp')
@nocache
def inventory_emp():
    if 'username' in session:
        try:
            search_query = request.args.get('search', '')

            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            if search_query:
                cursor.execute("""
                    SELECT * FROM prod 
                    WHERE prod_name LIKE %s OR category LIKE %s
                """, ('%' + search_query + '%', '%' + search_query + '%'))
            else:
                cursor.execute("SELECT * FROM prod")
            products = cursor.fetchall()

            # Fetch demand per product from checkout table
            cursor.execute("""
                SELECT product_id, SUM(quantity) as total_demand
                FROM checkout
                WHERE order_id IS NOT NULL
                GROUP BY product_id
            """)
            demand_data = cursor.fetchall()
            demand_map = {d['product_id']: d['total_demand'] for d in demand_data}

            # EOQ calculation per product
            for product in products:
                prod_id = product['prod_id']
                stock = product['stock']
                if prod_id in demand_map:
                    annual_demand = demand_map[prod_id]
                else:
                    annual_demand = 1

                # ordering_cost = product['ordering_cost']
                # holding_cost = product['holding_cost']

                try:
                    eoq = math.sqrt((2 * annual_demand * product['ordering_cost']) / product['holding_cost'])
                except ZeroDivisionError:
                    eoq = 0

                product['eoq'] = round(eoq)

                if prod_id not in demand_map:
                    product['status'] = 'Unsold Product'
                elif stock <= eoq:
                    product['status'] = 'Low Stock'
                else:
                    product['status'] = 'Normal'

            cursor.close()
            conn.close()
            return render_template('emp_inv.html', products=products)

        except Exception as e:
            return f"Error: {e}"

# Sales page from Admin panel
@app.route('/sales')
@nocache
def sales_page():
    if 'username' in session and session['role'] == 'Admin':
        return render_template('sales.html')
    return redirect(url_for('home'))

# Customer Page
@app.route('/customer_page', methods=['POST', 'GET'])
@nocache
def customer_page():
    if request.method == 'POST':
        birthdate = request.form.get('birthdate')
        age = request.form.get('age')

        if (not age or (isinstance(age, str) and not age.isdigit())) and birthdate:
            try:
                birth = datetime.strptime(birthdate, '%Y-%m-%d')
                today = datetime.today()
                age = today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))
            except:
                age = None

        session['customer_name'] = request.form['customer']
        session['email'] = request.form['email']
        session['contacts'] = request.form['contacts']

        if isinstance(age, str) and age.isdigit():
            session['age'] = int(age)
        elif isinstance(age, int):
            session['age'] = age
        else:
            session['age'] = None

        session['birthdate'] = birthdate
        session['sex'] = request.form.get('sex') or None
        session['tel_no'] = request.form.get('tel_no') or None
        session['street'] = request.form.get('street') or None
        session['city'] = request.form.get('city') or None
        session['zip'] = request.form.get('zip') or None

        return redirect(url_for('order_page'))
    
    return render_template('customer.html')

# Order Page
@app.route('/order_page', methods=['GET', 'POST'])
@nocache
def order_page():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        data = request.get_json()
        print("Received order data", data)

        if not data or len(data) == 0:
            return jsonify({"error": "Invalid data"}), 400

        if request.method == 'POST':
            # data = request.get_json()
            # print("Received order data", data)

            if not data or len(data) == 0:
                return jsonify({"error": "Invalid data"}), 400

            # Initialize if not already
            if 'order_list' not in session:
                session['order_list'] = []

            # Build a lookup map of existing items
            existing_items = {item['prod_id']: item for item in session['order_list']}

            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

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
            # connection.close()

            return jsonify({"message": "Order received", "redirect": "/checkout_page"})
    else:
        if 'order_list' not in session:
            session['order_list'] = []

        cursor.execute("SELECT prod_id, prod_name, stock, price, category FROM prod")
        products = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template('order.html', products=products)
    
@app.route('/check_existing_order')
@nocache
def check_existing_order():
    exists = 'order_list' in session and len(session['order_list']) > 0
    return jsonify({'exists': exists})

# Checkout Page
@app.route('/checkout_page')
@nocache
def checkout_page():
    order_list = session.get('order_list', [])
    total_cash_payment = sum(item['quantity'] * item['unit_price'] for item in order_list)
    return render_template('checkout.html', order_list=order_list, total_cash_payment=total_cash_payment)

# Save all data
@app.route('/submit_checkout', methods=['POST'])
@nocache
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

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

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

        conn.commit()
        session['latest_order_id'] = order_id
        session.pop('order_list', None)
        return redirect(url_for('receipt_page'))

    except Exception as e:
        conn.rollback()
        return f"Error during checkout: {e}"

    finally:
        cursor.close()
        conn.close()

@app.route('/remove_checkout_item/<int:prod_id>', methods=['POST'])
@nocache
def remove_checkout_item(prod_id):
    order_list = session.get('order_list', [])
    updated_list = [item for item in order_list if int(item['prod_id']) != prod_id]
    session['order_list'] = updated_list
    session['order_total'] = sum(item['quantity'] * item['unit_price'] for item in updated_list)
    return jsonify(success=True, new_total=session['order_total'])

@app.route('/receipt')
@nocache
def receipt_page():
    order_id = session.get('latest_order_id')
    if not order_id:
        return redirect(url_for('sales_page'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

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
    conn.close()

    return render_template('receipt.html', order=order_info, items=items)

# Sales page from Employee
@app.route('/sales_emp')
@nocache
def sales_emp():
    if 'username' in session and session['role'] == 'Employee':
        return render_template('emp_sale.html')
    return redirect(url_for('home'))

@app.route('/customer_emp', methods=['POST', 'GET'])
@nocache
def customer_emp():
    if request.method == 'POST':
        birthdate = request.form.get('birthdate')
        age = request.form.get('age')

        if (not age or (isinstance(age, str) and not age.isdigit())) and birthdate:
            try:
                birth = datetime.strptime(birthdate, '%Y-%m-%d')
                today = datetime.today()
                age = today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))
            except:
                age = None

        session['customer_name'] = request.form['customer']
        session['email'] = request.form['email']
        session['contacts'] = request.form['contacts']

        if isinstance(age, str) and age.isdigit():
            session['age'] = int(age)
        elif isinstance(age, int):
            session['age'] = age
        else:
            session['age'] = None
            
        session['birthdate'] = birthdate
        session['sex'] = request.form.get('sex') or None
        session['tel_no'] = request.form.get('tel_no') or None
        session['street'] = request.form.get('street') or None
        session['city'] = request.form.get('city') or None
        session['zip'] = request.form.get('zip') or None

        return redirect(url_for('order_emp'))
    
    return render_template('emp_customer.html')

@app.route('/order_emp', methods=['GET','POST'])
@nocache
def order_emp():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        data = request.get_json()
        print("Received order data", data)

        if not data or len(data) == 0:
            return jsonify({"error": "Invalid data"}), 400

        if request.method == 'POST':
            # data = request.get_json()
            # print("Received order data", data)

            if not data or len(data) == 0:
                return jsonify({"error": "Invalid data"}), 400

            # Initialize if not already
            if 'order_list' not in session:
                session['order_list'] = []

            # Build a lookup map of existing items
            existing_items = {item['prod_id']: item for item in session['order_list']}

            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

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
            conn.close()

            return jsonify({"message": "Order received", "redirect": "/checkout_emp"})
    else:
        if 'order_list' not in session:
            session['order_list'] = []

        cursor.execute("SELECT prod_id, prod_name, stock, price, category FROM prod")
        products = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template('emp_purchase.html', products=products)
    
@app.route('/check_existing_order_emp')
@nocache
def check_existing_order_emp():
    exists = 'order_list' in session and len(session['order_list']) > 0
    return jsonify({'exists': exists})

@app.route('/checkout_emp')
@nocache
def checkout_emp():
    order_list = session.get('order_list', [])
    total_cash_payment = sum(item['quantity'] * item['unit_price'] for item in order_list)
    return render_template('emp_checkout.html', order_list=order_list, total_cash_payment=total_cash_payment)

@app.route('/submit_checkout_emp', methods=['POST'])
@nocache
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

    conn = get_db_connection()
    cursor = conn.cursor()

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

        conn.commit()
        session['latest_order_id'] = order_id
        session.pop('order_list', None)
        return redirect(url_for('receipt_emp'))

    except Exception as e:
        conn.rollback()
        return f"Error during checkout: {e}"

    finally:
        cursor.close()
        conn.close()
        
@app.route('/remove_checkout_item_emp/<int:prod_id>', methods=['POST'])
@nocache
def remove_checkout_item_emp(prod_id):
    order_list = session.get('order_list', [])
    updated_list = [item for item in order_list if int(item['prod_id']) != prod_id]
    session['order_list'] = updated_list
    session['order_total'] = sum(item['quantity'] * item['unit_price'] for item in updated_list)
    return jsonify(success=True, new_total=session['order_total'])

@app.route('/receipt_emp')
@nocache
def receipt_emp():
    order_id = session.get('latest_order_id')
    if not order_id:
        return redirect(url_for('sales_emp'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

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
    conn.close()

    return render_template('emp_receipt.html', order=order_info, items=items)

# Maintenance page from Admin panel
@app.route('/maintenance')
@nocache
def maintenance_page():
    if 'username' in session and session['role'] == 'Admin':
        return render_template('maintenance.html')
    return redirect(url_for('home'))

# Add page from Admin panel
@app.route('/add_emp')
@nocache
def add_emp():
    if 'username' in session:
        try:
            search_query = request.args.get('search', '').strip()

            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            if search_query:
                query = """
                    SELECT user_id, firstname, lastname, role, username
                    FROM user
                    WHERE firstname LIKE %s OR lastname LIKE %s OR username LIKE %s
                """
                like_pattern = f"%{search_query}%"
                cursor.execute(query, (like_pattern, like_pattern, like_pattern))
            else:
                query = "SELECT user_id, firstname, lastname, role, username, email, address, sex, age, status FROM user"
                cursor.execute(query)

            users = cursor.fetchall()

            for user in users:
                user['full_name'] = f"{user['firstname']} {user['lastname']}"

            cursor.close()
            conn.close()

            return render_template('add_emp.html', users=users)

        except Exception as e:
            return f"Error: {e}"
        
    return redirect(url_for('home'))

@app.route('/add_details', methods=['POST'])
@nocache
def add_details():
    user_id = request.form.get('EmpUser').strip()
    address = request.form.get('EmpAddress').strip()
    email = request.form.get('EmpEmail').strip()
    birthday = request.form.get('EmpAge').strip()
    sex = request.form.get('EmpSex').strip()
    status = request.form.get('EmpStatus').strip()

    try:
        birthdate = datetime.strptime(birthday, "%Y-%m-%d")
        today = datetime.today()
        age = today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))
    except Exception:
        age = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        query = """
           UPDATE user
            SET email = %s, address = %s, sex = %s, status = %s, age = %s
            WHERE user_id = %s
        """
        values = (email, address, sex, status, age, user_id )
        cursor.execute(query, values)
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('add_emp'))
    except Exception as e:
        return f"Error inserting employee: {e}"

# Edit page from Admin panel
@app.route('/edit')
@nocache
def edit_page():
    if 'username' in session and session['role'] == 'Admin':
        return render_template('edit.html')
    return redirect(url_for('home'))

@app.route('/edit_emp')
@nocache
def edit_emp():
    if 'username' in session:
        try:
            search_query = request.args.get('search', '').strip()

            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            if search_query:
                query = """
                    SELECT user_id, firstname, lastname, role, username
                    FROM user
                    WHERE firstname LIKE %s OR lastname LIKE %s OR username LIKE %s
                """
                like_pattern = f"%{search_query}%"
                cursor.execute(query, (like_pattern, like_pattern, like_pattern))
            else:
                query = "SELECT user_id, firstname, lastname, role, username, sex, email, status, address, age FROM user"
                cursor.execute(query)

            users = cursor.fetchall()

            for user in users:
                user['full_name'] = f"{user['firstname']} {user['lastname']}"

            cursor.close()
            conn.close()

            return render_template('edit_emp.html', users=users)

        except Exception as e:
            return f"Error: {e}"
        
    return redirect(url_for('home'))

@app.route('/update_employee', methods=['POST'])
@nocache
def employee_update():
    user_id = request.form.get('user_id', '').strip()

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM user WHERE user_id = %s", (user_id,))
    current_data = cursor.fetchone()
    cursor.close()

    if not current_data:
        conn.close()
        return "Error: User not found", 404

    # Pull form values OR fallback to current data
    role = request.form.get('role', '').strip() or current_data['role']
    username = request.form.get('username', '').strip() or current_data['username']
    email = request.form.get('email', '').strip() or current_data['email']
    address = request.form.get('address', '').strip() or current_data['address']
    sex = request.form.get('sex', '').strip() or current_data['sex']
    status = request.form.get('status', '').strip() or current_data['status']
    birthday = request.form.get('birthday', '').strip()
    
    firstName = request.form.get('firstName', '').strip() or current_data['firstName', '']
    lastName = request.form.get('lastName', '').strip() or current_data['lastName', '']

    # Calculate age if birthday is given, otherwise keep existing
    try:
        if birthday:
            birthdate = datetime.strptime(birthday, "%Y-%m-%d")
            today = datetime.today()
            new_age = today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))
        else:
            new_age = current_data.get('age', None)
    except Exception:
        new_age = current_data.get('age', None)

    try:
        cursor = conn.cursor()
        query = """
            UPDATE user
            SET firstName = %s, lastName = %s, role = %s, username = %s, email = %s, address = %s,
                sex = %s, status = %s, age = %s
            WHERE user_id = %s
        """
        values = (firstName, lastName, role, username, email, address, sex, status, new_age, user_id)
        cursor.execute(query, values)
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('edit_emp'))
    except Exception as e:
        return f"Error updating employee: {e}"
    
@app.route('/Employee_delete', methods=['POST'])
@nocache
def Employee_delete():
    if 'username' not in session:
        return redirect(url_for('home'))
    
    user_id = request.form.get('deleteEmp_id', '').strip()

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("DELETE FROM user_logs WHERE user_id = %s", (user_id,))
        cursor.execute("DELETE FROM user WHERE user_id = %s", (user_id,))
        conn.commit()

        if cursor.rowcount > 0:
            print(f"✅ Employee with ID {user_id} deleted.")
        else:
            print(f"⚠️ No employee found with ID {user_id}.")

        cursor.close()
        return redirect(url_for('edit_emp'))

    except Exception as e:
        print("❌ Error deleting employee:", e)
        return f"Error deleting employee: {e}"

@app.route('/edit_prod')
@nocache
def edit_prod():
    if 'username' in session:
        try:
            search_query = request.args.get('search', '')

            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            if search_query:
                query = "SELECT * FROM prod WHERE prod_name LIKE %s OR category LIKE %s"
                cursor.execute(query, ('%' + search_query + '%', '%' + search_query + '%'))
            else:
                query = "SELECT * FROM prod"
                cursor.execute(query)

            products = cursor.fetchall()

            cursor.close()
            conn.close()

            return render_template('edit_prod.html', products=products)

        except Exception as e:
            return f"Error: {e}"
        
    return redirect(url_for('home'))

@app.route('/update_product', methods=['POST'])
@nocache
def update_product():
    prod_id = request.form.get('prod_id', '').strip()

    if not prod_id:
        return "Error: Product ID is required", 400

    # Get current product data
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM prod WHERE prod_id = %s", (prod_id,))
    current_data = cursor.fetchone()
    cursor.close()

    if not current_data:
        conn.close()
        return "Error: Product not found", 404

    # Use new value if provided, otherwise fallback to current
    prod_name = request.form.get('ProductName', '').strip() or current_data['prod_name']
    price = request.form.get('ProductPrice', '').strip() or current_data['price']
    category = request.form.get('ProductCategory', '').strip() or current_data['category']

    try:
        cursor = conn.cursor()
        query = """
            UPDATE prod
            SET prod_name = %s, price = %s, category = %s
            WHERE prod_id = %s
        """
        values = (prod_name, price, category, prod_id)
        cursor.execute(query, values)
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('edit_prod'))
    except Exception as e:
        return f"Error updating product: {e}"

@app.route('/delete_product', methods=['POST'])
@nocache
def delete_product():
    if 'username' not in session:
        return redirect(url_for('home'))

    prod_id = request.form.get('prod_id', '').strip()

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("DELETE FROM checkout WHERE product_id = %s", (prod_id,))
        cursor.execute("DELETE FROM prod WHERE prod_id = %s", (prod_id,))
        conn.commit()

        if cursor.rowcount > 0:
            print(f"✅ Product with ID {prod_id} deleted.")
        else:
            print(f"⚠️ No product found with ID {prod_id}.")

    except Exception as e:
        print("❌ Error deleting product:", e)
    finally:
        cursor.close()
        conn.close()
    return redirect(url_for('edit_prod'))

@app.route('/export_product_csv')
@nocache
def export_product_csv():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        query = "SELECT * FROM prod"
        cursor.execute(query)
        products = cursor.fetchall()
        cursor.close()
        conn.close()

        if not products:
            return "No products found to export."

        csv_file = io.StringIO()
        writer = csv.writer(csv_file)
        writer.writerow(['Product ID', 'Product Name', 'Stock', 'Price', 'Category'])

        for product in products:
            writer.writerow([product['prod_id'], product['prod_name'], product['stock'], product['price'], product['category']])

        csv_file.seek(0)
        today_str = datetime.now().strftime('%Y-%m-%d')

        return send_file(
            io.BytesIO(csv_file.getvalue().encode('utf-8')),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'products_{today_str}.csv'
        )

    except Exception as e:
        return f"Error exporting products: {e}"

@app.route('/export_employee_csv')
@nocache
def export_employee_csv():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        query = "SELECT * FROM user"
        cursor.execute(query)
        employees = cursor.fetchall()

        cursor.close()
        conn.close()

        if not employees:
            return "No employees found to export."

        csv_file = io.StringIO()
        writer = csv.writer(csv_file)
        writer.writerow(['User ID', 'Name', 'Role', 'Username'])

        for employee in employees:
            full_name = f"{employee['firstName']} {employee['lastName']}"
            writer.writerow([employee['user_id'], full_name, employee['role'], employee['username']])

        csv_file.seek(0)
        today_str = datetime.now().strftime('%Y-%m-%d')

        return send_file(
            io.BytesIO(csv_file.getvalue().encode('utf-8')),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'employees_{today_str}.csv'
        )

    except Exception as e:
        return f"Error exporting employees: {e}"

# Report page from Admin panel
@app.route('/report')
@nocache
def report_page():
    if 'username' in session and session['role'] == 'Admin':
        return render_template('report.html')
    return redirect(url_for('home'))

@app.route('/sales_summary_data')
@nocache
def sales_summary_data():
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT p.prod_name AS product_name, SUM(c.quantity) AS total_sales
        FROM checkout c
        JOIN prod p ON c.product_id = p.prod_id
        GROUP BY p.prod_name
    """
    cursor.execute(query)
    result = cursor.fetchall()

    cursor.close()
    conn.close()

    return jsonify(result)
    
# --- ORDER DETAILS ---
@app.route('/order_details_data')
@nocache
def order_details_data():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        query = """
            SELECT o.order_id, cu.customer_name, p.prod_name, c.quantity,
                   c.total_price, o.order_date
            FROM orders o
            JOIN customer cu ON o.customer_id = cu.customer_id
            JOIN checkout c ON o.order_id = c.order_id
            JOIN prod p ON c.product_id = p.prod_id
            WHERE DATE(o.order_date) = CURDATE()
            ORDER BY o.order_date DESC
        """

        cursor.execute(query)
        data = cursor.fetchall()

        # Optional: format the date nicely
        for row in data:
            row['order_date'] = row['order_date'].strftime('%B %d, %Y %I:%M %p')

        cursor.close()
        conn.close()
        return jsonify(data)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# --- RESTOCK (INVENTORY) ---
@app.route('/inventory_data')
@nocache
def inventory_data():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT prod_id, prod_name, stock FROM prod")
        data = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    

# --- RESTOCK ACTION ---
@app.route('/restock', methods=['POST'])
@nocache
def restock():
    try:
        req = request.get_json()
        prod_id = req.get('product_id')
        quantity = int(req.get('quantity', 0))
        if not prod_id or quantity <= 0:
            return jsonify({'success': False, 'message': 'Invalid input.'}), 400
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE prod SET stock = stock + %s WHERE prod_id = %s", (quantity, prod_id))
        conn.commit()
        cursor.execute("SELECT stock FROM prod WHERE prod_id = %s", (prod_id,))
        new_stock = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        return jsonify({'success': True, 'new_stock': new_stock})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500 


@app.route('/user_logs_data')
@nocache
def user_logs_data():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT 
                user_logs.log_id,
                user_logs.user_id,
                user_logs.action,
                user_logs.timestamp,
                user.username
            FROM 
                user_logs
            JOIN 
                user ON user_logs.user_id = user.user_id 
            WHERE 
                DATE(user_logs.timestamp) = CURDATE()
            ORDER BY 
                user_logs.timestamp DESC
        """)

        data = cursor.fetchall()

        for log in data:
            log['timestamp'] = log['timestamp'].strftime('%B %d, %Y %I:%M %p')

        cursor.close()
        conn.close()
        return jsonify(data)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Help page from Admin panel
@app.route('/help')
@nocache
def help_page():
    if 'username' in session and session['role'] == 'Admin':
        return render_template('help.html')
    return redirect(url_for('home'))

# About page from Admin panel
@app.route('/about')
@nocache
def about_page():
    if 'username' in session and session['role'] == 'Admin':
        return render_template('about.html')
    return redirect(url_for('home'))

# Help page from Employee panel
@app.route('/help_emp')
@nocache
def help_emp():
    if 'username' in session and session['role'] == 'Employee':
        return render_template('emp_help.html')
    return redirect(url_for('home'))

# About page from Employee panel
@app.route('/about_emp')
@nocache
def about_emp():
    if 'username' in session and session['role'] == 'Employee':
        return render_template('emp_about.html')
    return redirect(url_for('home'))

# Logout Route
@app.route('/logout')
def logout():
    username = session.get('username')

    if username:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT user_id FROM user WHERE username = %s", (username,))
        user = cursor.fetchone()

        if user:
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            update_logout_query = "UPDATE user SET last_logout = %s WHERE user_id = %s"
            cursor.execute(update_logout_query, (current_time, user['user_id']))
            
            log_query = "INSERT INTO user_logs (user_id, action) VALUES (%s, 'logout')"
            cursor.execute(log_query, (user['user_id'],))
            conn.commit()

        cursor.close()
        conn.close()

    session.clear()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)