"""
Football API Integration Service
Provides live match data, statistics, goals, cards, and more
Uses API-Football (api-football.com) or similar providers
"""

import os
import requests
from typing import Optional, Dict, List, Any
from datetime import datetime

class FootballAPIService:
    """Service to fetch live football data from external APIs"""
    
    def __init__(self):
        # Primary: Football-Data.org (free tier - user's token)
        self.api_key = os.getenv("FOOTBALL_DATA_KEY", "df07ac7c58bf4642bccde0ff65cc2863")
        self.base_url = "https://api.football-data.org/v4"
        
        # Alternative: API-Football (paid, more detailed)
        self.alt_api_key = os.getenv("FOOTBALL_API_KEY", "")
        self.alt_base_url = "https://v3.football.api-sports.io"
        
        self.headers = {
            "X-Auth-Token": self.api_key
        }
    
    def _make_request(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """Make API request to football-data.org with error handling"""
        try:
            url = f"{self.base_url}/{endpoint}"
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            
            # Check rate limiting headers
            remaining = response.headers.get('X-Requests-Available-Reset', 'unknown')
            if remaining != 'unknown':
                print(f"[FootballAPI] API calls reset in: {remaining}ms")
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 403:
                print(f"[FootballAPI] API Key invalid or expired")
                return None
            elif response.status_code == 429:
                print(f"[FootballAPI] Rate limit exceeded. Wait before next request.")
                return None
            else:
                print(f"[FootballAPI] Error {response.status_code}: {response.text}")
                return None
        except Exception as e:
            print(f"[FootballAPI] Request failed: {e}")
            return None
    
    def search_fixture(self, team_a: str, team_b: str, date: str = None) -> Optional[Dict]:
        """Search for a match between two teams using football-data.org API"""
        try:
            # For football-data.org, we search in matches endpoint
            # Use date filter if provided
            params = {}
            if date:
                params["dateFrom"] = date
                params["dateTo"] = date
            
            # Search in all matches (World Cup = competition code WC)
            # Note: World Cup 2026 might not have data yet, using current competitions
            data = self._make_request("matches", params)
            if not data or 'matches' not in data:
                return None
            
            matches = data['matches']
            
            # Normalize team names for comparison
            team_a_norm = team_a.lower().strip()
            team_b_norm = team_b.lower().strip()
            
            for match in matches:
                home_team = match.get("homeTeam", {}).get("name", "").lower()
                away_team = match.get("awayTeam", {}).get("name", "").lower()
                
                # Check if this match involves our teams
                if ((team_a_norm in home_team or home_team in team_a_norm) and 
                    (team_b_norm in away_team or away_team in team_b_norm)) or \
                   ((team_b_norm in home_team or home_team in team_b_norm) and 
                    (team_a_norm in away_team or away_team in team_b_norm)):
                    return match
            
            return None
        except Exception as e:
            print(f"[FootballAPI] Search error: {e}")
            return None
    
    def _get_team_id(self, team_name: str) -> Optional[int]:
        """Get team ID from name"""
        # Map common World Cup 2026 team names to IDs
        # In production, this should query the API or use a database
        team_mapping = {
            "brasil": 6, "brazil": 6,
            "argentina": 26,
            "alemanha": 25, "germany": 25,
            "frança": 2, "france": 2,
            "espanha": 9, "spain": 9,
            "inglaterra": 10, "england": 10,
            "portugal": 27,
            "itália": 768, "italy": 768,
            "holanda": 15, "netherlands": 15,
            "bélgica": 1, "belgium": 1,
            "croácia": 3, "croatia": 3,
            "uruguai": 7, "uruguay": 7,
            "colômbia": 8, "colombia": 8,
            "méxico": 16, "mexico": 16,
            "eua": 2384, "usa": 2384, "estados unidos": 2384,
            "canadá": 28, "canada": 28,
            "japão": 12, "japan": 12,
            "coreia do sul": 17, "south korea": 17,
            "austrália": 20, "australia": 20,
            "senegal": 13,
            "marrocos": 31, "morocco": 31,
            "suíça": 14, "switzerland": 14,
            "dinamarca": 21, "denmark": 21,
            "polônia": 24, "poland": 24,
        }
        
        team_lower = team_name.lower().strip()
        return team_mapping.get(team_lower)
    
    def get_live_fixtures(self) -> List[Dict]:
        """Get all currently live matches from football-data.org"""
        data = self._make_request("matches", {"status": "LIVE"})
        return data.get('matches', []) if data else []
    
    def get_match_details(self, match_id: int) -> Optional[Dict]:
        """Get detailed match information from football-data.org"""
        # football-data.org uses /matches/{id} endpoint
        return self._make_request(f"matches/{match_id}")
    
    def get_match_events_formatted(self, match_id: int) -> str:
        """Get formatted match events for display/WhatsApp from football-data.org"""
        match = self.get_match_details(match_id)
        if not match:
            return "Não foi possível obter dados da partida."
        
        home_team = match.get("homeTeam", {}).get("name", "Time A")
        away_team = match.get("awayTeam", {}).get("name", "Time B")
        
        score = match.get("score", {}).get("fullTime", {})
        home_score = score.get("home", 0) if score else 0
        away_score = score.get("away", 0) if score else 0
        
        status = match.get("status", "")
        
        # Build message
        status_emoji = "�" if status == "IN_PLAY" else "⚪" if status == "FINISHED" else "⏳"
        message = f"""{status_emoji} *{home_team} {home_score} x {away_score} {away_team}*
Status: {status}\n
"""
        
        # Note: football-data.org free tier doesn't provide detailed events
        # This would require a paid plan or different API
        message += "💡 *Detalhes de gols e cartões disponíveis apenas em planos pagos ou APIs alternativas.*\n"
        
        return message
    
    def get_world_cup_fixtures(self, date_from: str = None, date_to: str = None) -> List[Dict]:
        """Get World Cup fixtures from football-data.org"""
        # World Cup competition code is "WC" 
        # Note: World Cup 2026 data may not be available yet in free tier
        params = {}
        if date_from:
            params["dateFrom"] = date_from
        if date_to:
            params["dateTo"] = date_to
        
        # Try to get World Cup matches
        data = self._make_request("competitions/WC/matches", params)
        if data and 'matches' in data:
            return data['matches']
        
        # Fallback: get all matches
        data = self._make_request("matches", params)
        return data.get('matches', []) if data else []
    
    def sync_match_with_api(self, db_match, db_session) -> bool:
        """Sync a database match with football-data.org API"""
        try:
            # Search for the match
            match = self.search_fixture(db_match.team_a, db_match.team_b, 
                                         str(db_match.match_date.date()) if db_match.match_date else None)
            
            if not match:
                print(f"[FootballAPI] Match not found for {db_match.team_a} x {db_match.team_b}")
                return False
            
            match_id = match.get("id")
            
            # Get detailed data
            details = self.get_match_details(match_id)
            if not details:
                return False
            
            # football-data.org structure
            score = details.get("score", {})
            full_time = score.get("fullTime", {})
            status = details.get("status", "")
            
            # Update match data
            db_match.score_a = full_time.get("home", db_match.score_a) if full_time else db_match.score_a
            db_match.score_b = full_time.get("away", db_match.score_b) if full_time else db_match.score_b
            
            # Map football-data.org status to our status
            status_mapping = {
                "SCHEDULED": "scheduled",
                "TIMED": "scheduled",
                "IN_PLAY": "live",
                "PAUSED": "live",  # Halftime
                "FINISHED": "finished",
                "SUSPENDED": "suspended",
                "POSTPONED": "postponed",
                "CANCELLED": "cancelled",
                "AWARDED": "finished",
            }
            
            new_status = status_mapping.get(status, db_match.status.value if hasattr(db_match.status, 'value') else db_match.status)
            from app.models import MatchStatus
            if hasattr(MatchStatus, new_status.upper()):
                db_match.status = getattr(MatchStatus, new_status.upper())
            
            db_session.commit()
            
            print(f"[FootballAPI] Synced: {db_match.team_a} {db_match.score_a} x {db_match.score_b} {db_match.team_b} ({new_status})")
            return True
            
        except Exception as e:
            print(f"[FootballAPI] Sync error: {e}")
            import traceback
            print(traceback.format_exc())
            return False


# Singleton instance
football_api_service = FootballAPIService()
