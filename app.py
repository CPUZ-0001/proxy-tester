import requests
import random
import json
import time
import threading
import socket
from concurrent.futures import ThreadPoolExecutor
from collections import defaultdict
import os
import speedtest
import schedule
import signal
import sys
import logging
from datetime import datetime
from flask import Flask, jsonify, send_from_directory
import threading


# Create Flask app
app = Flask(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('proxy_tester.log'),
        logging.StreamHandler()
    ]
)

# Configuration
MAX_FINAL_PROXIES = 200
PHASE1_TIMEOUT = 8       # Quick connectivity test
PHASE2_TIMEOUT = 15      # Stability test duration
PHASE3_TIMEOUT = 10      # Speed test timeout
PHASE4_TIMEOUT = 10      # Location/anonymity check timeout
MAX_WORKERS = 200
BAD_PROXY_FILE_PREFIX = "bad_proxies_"
IPINFO_API = "https://ipinfo.io/{ip}/json"
IPAPI_API = "http://ip-api.com/json/{ip}?fields=status,message,country,countryCode,isp,proxy,hosting"
CHECK_INTERVAL_MINUTES = 60  # Run every 15 minutes

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1",
]

PROXY_SOURCES = [
    "https://api.proxyscrape.com/v4/free-proxy-list/get?request=displayproxies&protocol=http&timeout=10000&country=all&limit=2000",
    "https://api.proxyscrape.com/v4/free-proxy-list/get?request=displayproxies&protocol=socks4&timeout=10000&country=all&limit=2000",
    "https://api.proxyscrape.com/v4/free-proxy-list/get?request=displayproxies&protocol=socks5&timeout=10000&country=all&limit=2000",
    "https://proxylist.geonode.com/api/proxy-list?limit=500&page=1&sort_by=lastChecked&sort_type=desc",
    "https://www.proxy-list.download/api/v1/get?type=https",
    "https://www.proxy-list.download/api/v1/get?type=socks5",
    "https://proxy-spider.com/api/proxies.example.txt",
    "https://raw.githubusercontent.com/almroot/proxylist/master/list.txt",
    "https://raw.githubusercontent.com/B4RC0DE-TM/proxy-list/main/HTTP.txt",
    "https://raw.githubusercontent.com/Anonym0usWork1221/Free-Proxies/main/proxy_files/http_proxies.txt",
    "https://raw.githubusercontent.com/Anonym0usWork1221/Free-Proxies/main/proxy_files/socks4_proxies.txt",
    "https://raw.githubusercontent.com/Anonym0usWork1221/Free-Proxies/main/proxy_files/socks5_proxies.txt",
    "https://raw.githubusercontent.com/zevtyardt/proxy-list/main/http.txt",
    "https://raw.githubusercontent.com/zevtyardt/proxy-list/main/socks4.txt",
    "https://raw.githubusercontent.com/zevtyardt/proxy-list/main/socks5.txt",
    "https://raw.githubusercontent.com/ErcinDedeoglu/proxies/main/proxies/http.txt",
    "https://raw.githubusercontent.com/ErcinDedeoglu/proxies/main/proxies/socks4.txt",
    "https://raw.githubusercontent.com/ErcinDedeoglu/proxies/main/proxies/socks5.txt",
    "https://raw.githubusercontent.com/ProxyScraper/ProxyScraper/main/socks4.txt",
    "https://raw.githubusercontent.com/ProxyScraper/ProxyScraper/main/socks5.txt",
    "https://raw.githubusercontent.com/mmpx12/proxy-list/master/http.txt",
    "https://raw.githubusercontent.com/mmpx12/proxy-list/master/socks4.txt",
    "https://raw.githubusercontent.com/mmpx12/proxy-list/master/socks5.txt",
    "https://spys.me/proxy.txt",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks4.txt",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks5.txt",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies_anonymous/http.txt",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies_anonymous/socks4.txt",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies_anonymous/socks5.txt",
    "https://raw.githubusercontent.com/roosterkid/openproxylist/main/HTTPS_RAW.txt",
    "https://raw.githubusercontent.com/roosterkid/openproxylist/main/SOCKS5_RAW.txt",
    "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/http.txt",
    "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/socks4.txt",
    "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/socks5.txt",
    "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt",
    "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/socks4.txt",
    "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/socks5.txt",
    "https://raw.githubusercontent.com/rdavydov/proxy-list/main/proxies/http.txt",
    "https://raw.githubusercontent.com/rdavydov/proxy-list/main/proxies/socks4.txt",
    "https://raw.githubusercontent.com/rdavydov/proxy-list/main/proxies/socks5.txt",
    "https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt",
    "https://raw.githubusercontent.com/hookzof/socks5_list/master/proxy.txt",
    "https://raw.githubusercontent.com/proxy4parsing/proxy-list/main/http.txt",
    "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/http.txt",
    "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/socks4.txt",
    "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/socks5.txt",
    "https://raw.githubusercontent.com/hookzof/socks5_list/master/proxy.txt",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks4.txt",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks5.txt",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies_anonymous/http.txt",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies_anonymous/socks4.txt",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies_anonymous/socks5.txt",
    "https://raw.githubusercontent.com/proxy4parsing/proxy-list/main/http.txt",
    "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt",
    "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/https.txt",
    "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/socks4.txt",
    "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/socks5.txt",
    "https://raw.githubusercontent.com/roosterkid/openproxylist/main/HTTPS_RAW.txt",
    "https://raw.githubusercontent.com/roosterkid/openproxylist/main/SOCKS5_RAW.txt",
    "https://raw.githubusercontent.com/sunny9577/proxy-scraper/master/proxies.txt",
    "https://raw.githubusercontent.com/rdavydov/proxy-list/main/proxies/http.txt",
    "https://raw.githubusercontent.com/rdavydov/proxy-list/main/proxies/socks4.txt",
    "https://raw.githubusercontent.com/rdavydov/proxy-list/main/proxies/socks5.txt"
  ]

