"""
Arkanis Monitoring Tools — Web Intelligence Module
====================================================
Rastreamento em tempo real de criptos, câmbio, jogos,
clima e conteúdo de páginas externas.
Todas as ferramentas usam APIs públicas e gratuitas.
NÃO requerem banco de dados ou credenciais.
"""

import json
import time
import hashlib
import requests
import urllib3
from typing import Dict, Any
from tools.base_tool import BaseTool
from tools.registry import registry
from core.config_manager import config_manager

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
        '(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
    ),
    'Accept': 'application/json',
}

# Cache simples em memória para evitar requisições repetidas
_cache: Dict[str, Any] = {}
CACHE_TTL = 60  # segundos


def _cached_get(url: str, params: dict = None, ttl: int = CACHE_TTL) -> dict:
    key = url + str(params)
    if key in _cache:
        entry = _cache[key]
        if time.time() - entry["ts"] < ttl:
            return entry["data"]
    resp = requests.get(url, params=params, headers=HEADERS, timeout=10, verify=False)
    resp.raise_for_status()
    data = resp.json()
    _cache[key] = {"ts": time.time(), "data": data}
    return data


# ─────────────────────────────────────────────
#  CRIPTO
# ─────────────────────────────────────────────

class GetCryptoPriceTool(BaseTool):
    """Preço de criptomoedas em tempo real via CoinGecko."""
    @property
    def name(self) -> str: return "get_crypto_price"
    @property
    def description(self) -> str:
        return (
            "Get real-time cryptocurrency prices in BRL and USD. "
            "No API key required. "
            "Supports: bitcoin, ethereum, solana, cardano, ripple, dogecoin, and most others."
        )
    @property
    def arguments(self) -> Dict[str, str]:
        return {
            "coins": (
                "Comma-separated list of coin IDs (e.g., 'bitcoin,ethereum,solana'). "
                "Use CoinGecko IDs — lowercase, no spaces."
            ),
            "currencies": "Optional. Currencies (default: 'brl,usd')"
        }

    def execute(self, **kwargs) -> str:
        coins = kwargs.get("coins", "bitcoin").strip().lower()
        currencies = kwargs.get("currencies", "brl,usd").strip().lower()

        try:
            data = _cached_get(
                "https://api.coingecko.com/api/v3/simple/price",
                params={
                    "ids": coins,
                    "vs_currencies": currencies,
                    "include_24hr_change": "true",
                    "include_last_updated_at": "true",
                },
                ttl=30
            )

            if not data:
                return "Nenhum dado encontrado. Verifique os IDs das moedas (ex: bitcoin, not BTC)."

            lines = []
            for coin_id, prices in data.items():
                parts = [f"**{coin_id.upper()}**"]
                for curr, val in prices.items():
                    if curr.endswith("_24h_change"):
                        continue
                    if curr == "last_updated_at":
                        continue
                    symbol = "R$" if curr == "brl" else "$" if curr == "usd" else curr.upper()
                    change_key = f"{curr}_24h_change"
                    change = prices.get(change_key, None)
                    change_str = ""
                    if change is not None:
                        emoji = "📈" if change >= 0 else "📉"
                        change_str = f" ({emoji} {change:+.2f}% 24h)"
                    parts.append(f"  {symbol} {val:,.2f}{change_str}")
                lines.append("\n".join(parts))

            return "🪙 **Preços em Tempo Real**\n\n" + "\n\n".join(lines)

        except requests.HTTPError as e:
            if "429" in str(e):
                return "⚠️ Rate limit do CoinGecko atingido. Aguarde 1 minuto."
            return f"Error CoinGecko: {e}"
        except Exception as e:
            return f"Error ao buscar criptos: {str(e)}"


# ─────────────────────────────────────────────
#  CÂMBIO
# ─────────────────────────────────────────────

