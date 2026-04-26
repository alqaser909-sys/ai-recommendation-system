from flask import Flask, request, redirect, session, render_template_string
import pandas as pd
import os
from functools import lru_cache

from recommender import RecommendationEngine

app = Flask(__name__)
app.secret_key = "simple-secret-key"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
USERS_FILE = os.path.join(BASE_DIR, "users.csv")
PRODUCTS_FILE = os.path.join(BASE_DIR, "products.csv")
RATINGS_FILE = os.path.join(BASE_DIR, "ratings.csv")
BEHAVIOR_FILE = os.path.join(BASE_DIR, "behavior.csv")

users = pd.read_csv(USERS_FILE)
products_df = pd.read_csv(PRODUCTS_FILE)
ratings = pd.read_csv(RATINGS_FILE)
behavior = pd.read_csv(BEHAVIOR_FILE)

def read_excel(file_name):
    return pd.read_csv(file_name)

def get_products():
    return products_df

engine = RecommendationEngine(
    USERS_FILE,
    PRODUCTS_FILE,
    RATINGS_FILE,
    BEHAVIOR_FILE
)

def get_engine():
    return engine

@lru_cache(maxsize=100)
def cached_recommend(user_id):
    pool = engine.get_initial_pool_on_login(user_id)
    return engine.get_genetic_optimized_recommendations(user_id, pool)

def save_behavior(user_id, product_id, action):
    global behavior

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

    if action in ["clicked", "purchased"]:
        behavior.to_csv(BEHAVIOR_FILE, index=False)