TEST_URLS = [
    "https://httpbin.org/ip",
    "https://api.ipify.org?format=json",
    "https://icanhazip.com",
    "https://ident.me",
    "https://ifconfig.me/ip",
    "https://ipinfo.io/ip",
    "https://ip.seeip.org/jsonip?",
    "https://api.myip.com",
    "https://checkip.amazonaws.com",
    "https://wtfismyip.com/text",
    "https://ipwho.is",
    "https://ipapi.co/ip/",
    "https://ip.tyk.nu",
    "https://ip.360.cn/IPShare/info",
]

class ProxyTester:
    def __init__(self):
        self.bad_proxies = load_bad_proxies()
        self.stats = {
            'http': defaultdict(int),
            'socks4': defaultdict(int),
            'socks5': defaultdict(int)
        }
        self.running = True

    def get_random_user_agent(self):
        return random.choice(USER_AGENTS)

    def is_valid_proxy(self, proxy):
        try:
            if ':' not in proxy:
                return False
            host, port = proxy.split(':')
            socket.inet_aton(host)
            return 1 <= int(port) <= 65535
        except:
            return False

    def detect_proxy_type(self, url):
        url = url.lower()
        if "socks5" in url:
            return "socks5"
        elif "socks4" in url:
            return "socks4"
        elif "http" in url or "https" in url:
            return "http"
        return "unknown"

    def get_proxy_config(self, proxy, proxy_type):
        scheme = {
            "http": "http",
            "socks4": "socks4",
            "socks5": "socks5"
        }.get(proxy_type, "http")
        return {
            "http": f"{scheme}://{proxy}",
            "https": f"{scheme}://{proxy}"
        }

    def quick_test_proxy(self, proxy, proxy_type):
        """Phase 1: Basic connectivity test"""
        if not self.running:
            return False
            
        try:
            config = self.get_proxy_config(proxy, proxy_type)
            r = requests.get(random.choice(TEST_URLS), 
                           proxies=config,
                           headers={'User-Agent': self.get_random_user_agent()},
                           timeout=PHASE1_TIMEOUT)
            return r.status_code == 200
        except:
            self.bad_proxies[proxy_type].add(proxy)
            return False

    def stability_test_proxy(self, proxy, proxy_type):
        """Phase 2: Stability test with multiple requests"""
        if not self.running:
            return False
            
        config = self.get_proxy_config(proxy, proxy_type)
        end_time = time.time() + PHASE2_TIMEOUT
        success_count = 0
        
        while time.time() < end_time and self.running:
            try:
                r = requests.get(random.choice(TEST_URLS), 
                               proxies=config,
                               headers={'User-Agent': self.get_random_user_agent()},
                               timeout=5)
                if r.status_code == 200:
                    success_count += 1
                else:
                    self.bad_proxies[proxy_type].add(proxy)
                    return False
                time.sleep(random.uniform(1, 2))
            except:
                self.bad_proxies[proxy_type].add(proxy)
                return False
        
        # Require at least 3 successful requests to pass
        return success_count >= 3

    def speed_test_proxy(self, proxy, proxy_type):
        """Phase 3: Latency and bandwidth test"""
        if not self.running:
            return None
            
        config = self.get_proxy_config(proxy, proxy_type)
        start_time = time.time()
        
        try:
            # Test latency with small request
            latency_start = time.time()
            requests.get(TEST_URLS[0], 
                        proxies=config,
                        headers={'User-Agent': self.get_random_user_agent()},
                        timeout=PHASE3_TIMEOUT)
            latency = (time.time() - latency_start) * 1000  # in ms
            
            # Test download speed with medium file
            speed_test_url = "https://speedtest.selectel.ru/10MB"
            dl_start = time.time()
            response = requests.get(speed_test_url, 
                                  proxies=config,
                                  stream=True,
                                  headers={'User-Agent': self.get_random_user_agent()},
                                  timeout=PHASE3_TIMEOUT)
            dl_size = 10 * 1024 * 1024  # 10MB
            dl_time = time.time() - dl_start
            dl_speed = (dl_size / dl_time) / (1024 * 1024)  # in MB/s
            
            return {
                'latency': round(latency, 2),
                'download_speed': round(dl_speed, 2),
                'test_duration': round(time.time() - start_time, 2)
            }
        except:
            self.bad_proxies[proxy_type].add(proxy)
            return None

    def check_anonymity_and_location(self, proxy, proxy_type):
        """Phase 4: Check proxy anonymity and location"""
        if not self.running:
            return None
            
        config = self.get_proxy_config(proxy, proxy_type)
        try:
            # First get our external IP through the proxy
            r = requests.get("https://api.ipify.org?format=json", 
                           proxies=config,
                           headers={'User-Agent': self.get_random_user_agent()},
                           timeout=PHASE4_TIMEOUT)
            ip_data = r.json()
            proxy_ip = ip_data['ip']
            
            # Check for anonymity headers
            test_headers = requests.get("https://httpbin.org/headers", 
                                      proxies=config,
                                      headers={'User-Agent': self.get_random_user_agent()},
                                      timeout=PHASE4_TIMEOUT).json()
            
            anonymity = "transparent"
            headers = test_headers['headers']
            if 'Via' not in headers and 'X-Forwarded-For' not in headers:
                anonymity = "anonymous" if 'Proxy-Connection' not in headers else "elite"
            
            # Get location info
            location_info = requests.get(IPAPI_API.format(ip=proxy_ip),
                                    timeout=PHASE4_TIMEOUT).json()
            
            return {
                'ip': proxy_ip,
                'anonymity': anonymity,
                'country': location_info.get('country', 'Unknown'),
                'country_code': location_info.get('countryCode', 'XX'),
                'isp': location_info.get('isp', 'Unknown'),
                'is_hosting': location_info.get('hosting', False),
                'is_proxy': location_info.get('proxy', False)
            }
        except:
            self.bad_proxies[proxy_type].add(proxy)
            return None

    def stop(self):
        """Signal the tester to stop all operations"""
        self.running = False

