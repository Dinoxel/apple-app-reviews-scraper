from apple_app_reviews_scraper import start_fetching
import pandas as pd
import json

pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', None)


app_list_path = "../app_list.json"
app_list = json.load(open(app_list_path))

country = "fr"
user_agents = [
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 13_4) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.4 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36',
]

columns_naming = {
    "attributes.date": "review_date",
    "attributes.review": "review_text",
    "attributes.rating": "rating",
    "attributes.title": "review_title",
    "attributes.developerResponse.body": "developer_response",
    "attributes.developerResponse.modified": "developer_response_date",
}
columns_to_drop = [
    "id",
    "type",
    "attributes.isEdited",
    "attributes.userName",
    "attributes.developerResponse.id"
]

if __name__ == "__main__":
    start_fetching(app_list=app_list,
                   country=country,
                   user_agents=user_agents,
                   columns_naming=columns_naming,
                   columns_to_drop=columns_to_drop
                   )
