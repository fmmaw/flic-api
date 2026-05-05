from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import httpx
from bs4 import BeautifulSoup
from urllib.parse import quote
import re

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

async def get_serial_page(query: str):
    """Находит страницу сериала на seasonvar.ru"""
    search_url = f"https://seasonvar.ru/search/?q={quote(query)}"
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(search_url)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            first_link = soup.find("a", href=True)
            if first_link and "serial-" in first_link.get("href", ""):
                return clean_url(first_link["href"])
    return None

async def search_tmdb(query: str):
    """Ищет сериал в TMDB и возвращает данные"""
    search_url = "https://api.themoviedb.org/3/search/tv"
    params = {"api_key": TMDB_API_KEY, "query": query, "language": "ru-RU"}
    async with httpx.AsyncClient(timeout=10.0) as client:
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
                    "overview": item.get("overview"),
                    "tmdb_id": item.get("id")
                }
    return None

async def parse_episodes(serial_url: str):
    """Парсит страницу сериала и возвращает список серий с ссылками на плеер"""
    episodes = []
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(serial_url)
        if resp.status_code != 200:
            return episodes
        
        soup = BeautifulSoup(resp.text, "html.parser")
        
        # Ищем все iframe с плеерами (каждая серия — отдельный iframe)
        # На seasonvar.ru серии часто в блоках с классом "serial-serias"
        series_blocks = soup.find_all("div", class_=re.compile("serial-seria|series-item", re.I))
        
        for block in series_blocks:
            iframe = block.find("iframe", src=True)
            if iframe:
                embed_url = clean_url(iframe["src"])
                # Пытаемся найти номер серии
                num_tag = block.find("span", class_=re.compile("num|number", re.I))
                episode_num = num_tag.text.strip() if num_tag else "?"
                title_tag = block.find("div", class_=re.compile("title|name", re.I))
                episode_title = title_tag.text.strip() if title_tag else f"Серия {episode_num}"
                
                episodes.append({
                    "number": episode_num,
                    "title": episode_title,
                    "embed_url": embed_url
                })
        
        # Если не нашли блоки — ищем прямые iframe
        if not episodes:
            iframes = soup.find_all("iframe", src=True)
            for idx, iframe in enumerate(iframes, 1):
                embed_url = clean_url(iframe["src"])
                episodes.append({
                    "number": str(idx),
                    "title": f"Серия {idx}",
                    "embed_url": embed_url
                })
    
    return episodes

@app.get("/api/search")
async def search(query: str = Query(..., min_length=1)):
    # 1. Находим страницу сериала на seasonvar.ru
    serial_url = await get_serial_page(query)
    if not serial_url:
        return {"results": [], "telegram": TELEGRAM_LINK, "error": "Сериал не найден"}
    
    # 2. Получаем данные из TMDB
    tmdb_data = await search_tmdb(query)
    
    # 3. Парсим список серий
    episodes = await parse_episodes(serial_url)
    
    # 4. Формируем результат
    result = {
        "title": tmdb_data.get("title", query.title()) if tmdb_data else query.title(),
        "poster": tmdb_data.get("poster") if tmdb_data else None,
        "year": tmdb_data.get("year", "") if tmdb_data else "",
        "overview": tmdb_data.get("overview", "") if tmdb_data else "",
        "episodes": episodes,
        "serial_url": serial_url
    }
    
    return {"result": result, "telegram": TELEGRAM_LINK}

@app.get("/")
def root():
    return {"status": "FLIC API works", "telegram": TELEGRAM_LINK}
