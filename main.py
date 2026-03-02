import datetime
import json
import time
import warnings

import numpy as np
import pandas as pd
import requests
from bs4 import BeautifulSoup

warnings.filterwarnings('ignore')


def range_of_numbers(n):
    return list(range(1, n + 1))


def extract(pages : int, sleep_timer : int):
    def get_urls():
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.75 Safari/537.36'}
        urls_df = pd.DataFrame(columns=['recipe_urls'])

        for page in pages:
            time.sleep(sleep_timer)
            # Meal type can be a range of things - check the filters on the website.
            url = f'https://www.bbcgoodfood.com/search?tab=recipe&mealType=breakfast&sort=rating&page={page}'
            try:
                html = requests.get(url, timeout=10)
                html.raise_for_status()  # catches bad status codes (404, 500 etc)
            except requests.exceptions.Timeout:
                print(f"Timeout on {url}, skipping...")
                continue
            except requests.exceptions.RequestException as e:
                print(f"Failed on {url}: {e}, skipping...")
                continue
            
            soup = BeautifulSoup(html.text, 'html.parser')

            recipe_urls = pd.Series([
                a.get("href") 
                for a in soup.select(".layout-md-rail a[href]")
                ])
            recipe_urls = recipe_urls[(recipe_urls.str.count("-") > 0)
                                      & (recipe_urls.str.contains("/recipes/") == True)
                                      & (recipe_urls.str.contains("category") == False)
                                      & (recipe_urls.str.contains("collection") == False)
                                      & (recipe_urls.str.contains("/premium/") == False)].unique()
            df = pd.DataFrame({"recipe_urls": recipe_urls})
            urls_df = pd.concat([urls_df, df], ignore_index=True)

        urls_df['recipe_urls'] = urls_df['recipe_urls'].astype(str)
        list_urls = urls_df['recipe_urls'].to_list()
        return list_urls

    def get_recipes(list_urls):        
        recipes = []

        for i in range(len(list_urls) - 1):
            time.sleep(sleep_timer)
            url = list_urls[i]
            html = requests.get(url)
            soup = BeautifulSoup(html.text, 'html.parser')

            try:
                recipe_title = soup.find('h1', {'class': 'heading-1'}).text
            except:
                recipe_title = ""
            try:
                difficulty = soup.find_all('div', {'class': 'recipe-cook-and-prep-details__item'})[1].text
            except:
                difficulty = ""
            try:
                serves = soup.find_all('div', {'class': 'recipe-cook-and-prep-details__item'})[0].text
            except:
                serves = ""
            try:
                rating = soup.find_all('span', {'class': 'sr-only'})[26].text
            except:
                rating = ""
            try:
                number_of_review = soup.find('span', {'class': 'rating__count-text body-copy-small'}).text
            except:
                number_of_review = ""
            try:
                target = soup.find_all('div', {'data-testid': 'recipe-cook-and-prep-details-section-time'})
                # A list so you can't work directly on it.
                for div in target:
                    time_child = div.find_all('time')
                    prep_time = time_child[0].text if time_child else None
            except:
                prep_time = ""
            try:
                target = soup.find_all('div', {'data-testid': 'recipe-cook-and-prep-details-section-time'})
                for div in target:
                    time_child = div.find_all('time')
                    cook_time = time_child[1].text if time_child else None
            except:
                cook_time = ""
            try:
                tags = []
                target = soup.find('div', {'data-testid': 'post-header-masthead-tags'})
                for div in target:
                    tags.append(div.text.strip())
                print(tags)
            except:
                tags = []

            try:
                instructions = []
                target = soup.find('ul', {'class': 'method-steps__list'})
                for li in target:
                    child = li.find('p')
                    instructions.append(child.text.strip() + '\n' if child else '')
            except:
                instructions = []

            ingredient_list = []
            ingredients = soup.find_all('span', {'class': 'ingredients-list__item-ingredient'})
            quantities = soup.find_all('span', {'class': 'ingredients-list__item-quantity'})

            max_items = max(len(ingredients), len(quantities))
            for i in range(max_items):
                ingredient_text = ingredients[i].get_text(strip=True) if i < len(ingredients) else ''
                quantity_text = quantities[i].get_text(strip=True) if i < len(quantities) else ''

                ingredient_list.append([quantity_text, ingredient_text])
            
            if not ingredient_list: # If the ingredient list is empty, then nothing else will load.
                ingredient_list = [["", ""]]
                # This is how you handle the case....
            
            # Everything except rating and number of review is missing, and requires fixing in the soup queries.

            recipes.append({
                "title": recipe_title,
                "difficulty": difficulty,
                "serves": serves,
                "rating": rating,
                "reviews": number_of_review,
                "prep_time": prep_time,
                "cook_time": cook_time,
                "tags": tags,                    # keep as list, no need to join
                "ingredients": ingredient_list,  # keep as list too
                "instructions": instructions       # keep as list too
            })
            

        # Concatenates the dataframes, resets and aligns their indexes(?)

        return recipes

    list_urls = get_urls()
    recipes = get_recipes(list_urls)
    return recipes


if __name__ == '__main__':
    # enter how many pages of recipes you would like to scrape
    pages = range_of_numbers(8)
    # Last run: 8 pages.
    # here you can change the amount of time between each request to scrape data
    sleep_timer = 5
    week = datetime.datetime.now().strftime("%Y-%m-%d")

    print(f'Scraping {pages} pages from BBC good food')
    recipes = extract(pages, sleep_timer)
    with open ('recipes_breakfast.json', 'w', encoding='utf-8') as f:
        json.dump(recipes, f, indent=2, ensure_ascii=False)
    print('Complete')
