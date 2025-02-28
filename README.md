# How to run the program
1. Install python 3.11
2. Install packages with `pip install -r requirements.txt`
3. create a `data/` folder at the root of the project if there is none
4. use python `src/main.py` to run the program

# What the program does
The program will read the data from the `app_list.json` file and fetch all reviews for each app in the list. 
The program will then save the reviews in individual csv file in the data folder and into a single file named `all_reviews.csv`