class GetExchangeRateTool(BaseTool):
    """Taxa de câmbio em tempo real via API pública."""
    @property
    def name(self) -> str: return "get_exchange_rate"
    @property
    def description(self) -> str:
        return (
            "Get real-time exchange rates. "
            "Examples: USD→BRL, EUR→BRL, BTC→USD. "
            "Use for dollar quotes, euro rates, or any currency conversion."
        )
    @property
    def arguments(self) -> Dict[str, str]:
        return {
            "from_currency": "Source currency code (e.g., USD, EUR, GBP)",
            "to_currency": "Target currency code (e.g., BRL, USD). Default: BRL",
            "amount": "Optional amount to convert (default: 1)"
        }

    def execute(self, **kwargs) -> str:
        from_curr = kwargs.get("from_currency", "USD").strip().upper()
        to_curr = kwargs.get("to_currency", "BRL").strip().upper()
        amount = float(kwargs.get("amount", 1))

        try:
            # API pública gratuita (sem chave)
            data = _cached_get(
                f"https://api.exchangerate-api.com/v4/latest/{from_curr}",
                ttl=300  # 5 min cache
            )
            rates = data.get("rates", {})
            rate = rates.get(to_curr)

            if rate is None:
                return f"Moeda '{to_curr}' não encontrada. Use códigos padrão (USD, BRL, EUR, GBP...)."

            converted = amount * rate
            date = data.get("date", "hoje")

            return (
                f"💱 **Câmbio em Tempo Real** ({date})\n\n"
                f"  {amount:,.2f} {from_curr} = **{converted:,.4f} {to_curr}**\n"
                f"  Taxa: 1 {from_curr} = {rate:,.4f} {to_curr}"
            )

        except requests.HTTPError as e:
            # Fallback: AwesomeAPI (Banco Central BR)
            try:
                pair = f"{from_curr}-{to_curr}"
                data = _cached_get(
                    f"https://economia.awesomeapi.com.br/json/last/{pair}",
                    ttl=120
                )
                key = pair.replace("-", "")
                entry = data.get(key, {})
                bid = float(entry.get("bid", 0))
                date_str = entry.get("create_date", "")
                if bid:
                    converted = amount * bid
                    return (
                        f"💱 **Câmbio** (AwesomeAPI — {date_str})\n\n"
                        f"  {amount:,.2f} {from_curr} = **{converted:,.4f} {to_curr}**\n"
                        f"  Taxa (compra): {bid:,.4f}"
                    )
            except Exception:
                pass
            return f"Error ao buscar câmbio: {e}"
        except Exception as e:
            return f"Error ao buscar câmbio: {str(e)}"


# ─────────────────────────────────────────────
#  JOGOS / ESPORTES
# ─────────────────────────────────────────────

