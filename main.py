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

# Функция для поиска embed_url на seasonvar.ru
async def find_embed_url(query: str):
    search_url = f"https://seasonvar.ru/search/?q={quote(query)}"
    async with httpx.AsyncClient() as client:
        resp = await client.get(search_url)
        soup = BeautifulSoup(resp.text, "html.parser")
        first_link = soup.find("a", href=True)
        if not first_link:
            return None
        page_url = first_link["href"]
        if not page_url.startswith("http"):
            page_url = "https://seasonvar.ru" + page_url
        resp2 = await client.get(page_url)
        soup2 = BeautifulSoup(resp2.text, "html.parser")
        iframe = soup2.find("iframe", src=True)
        if iframe:
            embed_url = iframe["src"]
            if embed_url.startswith("//"):
                embed_url = "https:" + embed_url
            return embed_url
    return None

@app.get("/api/search")
async def search(query: str = Query(..., min_length=1)):
    # 1. Ищем плеер для точного запроса (например, "очень странные дела")
    embed_url = await find_embed_url(query)
    
    # 2. Если не нашли, пробуем транслитерировать или перевести на английский
    #    (для "очень странные дела" -> "stranger things")
    alt_query = None
    if query.lower() == "очень странные дела":
        alt_query = "stranger things"
    elif query.lower() == "эйфория":
        alt_query = "euphoria"
    
    if alt_query and not embed_url:
        embed_url = await find_embed_url(alt_query)
    
    # 3. Ищем в TMDB (по оригинальному запросу или альтернативному)
    search_query = alt_query if alt_query else query
    tmdb_params = {
        "api_key": TMDB_API_KEY,
        "query": search_query,
        "language": "ru-RU"
    }
    movies = []
    async with httpx.AsyncClient() as client:
        tmdb_resp = await client.get("https://api.themoviedb.org/3/search/movie", params=tmdb_params)
        if tmdb_resp.status_code == 200:
            results = tmdb_resp.json().get("results", [])
            for item in results:
                poster = f"https://image.tmdb.org/t/p/w500{item['poster_path']}" if item.get("poster_path") else None
                movies.append({
                    "title": f"{item['title']} ({item.get('release_date', '')[:4]})",
                    "embed_url": embed_url,
                    "poster": poster,
                    "year": item.get("release_date", "")[:4],
                    "overview": item.get("overview"),
                    "tmdb_id": item["id"]
                })
    
    # Если TMDB ничего не нашёл, пробуем поиск сериалов (через другой эндпоинт)
    if not movies:
        tmdb_tv_params = {
            "api_key": TMDB_API_KEY,
            "query": search_query,
            "language": "ru-RU"
        }
        async with httpx.AsyncClient() as client:
            tmdb_resp = await client.get("https://api.themoviedb.org/3/search/tv", params=tmdb_tv_params)
            if tmdb_resp.status_code == 200:
                results = tmdb_resp.json().get("results", [])
                for item in results:
                    poster = f"https://image.tmdb.org/t/p/w500{item['poster_path']}" if item.get("poster_path") else None
                    movies.append({
                        "title": f"{item['name']} ({item.get('first_air_date', '')[:4]})",
                        "embed_url": embed_url,
                        "poster": poster,
                        "year": item.get("first_air_date", "")[:4],
                        "overview": item.get("overview"),
                        "tmdb_id": item["id"]
                    })
    
    return {"movies": movies, "telegram": TELEGRAM_LINK}

@app.get("/")
def root():
    return {"status": "FLIC API works", "telegram": TELEGRAM_LINK}
