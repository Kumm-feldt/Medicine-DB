from flask import Flask, render_template, request, url_for, redirect
import sqlite3
from sqlite3 import Error


tax = 0.0975
quetzal = 7.85




# db functions
def create_connection(db_file):
    """Create a database connection to a SQLite database."""
    connection = None
    try:
        connection = sqlite3.connect(db_file)
        print(f"Connected to {db_file}")
    except Error as e:
        print(e)
    return connection


def create_table(connection, create_table_sql):
    """Create a table from the create_table_sql statement."""
    try:
        cursor = connection.cursor()
        cursor.execute(create_table_sql)
        print("Table created successfully")
    except Error as e:
        print(e)


def table_empty(table_name):
    connection = sqlite3.connect("med_db.db")
    cursor = connection.cursor()
    cursor.execute(f'SELECT * FROM {table_name} LIMIT 1')
    result = cursor.fetchone()

    if result is None:
        return True
    else:
        return False


def create_db():
    database = "med_db.db"

    # SQL statements to create tables
    users_table_sql = """
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE
    );
    """

    products_table_sql = """
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        medCode TEXT, 
        name TEXT, 
        currentPrice REAL, 
        priceQuetzal REAL, 
        sellPublicQuetzal REAL, 
        url TEXT
    );
    """

    orders_table_sql = """
    CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT, 
    user_id INTEGER, user_name TEXT, 
    product_id INTEGER, 
    amount INTEGER, 
    total_price REAL, 
    product_name TEXT, 
    unit_price_q REAL, 
    FOREIGN KEY (user_id) REFERENCES users (id), 
    FOREIGN KEY (product_id) REFERENCES receipt (id));

    """

    balance_table_sql = """
    CREATE TABLE IF NOT EXISTS balance (
    payedQuetzal REAL, 
    balanceBankQuetzal REAL
    );
    """

    receipt_table_sql = """
    CREATE TABLE IF NOT EXISTS receipt (
    product TEXT, 
    amount NUMERIC, 
    price REAL, 
    priceQuetzal REAL, 
    id INTEGER PRIMARY KEY AUTOINCREMENT, 
    totalPriceQuetzal REAL
    );
"""

    # create a database connection
    connection = create_connection(database)

    if connection is not None:
        # create tables
        create_table(connection, users_table_sql)
        create_table(connection, orders_table_sql)
        create_table(connection, products_table_sql)
        create_table(connection, balance_table_sql)
        create_table(connection, receipt_table_sql)
        # close the database connection
        connection.close()
    else:
        print("Error! Cannot create the database connection.")


def validate_form_data(form_data, arr):
    # Check if any of the required fields are empty & Check if elements are present
    for element in arr:
        if element not in form_data:
            return False
        elif not form_data[element]:
            return False
    return True


def price_taxed(net_price):
    price = float(net_price)
    after_tax_price = price + (price * tax)
    return round(after_tax_price, 2)


def count_elements(table):
    conn = sqlite3.connect('med_db.db')
    cursor = conn.cursor()
    query_count = f"SELECT COUNT(*) FROM {table};"
    cursor.execute(query_count)
    count = cursor.fetchone()
    conn.close()

    return count


def code_generator():
    code_base = "med"
    med_code = None
    count = count_elements("products")

    if int(count[0]) < 9:
        med_code = code_base + "00" + str(int(count[0]) + 1)
    elif 9 <= int(count[0]) < 99:
        med_code = code_base + "0" + str(int(count[0]) + 1)

    return med_code


def update_products_db(name, current_price, sell_public_q, url, med_code):
    conn = sqlite3.connect('med_db.db')
    cursor = conn.cursor()
    query = "UPDATE products SET name = ?, currentPrice = ?, " \
            "sellPublicQuetzal = ?, url = ? WHERE medCode = ?"
    cursor.execute(query, (name, current_price, sell_public_q, url, med_code))
    conn.commit()
    conn.close()


def search_element(table, column, med_code="med000", product_id=0):
    conn = sqlite3.connect('med_db.db')
    cursor = conn.cursor()
    if med_code != "med000" and product_id == 0:
        query = f"SELECT {column} FROM {table} where medCode=?;"
        cursor.execute(query, (med_code,))
    elif med_code == "med000":
        query = f"SELECT {column} FROM {table} WHERE id=?;"
        cursor.execute(query, (product_id,))

    result = cursor.fetchone()
    conn.commit()
    conn.close()
    if result:
        return result[0]
    else:
        return None


