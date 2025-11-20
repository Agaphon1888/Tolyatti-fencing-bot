import requests
import time
import logging
import threading

logger = logging.getLogger(__name__)

class KeepAlive:
    def __init__(self, app_urls, interval=600):
        self.app_urls = app_urls if isinstance(app_urls, list) else [app_urls]
        self.interval = interval
        self.running = False
        self.thread = None
    
    def ping_all(self):
        """Пингует все указанные URL"""
        for url in self.app_urls:
            try:
                response = requests.get(f"{url}/health", timeout=10)
                logger.info(f"✅ Ping to {url}: {response.status_code}")
            except Exception as e:
                logger.error(f"❌ Ping to {url} failed: {e}")
    
    def start(self):
        """Запускает автоматический пинг"""
        if self.running:
            logger.warning("KeepAlive already running")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        logger.info(f"🔄 KeepAlive started with {self.interval}s interval")
    
    def _run(self):
        """Основной цикл пинга"""
        while self.running:
            self.ping_all()
            time.sleep(self.interval)
    
    def stop(self):
        """Останавливает пинг"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("🛑 KeepAlive stopped")

# Глобальный экземпляр
keep_alive = KeepAlive("https://tolyatti-fencing-bot.onrender.com")

def start_keep_alive():
    """Запускает keep-alive"""
    keep_alive.start()
