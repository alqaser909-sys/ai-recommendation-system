from flask import Flask, request, redirect, session, render_template_string
import pandas as pd
import os
import numpy as np
from recommender import RecommendationEngine

app = Flask(__name__)
app.secret_key = "simple-secret-key"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
USERS_FILE = os.path.join(BASE_DIR, "users.xlsx")
PRODUCTS_FILE = os.path.join(BASE_DIR, "products.xlsx")
RATINGS_FILE = os.path.join(BASE_DIR, "ratings.xlsx")
BEHAVIOR_FILE = os.path.join(BASE_DIR, "behavior.xlsx")


def read_excel(file_name):
    return pd.read_excel(file_name, engine="openpyxl")


def get_engine():
    return RecommendationEngine(USERS_FILE, PRODUCTS_FILE, RATINGS_FILE, BEHAVIOR_FILE)


def save_behavior(user_id, product_ids, action):
    behavior = read_excel(BEHAVIOR_FILE)
    for col in ["viewed", "clicked", "purchased"]:
        if col not in behavior.columns:
            behavior[col] = 0
    user_id = int(user_id)
    if not isinstance(product_ids, list):
        product_ids = [product_ids]
    for p_id in product_ids:
        p_id = int(p_id)
        same_row = (behavior["user_id"].astype(int) == user_id) & (
            behavior["product_id"].astype(int) == p_id
        )
        if same_row.any():
            behavior.loc[same_row, action] = 1
        else:
            new_row = {
                "user_id": user_id,
                "product_id": p_id,
                "viewed": 0,
                "clicked": 0,
                "purchased": 0,
            }
            new_row[action] = 1
            behavior = pd.concat([behavior, pd.DataFrame([new_row])], ignore_index=True)
    behavior.to_excel(BEHAVIOR_FILE, index=False, engine="openpyxl")


# --- HTML TEMPLATES ---

