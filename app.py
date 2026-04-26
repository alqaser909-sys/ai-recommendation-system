from flask import Flask, request, redirect, session, render_template_string
import pandas as pd
import os

from recommender import RecommendationEngine

app = Flask(__name__)
app.secret_key = "simple-secret-key"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
USERS_FILE = os.path.join(BASE_DIR, "users.csv")
PRODUCTS_FILE = os.path.join(BASE_DIR, "products.csv")
RATINGS_FILE = os.path.join(BASE_DIR, "ratings.csv")
BEHAVIOR_FILE = os.path.join(BASE_DIR, "behavior.csv")


def read_excel(file_name):
    return pd.read_excel(file_name, engine="openpyxl")


def get_products():
    return read_excel(PRODUCTS_FILE)


def get_engine():
    return RecommendationEngine(
        USERS_FILE,
        PRODUCTS_FILE,
        RATINGS_FILE,
        BEHAVIOR_FILE
    )


def save_behavior(user_id, product_id, action):
    behavior = read_excel(BEHAVIOR_FILE)

    for col in ["viewed", "clicked", "purchased"]:
        if col not in behavior.columns:
            behavior[col] = 0

    user_id = int(user_id)
    product_id = int(product_id)

    same_row = (
        (behavior["user_id"].astype(int) == user_id) &
        (behavior["product_id"].astype(int) == product_id)
    )

    if same_row.any():
        behavior.loc[same_row, action] = 1
    else:
        new_row = {
            "user_id": user_id,
            "product_id": product_id,
            "viewed": 0,
            "clicked": 0,
            "purchased": 0
        }
        new_row[action] = 1
        behavior = pd.concat([behavior, pd.DataFrame([new_row])], ignore_index=True)

    behavior.to_excel(BEHAVIOR_FILE, index=False, engine="openpyxl")


LOGIN_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>Login</title>
    <style>
        body { font-family: Arial; background: #f4f4f4; padding: 40px; }
        .box { background: white; padding: 25px; max-width: 400px; margin: auto; border-radius: 10px; }
        input, button { width: 100%; padding: 10px; margin-top: 10px; }
        button { background: #222; color: white; border: none; cursor: pointer; }
    </style>
</head>
<body>
    <div class="box">
        <h2>Login</h2>
        <form method="post">
            <label>Enter User ID</label>
            <input type="number" name="user_id" required>
            <button type="submit">Login</button>
        </form>
    </div>
</body>
</html>
"""


HOME_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>Products</title>
    <style>
        body { font-family: Arial; background: #f4f4f4; padding: 20px; }
        .top { display: flex; justify-content: space-between; align-items: center; }
        .grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; }
        .card { background: white; padding: 15px; border-radius: 10px; }
        a.button { display: inline-block; padding: 8px 12px; background: #222; color: white; text-decoration: none; border-radius: 5px; }
        .recommend { border: 2px solid #222; }
    </style>
</head>
<body>
    <div class="top">
        <h2>Welcome User {{ user_id }}</h2>
        <a href="/logout">Logout</a>
    </div>

    <h3>Normal Products</h3>
    <div class="grid">
        {% for p in normal_products %}
        <div class="card">
            <h4>Product #{{ p.product_id }}</h4>
            <p>Category: {{ p.category }}</p>
            <p>Price: {{ p.price }}</p>
            <a class="button" href="/click/{{ p.product_id }}">Open Product</a>
        </div>
        {% endfor %}
    </div>

    <h3>Recommended Products</h3>
    <div class="grid">
        {% for p in recommended_products %}
        <div class="card recommend">
            <h4>Product #{{ p.product_id }}</h4>
            <p>Category: {{ p.category }}</p>
            <p>Price: {{ p.price }}</p>
            <p>Score: {{ p.score }}</p>
            <p>{{ p.reason }}</p>
            <a class="button" href="/click/{{ p.product_id }}">Open Product</a>
        </div>
        {% endfor %}
    </div>
</body>
</html>
"""


PRODUCT_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>Product</title>
    <style>
        body { font-family: Arial; background: #f4f4f4; padding: 40px; }
        .box { background: white; padding: 25px; max-width: 500px; margin: auto; border-radius: 10px; }
        a.button { display: inline-block; padding: 10px 15px; background: #222; color: white; text-decoration: none; border-radius: 5px; margin-right: 10px; }
    </style>
</head>
<body>
    <div class="box">
        <h2>Product #{{ product.product_id }}</h2>
        <p>Category: {{ product.category }}</p>
        <p>Price: {{ product.price }}</p>

        {% if message %}
            <h3>{{ message }}</h3>
        {% endif %}

        <a class="button" href="/buy/{{ product.product_id }}">Buy Product</a>
        <a class="button" href="/home">Back</a>
    </div>
</body>
</html>
"""


@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        session["user_id"] = int(request.form["user_id"])
        return redirect("/home")

    return render_template_string(LOGIN_PAGE)


@app.route("/home")
def home():
    if "user_id" not in session:
        return redirect("/")

    user_id = session["user_id"]

    products = get_products()
    normal_products = products.head(9).to_dict("records")

    for p in normal_products:
        save_behavior(user_id, p["product_id"], "viewed")

    engine = get_engine()
    pool = engine.get_initial_pool_on_login(user_id)
    recommended_products = engine.get_genetic_optimized_recommendations(user_id, pool)

    for p in recommended_products:
        save_behavior(user_id, p["product_id"], "viewed")

    return render_template_string(
        HOME_PAGE,
        user_id=user_id,
        normal_products=normal_products,
        recommended_products=recommended_products
    )


@app.route("/click/<int:product_id>")
def click_product(product_id):
    if "user_id" not in session:
        return redirect("/")

    save_behavior(session["user_id"], product_id, "clicked")

    products = get_products()
    product = products[products["product_id"] == product_id].iloc[0].to_dict()

    return render_template_string(PRODUCT_PAGE, product=product, message="Product clicked")


@app.route("/buy/<int:product_id>")
def buy_product(product_id):
    if "user_id" not in session:
        return redirect("/")

    save_behavior(session["user_id"], product_id, "purchased")

    products = get_products()
    product = products[products["product_id"] == product_id].iloc[0].to_dict()

    return render_template_string(PRODUCT_PAGE, product=product, message="Product purchased")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)