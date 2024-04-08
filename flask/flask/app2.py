import json
import math
from collections import defaultdict
from flask import Flask, abort, request
from flask_basicauth import BasicAuth
from flask_swagger_ui import get_swaggerui_blueprint
import pymysql
from requests.auth import HTTPBasicAuth
from flask_swagger_ui import get_swaggerui_blueprint

app = Flask(__name__)


MAX_PAGE_SIZE = 100


@app.route("/movies")
def movies():
    # URL parameters
    page = int(request.args.get('page', 0))
    page_size = int(request.args.get('page_size', MAX_PAGE_SIZE))
    page_size = min(page_size, MAX_PAGE_SIZE)
    include_details = bool(int(request.args.get('include_details', 0)))

    db_conn = pymysql.connect(host="localhost",
                            user="root", 
                            database="bechdel",  
                            password = "-1Xy781227@",
                            cursorclass=pymysql.cursors.DictCursor)
    # Get the movies
    with db_conn.cursor() as cursor:
        cursor.execute("""
            SELECT
                M.movieId,
                M.originalTitle,
                M.primaryTitle AS englishTitle,
                B.rating AS bechdelScore,
                M.runtimeMinutes,
                M.startYear AS year,
                M.movieType,
                M.isAdult
            FROM Movies M
            JOIN Bechdel B ON B.movieId = M.movieId 
            ORDER BY movieId
            LIMIT %s
            OFFSET %s
        """, (page_size, page * page_size))
        movies = cursor.fetchall()
        movie_ids = [mov['movieId'] for mov in movies]
    
    if include_details:
        # Get genres
        with db_conn.cursor() as cursor:
            placeholder = ','.join(['%s'] * len(movie_ids))
            cursor.execute(f"SELECT * FROM MoviesGenres WHERE movieId IN ({placeholder})",
                        movie_ids)
            genres = cursor.fetchall()
        genres_dict = defaultdict(list)
        for obj in genres:
            genres_dict[obj['movieId']].append(obj['genre'])
        
        # Get people
        with db_conn.cursor() as cursor:
            placeholder = ','.join(['%s'] * len(movie_ids))
            cursor.execute(f"""
                SELECT
                    MP.movieId,
                    P.personId,
                    P.primaryName AS name,
                    P.birthYear,
                    P.deathYear,
                    MP.category AS role
                FROM MoviesPeople MP
                JOIN People P on P.personId = MP.personId
                WHERE movieId IN ({placeholder})
            """, movie_ids)
            people = cursor.fetchall()
        people_dict = defaultdict(list)
        for obj in people:
            movieId = obj['movieId']
            del obj['movieId']
            people_dict[movieId].append(obj)

        # Merge genres and people into movies
        for movie in movies:
            movieId = movie['movieId']
            movie['genres'] = genres_dict[movieId]
            movie['people'] = people_dict[movieId]

    # Get the total movies count
    with db_conn.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) AS total FROM Movies")
        total = cursor.fetchone()
        last_page = math.ceil(total['total'] / page_size)

    db_conn.close()
    return {
        'movies': movies,
        'next_page': f'/movies?page={page+1}&page_size={page_size}&include_details={int(include_details)}',
        'last_page': f'/movies?page={last_page}&page_size={page_size}&include_details={int(include_details)}',
    }
    
    

swaggerui_blueprint = get_swaggerui_blueprint(
    base_url='/docs',
    api_url='/static/openapi.yaml',
)
app.register_blueprint(swaggerui_blueprint)