def load_bad_proxies():
    bad_proxies = defaultdict(set)
    for ptype in ['http', 'socks4', 'socks5']:
        try:
            with open(f"{BAD_PROXY_FILE_PREFIX}{ptype}.json", "r") as f:
                bad_proxies[ptype] = set(json.load(f))
        except (FileNotFoundError, json.JSONDecodeError):
            pass
    return bad_proxies

def save_bad_proxies(bad_proxies):
    for ptype, proxies in bad_proxies.items():
        with open(f"{BAD_PROXY_FILE_PREFIX}{ptype}.json", "w") as f:
            json.dump(list(proxies), f, indent=2)

def fetch_proxies(tester):
    proxies_by_type = defaultdict(set)
    
    for src in PROXY_SOURCES:
        try:
            logging.info(f"Fetching: {src}")
            r = requests.get(src, headers={'User-Agent': tester.get_random_user_agent()}, timeout=15)
            if r.status_code == 200:
                lines = r.text.strip().splitlines()
                ptype = tester.detect_proxy_type(src)
                # Filter out known bad proxies
                valid = [p.strip() for p in lines 
                        if tester.is_valid_proxy(p.strip()) 
                        and p.strip() not in tester.bad_proxies.get(ptype, set())]
                proxies_by_type[ptype].update(valid)
                logging.info(f"  → {len(valid)} valid {ptype.upper()} proxies (after filtering bad proxies)")
        except Exception as e:
            logging.error(f"  → Error fetching {src}: {e}")
    return proxies_by_type

