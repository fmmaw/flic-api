from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import httpx
from bs4 import BeautifulSoup
from urllib.parse import quote
import json

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

TMDB_API_KEY = "c925fc7279be6401180a09d59708a916"
TELEGRAM_LINK = "https://t.me/flic_channel"
MOVIES_JSON_URL = "https://bronzevpn.ru/flic/movies.json"

async def load_movies():
    """Загружает фильмы из JSON, при ошибке возвращает пустой список"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(MOVIES_JSON_URL)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("movies", []), data.get("telegram", TELEGRAM_LINK)
            else:
                print(f"JSON недоступен, статус: {resp.status_code}")
                return [], TELEGRAM_LINK
    except json.JSONDecodeError as e:
        print(f"Ошибка JSON: {e}")
        return [], TELEGRAM_LINK
    except Exception as e:
        print(f"Ошибка загрузки movies.json: {e}")
        return [], TELEGRAM_LINK

async def find_serial_url(query: str):
    """Ищет страницу сериала на seasonvar.ru"""
    try:
        search_url = f"https://seasonvar.ru/search/?q={quote(query)}"
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(search_url)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                first_link = soup.find("a", href=True)
                if first_link and "serial-" in first_link.get("href", ""):
                    url = first_link["href"]
                    if url.startswith("/"):
                        return "https://seasonvar.ru" + url
                    if url.startswith("//"):
                        return "https:" + url
                    return url
    except Exception as e:
        print(f"Ошибка поиска сериала: {e}")
    return None

@app.get("/api/search")
async def search(query: str = Query(..., min_length=1)):
    results = []
    
    # 1. Загружаем фильмы из JSON (если получится)
    movies, tg = await load_movies()
    for movie in movies:
        if query.lower() in movie.get("title", "").lower():
            results.append({
                "title": movie.get("title"),
                "type": "movie",
                "embed_url": movie.get("embed_url"),
                "tv_page_url": None,
                "poster": movie.get("poster"),
                "year": movie.get("year", ""),
                "overview": movie.get("overview", "")
            })
    
    # 2. Если фильмы не нашли — ищем сериал на seasonvar
    if not results:
        tv_url = await find_serial_url(query)
        if tv_url:
            results.append({
                "title": query.title(),
                "type": "tv",
                "embed_url": None,
                "tv_page_url": tv_url,
                "poster": None,
                "year": "",
                "overview": "Выберите серию на сайте seasonvar.ru"
            })
    
    # 3. Если вообще ничего не нашли
    if not results:
        results.append({
            "title": query.title(),
            "type": "unknown",
            "embed_url": None,
            "tv_page_url": None,
            "poster": None,
            "year": "",
            "overview": "Ничего не найдено. Попробуйте другой запрос."
        })
    
    return {"results": results, "telegram": TELEGRAM_LINK}

@app.get("/")
def root():
    return {"status": "FLIC API works", "telegram": TELEGRAM_LINK}