def show_products_receipt(table="receipt"):
    with sqlite3.connect('med_db.db') as conn:
        cursor = conn.cursor()
        query = f"SELECT * FROM {table};"
        products = cursor.execute(query).fetchall()
    conn.close()
    return products


def insert_element(table, column, value):
    if not (table.isidentifier() and column.isidentifier()):
        raise ValueError("Invalid table or column name")

    # Use a context manager for the database connection
    with sqlite3.connect('med_db.db') as conn:
        cursor = conn.cursor()

        # Use parameterized queries to prevent SQL injection
        query = f"INSERT INTO {table} ({column}) VALUES (?);"

        # Inserting Parameters
        cursor.execute(query, (value,))
        conn.commit()


def insert_column_values(table, columns_values):
    if not table.isidentifier():
        raise ValueError("Invalid table name")

    with sqlite3.connect('med_db.db') as conn:
        cursor = conn.cursor()

        # Use parameterized queries to prevent SQL injection
        columns = ', '.join(columns_values.keys())
        placeholders = ', '.join(['?' for _ in columns_values.values()])
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders});"

        # Inserting Parameters
        cursor.execute(query, tuple(columns_values.values()))
        conn.commit()

        cursor.close()
        conn.close()



def get_balance():
    conn = sqlite3.connect('med_db.db')
    cursor = conn.cursor()
    query = "SELECT payedQuetzal, balanceBankQuetzal FROM balance"
    cursor.execute(query)
    result = cursor.fetchall()
    if len(result) != 0:
        total_q = round(get_total("receipt", "totalPriceQuetzal"),2)
        total_d = round(total_q / quetzal, 2)
        payed_q = round(get_total("balance", "payedQuetzal"),2)
        payed_d = round(payed_q / quetzal, 2)
        balance_bank_q = round(get_total("balance", "balanceBankQuetzal"),2)
        balance_bank_d = round(balance_bank_q / quetzal, 2)
        remainder_q = round(total_q - payed_q, 2)
        remainder_d = round(remainder_q / quetzal, 2)
    else:
        total_q = get_total("receipt", "totalPriceQuetzal")
        total_d = round(total_q / quetzal, 2) if total_q != 0 else 0
        payed_q, payed_d, balance_bank_q, balance_bank_d, remainder_q, remainder_d = 0, 0, 0, 0, 0, 0

    cursor.close()
    conn.close()

    return total_q, total_d, payed_q, payed_d, balance_bank_q, balance_bank_d, remainder_q, remainder_d


def add_data_receipt_db(product, amount, price, price_q, total_price):
    # check this
    conn = sqlite3.connect('med_db.db')
    cursor = conn.cursor()
    query = """INSERT INTO receipt
                          (product, amount, price, priceQuetzal,totalPriceQuetzal)
                          VALUES (?,?,?,?,?);"""
    data_tuple = (product, amount, price, price_q, total_price)
    cursor.execute(query, data_tuple)
    conn.commit()
    cursor.close()
    conn.close()


def get_total(table, column):
    total_price = 0
    with sqlite3.connect('med_db.db') as conn:
        cursor = conn.cursor()
        query = f"SELECT {column} FROM {table};"
        total = cursor.execute(query).fetchall()

        for result_tuple in total:
            for price in result_tuple:
                if price is None:
                    total_price = total_price + 0
                else:
                    total_price = total_price + price
    cursor.close()
    conn.close()
    return total_price


def show_updated_products_db(med_code):
    conn = sqlite3.connect('med_db.db')
    cursor = conn.cursor()
    query = "SELECT name, currentPrice, sellPublicQuetzal, url FROM products WHERE medCode=?"
    cursor.execute(query, (med_code,))
    result = cursor.fetchall()
    cursor.close()
    conn.close()
    db_names = ["name", "currentPrice", "sellPublicQuetzal", "url"]
    return result, db_names, bool(result)


app = Flask(__name__)


@app.route('/', methods=["GET", "POST"])
def index():
    with sqlite3.connect('med_db.db') as conn:
        cursor = conn.cursor()
        query = """SELECT * FROM products;"""
        products = cursor.execute(query).fetchall()
    cursor.close()
    conn.close()
    return render_template("index.html", products=products)


