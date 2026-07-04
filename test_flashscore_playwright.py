"""
Script de teste para FlashScore usando Playwright (navegador real)
Execute: python test_flashscore_playwright.py
Instale primeiro: pip install playwright
Depois: playwright install chromium
"""

import asyncio
from playwright.async_api import async_playwright
import re


async def scrape_flashscore_with_playwright(url: str):
    """
    Faz scraping usando Playwright (executa JavaScript do site)
    """
    print(f"\n{'='*60}")
    print(f"🔗 URL: {url}")
    print(f"{'='*60}")
    
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
    
    async with async_playwright() as p:
        print("🖥️  Iniciando navegador...")
        browser = await p.chromium.launch(headless=True)
        
        print("📄 Criando nova página...")
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='pt-BR'
        )
        page = await context.new_page()
        
        try:
            print("🌐 Acessando URL...")
            await page.goto(url, wait_until='networkidle', timeout=30000)
            
            print("⏳ Aguardando carregamento...")
            await asyncio.sleep(3)  # Aguarda JavaScript carregar
            
            # 1. NOME DOS TIMES
            print("\n🔍 Buscando nomes dos times...")
            
            team_selectors = [
                '.participant__participantName',
                '.tname__text',
                '[class*="participant"] [class*="name"]',
                '.match-info [class*="team"]',
                '[data-testid="participant-name"]'
            ]
            
            for selector in team_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    if len(elements) >= 2:
                        home = await elements[0].text_content()
                        away = await elements[1].text_content()
                        if home and away:
                            result['home_team'] = home.strip()
                            result['away_team'] = away.strip()
                            print(f"  ✅ Times: {result['home_team']} x {result['away_team']}")
                            break
                except:
                    continue
            
            # 2. PLACAR
            print("\n🔍 Buscando placar...")
            
            score_selectors = [
                '.detailScore__wrapper',
                '.current-result',
                '[class*="score"]',
                '.scoreboard',
                '[data-testid="score"]'
            ]
            
            for selector in score_selectors:
                try:
                    elem = await page.query_selector(selector)
                    if elem:
                        text = await elem.text_content()
                        if text:
                            print(f"  📊 Texto encontrado: {text.strip()}")
                            
                            # Extrai números
                            numbers = re.findall(r'(\d+)', text)
                            if len(numbers) >= 2:
                                result['score_home'] = int(numbers[0])
                                result['score_away'] = int(numbers[1])
                                print(f"  ✅ Placar: {result['score_home']} x {result['score_away']}")
                                break
                except:
                    continue
            
            # 3. STATUS/TEMPO
            print("\n🔍 Buscando status/tempo...")
            
            status_selectors = [
                '.matchStatus',
                '.status',
                '.matchTime',
                '[class*="time"]',
                '[data-testid="status"]'
            ]
            
            for selector in status_selectors:
                try:
                    elem = await page.query_selector(selector)
                    if elem:
                        text = await elem.text_content()
                        if text:
                            result['status'] = text.strip()
                            print(f"  ⏱️ Status: {result['status']}")
                            
                            # Extrai minuto
                            minute_match = re.search(r'(\d+)', text)
                            if minute_match:
                                result['minute'] = int(minute_match.group(1))
                            break
                except:
                    continue
            
            # 4. COMPETIÇÃO
            print("\n🔍 Buscando competição...")
            
            comp_selectors = [
                '.tournament',
                '.tournament-name',
                '[class*="competition"]',
                '[data-testid="tournament-name"]'
            ]
            
            for selector in comp_selectors:
                try:
                    elem = await page.query_selector(selector)
                    if elem:
                        text = await elem.text_content()
                        if text:
                            result['competition'] = text.strip()
                            print(f"  🏆 Competição: {result['competition']}")
                            break
                except:
                    continue
            
            # 5. DATA
            print("\n🔍 Buscando data...")
            
            date_selectors = [
                '.match-date',
                '.date',
                'time',
                '[data-testid="date"]'
            ]
            
            for selector in date_selectors:
                try:
                    elem = await page.query_selector(selector)
                    if elem:
                        text = await elem.text_content()
                        if text:
                            result['match_date'] = text.strip()
                            print(f"  📅 Data: {result['match_date']}")
                            break
                except:
                    continue
            
            # 6. EVENTOS
            print("\n🔍 Buscando eventos...")
            
            event_selectors = [
                '.event',
                '.match-event',
                '[class*="incident"]',
                '[data-testid="incident"]'
            ]
            
            for selector in event_selectors:
                try:
                    events = await page.query_selector_all(selector)
                    for i, event in enumerate(events[:5]):  # Primeiros 5 eventos
                        text = await event.text_content()
                        if text:
                            result['events'].append(text.strip())
                            print(f"  ⚡ Evento {i+1}: {text.strip()[:80]}")
                except:
                    continue
            
            # Tenta pegar mais dados via JavaScript direto
            print("\n🔍 Tentando extrair via JavaScript...")
            try:
                js_result = await page.evaluate('''() => {
                    // Tenta achar dados em variáveis globais ou elementos específicos
                    const data = {};
                    
                    // Procura em scripts da página
                    const scripts = document.querySelectorAll('script');
                    for (const script of scripts) {
                        const text = script.textContent;
                        if (text && text.includes('score') || text.includes('home')) {
                            // Procura padrões de JSON
                            const matches = text.match(/\{[^}]*"score"[^}]*\}/g);
                            if (matches) {
                                data.script_data = matches[0];
                            }
                        }
                    }
                    
                    // Tenta extrair de meta tags ou data attributes
                    const scoreboard = document.querySelector('[class*="score"]');
                    if (scoreboard) {
                        data.score_text = scoreboard.textContent;
                        data.score_html = scoreboard.innerHTML;
                    }
                    
                    return data;
                }''')
                
                if js_result:
                    print(f"  📦 Dados JS encontrados: {js_result}")
                    
            except Exception as e:
                print(f"  ⚠️ Erro no JS: {e}")
            
            await browser.close()
            
            # RESULTADO
            print(f"\n{'='*60}")
            print("📊 RESULTADO DO SCRAPING:")
            print(f"{'='*60}")
            print(f"🏠 Time da Casa: {result['home_team'] or '❌ Não encontrado'}")
            print(f"✈️ Time Visitante: {result['away_team'] or '❌ Não encontrado'}")
            print(f"📊 Placar: {result['score_home'] if result['score_home'] is not None else '?'} x {result['score_away'] if result['score_away'] is not None else '?'}")
            print(f"⏱️ Status: {result['status'] or '❌ Não encontrado'}")
            print(f"🏆 Competição: {result['competition'] or '❌ Não encontrado'}")
            print(f"{'='*60}\n")
            
            return result
            
        except Exception as e:
            print(f"❌ Erro: {e}")
            await browser.close()
            return None


def check_installation():
    """Verifica se playwright está instalado"""
    try:
        import playwright
        print("✅ Playwright instalado")
        return True
    except ImportError:
        print("❌ Playwright não instalado")
        print("\n📦 Instale com:")
        print("   pip install playwright")
        print("   playwright install chromium")
        return False


async def main():
    print("🌐 FLASHSCORE SCRAPER - PLAYWRIGHT EDITION")
    print("="*60)
    
    if not check_installation():
        return
    
    print("Cole a URL da partida do FlashScore")
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
        
        result = await scrape_flashscore_with_playwright(url)
        
        if result:
            save = input("\n💾 Salvar resultado em arquivo? (s/n): ").strip().lower()
            if save == 's':
                import json
                filename = "flashscore_result.json"
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
                print(f"✅ Salvo em {filename}")


if __name__ == "__main__":
    asyncio.run(main())
