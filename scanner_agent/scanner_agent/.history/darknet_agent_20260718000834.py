import requests
from bs4 import BeautifulSoup
import urllib3
import json
import os
from datetime import datetime

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class WebScannerAgent:
    def __init__(self):
        self.results_dir = os.path.join(os.path.dirname(__file__), 'results')
        os.makedirs(self.results_dir, exist_ok=True)
        
        self.tor_proxies = {
            'http': 'socks5h://127.0.0.1:9050',
            'https': 'socks5h://127.0.0.1:9050'
        }
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        self.scan_results = []

    def is_onion(self, url):
        return '.onion' in url.lower()

    def load_urls_from_file(self, filename='urls.txt'):
        """Загружает URL из файла"""
        filepath = os.path.join(os.path.dirname(__file__), filename)
        if not os.path.exists(filepath):
            print(f"❌ Файл {filename} не найден!")
            return []
        
        with open(filepath, 'r', encoding='utf-8') as f:
            urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        
        print(f" Загружено {len(urls)} URL из {filename}")
        return urls

    def save_results(self):
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = os.path.join(self.results_dir, f'scan_{timestamp}.json')
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.scan_results, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 Результаты сохранены: {filename}")

    def scan(self, url, timeout=15):
        url = url.strip()
        if not url.startswith('http'):
            url = 'http://' + url
        
        print(f"\n[+] Сканирование: {url}")
        
        result = {
            'url': url,
            'timestamp': datetime.now().isoformat(),
            'success': False,
            'status': None,
            'title': None,
            'preview': None,
            'error': None
        }
        
        try:
            proxies = self.tor_proxies if self.is_onion(url) else None
            response = requests.get(url, proxies=proxies, headers=self.headers, timeout=timeout, verify=False)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            title = soup.title.string.strip() if soup.title else 'Без заголовка'
            text_preview = soup.get_text(separator=' ', strip=True)[:500]
            
            result.update({
                'success': True,
                'status': response.status_code,
                'title': title,
                'preview': text_preview
            })
            
            print(f"✅ Статус: {response.status_code}")
            print(f"📌 Заголовок: {title}")
            
        except requests.exceptions.ProxyError:
            result['error'] = "Tor не запущен!"
            print("❌ Tor не запущен! Запусти ярлык 'Запустить Tor'")
        except requests.exceptions.Timeout:
            result['error'] = "Таймаут"
            print("❌ Сайт не отвечает")
        except Exception as e:
            result['error'] = str(e)
            print(f"❌ Ошибка: {e}")
        
        self.scan_results.append(result)
        return result

if __name__ == "__main__":
    agent = WebScannerAgent()
    print(" Darknet Agent v2.0")
    print("=" * 50)
    
    # Загружаем URLs из файла
    urls = agent.load_urls_from_file('urls.txt')
    
    if not urls:
        print("Список пуст. Введите URL вручную или создайте urls.txt")
        while True:
            target = input("\nURL: ")
            if target.lower() in ['exit', 'quit', 'выход']:
                break
            if target:
                agent.scan(target)
    else:
        print(f"🚀 Начинаю массовое сканирование {len(urls)} сайтов...")
        for i, url in enumerate(urls, 1):
            print(f"\n--- [{i}/{len(urls)}] ---")
            agent.scan(url)
    
    # Сохраняем результаты
    if agent.scan_results:
        agent.save_results()
        success_count = sum(1 for r in agent.scan_results if r['success'])
        print(f"\n📊 Итог: {success_count}/{len(agent.scan_results)} успешных")
    
    print("👋 Готово!")