LOGIN_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>Login | Smart Store</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); height: 100vh; display: flex; align-items: center; justify-content: center; margin: 0; }
        .login-card { background: white; padding: 40px; border-radius: 20px; box-shadow: 0 15px 35px rgba(0,0,0,0.3); width: 100%; max-width: 400px; text-align: center; }
        input { width: 100%; padding: 12px; margin: 10px 0; border: 2px solid #eee; border-radius: 10px; box-sizing: border-box; }
        button { width: 100%; padding: 15px; background: #1e3c72; color: white; border: none; border-radius: 10px; font-size: 18px; font-weight: bold; cursor: pointer; }
    </style>
</head>
<body>
    <div class="login-card">
        <h2>Smart Store</h2>
        <p>Login with your User ID</p>
        <form method="post">
            <input type="number" name="user_id" placeholder="User ID" required>
            <button type="submit">Sign In</button>
        </form>
    </div>
</body>
</html>
"""

HOME_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>Smart Store | Home</title>
    <style>
        body { font-family: 'Segoe UI', Arial; background: #f8f9fa; margin: 0; overflow-x: hidden; }
        .navbar { background: white; padding: 15px 50px; display: flex; justify-content: space-between; box-shadow: 0 2px 10px rgba(0,0,0,0.05); position: sticky; top: 0; z-index: 100; }
        .container { max-width: 1200px; margin: 30px auto; padding: 0 20px; }
        .header-box { text-align: center; margin-bottom: 40px; }
        .improve-btn { display: inline-block; padding: 15px 35px; background: #ff4757; color: white; text-decoration: none; border-radius: 50px; font-weight: bold; box-shadow: 0 4px 15px rgba(255, 71, 87, 0.3); transition: 0.3s; }
        .improve-btn:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(255, 71, 87, 0.4); }
        .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 25px; }
        .card { background: white; padding: 20px; border-radius: 15px; box-shadow: 0 5px 15px rgba(0,0,0,0.05); position: relative; border: 1px solid #eee; display: flex; flex-direction: column; justify-content: space-between; transition: 0.3s; }
        .card:hover { transform: translateY(-5px); box-shadow: 0 10px 25px rgba(0,0,0,0.1); }
        .recommend-border { border: 2px solid #ff4757; background: #fffafb; }
        .badge { position: absolute; top: 15px; right: 15px; background: #ff4757; color: white; padding: 4px 12px; border-radius: 20px; font-size: 11px; font-weight: bold; }
        .price { font-size: 1.4em; color: #2ed573; font-weight: bold; margin: 10px 0; }
        .info-box { background: #f1f2f6; padding: 12px; border-radius: 10px; margin: 15px 0; font-size: 0.85em; line-height: 1.4; border-left: 4px solid #ff4757; }
        .btn-open { display: block; text-align: center; padding: 12px; background: #2f3542; color: white; text-decoration: none; border-radius: 10px; font-weight: bold; }
        
        /* GA Monitor Styles */
        #monitor-panel { position: fixed; top: 0; right: -350px; width: 320px; height: 100%; background: white; box-shadow: -10px 0 30px rgba(0,0,0,0.1); z-index: 1001; transition: 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275); padding: 30px; box-sizing: border-box; }
        .monitor-active { right: 0 !important; }
        .monitor-btn { position: fixed; bottom: 30px; right: 30px; width: 60px; height: 60px; border-radius: 50%; background: #1e3c72; color: white; border: none; cursor: pointer; z-index: 1000; box-shadow: 0 5px 20px rgba(30, 60, 114, 0.4); font-size: 24px; display: flex; align-items: center; justify-content: center; }
        .stat-item { margin-bottom: 20px; padding: 15px; background: #f8f9fa; border-radius: 12px; }
        .stat-label { font-size: 12px; color: #777; text-transform: uppercase; letter-spacing: 1px; }
        .stat-value { font-size: 18px; font-weight: bold; color: #1e3c72; display: block; margin-top: 5px; }
        
        /* Animation Loader */
        #ga-loader { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(30, 60, 114, 0.98); z-index: 2000; color: white; flex-direction: column; align-items: center; justify-content: center; }
        .loader-bar { width: 300px; height: 8px; background: rgba(255,255,255,0.1); border-radius: 10px; overflow: hidden; margin-top: 25px; }
        .loader-progress { width: 0%; height: 100%; background: #ff4757; transition: 0.4s; }
    </style>
</head>
<body>
    <div id="ga-loader">
        <h2 id="loader-text">Analyzing Behavior...</h2>
        <div class="loader-bar"><div class="loader-progress" id="p-bar"></div></div>
    </div>

    <button class="monitor-btn" onclick="toggleMonitor()">📊</button>
    
    <div id="monitor-panel">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:30px;">
            <h3 style="margin:0; color:#1e3c72;">GA Live Insights</h3>
            <button onclick="toggleMonitor()" style="background:none; border:none; font-size:24px; cursor:pointer;">&times;</button>
        </div>
        <div class="stat-item">
            <span class="stat-label">User Target Budget</span>
            <span class="stat-value">${{ intel.target_price }}</span>
        </div>
        <div class="stat-item">
            <span class="stat-label">Active Interest</span>
            <span class="stat-value" style="font-size:14px; color:#ff4757;">{{ intel.fav_cats or 'General Exploration' }}</span>
        </div>
        <div class="stat-item">
            <span class="stat-label">Blacklisted Items</span>
            <span class="stat-value">{{ intel.blacklist_count }} Items</span>
        </div>
        <div style="background:#eef2f7; padding:15px; border-radius:12px; font-size:0.85em;">
            <strong style="color:#1e3c72;">Engine Configuration:</strong><br>
            <div style="margin-top:10px; display:flex; justify-content:space-between;">
                <span>Pop Size: 80</span>
                <span>Gens: 50</span>
            </div>
            <div style="margin-top:5px; color:#2ed573; font-weight:bold;">Status: System Evolving...</div>
        </div>
    </div>

    <div class="navbar">
        <h2>Smart<span style="color:#ff4757;">Store</span></h2>
        <div style="font-weight:500;">User ID: {{ user_id }} | <a href="/logout" style="color:#ff4757; text-decoration:none;">Logout</a></div>
    </div>

    <div class="container">
        <div class="header-box">
            {% if not is_recommendation %}
                <h1>Product Catalog</h1>
                <p style="color:#666;">Explore our standard collection or use AI to evolve your feed.</p>
                <a href="/home?improve=1" onclick="runGAEffect(event)" class="improve-btn">✨ EVOLVE MY FEED</a>
            {% else %}
                <h1 style="color:#ff4757;">Evolved Recommendations</h1>
                <p style="color:#666;">Genetic Algorithm optimized these results based on your real-time behavior.</p>
                <a href="/home" class="improve-btn" style="background:#747d8c; box-shadow:none;">⬅ BACK TO CATALOG</a>
            {% endif %}
        </div>

        <div class="grid">
            {% for p in products %}
            <div class="card {% if is_recommendation %}recommend-border{% endif %}">
                {% if is_recommendation %}<div class="badge">AI MATCH</div>{% endif %}
                <div>
                    <h4 style="margin:0; font-size:1.1em;">Product #{{ p.product_id }}</h4>
                    <p style="color:#888; font-size:0.85em; text-transform:uppercase; margin:5px 0;">{{ p.category }}</p>
                    <p class="price">${{ p.price }}</p>
                    {% if is_recommendation %}
                    <div class="info-box">
                        <b style="color:#ff4757;">Fitness: {{ p.score }}%</b><br>
                        {{ p.reason }}
                    </div>
                    {% endif %}
                </div>
                <a class="btn-open" href="/click/{{ p.product_id }}?improve={{ '1' if is_recommendation else '0' }}">View Details</a>
            </div>
            {% endfor %}
        </div>
    </div>

    <script>
    function toggleMonitor() {
        document.getElementById('monitor-panel').classList.toggle('monitor-active');
    }

    function runGAEffect(event) {
        event.preventDefault();
        const url = event.target.href;
        const loader = document.getElementById('ga-loader');
        const pBar = document.getElementById('p-bar');
        const text = document.getElementById('loader-text');

        loader.style.display = 'flex';
        
        const steps = [
            {t: "Initializing Population (80 Chromosomes)...", p: 25, d: 0},
            {t: "Calculating Fitness (Price vs Interest)...", p: 50, d: 1000},
            {t: "Executing Crossover & Mutation (Rate 15%)...", p: 85, d: 2000},
            {t: "Selection Complete! Generating View...", p: 100, d: 2800}
        ];

        steps.forEach((step) => {
            setTimeout(() => {
                text.innerText = step.t;
                pBar.style.width = step.p + "%";
            }, step.d);
        });

        setTimeout(() => {
            window.location.href = url;
        }, 3200);
    }
</script>
</body>
</html>
"""

PRODUCT_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>Product Details</title>
    <style>
        body { font-family: 'Segoe UI', Arial; background: #f4f7f6; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }
        .box { background: white; padding: 50px; border-radius: 25px; box-shadow: 0 20px 50px rgba(0,0,0,0.05); text-align: center; width: 450px; }
        .price { font-size: 2.5em; color: #2ed573; font-weight: 800; margin: 25px 0; }
        .btn { display: inline-block; padding: 15px 35px; border-radius: 12px; text-decoration: none; font-weight: bold; transition: 0.3s; margin: 5px; }
        .btn-buy { background: #ff4757; color: white; border: none; box-shadow: 0 5px 15px rgba(255, 71, 87, 0.3); }
        .btn-back { background: #f1f2f6; color: #2f3542; }
        .success-msg { background: #e7f9ee; color: #2ecc71; padding: 15px; border-radius: 10px; margin-bottom: 20px; font-weight: bold; }
    </style>
</head>
<body>
    <div class="box">
        {% if message %} <div class="success-msg">✓ {{ message }}</div> {% endif %}
        <h4 style="color:#888; margin:0;">{{ product.category }}</h4>
        <h1 style="margin:10px 0;">Product #{{ product.product_id }}</h1>
        <div class="price">${{ product.price }}</div>
        
        <div style="margin-top:30px;">
            <a class="btn btn-buy" href="/buy/{{ product.product_id }}?improve={{ '1' if is_imp else '0' }}">Buy Now</a>
            <a class="btn btn-back" href="/home{{ '?improve=1' if is_imp else '' }}">Back to List</a>
        </div>
    </div>
</body>
</html>
"""

# --- ROUTES ---


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
    is_imp = request.args.get("improve", "0") == "1"
    engine = get_engine()

    # Intelligence Data for Monitor
    profile = engine._get_user_context(user_id)
    intel = {
        "target_price": round(profile["target_price"], 2),
        "fav_cats": ", ".join(profile["fav_cats"][:3]),
        "blacklist_count": len(profile["blacklist"]),
    }

    if is_imp:
        pool = engine.get_initial_pool_on_login(user_id)
        recs = engine.get_genetic_optimized_recommendations(user_id, pool)
        save_behavior(user_id, [p["product_id"] for p in recs], "viewed")
        return render_template_string(
            HOME_PAGE,
            user_id=user_id,
            products=recs,
            is_recommendation=True,
            intel=intel,
        )
    else:
        pool_ids = engine.get_initial_pool_on_login(user_id)
        normal_list = []
        for p_id in pool_ids[:25]:
            if p_id in engine.products_dict:
                p_data = engine.products_dict[p_id].copy()
                p_data["product_id"] = p_id
                normal_list.append(p_data)
        save_behavior(user_id, [p["product_id"] for p in normal_list], "viewed")
        return render_template_string(
            HOME_PAGE,
            user_id=user_id,
            products=normal_list,
            is_recommendation=False,
            intel=intel,
        )


@app.route("/click/<int:product_id>")
def click_product(product_id):
    if "user_id" not in session:
        return redirect("/")
    is_imp = request.args.get("improve", "0") == "1"
    save_behavior(session["user_id"], [product_id], "clicked")
    engine = get_engine()
    product = engine.products_dict[product_id].copy()
    product["product_id"] = product_id
    return render_template_string(
        PRODUCT_PAGE,
        product=product,
        message="Product Logged to Context",
        is_imp=is_imp,
    )


@app.route("/buy/<int:product_id>")
def buy_product(product_id):
    if "user_id" not in session:
        return redirect("/")
    is_imp = request.args.get("improve", "0") == "1"
    save_behavior(session["user_id"], [product_id], "purchased")
    engine = get_engine()
    product = engine.products_dict[product_id].copy()
    product["product_id"] = product_id
    return render_template_string(
        PRODUCT_PAGE,
        product=product,
        message="Purchase Complete! Blacklist Updated.",
        is_imp=is_imp,
    )


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)