class GetSportsScoreTool(BaseTool):
    """Resultados e placar de jogos de futebol via API pública."""
    @property
    def name(self) -> str: return "get_sports_score"
    @property
    def description(self) -> str:
        return (
            "Get sports scores, recent matches, and team information. "
            "Covers football (soccer), basketball, and more. "
            "Use to check match results, next games, or team standings."
        )
    @property
    def arguments(self) -> Dict[str, str]:
        return {
            "team": "Team name to search for (e.g., 'Flamengo', 'Brasil', 'Palmeiras')",
            "type": "Optional: 'last' for last matches, 'next' for upcoming (default: last)"
        }

    def execute(self, **kwargs) -> str:
        team_search = kwargs.get("team", "").strip()
        search_type = kwargs.get("type", "last").strip().lower()

        if not team_search:
            return "Error: nome do time ou liga ausente."

        # Load API Key from integrations config
        integrations = config_manager.load_integrations()
        tsdb_cfg = integrations.get("thesportsdb", {})
        api_key = tsdb_cfg.get("api_key", "123")
        
        # Determine if we should start with V2 or V1
        # Keys '123' or '3' are officially for V1 test access
        is_test_key = api_key in ["123", "3"]
        
        headers = HEADERS.copy()
        if not is_test_key:
            headers["X-API-KEY"] = api_key
        
        base_v2 = "https://www.thesportsdb.com/api/v2/json"
        # The V1 uses the key in the URL: https://www.thesportsdb.com/api/v1/json/{api_key}/...
        base_v1 = f"https://www.thesportsdb.com/api/v1/json/{api_key}"

        try:
            # 1. Search Logic
            teams = []
            leagues = []
            
            if not is_test_key:
                # Try V2 Search first
                try:
                    search_resp = requests.get(f"{base_v2}/search/team/{team_search}", headers=headers, timeout=10, verify=False)
                    if search_resp.ok:
                        teams = search_resp.json().get("teams", [])
                    
                    if not teams:
                        search_resp = requests.get(f"{base_v2}/search/league/{team_search}", headers=headers, timeout=10, verify=False)
                        if search_resp.ok:
                            leagues = search_resp.json().get("leagues", [])
                except:
                    pass # Fallback to V1 if V2 fails or times out

            # Fallback to V1 Search if V2 failed or skipped
            if not teams and not leagues:
                # V1 Team Search
                search_resp = requests.get(f"{base_v1}/searchteams.php", params={"t": team_search}, timeout=10, verify=False)
                if search_resp.ok:
                    teams = search_resp.json().get("teams", [])
                
                # V1 League Search (if no team found)
                if not teams:
                    search_resp = requests.get(f"{base_v1}/search_all_leagues.php", params={"s": team_search}, timeout=10, verify=False)
                    if search_resp.ok:
                        leagues = search_resp.json().get("leagues", [])

            if not teams and not leagues:
                return f"Nenhum time ou liga encontrado para '{team_search}' no TheSportsDB."

            # 2. Results Fetching
            label = ""
            endpoint_v2 = ""
            endpoint_v1 = ""
            v1_params = {}

            if teams:
                found_team = teams[0]
                team_id = found_team.get("idTeam")
                team_name = found_team.get("strTeam")
                
                if search_type == "next":
                    endpoint_v2 = f"/schedule/next/team/{team_id}"
                    endpoint_v1 = "eventsnext.php"
                    v1_params = {"id": team_id}
                    label = f"Próximos Jogos: {team_name}"
                else:
                    endpoint_v2 = f"/schedule/previous/team/{team_id}"
                    endpoint_v1 = "eventslast.php"
                    v1_params = {"id": team_id}
                    label = f"Últimos Resultados: {team_name}"
            else:
                found_league = leagues[0]
                league_id = found_league.get("idLeague")
                league_name = found_league.get("strLeague")
                
                if search_type == "next":
                    endpoint_v2 = f"/schedule/next/league/{league_id}"
                    endpoint_v1 = "eventsnextleague.php"
                    v1_params = {"id": league_id}
                    label = f"Próximos Jogos: {league_name}"
                else:
                    endpoint_v2 = f"/livescore/league/{league_id}"
                    endpoint_v1 = "eventslast.php" # Fallback
                    v1_params = {"id": league_id}
                    label = f"Placar / Últimos: {league_name}"

            # Fetch implementation
            events = []
            # Try V2 first if not test key
            if not is_test_key and endpoint_v2:
                try:
                    ev_resp = requests.get(f"{base_v2}{endpoint_v2}", headers=headers, timeout=10, verify=False)
                    if ev_resp.ok:
                        events_data = ev_resp.json()
                        events = events_data.get("events") or events_data.get("livescore") or events_data.get("results") or []
                except:
                    pass

            # Fallback to V1
            if not events and endpoint_v1:
                ev_resp = requests.get(f"{base_v1}/{endpoint_v1}", params=v1_params, timeout=10, verify=False)
                if ev_resp.ok:
                    ed = ev_resp.json()
                    events = ed.get("events") or ed.get("results") or []

            # 3. Format Output
            header_str = f"⚽ **TheSportsDB {'(V2)' if not is_test_key else '(V1)'}**\n{label}:\n"
            if not events:
                return header_str + "  Nenhum evento encontrado no momento."

            lines = []
            for ev in events[:8]:
                home = ev.get("strHomeTeam") or ev.get("strEvent", "").split(" vs ")[0]
                away = ev.get("strAwayTeam") or ev.get("strEvent", "").split(" vs ")[-1]
                date = ev.get("dateEvent") or ev.get("strTimestamp", "Hoje")
                
                s_home = ev.get("intHomeScore")
                s_away = ev.get("intAwayScore")
                
                result_str = f"{s_home} x {s_away}" if s_home is not None else "Agendado"
                lines.append(f"  📅 {date} — {home} vs {away} → **{result_str}**")

            return header_str + "\n".join(lines)

        except Exception as e:
            return f"Error ao buscar esportes (V1/V2): {str(e)}"


