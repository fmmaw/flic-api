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

TMDB_API_KEY = "c925fc7279be6401180a09d59708a916"
TELEGRAM_LINK = "https://t.me/flic_channel"

def clean_url(url: str) -> str:
    if not url:
        return None
    if url.startswith("//"):
        return "https:" + url
    if url.startswith("/"):
        return "https://seasonvar.ru" + url
    return url

async def find_serial_url(query: str):
    """Ищет страницу сериала на seasonvar.ru"""
    search_url = f"https://seasonvar.ru/search/?q={quote(query)}"
    async with httpx.AsyncClient() as client:
        resp = await client.get(search_url)
        soup = BeautifulSoup(resp.text, "html.parser")
        first_link = soup.find("a", href=True)
        if first_link and "serial-" in first_link["href"]:
            return clean_url(first_link["href"])
    return None

async def find_movie_url(query: str):
    """Ищет фильм на kinokrad.cc и возвращает embed_url"""
    search_url = f"https://kinokrad.cc/search/?q={quote(query)}"
    async with httpx.AsyncClient() as client:
        resp = await client.get(search_url)
        soup = BeautifulSoup(resp.text, "html.parser")
        # Ищем первую ссылку на фильм
        link = soup.find("a", class_="short-img")
        if link:
            movie_url = "https://kinokrad.cc" + link["href"]
            resp2 = await client.get(movie_url)
            soup2 = BeautifulSoup(resp2.text, "html.parser")
            # Ищем iframe с плеером
            iframe = soup2.find("iframe", src=True)
            if iframe:
                return clean_url(iframe["src"])
    return None

@app.get("/api/search")
async def search(query: str = Query(..., min_length=1)):
    # 1. Определяем тип (смотрим TMDB)
    tmdb_params = {"api_key": TMDB_API_KEY, "query": query, "language": "ru-RU"}
    is_tv = False
    async with httpx.AsyncClient() as client:
        tv_resp = await client.get("https://api.themoviedb.org/3/search/tv", params=tmdb_params)
        if tv_resp.status_code == 200:
            results = tv_resp.json().get("results", [])
            if results:
                is_tv = True

    # 2. Ищем ссылку в зависимости от типа
    tv_page_url = None
    embed_url = None

    if is_tv:
        # Сериал: ищем на seasonvar.ru
        tv_page_url = await find_serial_url(query)
    else:
        # Фильм: ищем на kinokrad.cc
        embed_url = await find_movie_url(query)

    # 3. Получаем данные из TMDB (постеры, описание, год)
    results = []
    async with httpx.AsyncClient() as client:
        # Фильмы
        movie_resp = await client.get("https://api.themoviedb.org/3/search/movie", params=tmdb_params)
        if movie_resp.status_code == 200:
            for item in movie_resp.json().get("results", [])[:5]:
                poster = f"https://image.tmdb.org/t/p/w500{item['poster_path']}" if item.get("poster_path") else None
                results.append({
                    "title": f"{item['title']} ({item.get('release_date', '')[:4]})",
                    "type": "movie",
                    "embed_url": embed_url,
                    "tv_page_url": None,
                    "poster": poster,
                    "year": item.get("release_date", "")[:4],
                    "overview": item.get("overview")
                })
        # Сериалы
        if is_tv:
            tv_resp = await client.get("https://api.themoviedb.org/3/search/tv", params=tmdb_params)
            if tv_resp.status_code == 200:
                for item in tv_resp.json().get("results", [])[:5]:
                    poster = f"https://image.tmdb.org/t/p/w500{item['poster_path']}" if item.get("poster_path") else None
                    results.append({
                        "title": f"{item['name']} ({item.get('first_air_date', '')[:4]})",
                        "type": "tv",
                        "embed_url": None,
                        "tv_page_url": tv_page_url,
                        "poster": poster,
                        "year": item.get("first_air_date", "")[:4],
                        "overview": item.get("overview")
                    })

    return {"results": results, "telegram": TELEGRAM_LINK}

@app.get("/")
def root():
    return {"status": "FLIC API works", "telegram": TELEGRAM_LINK}
