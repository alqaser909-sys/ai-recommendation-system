import pandas as pd
import numpy as np
import random
from typing import List, Dict


class RecommendationEngine:
    def __init__(self, users_file, products_file, ratings_file, behavior_file):
        """Data loading and cleaning setup"""
        self.df_users = (
            pd.read_excel(users_file).dropna(subset=["user_id"]).drop_duplicates()
        )
        self.df_products = (
            pd.read_excel(products_file).dropna(subset=["product_id"]).drop_duplicates()
        )
        self.df_ratings = (
            pd.read_excel(ratings_file)
            .dropna(subset=["user_id", "product_id"])
            .drop_duplicates()
        )
        self.df_behavior = (
            pd.read_excel(behavior_file)
            .dropna(subset=["user_id", "product_id"])
            .drop_duplicates()
        )

        # O(1) Access optimization
        self.products_dict = self.df_products.set_index("product_id").to_dict("index")

    def _get_user_context(self, user_id: int):
        """Analyze user behavior, preferences, and budget"""
        u_behavior = self.df_behavior[self.df_behavior["user_id"] == user_id]
        u_ratings = self.df_ratings[self.df_ratings["user_id"] == user_id]

        interacted_ids = u_behavior["product_id"].unique()
        fav_cats = list(
            set(
                [
                    self.products_dict[pid]["category"]
                    for pid in interacted_ids
                    if pid in self.products_dict
                ]
            )
        )

        # Calculate target budget based on purchases and clicks
        interest_ids = u_behavior[
            (u_behavior["purchased"] == 1) | (u_behavior["clicked"] == 1)
        ]["product_id"].unique()
        if len(interest_ids) > 0:
            target_price = np.mean(
                [
                    self.products_dict[pid]["price"]
                    for pid in interest_ids
                    if pid in self.products_dict
                ]
            )
        else:
            target_price = self.df_products["price"].mean()

        # Blacklist logic: exclude already purchased and low-rated products
        purchased_ids = u_behavior[u_behavior["purchased"] == 1]["product_id"].tolist()
        bad_ratings = u_ratings[u_ratings["rating"] <= 2]["product_id"].tolist()
        blacklist = set(purchased_ids + bad_ratings)

        return {
            "fav_cats": fav_cats,
            "target_price": target_price,
            "blacklist": blacklist,
        }

    def get_initial_pool_on_login(self, user_id: int) -> List[int]:
        """Filtering candidate products for the Genetic Algorithm"""
        profile = self._get_user_context(user_id)
        pool = []

        for p_id, info in self.products_dict.items():
            if p_id in profile["blacklist"]:
                continue

            price_match = abs(info["price"] - profile["target_price"]) <= (
                0.3 * profile["target_price"]
            )
            if info["category"] in profile["fav_cats"] or price_match:
                pool.append(p_id)

        # Ensure pool size for diversity
        if len(pool) < 50:
            rem = list(
                set(self.products_dict.keys()) - set(pool) - profile["blacklist"]
            )
            pool.extend(random.sample(rem, min(50 - len(pool), len(rem))))

        return random.sample(pool, min(len(pool), 100))

    def get_genetic_optimized_recommendations(
        self, user_id: int, initial_pool: List[int]
    ) -> List[Dict]:
        """Genetic Algorithm to evolve the best 5-product recommendation list"""
        profile = self._get_user_context(user_id)

        def fitness(chromosome):
            """Evaluate list quality based on category, price, and diversity"""
            score = 0
            seen_cats = set()
            for p_id in chromosome:
                if p_id not in self.products_dict:
                    continue
                p = self.products_dict[p_id]

                # Category relevance
                if p["category"] in profile["fav_cats"]:
                    score += 20

                # Price suitability
                price_diff = (
                    abs(p["price"] - profile["target_price"]) / profile["target_price"]
                )
                score += max(0, 15 * (1 - price_diff))

                # Hard Penalty for blacklisted items
                if p_id in profile["blacklist"]:
                    score -= 2000

                seen_cats.add(p["category"])

            # Diversity bonus
            score += len(seen_cats) * 10
            return score

        # GA Parameters
        pop_size, generations = 80, 50
        population = [random.sample(initial_pool, 5) for _ in range(pop_size)]

        for _ in range(generations):
            population = sorted(population, key=fitness, reverse=True)
            new_gen = population[:10]  # Elitism

            while len(new_gen) < pop_size:
                p1, p2 = random.sample(population[:25], 2)

                # Crossover
                cut = random.randint(1, 4)
                child = list(dict.fromkeys(p1[:cut] + p2[cut:]))

                # Refill if crossover caused duplicates
                while len(child) < 5:
                    candidate = random.choice(initial_pool)
                    if candidate not in child:
                        child.append(candidate)

                # Mutation
                if random.random() < 0.15:
                    idx = random.randint(0, 4)
                    mutant = random.choice(initial_pool)
                    if mutant not in child:
                        child[idx] = mutant

                new_gen.append(child[:5])
            population = new_gen

        # Final selection
        best_chromosome = sorted(population, key=fitness, reverse=True)[0]

        results = []
        for p_id in best_chromosome:
            p = self.products_dict[p_id]
            results.append(
                {
                    "product_id": int(p_id),
                    "category": p["category"],
                    "price": float(p["price"]),
                    "score": round(fitness([p_id]), 2),
                    "reason": f"Matches interest in {p['category']} and budget ({round(profile['target_price'])}).",
                }
            )
        return results