# ─────────────────────────────────────────────
#  CLIMA
# ─────────────────────────────────────────────

class GetWeatherTool(BaseTool):
    """Clima atual de qualquer cidade via Open-Meteo (sem chave de API)."""
    @property
    def name(self) -> str: return "get_weather"
    @property
    def description(self) -> str:
        return (
            "Get current weather for any city worldwide. "
            "No API key needed. "
            "Returns temperature, humidity, wind speed, and condition."
        )
    @property
    def arguments(self) -> Dict[str, str]:
        return {
            "city": "City name (e.g., 'São Paulo', 'Rio de Janeiro', 'Curitiba')",
            "country": "Optional 2-letter country code (default: BR)"
        }

    def execute(self, **kwargs) -> str:
        city = kwargs.get("city", "").strip()
        country = kwargs.get("country", "BR").strip().upper()

        if not city:
            return "Error: nome da cidade ausente."

        try:
            # Geocoding via Open-Meteo
            geo = _cached_get(
                "https://geocoding-api.open-meteo.com/v1/search",
                params={"name": city, "count": 5, "language": "pt", "format": "json"},
                ttl=3600
            )
            results = geo.get("results", [])

            # Filtrar pelo país
            target = None
            for r in results:
                if r.get("country_code", "").upper() == country:
                    target = r
                    break
            if not target and results:
                target = results[0]

            if not target:
                return f"Cidade '{city}' não encontrada."

            lat = target["latitude"]
            lon = target["longitude"]
            city_name = target.get("name", city)
            region = target.get("admin1", "")
            country_name = target.get("country", country)

            # Previsão atual
            weather = _cached_get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,weathercode,apparent_temperature",
                    "timezone": "America/Sao_Paulo",
                    "wind_speed_unit": "kmh",
                },
                ttl=600
            )

            curr = weather.get("current", {})
            temp = curr.get("temperature_2m", "?")
            feels_like = curr.get("apparent_temperature", "?")
            humidity = curr.get("relative_humidity_2m", "?")
            wind = curr.get("wind_speed_10m", "?")
            wcode = curr.get("weathercode", 0)

            # Mapear código de tempo para descrição
            condition_map = {
                0: "☀️ Céu limpo", 1: "🌤 Principalmente limpo",
                2: "⛅ Parcialmente nublado", 3: "☁️ Nublado",
                45: "🌫 Neblina", 48: "🌫 Neblina com geada",
                51: "🌦 Garoa leve", 53: "🌦 Garoa moderada", 55: "🌧 Garoa intensa",
                61: "🌧 Chuva leve", 63: "🌧 Chuva moderada", 65: "🌧 Chuva intensa",
                71: "❄️ Neve leve", 73: "❄️ Neve moderada", 75: "❄️ Neve intensa",
                80: "🌦 Pancadas leves", 81: "🌧 Pancadas moderadas", 82: "⛈ Pancadas intensas",
                95: "⛈ Tempestade", 96: "⛈ Tempestade com granizo",
            }
            condition = condition_map.get(int(wcode), f"Código {wcode}")

            location = f"{city_name}, {region}, {country_name}" if region else f"{city_name}, {country_name}"

            return (
                f"🌍 **Clima em {location}**\n\n"
                f"  {condition}\n"
                f"  🌡️ Temperatura: {temp}°C (sensação: {feels_like}°C)\n"
                f"  💧 Umidade: {humidity}%\n"
                f"  💨 Vento: {wind} km/h"
            )

        except Exception as e:
            return f"Error ao buscar clima: {str(e)}"