@app.route('/edit', methods=["GET", "POST"])
def edit():
    med_code = request.form.get('med_code') or request.args.get('med_code')

    if request.method == 'POST':
        # If there is no med_code it will continue redirecting to the same page
        if med_code is None:
            return render_template("edit.html")
        else:
            result, db_names, record_exists = show_updated_products_db(med_code)
            change_list = request.form.getlist('changeList[]')
            if not record_exists:
                return render_template("error.html", error_message="Invalid form data")

            # If there is data in changeList it means it is ready to update Data
            if len(change_list) != 0:
                name = request.form.getlist('changeList[]')[0]
                current_price = request.form.getlist('changeList[]')[1]
                current_price_db = search_element("products", "currentPrice", med_code)
                sell_public_q = request.form.getlist('changeList[]')[2]
                url = request.form.getlist('changeList[]')[3]

                # If prices in db do not match with price given the db will be updated to the price given,
                # otherwise it will not be modified, nor taxed again
                if round(current_price_db, 2) != round(float(current_price), 2):
                    current_price = price_taxed(request.form.getlist('changeList[]')[1])

                update_products_db(name, current_price, sell_public_q, url, med_code)

                result, db_names, record_exists = show_updated_products_db(med_code)
            return render_template("edit.html", result=result, db_names=db_names, med_code=med_code)

    else:
        result = None
        db_names = None

    return render_template("edit.html")


@app.route('/add', methods=["GET", "POST"])
def add_inventory():
    if request.method == 'POST':
        form_data = request.form
        check_elements =['product','price_d', 'sell_public', 'url']
        # Validate form data
        if not validate_form_data(form_data, check_elements):
            # If validation fails, you can redirect or render an error page
            return render_template("error.html", error_message="Invalid form data")
        try:
            product = request.form['product']
            price_d = price_taxed(float(request.form['price_d']))
            price_q = round(price_d * quetzal, 2)
            sell_public = price_taxed(float(request.form['sell_public']))
            url = request.form['url']
        except ValueError:
            return render_template("error.html", error_message="Invalid form data")

        med_code = code_generator()
        insert_column_values("products", {
                    "medCode": med_code,
                    "name": product,
                    "currentPrice": price_d,
                    "priceQuetzal": price_q,
                    "sellPublicQuetzal": sell_public,
                    "url": url,
                })

    products = show_products_receipt("products")
    return render_template("add_product.html", products=products)


@app.route('/receipt', methods=["GET", "POST"])
def receipt():
    # Get info when page is loaded
    total_q, total_d, payed_q, payed_d, balance_bank_q, balance_bank_d, remainder_q, remainder_d = get_balance()
    products = show_products_receipt()
    total_price_products = get_total("receipt", "totalPriceQuetzal")
    if request.method == 'POST':
        form_data = request.form
        check_elements = ['product', 'amount','price', 'sell_public', 'url']

        # Validate form data of products
        if not validate_form_data(form_data, check_elements):
            # If validation fails, you can redirect or render an error page
            return render_template("error.html", error_message="Invalid form data")

        # Get info ONLY from products form
        if 'product' in request.form and 'amount' in request.form and 'price' in request.form:
            product = request.form['product']
            amount = int(request.form['amount'])
            price = price_taxed(float(request.form['price']))
            price_q = round(price * quetzal, 2)
            total_price = round(price_q * amount,2)
            print(total_price)
            add_data_receipt_db(product, amount, price, price_q, total_price)
            total_price_products = get_total("receipt", "totalPriceQuetzal")
            products = show_products_receipt()

        # Get info ONLY from balance form
        if 'add_payment' in request.form:
            add_payment = round(float(request.form['add_payment']), 2)
            insert_element("balance", "payedQuetzal", add_payment)
            insert_element("balance", "balanceBankQuetzal", add_payment)

        if 'add_bank_balance' in request.form:
            bank_balance = round(float(request.form['add_bank_balance']), 2)
            insert_element("balance", "balanceBankQuetzal", bank_balance)

        # refresh all the variables when add data
        total_q, total_d, payed_q, payed_d, balance_bank_q, balance_bank_d, remainder_q, remainder_d = get_balance()

        return render_template("receipt.html", products=products,
                               total_q=total_q, total_d=total_d, payed_q=payed_q, payed_d=payed_d,
                               balance_bank_q=balance_bank_q, balance_bank_d=balance_bank_d,
                               remainder_q=remainder_q, remainder_d=remainder_d)

    return render_template("receipt.html", products=products,
                           total_q=total_q, total_d=total_d, payed_q=payed_q, payed_d=payed_d,
                           balance_bank_q=balance_bank_q, balance_bank_d=balance_bank_d,
                           remainder_q=remainder_q, remainder_d=remainder_d)


