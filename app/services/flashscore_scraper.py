"""
FlashScore Web Scraper Service
Busca resultados ao vivo do FlashScore Brasil
"""

import requests
from bs4 import BeautifulSoup
from typing import Optional, Dict
import re


class FlashScoreScraper:
    """Scraper para buscar resultados ao vivo do FlashScore"""
    
    BASE_URL = "https://www.flashscore.com.br"
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
    }
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)
    
    def search_match(self, team_a: str, team_b: str) -> Optional[Dict]:
        """
        Busca uma partida entre dois times no FlashScore
        """
        try:
            # Normaliza nomes dos times para busca
            team_a_search = self._normalize_team_name(team_a)
            team_b_search = self._normalize_team_name(team_b)
            
            print(f"[FlashScore] Buscando: {team_a_search} x {team_b_search}")
            
            # Busca na API de pesquisa do FlashScore
            search_url = f"{self.BASE_URL}/pesquisa/"
            params = {
                'q': f"{team_a_search} {team_b_search}",
                'type': 'match'
            }
            
            response = self.session.get(search_url, params=params, timeout=10)
            
            if response.status_code != 200:
                print(f"[FlashScore] Erro na busca: {response.status_code}")
                return None
            
            # Parse do HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Procura resultados de partidas
            match_links = soup.find_all('a', href=re.compile(r'/jogo/'))
            
            for link in match_links:
                href = link.get('href', '')
                title = link.get('title', '')
                
                # Verifica se o título contém os dois times
                if self._teams_match(title, team_a_search, team_b_search):
                    match_id = self._extract_match_id(href)
                    if match_id:
                        return self.get_match_details(match_id)
            
            print(f"[FlashScore] Partida não encontrada: {team_a} x {team_b}")
            return None
            
        except Exception as e:
            print(f"[FlashScore] Erro na busca: {e}")
            return None
    
    def get_match_details(self, match_id: str) -> Optional[Dict]:
        """
        Pega detalhes de uma partida específica
        """
        try:
            url = f"{self.BASE_URL}/jogo/{match_id}/"
            
            response = self.session.get(url, timeout=10)
            
            if response.status_code != 200:
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extrai dados da partida
            match_data = {
                'match_id': match_id,
                'home_team': '',
                'away_team': '',
                'score_home': 0,
                'score_away': 0,
                'status': 'scheduled',
                'minute': None,
                'events': []
            }
            
            # Nome dos times
            home_team_elem = soup.find('div', class_=['participant__participantName', 'home-team'])
            away_team_elem = soup.find('div', class_=['participant__participantName', 'away-team'])
            
            if home_team_elem:
                match_data['home_team'] = home_team_elem.get_text(strip=True)
            if away_team_elem:
                match_data['away_team'] = away_team_elem.get_text(strip=True)
            
            # Placar
            score_elem = soup.find('div', class_=['detailScore__wrapper', 'score'])
            if score_elem:
                score_text = score_elem.get_text(strip=True)
                scores = re.findall(r'(\d+)', score_text)
                if len(scores) >= 2:
                    match_data['score_home'] = int(scores[0])
                    match_data['score_away'] = int(scores[1])
            
            # Status/Tempo
            status_elem = soup.find('div', class_=['matchStatus', 'status'])
            time_elem = soup.find('div', class_=['matchTime', 'time'])
            
            if status_elem:
                status_text = status_elem.get_text(strip=True).upper()
                if 'ENCERRADO' in status_text or 'FIM' in status_text:
                    match_data['status'] = 'finished'
                elif 'AO VIVO' in status_text or 'LIVE' in status_text:
                    match_data['status'] = 'live'
                elif 'INTERVALO' in status_text or 'HT' in status_text:
                    match_data['status'] = 'live'
            
            if time_elem:
                time_text = time_elem.get_text(strip=True)
                minute_match = re.search(r'(\d+)', time_text)
                if minute_match:
                    match_data['minute'] = int(minute_match.group(1))
            
            print(f"[FlashScore] Encontrado: {match_data['home_team']} {match_data['score_home']} x {match_data['score_away']} {match_data['away_team']} ({match_data['status']})")
            
            return match_data
            
        except Exception as e:
            print(f"[FlashScore] Erro ao pegar detalhes: {e}")
            return None
    
    def _normalize_team_name(self, name: str) -> str:
        """Normaliza nome do time para busca"""
        # Remove acentos e caracteres especiais
        import unicodedata
        name = unicodedata.normalize('NFKD', name).encode('ASCII', 'ignore').decode('ASCII')
        return name.lower().strip()
    
    def _teams_match(self, title: str, team_a: str, team_b: str) -> bool:
        """Verifica se os dois times estão no título"""
        title_norm = self._normalize_team_name(title)
        return team_a in title_norm and team_b in title_norm
    
    def _extract_match_id(self, href: str) -> Optional[str]:
        """Extrai ID da partida da URL"""
        match = re.search(r'/jogo/([^/]+)/', href)
        return match.group(1) if match else None


# Instância global
flashscore_scraper = FlashScoreScraper()


def sync_match_from_flashscore(team_a: str, team_b: str) -> Optional[Dict]:
    """
    Função pública para buscar uma partida
    """
    return flashscore_scraper.search_match(team_a, team_b)