def update_proxies():
    start = time.time()
    tester = ProxyTester()
    proxies_by_type = fetch_proxies(tester)

    for ptype, proxies in proxies_by_type.items():
        if ptype == "unknown":
            continue

        logging.info(f"\n🧪 Phase 1 ({ptype.upper()}): Quick connectivity test for {len(proxies)} proxies...")
        phase1_proxies = []
        lock1 = threading.Lock()

        def phase1_worker(proxy):
            if tester.quick_test_proxy(proxy, ptype):
                with lock1:
                    phase1_proxies.append(proxy)
                    logging.info(f"[✓] Phase 1 ({ptype}): {proxy}")

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            executor.map(phase1_worker, proxies)

        logging.info(f"\n✅ {ptype.upper()} Phase 1 complete: {len(phase1_proxies)} passed quick check")

        logging.info(f"\n⏳ Phase 2 ({ptype.upper()}): Stability test (15s each)")
        phase2_proxies = []
        lock2 = threading.Lock()

        def phase2_worker(proxy):
            if len(phase2_proxies) >= MAX_FINAL_PROXIES:
                return
            if tester.stability_test_proxy(proxy, ptype):
                with lock2:
                    if len(phase2_proxies) < MAX_FINAL_PROXIES:
                        phase2_proxies.append(proxy)
                        logging.info(f"[★] {ptype.upper()} Stable ({len(phase2_proxies)}/{MAX_FINAL_PROXIES}): {proxy}")

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            executor.map(phase2_worker, phase1_proxies)

        logging.info(f"\n🚀 Phase 3 ({ptype.upper()}): Speed test for {len(phase2_proxies)} proxies")
        phase3_results = {}
        lock3 = threading.Lock()

        def phase3_worker(proxy):
            speed_data = tester.speed_test_proxy(proxy, ptype)
            if speed_data:
                with lock3:
                    phase3_results[proxy] = speed_data
                    logging.info(f"[⚡] {ptype.upper()} Speed: {proxy} | "
                          f"Latency: {speed_data['latency']}ms | "
                          f"Speed: {speed_data['download_speed']}MB/s")

        with ThreadPoolExecutor(max_workers=min(MAX_WORKERS, 10)) as executor:  # Fewer workers for speed tests
            executor.map(phase3_worker, phase2_proxies)

        logging.info(f"\n🌍 Phase 4 ({ptype.upper()}): Location & anonymity check")
        final_proxies = []
        lock4 = threading.Lock()

        def phase4_worker(proxy):
            if proxy in phase3_results:  # Only test proxies that passed speed test
                geo_data = tester.check_anonymity_and_location(proxy, ptype)
                if geo_data:
                    with lock4:
                        final_data = {
                            'proxy': proxy,
                            'type': ptype,
                            'speed': phase3_results[proxy],
                            'location': geo_data
                        }
                        final_proxies.append(final_data)
                        logging.info(f"[🌐] {ptype.upper()} Location: {proxy} | "
                              f"Country: {geo_data['country']} | "
                              f"Anonymity: {geo_data['anonymity'].upper()}")

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            executor.map(phase4_worker, phase2_proxies)

        # Save final results
        with open(f"proxies_{ptype}.json", "w") as f:
            json.dump(final_proxies, f, indent=2)

        logging.info(f"\n✔️ Final working {ptype.upper()} proxies: {len(final_proxies)} saved to proxies_{ptype}.json")

    # Save bad proxies
    save_bad_proxies(tester.bad_proxies)
    logging.info(f"\n🎉 All done in {time.time() - start:.2f}s")
    logging.info(f"🚫 Bad proxies saved to {BAD_PROXY_FILE_PREFIX}*.json files")