# ─────────────────────────────────────────────
#  MONITOR DE PÁGINA
# ─────────────────────────────────────────────

_page_snapshots: Dict[str, str] = {}


class PageMonitorTool(BaseTool):
    """
    Monitora mudanças no conteúdo de uma página externa.
    Compara o conteúdo atual com o último snapshot guardado em memória.
    """
    @property
    def name(self) -> str: return "page_monitor"
    @property
    def description(self) -> str:
        return (
            "Check if a webpage has changed since last time it was checked. "
            "First call saves a snapshot. Subsequent calls detect changes. "
            "Use for monitoring clinic appointment pages, stock pages, etc."
        )
    @property
    def arguments(self) -> Dict[str, str]:
        return {
            "url": "The URL to monitor.",
            "selector_hint": "Optional keyword to extract specific text from the page (e.g., 'disponível', 'aberto')."
        }

    def execute(self, **kwargs) -> str:
        url = kwargs.get("url", "").strip()
        hint = kwargs.get("selector_hint", "").strip().lower()

        if not url:
            return "Error: URL ausente."

        try:
            resp = requests.get(url, headers={
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
                              '(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
            }, timeout=10, verify=False)
            resp.raise_for_status()

            from html.parser import HTMLParser

            class TextExtractor(HTMLParser):
                def __init__(self):
                    super().__init__()
                    self.texts = []
                    self.skip = False
                    self.skip_tags = {'script', 'style', 'head', 'noscript'}

                def handle_starttag(self, tag, attrs):
                    if tag in self.skip_tags:
                        self.skip = True

                def handle_endtag(self, tag):
                    if tag in self.skip_tags:
                        self.skip = False

                def handle_data(self, data):
                    if not self.skip:
                        t = data.strip()
                        if t:
                            self.texts.append(t)

            parser = TextExtractor()
            parser.feed(resp.text)
            full_text = " ".join(parser.texts)

            # Filtrar por hint se fornecido
            if hint:
                import re
                sentences = re.split(r'[.!?\n]', full_text)
                relevant = [s.strip() for s in sentences if hint in s.lower()]
                content = " | ".join(relevant[:10]) if relevant else full_text[:1000]
            else:
                content = full_text[:2000]

            # Hash para detectar mudança
            current_hash = hashlib.md5(content.encode()).hexdigest()
            prev_hash = _page_snapshots.get(url)

            _page_snapshots[url] = current_hash

            if prev_hash is None:
                return (
                    f"📸 **Snapshot inicial salvo** para:\n{url}\n\n"
                    f"Conteúdo capturado ({len(content)} chars):\n{content[:500]}..."
                )
            elif prev_hash == current_hash:
                return (
                    f"✅ **Sem mudanças detectadas** em:\n{url}\n\n"
                    f"Conteúdo atual:\n{content[:500]}..."
                )
            else:
                return (
                    f"🚨 **MUDANÇA DETECTADA** em:\n{url}\n\n"
                    f"Novo conteúdo:\n{content[:800]}..."
                )

        except Exception as e:
            return f"Error ao monitorar página: {str(e)}"


# ─────────────────────────────────────────────
#  Auto-registration
# ─────────────────────────────────────────────
registry.register(GetCryptoPriceTool())
registry.register(GetExchangeRateTool())
registry.register(GetSportsScoreTool())
registry.register(GetWeatherTool())
registry.register(PageMonitorTool())
