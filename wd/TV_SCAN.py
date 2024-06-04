import asyncio
import aiohttp
import re
import os
import json
from aiohttp import ClientSession

API_KEY = '6a5be4999abf74eba1f9a8311294c267'
SEARCH_URL = "https://api.themoviedb.org/3/search/tv"
EXTERNAL_ID_URL = "https://api.themoviedb.org/3/tv/{tv_id}/external_ids"
CONCURRENT_REQUESTS_LIMIT = 10

CACHE_FILE_PATH = 'id_cache.json'


def load_cache():
    print("Loading cache...")
    if os.path.exists(CACHE_FILE_PATH):
        with open(CACHE_FILE_PATH, 'r') as file:
            cache = json.load(file)
            print(f"Cache loaded with {len(cache)} entries.")
            return cache
    print("No cache file found, starting with an empty cache.")
    return {}


def save_cache(cache):
    print(f"Saving cache with {len(cache)} entries...")
    with open(CACHE_FILE_PATH, 'w') as file:
        json.dump(cache, file, indent=4)
    print("Cache saved.")


id_cache = load_cache()

async def get_series_id(series_name, session):
    print(f"Fetching TMDb ID for series: {series_name}")
    if series_name in id_cache:
        print(f"Series found in cache: {series_name}")
        return id_cache[series_name].get('tmdb_id')

    params = {'api_key': API_KEY, 'query': series_name}
    async with session.get(SEARCH_URL, params=params) as response:
        data = await response.json()
        tmdb_id = data['results'][0].get('id') if data['results'] else None
        if tmdb_id:
            print(f"TMDb ID found: {tmdb_id} for series: {series_name}")
            id_cache[series_name] = {'tmdb_id': tmdb_id}
        else:
            print(f"No TMDb ID found for series: {series_name}")
        return tmdb_id


async def get_imdb_id(tmdb_id, series_name, session):
    print(f"Fetching IMDb ID for series: {series_name} with TMDb ID: {tmdb_id}")
    if series_name in id_cache and 'imdb_id' in id_cache[series_name]:
        print(f"IMDb ID found in cache for series: {series_name}")
        return id_cache[series_name]['imdb_id']

    params = {'api_key': API_KEY}
    url = EXTERNAL_ID_URL.format(tv_id=tmdb_id)
    async with session.get(url, params=params) as response:
        if response.status != 200:
            print(f"Failed to fetch IMDb ID for TMDb ID {tmdb_id}: HTTP status {response.status}")
            return None

        data = await response.json()
        imdb_id = data.get('imdb_id')
        if imdb_id:
            print(f"IMDb ID found: {imdb_id} for series: {series_name}")
            id_cache[series_name]['imdb_id'] = imdb_id
        else:
            print(f"No IMDb ID found for series: {series_name}")
        return imdb_id



async def fetch_m3u_content(m3u_url, session):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'

    }
    async with session.get(m3u_url, headers=headers) as response:
        if response.status == 200:
            print(f"Successfully fetched content from {m3u_url}")
            return await response.text()
        else:
            print(f"Failed to fetch M3U content from {m3u_url} with status {response.status}")
            return None


def parse_series(m3u_content):
    print("Parsing M3U content...")
    series_pattern = re.compile(r'#EXTINF:-1,(.*?)(?:\s\(\d{4}\))?(?:\s\(.*?\))?\sS(\d+)(?:\s)?E(\d+)(?:\s(.*?))?\n(http.*)', re.IGNORECASE)
    series_data = []
    matches = series_pattern.findall(m3u_content)
    for match in matches:
        series_name, season, episode, episode_name, stream_url = match
        series_data.append({
            'series_name': series_name.strip(),
            'season': int(season),
            'episode': int(episode),
            'episode_name': episode_name.strip() if episode_name else '',
            'stream_url': stream_url.strip()
        })
    print(f"Parsed {len(series_data)} series entries from M3U content.")
    return series_data




async def process_series_data(series_data, session):
    organized_data = {}
    for data in series_data:
        series_name = data['series_name']
        tmdb_id = await get_series_id(series_name, session)
        if not tmdb_id:
            print(f"Could not fetch TMDb ID for series: {series_name}. Skipping...")
            continue
        imdb_id = await get_imdb_id(tmdb_id, series_name, session)
        if not imdb_id:
            print(f"Could not fetch IMDb ID for series: {series_name}. Skipping...")
            continue
        if series_name not in organized_data:
            organized_data[series_name] = {
                'id': imdb_id,
                'name': series_name,
                'seasons': {}
            }
        season = data['season']
        episode_info = {
            'episode': data['episode'],
            'stream_url': data['stream_url']
        }
        if season not in organized_data[series_name]['seasons']:
            organized_data[series_name]['seasons'][season] = {'season': season, 'episodes': []}
        organized_data[series_name]['seasons'][season]['episodes'].append(episode_info)

    for series in organized_data.values():
        series['seasons'] = list(series['seasons'].values())
    return list(organized_data.values())



async def main():
    async with ClientSession() as session:
        with open("m3u_series_list.txt", 'r') as file:
            m3u_urls = [line.strip() for line in file.readlines() if line.strip()]
            print(f"Found {len(m3u_urls)} M3U URLs to process.")

        m3u_contents = await asyncio.gather(*(fetch_m3u_content(url, session) for url in m3u_urls))

        series_data = []
        for content in m3u_contents:
            series_data.extend(parse_series(content))

        organized_data = await process_series_data(series_data, session)

        with open('organized_series_data.json', 'w') as f:
            json.dump(organized_data, f, indent=4)

        save_cache(id_cache)

if __name__ == "__main__":
    asyncio.run(main())
