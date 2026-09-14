import os
import json

from dotenv import load_dotenv
from openai import OpenAI

from database import (
    get_movie_by_id,
    search_movies_db,
    filter_movies_db,
)