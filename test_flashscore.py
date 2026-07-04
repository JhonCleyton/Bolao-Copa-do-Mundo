"""
Script de teste para FlashScore Scraper
Execute: python test_flashscore.py
"""

import requests
from bs4 import BeautifulSoup
import re


def extract_match_id_from_url(url: str) -> str:
    """Extrai o ID da partida da URL do FlashScore"""
    # Padrões comuns:
    # https://www.flashscore.com.br/jogo/futebol/palmeiras-zeHzAVPu/santos-YBnXbQYG/?mid=tr7cFFXG
    # https://www.flashscore.com.br/jogo/tr7cFFXG/
    
    # Tenta extrair o mid da query string
    if 'mid=' in url:
        match = re.search(r'mid=([^&]+)', url)
        if match:
            return match.group(1)
    
    # Tenta extrair da path
    match = re.search(r'/jogo/([^/]+)/?$', url)
    if match:
        return match.group(1)
    
    # Tenta extrair os IDs dos times
    match = re.search(r'/jogo/futebol/[^/]+-([A-Za-z0-9]+)/[^/]+-([A-Za-z0-9]+)/', url)
    if match:
        return f"{match.group(1)}-{match.group(2)}"
    
    return None


def scrape_flashscore_match(url: str):
    """
    Faz scraping de uma partida do FlashScore
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
    }
    
    print(f"\n{'='*60}")
    print(f"🔗 URL: {url}")
    print(f"{'='*60}")
    
    try:
        print("📡 Fazendo requisição...")
        response = requests.get(url, headers=headers, timeout=15)
        print(f"📊 Status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"❌ Erro: Status {response.status_code}")
            return None
        
        print(f"📄 Tamanho: {len(response.text)} bytes")
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        result = {
            'url': url,
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
        
        # 1. NOME DOS TIMES
        print("\n🔍 Buscando nomes dos times...")
        
        # Tenta vários seletores
        selectors = [
            ('div', {'class': 'participant__participantName'}),
            ('span', {'class': 'participant__participantName'}),
            ('div', {'class': 'tname__text'}),
            ('a', {'class': 'participant__participantName'}),
        ]
        
        teams_found = []
        for tag, attrs in selectors:
            elements = soup.find_all(tag, attrs=attrs)
            for elem in elements:
                text = elem.get_text(strip=True)
                if text and text not in teams_found:
                    teams_found.append(text)
                    print(f"  🏃 Time encontrado: {text}")
        
        if len(teams_found) >= 2:
            result['home_team'] = teams_found[0]
            result['away_team'] = teams_found[1]
        
        # 2. PLACAR
        print("\n🔍 Buscando placar...")
        
        score_selectors = [
            ('div', {'class': 'detailScore__wrapper'}),
            ('div', {'class': 'scoreboard'}),
            ('div', {'class': 'current-result'}),
            ('span', {'class': 'score'}),
        ]
        
        for tag, attrs in score_selectors:
            elem = soup.find(tag, attrs=attrs)
            if elem:
                text = elem.get_text(strip=True)
                print(f"  📊 Texto do placar: {text}")
                
                # Tenta extrair números
                numbers = re.findall(r'(\d+)', text)
                if len(numbers) >= 2:
                    result['score_home'] = int(numbers[0])
                    result['score_away'] = int(numbers[1])
                    print(f"  ✅ Placar: {result['score_home']} x {result['score_away']}")
                    break
        
        # 3. STATUS/TEMPO
        print("\n🔍 Buscando status/tempo...")
        
        status_selectors = [
            ('div', {'class': 'matchStatus'}),
            ('div', {'class': 'status'}),
            ('span', {'class': 'matchTime'}),
            ('div', {'class': 'match-time'}),
        ]
        
        for tag, attrs in status_selectors:
            elem = soup.find(tag, attrs=attrs)
            if elem:
                text = elem.get_text(strip=True)
                print(f"  ⏱️ Status/Tempo: {text}")
                result['status'] = text
                
                # Tenta extrair minuto
                minute_match = re.search(r'(\d+)', text)
                if minute_match:
                    result['minute'] = int(minute_match.group(1))
                break
        
        # 4. COMPETIÇÃO
        print("\n🔍 Buscando competição...")
        
        comp_selectors = [
            ('span', {'class': 'tournament'}),
            ('div', {'class': 'tournament-name'}),
            ('a', {'class': 'tournament'}),
        ]
        
        for tag, attrs in comp_selectors:
            elem = soup.find(tag, attrs=attrs)
            if elem:
                text = elem.get_text(strip=True)
                print(f"  🏆 Competição: {text}")
                result['competition'] = text
                break
        
        # 5. DATA DA PARTIDA
        print("\n🔍 Buscando data...")
        
        date_selectors = [
            ('div', {'class': 'match-date'}),
            ('span', {'class': 'date'}),
            ('time', {}),
        ]
        
        for tag, attrs in date_selectors:
            elem = soup.find(tag, attrs=attrs)
            if elem:
                text = elem.get_text(strip=True)
                if text:
                    print(f"  📅 Data: {text}")
                    result['match_date'] = text
                    break
        
        # 6. EVENTOS (gols, cartões)
        print("\n🔍 Buscando eventos...")
        
        event_selectors = [
            ('div', {'class': 'event'}),
            ('div', {'class': 'match-event'}),
        ]
        
        for tag, attrs in event_selectors:
            events = soup.find_all(tag, attrs=attrs, limit=5)
            for event in events:
                text = event.get_text(strip=True)
                if text:
                    print(f"  ⚡ Evento: {text}")
                    result['events'].append(text)
        
        # RESULTADO FINAL
        print(f"\n{'='*60}")
        print("📊 RESULTADO DO SCRAPING:")
        print(f"{'='*60}")
        print(f"🏠 Time da Casa: {result['home_team'] or 'Não encontrado'}")
        print(f"✈️ Time Visitante: {result['away_team'] or 'Não encontrado'}")
        print(f"📊 Placar: {result['score_home'] or '?'} x {result['score_away'] or '?'}")
        print(f"⏱️ Status: {result['status'] or 'Não encontrado'}")
        print(f"🏆 Competição: {result['competition'] or 'Não encontrado'}")
        print(f"{'='*60}\n")
        
        return result
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    print("🌐 FLASHSCORE SCRAPER - TESTE")
    print("="*60)
    print("Cole a URL da partida do FlashScore (ex: https://www.flashscore.com.br/jogo/...)")
    print("Ou digite 'sair' para encerrar")
    print("="*60)
    
    while True:
        print("\n")
        url = input("🔗 URL: ").strip()
        
        if url.lower() in ['sair', 'exit', 'quit']:
            print("👋 Até logo!")
            break
        
        if not url:
            continue
        
        if not url.startswith('http'):
            url = 'https://' + url
        
        result = scrape_flashscore_match(url)
        
        if result:
            save = input("\n💾 Salvar resultado em arquivo? (s/n): ").strip().lower()
            if save == 's':
                import json
                filename = "flashscore_result.json"
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
                print(f"✅ Salvo em {filename}")


if __name__ == "__main__":
    main()
