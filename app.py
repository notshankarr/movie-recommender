import streamlit as st
import pymongo
import requests
import pandas as pd

# MongoDB setup
client = pymongo.MongoClient('mongodb://127.0.0.1:27017/')
db = client['cineMatchDB']
movies_collection = db['movies']

# The Movie Database API setup
API_KEY = '8265bd1679663a7ea12ac168da84d2e8'
BASE_URL = 'https://api.themoviedb.org/3'

def fetch_movie_details(query):
    url = f"{BASE_URL}/search/movie?api_key={API_KEY}&query={query}"
    response = requests.get(url).json()
    results = response.get('results', [])
    if results:
        return results[0]  # Return the first result
    return None

def fetch_poster(movie_id):
    url = f"{BASE_URL}/movie/{movie_id}?api_key={API_KEY}&language=en-US"
    response = requests.get(url).json()
    poster_path = response.get('poster_path', '')
    if poster_path:
        full_path = f"https://image.tmdb.org/t/p/w500/{poster_path}"
    else:
        full_path = "https://via.placeholder.com/500x750?text=No+Image"
    return full_path

def calculate_jaccard_similarity(movie_genres, target_genres):
    movie_genres_set = set(movie_genres)
    target_genres_set = set(target_genres)
    intersection = len(movie_genres_set & target_genres_set)
    union = len(movie_genres_set | target_genres_set)
    if union == 0:
        return 0
    return intersection / union

def recommend_by_genre_jaccard(target_genre):
    target_genre_set = set([genre.strip().lower() for genre in target_genre.split(',')])
    movies = movies_collection.find()
    similarities = []

    for movie in movies:
        movie_genres = [genre.lower() for genre in movie['genre']]
        similarity = calculate_jaccard_similarity(movie_genres, target_genre_set)
        if similarity > 0:  # Ensure there is some overlap
            similarities.append((similarity, movie))

    # Sort movies by similarity in descending order and return the top 5
    similarities.sort(reverse=True, key=lambda x: x[0])
    recommended_movies = [movie for similarity, movie in similarities[:5]]
    return recommended_movies

def recommend_by_rating():
    recommended_movies = movies_collection.find().sort('rating', pymongo.DESCENDING).limit(5)
    return list(recommended_movies)

# Streamlit App
st.title("CineMatch: Movie Recommendation System")

menu = ["Search/Recommend", "Insert/Delete"]
choice = st.sidebar.selectbox("Menu", menu)

if choice == "Search/Recommend":
    st.subheader("Search for a Movie")
    search_query = st.text_input("Enter movie name")

    if st.button("Search"):
        movie_details = fetch_movie_details(search_query)
        if movie_details:
            st.image(fetch_poster(movie_details['id']), width=200)
            st.write(f"**Title:** {movie_details['title']}")
            st.write(f"**Rating:** {movie_details['vote_average']}")
        else:
            st.error("Movie not found!")

    st.subheader("Get Recommendations")
    recommend_type = st.selectbox("Recommend by", ["Genre", "Rating"])

    if recommend_type == "Genre":
        genre_query = st.text_input("Enter genre")
        if st.button("Recommend by Genre"):
            recommendations = recommend_by_genre_jaccard(genre_query)
            if recommendations:
                # Create a DataFrame to display the recommendations
                data = {
                    "Title": [movie['title'] for movie in recommendations],
                    "Genre": [', '.join(movie['genre']) for movie in recommendations],
                    "Rating": [movie['rating'] for movie in recommendations],
                    "Language": [movie['language'] for movie in recommendations]
                }
                df = pd.DataFrame(data)
                st.table(df)
            else:
                st.write("No recommendations found for the given genre.")

    elif recommend_type == "Rating":
        if st.button("Recommend Top Rated"):
            recommendations = recommend_by_rating()
            if recommendations:
                # Create a DataFrame to display the recommendations
                data = {
                    "Title": [movie['title'] for movie in recommendations],
                    "Genre": [', '.join(movie['genre']) for movie in recommendations],
                    "Rating": [movie['rating'] for movie in recommendations],
                    "Language": [movie['language'] for movie in recommendations]
                }
                df = pd.DataFrame(data)
                st.table(df)
            else:
                st.write("No recommendations found.")

elif choice == "Insert/Delete":
    st.subheader("Insert a New Movie")
    title = st.text_input("Enter movie title")
    genre = st.text_input("Enter movie genre (comma separated)")
    rating = st.number_input("Enter movie rating", min_value=0.0, max_value=10.0, step=0.1)
    language = st.text_input("Enter movie language")

    if st.button("Insert"):
        genre_list = [g.strip() for g in genre.split(',')]
        movie = {
            'title': title,
            'genre': genre_list,
            'rating': rating,
            'language': language,
            'movie_id': None  # Ensure the field exists, even if empty
        }
        movies_collection.insert_one(movie)
        st.success("Movie added successfully!")

    st.subheader("Delete a Movie")
    delete_query = st.text_input("Enter the title of the movie to delete")
    if st.button("Delete"):
        result = movies_collection.delete_one({'title': delete_query})
        if result.deleted_count > 0:
            st.success("Movie deleted successfully!")
        else:
            st.error("Movie not found!")
1