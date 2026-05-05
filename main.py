from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import httpx

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

TMDB_API_KEY = "c925fc7279be6401180a09d59708a916"
TELEGRAM_LINK = "https://t.me/flic_channel"

# Ручная база ID сериалов (добавляй сам)
SERIALS_DB = {
    "очень странные дела": 13913,
    "эйфория": 22047,
    "halo": 52852,
    "ahsoka": 225327
}

@app.get("/api/search")
async def search(query: str = Query(..., min_length=1)):
    query_lower = query.lower().strip()
    
    # 1. Ищем в TMDB
    tmdb_url = "https://api.themoviedb.org/3/search/tv"
    params = {"api_key": TMDB_API_KEY, "query": query, "language": "ru-RU"}
    tmdb_data = None
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(tmdb_url, params=params)
        if resp.status_code == 200:
            results = resp.json().get("results", [])
            if results:
                item = results[0]
                poster = f"https://image.tmdb.org/t/p/w500{item.get('poster_path')}" if item.get("poster_path") else None
                tmdb_data = {
                    "title": item.get("name"),
                    "poster": poster,
                    "year": item.get("first_air_date", "")[:4],
                    "overview": item.get("overview")
                }
    
    # 2. Ищем в ручной базе ID
    if query_lower in SERIALS_DB:
        serial_id = SERIALS_DB[query_lower]
        tv_page_url = f"https://seasonvar.ru/serial-{serial_id}.html"
        
        return {
            "result": {
                "title": tmdb_data.get("title", query.title()) if tmdb_data else query.title(),
                "poster": tmdb_data.get("poster") if tmdb_data else None,
                "year": tmdb_data.get("year", "") if tmdb_data else "",
                "overview": tmdb_data.get("overview", "") if tmdb_data else "",
                "tv_page_url": tv_page_url
            },
            "telegram": TELEGRAM_LINK
        }
    
    # 3. Если не нашли
    return {
        "result": None,
        "telegram": TELEGRAM_LINK,
        "error": "Сериал не найден. Добавьте ID вручную."
    }

@app.get("/")
def root():
    return {"status": "FLIC API works", "telegram": TELEGRAM_LINK}
