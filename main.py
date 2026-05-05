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
# Формат: "ключ для поиска": {"id": ID, "slug": "часть URL после ID-"}
SERIALS_DB = {
    "очень странные дела": {
        "id": 13913,
        "slug": "Ochen__strannye_dela_pshyukv-1-season"
    },
    "очень странные дела 1 сезон": {
        "id": 13913,
        "slug": "Ochen__strannye_dela_pshyukv-1-season"
    },
    "очень странные дела 2 сезон": {
        "id": 16200,
        "slug": "Ochen__strannye_dela_psxfikz-2-season"
    },
    "очень странные дела 3 сезон": {
        "id": 21059,
        "slug": "Ochen__strannye_dela_psupjmf-3-sezon"
    },
    "очень странные дела 4 сезон": {
        "id": 29832,
        "slug": "Ochen__strannye_dela_pskrdiv-4-season"
    },
    "очень странные дела 5 сезон": {
        "id": 41230,
        "slug": "Ochen__strannye_dela_psinyso-5-season"
    },
    "эйфория": {
        "id": 22047,
        "slug": "Ejforiya_psxmtkb-000-sezon"
    },
    "эйфория 1 сезон": {
        "id": 22047,
        "slug": "Ejforiya_psxmtkb-000-sezon"
    },
    "эйфория 2 сезон": {
        "id": 28177,
        "slug": "Ejforiya_pshfpvs-2-season"
    },
    "эйфория 3 сезон": {
        "id": 47652,
        "slug": "Ejforiya-3-season"
    }
}

def make_tv_page_url(serial_id: int, slug: str) -> str:
    """Формирует полную ссылку на страницу сериала"""
    return f"https://seasonvar.ru/serial-{serial_id}-{slug}.html"

async def get_tmdb_data(query: str):
    """Ищет сериал в TMDB и возвращает постер, описание, год"""
    search_url = "https://api.themoviedb.org/3/search/tv"
    params = {"api_key": TMDB_API_KEY, "query": query, "language": "ru-RU"}
    async with httpx.AsyncClient() as client:
        resp = await client.get(search_url, params=params)
        if resp.status_code == 200:
            results = resp.json().get("results", [])
            if results:
                item = results[0]
                poster = f"https://image.tmdb.org/t/p/w500{item.get('poster_path')}" if item.get("poster_path") else None
                return {
                    "title": item.get("name"),
                    "poster": poster,
                    "year": item.get("first_air_date", "")[:4],
                    "overview": item.get("overview")
                }
    return None

@app.get("/api/search")
async def search(query: str = Query(..., min_length=1)):
    query_lower = query.lower().strip()
    
    # 1. Проверяем ручную базу
    if query_lower in SERIALS_DB:
        serial_info = SERIALS_DB[query_lower]
        tv_page_url = make_tv_page_url(serial_info["id"], serial_info["slug"])
        
        # 2. Получаем данные из TMDB
        tmdb_data = await get_tmdb_data(query_lower)
        
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
        "error": "Сериал не найден. Добавьте его в базу."
    }

@app.get("/")
def root():
    return {"status": "FLIC API works", "telegram": TELEGRAM_LINK}
