"""
FlashScore Scraper usando Playwright (navegador real)
Para sites que usam JavaScript para renderizar conteúdo
"""

import asyncio
from playwright.async_api import async_playwright
from typing import Optional, Dict
import re


class FlashScorePlaywrightScraper:
    """Scraper avançado usando Playwright para JavaScript-heavy sites"""
    
    def __init__(self):
        self.browser = None
        self.context = None
    
    async def init(self):
        """Inicializa o navegador"""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=True)
        self.context = await self.browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            locale='pt-BR',
            viewport={'width': 1280, 'height': 720}
        )
    
    async def close(self):
        """Fecha o navegador"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
    
    async def scrape_match_by_url(self, url: str) -> Optional[Dict]:
        """
        Faz scraping de uma partida pela URL completa
        """
        if not self.browser:
            await self.init()
        
        page = await self.context.new_page()
        
        try:
            print(f"[FlashScore] Acessando: {url}")
            await page.goto(url, wait_until='networkidle', timeout=30000)
            await asyncio.sleep(2)  # Aguarda JS renderizar
            
            result = await self._extract_match_data(page)
            
            await page.close()
            return result
            
        except Exception as e:
            print(f"[FlashScore] Erro: {e}")
            await page.close()
            return None
    
    async def _extract_match_data(self, page) -> Dict:
        """Extrai dados da partida da página"""
        result = {
            'home_team': None,
            'away_team': None,
            'score_home': None,
            'score_away': None,
            'status': None,
            'minute': None,
            'competition': None,
            'match_date': None,
            'events': []
        }
        
        # Aguarda um pouco mais para o conteúdo carregar
        await asyncio.sleep(3)
        
        # Extrai times usando múltiplas estratégias
        team_selectors = [
            # Seletores específicos do FlashScore
            '.duelParticipant__participantName',
            '.participant__participantName',
            '.tname__text',
            '[class*="participantName"]',
            'div[class*="participant"] h2',
            'div[class*="participant"] a',
            # Seletores mais genéricos
            '.match-header-team-name',
            '.team-name',
            '[data-testid*="team"]',
        ]
        
        for selector in team_selectors:
            try:
                elements = await page.query_selector_all(selector)
                if len(elements) >= 2:
                    texts = []
                    for i, elem in enumerate(elements[:2]):
                        text = await elem.text_content()
                        if text:
                            texts.append(text.strip())
                    if len(texts) >= 2:
                        result['home_team'] = texts[0]
                        result['away_team'] = texts[1]
                        print(f"[FlashScore] Times encontrados: {texts[0]} x {texts[1]}")
                        break
            except Exception as e:
                print(f"[FlashScore] Erro ao extrair times: {e}")
                continue
        
        # Extrai placar - procura por padrões de placar
        score_selectors = [
            '.detailScore__wrapper',
            '.current-result',
            '.duelScore__score',
            '[class*="score"]',
            '.match-header-score',
            '[data-testid*="score"]',
        ]
        
        for selector in score_selectors:
            try:
                elem = await page.query_selector(selector)
                if elem:
                    text = await elem.text_content()
                    if text:
                        home, away = self._extract_scores(text)
                        if home is not None and away is not None:
                            result['score_home'] = home
                            result['score_away'] = away
                            print(f"[FlashScore] Placar encontrado: {home} x {away}")
                            break
            except:
                continue
        
        # Extrai status/tempo
        status_selectors = [
            '.matchStatus',
            '.matchTime',
            '.status',
            '[class*="time"]',
            '[class*="period"]',
            '.live-indicator',
        ]
        
        for selector in status_selectors:
            try:
                elem = await page.query_selector(selector)
                if elem:
                    text = await elem.text_content()
                    if text:
                        text = text.strip()
                        result['status'] = text
                        # Tenta extrair minuto do status
                        minute_match = re.search(r'(\d+)[\'\']?', text)
                        if minute_match:
                            result['minute'] = int(minute_match.group(1))
                        break
            except:
                continue
        
        # Se não achou times, tenta extrair do título da página
        if not result['home_team'] or not result['away_team']:
            try:
                title = await page.title()
                if title:
                    # Padrão: "TimeA x TimeB - FlashScore"
                    match = re.search(r'(.+?)\s*x\s+(.+?)\s*-', title)
                    if match:
                        result['home_team'] = match.group(1).strip()
                        result['away_team'] = match.group(2).strip()
                        print(f"[FlashScore] Times extraídos do título: {result['home_team']} x {result['away_team']}")
            except:
                pass
        
        return result
    
    def _extract_scores(self, text: str) -> tuple:
        """Extrai placares do texto"""
        if not text:
            return None, None
        
        # Procura padrões como "2 - 1", "2:1", "2x1"
        patterns = [
            r'(\d+)\s*[-–:]\s*(\d+)',
            r'(\d+)\s*x\s*(\d+)',
            r'(\d+)\s+(\d+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return int(match.group(1)), int(match.group(2))
        
        # Se não achou, procura todos os números
        numbers = re.findall(r'\d+', text)
        if len(numbers) >= 2:
            return int(numbers[0]), int(numbers[1])
        
        return None, None


# Instância global
_flashscore_scraper = None

async def get_flashscore_scraper():
    """Singleton para o scraper"""
    global _flashscore_scraper
    if _flashscore_scraper is None:
        _flashscore_scraper = FlashScorePlaywrightScraper()
        await _flashscore_scraper.init()
    return _flashscore_scraper


async def scrape_match_url(url: str) -> Optional[Dict]:
    """
    Função pública para fazer scraping de uma URL
    """
    scraper = await get_flashscore_scraper()
    return await scraper.scrape_match_by_url(url)


async def close_scraper():
    """Fecha o scraper ao encerrar"""
    global _flashscore_scraper
    if _flashscore_scraper:
        await _flashscore_scraper.close()
        _flashscore_scraper = None
