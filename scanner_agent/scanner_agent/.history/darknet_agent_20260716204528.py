import requests
from bs4 import BeautifulSoup
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class WebScannerAgent:
    def __init__(self):
        self.tor_proxies = {
            'http': 'socks5h://127.0.0.1:9050',
            'https': 'socks5h://127.0.0.1:9050'
        }
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

    def is_onion(self, url):
        return '.onion' in url.lower()

    def scan(self, url, timeout=15):
        url = url.strip()
        if not url.startswith('http'):
            url = 'http://' + url
        print(f"\n[+] Сканирование: {url}")
        try:
            proxies = self.tor_proxies if self.is_onion(url) else None
            response = requests.get(url, proxies=proxies, headers=self.headers, timeout=timeout, verify=False)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            title = soup.title.string.strip() if soup.title else 'Без заголовка'
            text_preview = soup.get_text(separator=' ', strip=True)[:200]
            print(f"✅ Статус: {response.status_code}")
            print(f"📌 Заголовок: {title}")
            print(f"📄 Превью: {text_preview}...")
            return {'url': url, 'success': True}
        except requests.exceptions.ProxyError:
            print("❌ Ошибка: Tor не запущен. Нажми на ярлык 'Запустить Tor'.")
        except requests.exceptions.Timeout:
            print("❌ Ошибка: Сайт не отвечает.")
        except Exception as e:
            print(f"❌ Ошибка: {e}")
        return {'url': url, 'success': False}

if __name__ == "__main__":
    agent = WebScannerAgent()
    print("🤖 Агент запущен. Введи URL или 'exit' для выхода.")
    while True:
        target = input("\nURL: ")
        if target.lower() in ['exit', 'quit', 'выход']:
            break
        if target:
            agent.scan(target)