@app.route('/receipt/user', methods=["GET", "POST"])
def add_user():
    conn = sqlite3.connect('med_db.db')
    cursor = conn.cursor()
    data_user = None

    if 'name' in request.form:
        user_name = request.form['name']
        if table_empty("orders") is True:
            data_user = 0

        # Find user_id based on the given user_name
        user_id_query = "SELECT id FROM users WHERE username = ?"
        user_id_result = cursor.execute(user_id_query, (user_name,)).fetchone()

        if user_id_result is None:
            insert_element("users", "username", user_name)

        products = show_products_receipt()
        conn.close()
        return redirect(url_for("receipt_order", products=products, data_user=data_user, user_name=user_name))
    else:
        user_name = "Cliente"
        products = show_products_receipt()
        conn.close()
        return render_template("add_user_receipt.html", products=products, data_user=data_user, user_name=user_name)


@app.route('/receipt/add_order', methods=["GET", "POST"])
def receipt_order():
    username = request.args.get('user_name')
    conn = sqlite3.connect('med_db.db')
    cursor = conn.cursor()

    if username is None:
        username = request.form.get('user_name')
        if username is None:
            return redirect(url_for("add_user"))

    if table_empty("orders"):
        data_user = None
    else:
        data_user = "data_available"

    if request.method == 'POST':
        form_data = request.form
        arr_elements = ['amount', 'id']

        # Check if values are entered correctly
        if not validate_form_data(form_data, arr_elements):
            error_message = f"Not amount or id provided"
            return render_template("error.html", error_message=error_message)

        username = request.form.get('user_name')
        amount = int(request.form['amount'])
        product_id = int(request.form['id'])
        product_name = search_element("receipt", "product", "med000", product_id)
        price_dollar = search_element("receipt", "price", "med000", product_id)

        # Check if ID of product is found
        if product_name is None:
            error_message = f"Product with ID {product_id} not found."
            return render_template("error.html", error_message=error_message)

        unit_price_q = round(price_dollar * quetzal, 2)
        total_price = amount * unit_price_q

        # If username is not provided it will automatically be "Cliente"
        if username == "":
            username = "Cliente"

        # Find user_id based on the given user_name
        user_id_query = "SELECT id FROM users WHERE username = ?"
        user_id_result = cursor.execute(user_id_query, (username,)).fetchone()

        if user_id_result is not None:
            user_id = user_id_result[0]
        else:
            # If the username doesn't exist, insert a new user
            insert_column_values("users", {"username": username})
            # Retrieve the user_id for the newly inserted user
            user_id = cursor.lastrowid

        # Find product details
        product_query = "SELECT * FROM receipt WHERE id = ?"
        product_result = cursor.execute(product_query, (product_id,)).fetchone()

        if product_result is not None:
            # Insert into the orders table with user_id
            insert_column_values("orders", {
                "user_id": user_id,
                "user_name": username,
                "product_id": product_id,
                "amount": amount,
                "total_price": total_price,
                "product_name": product_name,
                "unit_price_q": unit_price_q
            })
        else:
            error_message = f"Product with ID {product_id} not found."
            return render_template("error.html", error_message=error_message)

        # Fetch order details
        order = show_products_receipt("orders")

        products = show_products_receipt()
        conn.close()
        if table_empty("orders") is True:
            data_user = "data"

        return render_template("user_receipt.html", orders=order, products=products, data_user=data_user, user_name=username)

    order = show_products_receipt("orders")
    products = show_products_receipt()
    conn.close()

    return render_template("user_receipt.html", orders=order, products=products, data_user=data_user, user_name=username)


@app.route('/orders')
def orders():
    order = show_products_receipt("orders")
    return render_template("orders.html", orders=order)


@app.route('/receipt/delete_order/<int:order_id>', methods=['POST'])
def delete_order(order_id):
    # Get username so it  will not be redirected to add_user()
    username = request.args.get('username')
    if username is None:
        username = request.form.get('username')
    conn = sqlite3.connect('med_db.db')
    cursor = conn.cursor()

    # Delete the record from the 'orders' table based on order_id
    delete_query = "DELETE FROM orders WHERE id = ?"
    cursor.execute(delete_query, (order_id,))

    # Commit the changes to the database
    conn.commit()
    conn.close()

    # Redirect back to the receipt page after deletion
    return redirect(url_for('receipt_order', username = username))


@app.route('/delete_data/<int:order_id>', methods=['POST'])
def delete_product(order_id):
    conn = sqlite3.connect('med_db.db')
    cursor = conn.cursor()

    # Delete the record from the 'products' table based on order_id
    delete_query = "DELETE FROM products WHERE id = ?"
    cursor.execute(delete_query, (order_id,))

    # Commit the changes to the database
    conn.commit()
    conn.close()

    # Redirect back to the receipt page after deletion
    return redirect(url_for('index'))


if __name__ == '__main__':
    create_db()
    app.run()
