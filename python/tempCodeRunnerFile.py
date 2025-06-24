@app.route('/order_page', methods=['GET', 'POST'])
def order_page():
    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor(dictionary=True)

    if request.method == 'POST':
        data = request.get_json()
        print("Received order data", data)

        if not data or len(data) == 0:
            return jsonify({"error": "Invalid data"}), 400

        # 🔧 FIX 1: Always reset session['order_list'] on new POST
        session['order_list'] = []

        # Accumulate and consolidate quantities per product
        new_items = {}
        for item in data:
            prod_id = item['prod_id']
            quantity = int(item['quantity'])

            if prod_id in new_items:
                new_items[prod_id] += quantity
            else:
                new_items[prod_id] = quantity

        # Add unique products to session['order_list']
        for prod_id, quantity in new_items.items():
            cursor.execute("SELECT * FROM prod WHERE prod_id = %s", (prod_id,))
            product = cursor.fetchone()

            if product:
                session['order_list'].append({
                    'prod_id': prod_id,
                    'prod_name': product['prod_name'],
                    'quantity': quantity,
                    'unit_price': float(product['price']),
                    'total_price': float(product['price']) * quantity
                })

        session['order_total'] = sum(item['total_price'] for item in session['order_list'])
        cursor.close()
        connection.close()

        return jsonify({"message": "Order received", "redirect": "/checkout_page"})

    else:
        # 🔧 FIX 2: Clear any existing order data when reloading the order page
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