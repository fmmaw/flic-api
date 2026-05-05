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

# ========== РУЧНАЯ БАЗА СЕРИАЛОВ ==========
# Формат: "название": { "seasons": [ {"id": ID, "slug": "текст", "season_num": номер} ] }
SERIALS_DB = {
    "очень странные дела": {
        "seasons": [
            {"id": 13913, "slug": "Ochen__strannye_dela_pshyukv-1-season", "season_num": 1},
            {"id": 16200, "slug": "Ochen__strannye_dela_psxfikz-2-season", "season_num": 2},
            {"id": 21059, "slug": "Ochen__strannye_dela_psupjmf-3-sezon", "season_num": 3},
            {"id": 29832, "slug": "Ochen__strannye_dela_pskrdiv-4-season", "season_num": 4},
            {"id": 41230, "slug": "Ochen__strannye_dela_psinyso-5-season", "season_num": 5}
        ]
    },
    "эйфория": {
        "seasons": [
            {"id": 22047, "slug": "Ejforiya_psxmtkb-000-sezon", "season_num": 1},
            {"id": 28177, "slug": "Ejforiya_pshfpvs-2-season", "season_num": 2},
            {"id": 47652, "slug": "Ejforiya-3-season", "season_num": 3}
        ]
    }
}

def make_tv_page_url(serial_id: int, slug: str) -> str:
    return f"https://seasonvar.ru/serial-{serial_id}-{slug}.html"

def extract_season_number(query: str) -> int:
    """Пытается извлечь номер сезона из запроса (например, 'очень странные дела 2 сезон')"""
    query_lower = query.lower()
    if "1 сезон" in query_lower or "1 сезон" in query_lower:
        return 1
    if "2 сезон" in query_lower:
        return 2
    if "3 сезон" in query_lower or "3 сезон" in query_lower:
        return 3
    if "4 сезон" in query_lower:
        return 4
    if "5 сезон" in query_lower:
        return 5
    return 1  # по умолчанию первый сезон

@app.get("/api/search")
async def search(query: str = Query(..., min_length=1)):
    query_lower = query.lower().strip()
    
    # 1. Ищем в TMDB (постеры, описание)
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
    
    # 2. Определяем, какой сериал и сезон ищет пользователь
    for serial_name, data in SERIALS_DB.items():
        if serial_name in query_lower:
            season_number = extract_season_number(query_lower)
            # Ищем данные для нужного сезона
            for season in data["seasons"]:
                if season["season_num"] == season_number:
                    tv_page_url = make_tv_page_url(season["id"], season["slug"])
                    return {
                        "result": {
                            "title": f"{tmdb_data.get('title', serial_name.title())} {season_number} сезон" if tmdb_data else f"{serial_name.title()} {season_number} сезон",
                            "poster": tmdb_data.get("poster") if tmdb_data else None,
                            "year": tmdb_data.get("year", "") if tmdb_data else "",
                            "overview": tmdb_data.get("overview", "") if tmdb_data else "",
                            "tv_page_url": tv_page_url
                        },
                        "telegram": TELEGRAM_LINK
                    }
            # Если сезон не найден — берём первый
            first_season = data["seasons"][0]
            tv_page_url = make_tv_page_url(first_season["id"], first_season["slug"])
            return {
                "result": {
                    "title": tmdb_data.get("title", serial_name.title()) if tmdb_data else serial_name.title(),
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
        "error": "Сериал не найден. Добавьте его в базу."
    }

@app.get("/")
def root():
    return {"status": "FLIC API works", "telegram": TELEGRAM_LINK}
