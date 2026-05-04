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

def clean_seasonvar_url(url: str) -> str:
    """Превращает относительный URL в полный."""
    if url.startswith("/"):
        return "https://seasonvar.ru" + url
    return url

@app.get("/api/search")
async def search(query: str = Query(..., min_length=1)):
    # 1. Ищем сериал/фильм на seasonvar.ru
    search_url = f"https://seasonvar.ru/search/?q={quote(query)}"
    async with httpx.AsyncClient() as client:
        resp = await client.get(search_url)
        soup = BeautifulSoup(resp.text, "html.parser")
        first_link = soup.find("a", href=True)
    
    tv_page_url = None
    embed_url = None
    
    if first_link:
        page_url = clean_seasonvar_url(first_link["href"])
        async with httpx.AsyncClient() as client:
            resp2 = await client.get(page_url)
            soup2 = BeautifulSoup(resp2.text, "html.parser")
            iframe = soup2.find("iframe", src=True)
            if iframe:
                embed_url = iframe["src"]
                if embed_url.startswith("//"):
                    embed_url = "https:" + embed_url
                # Если на странице есть плеер — скорее всего, это фильм, но мы оставим оба варианта
        # В любом случае, сохраняем URL страницы сериала (для TV)
        tv_page_url = page_url
    
    # 2. Ищем в TMDB (фильмы и сериалы)
    tmdb_params = {"api_key": TMDB_API_KEY, "query": query, "language": "ru-RU"}
    results = []
    
    async with httpx.AsyncClient() as client:
        # Фильмы
        movie_resp = await client.get("https://api.themoviedb.org/3/search/movie", params=tmdb_params)
        if movie_resp.status_code == 200:
            for item in movie_resp.json().get("results", []):
                poster = f"https://image.tmdb.org/t/p/w500{item['poster_path']}" if item.get("poster_path") else None
                results.append({
                    "title": f"{item['title']} ({item.get('release_date', '')[:4]})",
                    "type": "movie",
                    "embed_url": embed_url,  # для фильма
                    "tv_page_url": None,
                    "poster": poster,
                    "year": item.get("release_date", "")[:4],
                    "overview": item.get("overview"),
                    "tmdb_id": item["id"]
                })
        
        # Сериалы
        tv_resp = await client.get("https://api.themoviedb.org/3/search/tv", params=tmdb_params)
        if tv_resp.status_code == 200:
            for item in tv_resp.json().get("results", []):
                poster = f"https://image.tmdb.org/t/p/w500{item['poster_path']}" if item.get("poster_path") else None
                results.append({
                    "title": f"{item['name']} ({item.get('first_air_date', '')[:4]})",
                    "type": "tv",
                    "embed_url": None,
                    "tv_page_url": tv_page_url,  # страница сериала на seasonvar.ru
                    "poster": poster,
                    "year": item.get("first_air_date", "")[:4],
                    "overview": item.get("overview"),
                    "tmdb_id": item["id"]
                })
    
    # Сортируем по году (новые сверху)
    results.sort(key=lambda x: x["year"] or "", reverse=True)
    
    return {"results": results, "telegram": TELEGRAM_LINK}

@app.get("/")
def root():
    return {"status": "FLIC API works", "telegram": TELEGRAM_LINK}
