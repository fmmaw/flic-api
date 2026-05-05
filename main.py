from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import httpx
from bs4 import BeautifulSoup
from urllib.parse import quote

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

TELEGRAM_LINK = "https://t.me/flic_channel"
MOVIES_JSON_URL = "https://bronzevpn.ru/flic/movies.json"

async def load_movies():
    """Загружает список фильмов из JSON-файла"""
    async with httpx.AsyncClient() as client:
        resp = await client.get(MOVIES_JSON_URL)
        if resp.status_code == 200:
            data = resp.json()
            return data.get("movies", []), data.get("telegram", TELEGRAM_LINK)
    return [], TELEGRAM_LINK

async def find_serial_url(query: str):
    """Ищет страницу сериала на seasonvar.ru"""
    search_url = f"https://seasonvar.ru/search/?q={quote(query)}"
    async with httpx.AsyncClient() as client:
        resp = await client.get(search_url)
        soup = BeautifulSoup(resp.text, "html.parser")
        first_link = soup.find("a", href=True)
        if first_link and "serial-" in first_link["href"]:
            url = first_link["href"]
            if url.startswith("/"):
                return "https://seasonvar.ru" + url
            if url.startswith("//"):
                return "https:" + url
            return url
    return None

@app.get("/api/search")
async def search(query: str = Query(..., min_length=1)):
    query_lower = query.lower().strip()
    results = []

    # 1. Загружаем фильмы из JSON
    movies, tg_link = await load_movies()
    for movie in movies:
        if query_lower in movie["title"].lower():
            results.append({
                "title": movie["title"],
                "type": "movie",
                "embed_url": movie["embed_url"],
                "tv_page_url": None,
                "poster": movie.get("poster"),
                "year": movie.get("year", ""),
                "overview": movie.get("overview", "")
            })

    # 2. Ищем сериал на seasonvar.ru (если не нашли фильм)
    if not results:
        tv_url = await find_serial_url(query_lower)
        if tv_url:
            results.append({
                "title": query.title(),
                "type": "tv",
                "embed_url": None,
                "tv_page_url": tv_url,
                "poster": None,
                "year": "",
                "overview": "Выберите серию на сайте"
            })

    return {"results": results, "telegram": tg_link}

@app.get("/")
def root():
    return {"status": "FLIC API works", "telegram": TELEGRAM_LINK}