def run_scheduled_job():
    """Run the proxy update job with error handling"""
    try:
        logging.info(f"\n{'='*50}")
        logging.info(f"🚀 Starting scheduled proxy check at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        update_proxies()
        logging.info(f"✅ Completed proxy check at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logging.info(f"{'='*50}\n")
    except Exception as e:
        logging.error(f"❌ Error in scheduled job: {e}", exc_info=True)

def signal_handler(sig, frame):
    """Handle shutdown signals gracefully"""
    logging.info("🛑 Received shutdown signal. Exiting gracefully...")
    sys.exit(0)

@app.route('/proxies/http', methods=['GET'])
def get_http_proxies():
    """Endpoint to get HTTP proxies"""
    try:
        return send_from_directory('.', 'proxies_http.json', mimetype='application/json')
    except FileNotFoundError:
        return jsonify({"error": "HTTP proxies file not found"}), 404

@app.route('/proxies/socks4', methods=['GET'])
def get_socks4_proxies():
    """Endpoint to get SOCKS4 proxies"""
    try:
        return send_from_directory('.', 'proxies_socks4.json', mimetype='application/json')
    except FileNotFoundError:
        return jsonify({"error": "SOCKS4 proxies file not found"}), 404

@app.route('/proxies/socks5', methods=['GET'])
def get_socks5_proxies():
    """Endpoint to get SOCKS5 proxies"""
    try:
        return send_from_directory('.', 'proxies_socks5.json', mimetype='application/json')
    except FileNotFoundError:
        return jsonify({"error": "SOCKS5 proxies file not found"}), 404

@app.route('/proxies/all', methods=['GET'])
def get_all_proxies():
    """Endpoint to get all proxies combined"""
    try:
        proxies = {}
        with open('proxies_http.json', 'r') as f:
            proxies['http'] = json.load(f)
        with open('proxies_socks4.json', 'r') as f:
            proxies['socks4'] = json.load(f)
        with open('proxies_socks5.json', 'r') as f:
            proxies['socks5'] = json.load(f)
        return jsonify(proxies)
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 404

def run_flask_app():
    """Run the Flask API in a separate thread"""
    app.run(host='0.0.0.0', port=5000, threaded=True)

def main():
    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logging.info("🚀 Starting Proxy Tester Service")
    logging.info(f"🔁 Will check proxies every {CHECK_INTERVAL_MINUTES} minutes")
    
    # Start Flask API in a separate thread
    flask_thread = threading.Thread(target=run_flask_app, daemon=True)
    flask_thread.start()
    
    # Run immediately on startup
    run_scheduled_job()
    
    # Schedule the job to run every 15 minutes
    schedule.every(CHECK_INTERVAL_MINUTES).minutes.do(run_scheduled_job)
    
    # Keep the program running
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    main()
