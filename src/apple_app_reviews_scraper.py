import random

import pandas as pd
import requests
import re
import time
from tqdm import tqdm
import datetime


def get_token(country: str, app_name: str, app_id: str, user_agents: list) -> str:
    """
    Retrieves the bearer token required for API requests
    Regex adapted from base.py of https://github.com/cowboy-bebug/app-store-scraper
    """

    response = requests.get(f'https://apps.apple.com/{country}/app/{app_name}/id{app_id}',
                            headers={'User-Agent': random.choice(user_agents)},
                            )

    if response.status_code != 200:
        print(f"GET request failed. Response: {response.status_code} {response.reason}")

    token = None
    tags = response.text.splitlines()
    for tag in tags:
        if re.match(r"<meta.+web-experience-app/config/environment", tag):
            token = re.search(r"token%22%3A%22(.+?)%22", tag).group(1)

    if token is None:
        raise ValueError("Token not found.")

    # print(f"Bearer {token}")
    return token


def fetch_reviews(country: str,
                  app_name: str,
                  app_id: str,
                  user_agents: list,
                  token: str,
                  offset: str = '1'
                  ) -> tuple[list[dict], str | None, int]:
    """
    Fetches reviews for a given app from the Apple App Store API.

    - Default sleep after each call to reduce risk of rate limiting
    - Retry with increasing backoff if rate-limited (429)
    - No known ability to sort by date, but the higher the offset, the older the reviews tend to be
    """

    ## Define request headers and params ------------------------------------
    landing_url = f'https://apps.apple.com/{country}/app/{app_name}/id{app_id}'
    request_url = f'https://amp-api.apps.apple.com/v1/catalog/{country}/apps/{app_id}/reviews'

    MAX_RETURN_LIMIT = '20'

    headers = {
        'Accept': 'application/json',
        'Authorization': f'bearer {token}',
        'Connection': 'keep-alive',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'Origin': 'https://apps.apple.com',
        'Referer': landing_url,
        'User-Agent': random.choice(user_agents)
    }

    params = (
        ('l', 'fr-FR'),  # language
        ('offset', str(offset)),  # paginate this offset
        ('limit', MAX_RETURN_LIMIT),  # max valid is 20
        ('platform', 'web'),
        ('additionalPlatforms', 'appletv,ipad,iphone,mac')
    )

    ## Perform request & exception handling ----------------------------------
    retry_count = 0
    MAX_RETRIES = 5
    BASE_DELAY_SECS = 10
    # Assign dummy variables in case of GET failure
    result = {'data': [], 'next': None}
    reviews = []
    response = None
    while retry_count < MAX_RETRIES:

        # Perform request
        response = requests.get(request_url, headers=headers, params=params)

        # SUCCESS
        # Parse response as JSON and exit loop if request was successful
        if response.status_code == 200:
            result = response.json()
            reviews = result['data']
            if len(reviews) < 20:
                print(f"{len(reviews)} reviews scraped. This is fewer than the expected 20.")
            break

        # FAILURE
        elif response.status_code != 200:
            print(f"GET request failed. Response: {response.status_code} {response.reason}")

            # RATE LIMITED
            if response.status_code == 429:
                # Perform backoff using retry_count as the backoff factor
                retry_count += 1
                backoff_time = BASE_DELAY_SECS * retry_count
                print(f"Rate limited! Retrying ({retry_count}/{MAX_RETRIES}) after {backoff_time} seconds...")

                with tqdm(total=backoff_time, unit="sec", ncols=50) as pbar:
                    for _ in range(backoff_time):
                        time.sleep(1)
                        pbar.update(1)
                continue

            # NOT FOUND
            elif response.status_code == 404:
                print(f"{response.status_code} {response.reason}. There are no more reviews.")
                break

    if response is None:
        return [], None, 0

    ## Final output ---------------------------------------------------------
    # Get pagination offset for next request
    if 'next' in result and result.get('next') is not None:
        offset_pattern = re.compile(r"^.+offset=([0-9]+).*$")
        offset = re.search(offset_pattern, result.get('next')).group(1)
        print(f"Offset: {offset}")
    else:
        offset = None
        print("No offset found.")

    # Append offset, number of reviews in batch, and app_id
    for rev in reviews:
        rev['app_id'] = app_id
        rev['app_name'] = app_name

    # Default sleep to decrease rate of calls
    time.sleep(0.5)
    return reviews, offset, response.status_code


def fetch_multiple_reviews(country: str,
                           app_name: str,
                           app_id: str,
                           user_agents: list,
                           token: str
                           ) -> pd.DataFrame:
    data = pd.DataFrame()
    offset = '1'
    while offset is not None:
        reviews, offset, _ = fetch_reviews(country=country,
                                           app_name=app_name,
                                           app_id=app_id,
                                           user_agents=user_agents,
                                           token=token,
                                           offset=offset
                                           )
        data = pd.concat([data, pd.json_normalize(reviews)])
        print(f"Data shape: {data.shape}")

    return data

def start_fetching(app_list,
                   country,
                   user_agents,
                   columns_naming,
                   columns_to_drop
                   ):
    df = pd.DataFrame()

    current_date = datetime.datetime.now().strftime("%Y_%m_%d_%H_%M_%S")

    for app in app_list:
        app_name = app.get("app_name")
        print("=====================================================================================================")
        print("App Name: ", app_name)
        token = get_token(country=country,
                          app_name=app_name,
                          app_id=app.get("app_id"),
                          user_agents=user_agents)
        df_app_reviews = fetch_multiple_reviews(country=country,
                                                app_name=app_name,
                                                app_id=app.get("app_id"),
                                                user_agents=user_agents,
                                                token=token)

        df_app_reviews = df_app_reviews.drop(columns=columns_to_drop, errors='ignore')
        df_app_reviews = df_app_reviews.rename(columns=columns_naming, errors='ignore')
        path = f"../data/{current_date}_{app_name}_reviews.csv"
        df_app_reviews.to_csv(path, index=False, sep=";", encoding="utf-8")
        print(f"Saved '{app_name}' data to '{path}'.")

        df = pd.concat([df, df_app_reviews])

    master_path = f"../data/{current_date}_all_reviews.csv"
    df.to_csv(master_path, index=False, sep=";", encoding="utf-8")
    print(f"Saved all apps data to '{master_path}'.")