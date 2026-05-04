from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import httpx
from bs4 import BeautifulSoup

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

TMDB_KEY = "c925fc7279be6401180a09d59708a916"          # получи на themoviedb.org
TELEGRAM_LINK = "https://t.me/flic_channel"

@app.get("/api/search")
async def search(query: str = Query(..., min_length=1)):
    # 1. Ищем плеер на seasonvar.ru
    search_url = f"https://seasonvar.ru/search/?q={query.replace(' ', '+')}"
    async with httpx.AsyncClient() as client:
        resp = await client.get(search_url)
        soup = BeautifulSoup(resp.text, "html.parser")

    embed_url = None
    first = soup.find("a", href=True)
    if first:
        page_url = first["href"]
        if not page_url.startswith("http"):
            page_url = "https://seasonvar.ru" + page_url
        resp2 = await client.get(page_url)
        soup2 = BeautifulSoup(resp2.text, "html.parser")
        iframe = soup2.find("iframe", src=True)
        if iframe:
            embed_url = iframe["src"]
            if embed_url.startswith("//"):
                embed_url = "https:" + embed_url

    # 2. Берём постер, год, описание из TMDB
    poster = None
    year = None
    overview = None
    tmdb_params = {"api_key": TMDB_KEY, "query": query, "language": "ru-RU"}
    async with httpx.AsyncClient() as client:
        tmdb_resp = await client.get("https://api.themoviedb.org/3/search/movie", params=tmdb_params)
        if tmdb_resp.status_code == 200:
            results = tmdb_resp.json().get("results", [])
            if results:
                first = results[0]
                poster = f"https://image.tmdb.org/t/p/w500{first['poster_path']}" if first.get("poster_path") else None
                year = first.get("release_date", "")[:4]
                overview = first.get("overview")

    return {
        "embed_url": embed_url,
        "poster": poster,
        "year": year,
        "overview": overview,
        "telegram": TELEGRAM_LINK
    }

@app.get("/")
def root():
    return {"status": "FLIC API works", "telegram": TELEGRAM_LINK}

@app.get("/api/status")
def status():
    return {"status": "online"}
