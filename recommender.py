class RecommendationEngine:
    def __init__(self, users_file, products_file, ratings_file, behavior_file):
        self.df_users = (
            pd.read_csv(users_file).dropna(subset=["user_id"]).drop_duplicates()
        )
        self.df_products = (
            pd.read_csv(products_file).dropna(subset=["product_id"]).drop_duplicates()
        )
        self.df_ratings = (
            pd.read_csv(ratings_file)
            .dropna(subset=["user_id", "product_id"])
            .drop_duplicates()
        )
        self.df_behavior = (
            pd.read_csv(behavior_file)
            .dropna(subset=["user_id", "product_id"])
            .drop_duplicates()
        )

        self.products_dict = self.df_products.set_index("product_id").to_dict("index")