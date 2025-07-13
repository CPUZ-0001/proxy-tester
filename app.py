import requests
import random
import json
import time
import threading
import socket
from concurrent.futures import ThreadPoolExecutor
from collections import defaultdict
import os
from flask import Flask, jsonify

app = Flask(__name__)

# Configuration
MAX_FINAL_PROXIES = 200
PHASE1_TIMEOUT = 5
PHASE2_TIMEOUT = 45
MAX_WORKERS = 50
API_PORT = 3000

# Global variable to store working proxies
working_proxies = {
    "http": [],
    "socks4": [],
    "socks5": []
}

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

def get_random_user_agent():
    return random.choice(USER_AGENTS)

def is_valid_proxy(proxy):
    try:
        if ':' not in proxy:
            return False
        host, port = proxy.split(':')
        socket.inet_aton(host)
        return 1 <= int(port) <= 65535
    except:
        return False

def detect_proxy_type(url):
    url = url.lower()
    if "socks5" in url:
        return "socks5"
    elif "socks4" in url:
        return "socks4"
    elif "http" in url or "https" in url:
        return "http"
    return "unknown"

def fetch_proxies():
    proxies_by_type = defaultdict(set)
    for src in PROXY_SOURCES:
        try:
            print(f"[+] Fetching: {src}")
            r = requests.get(src, headers={'User-Agent': get_random_user_agent()}, timeout=15)
            if r.status_code == 200:
                lines = r.text.strip().splitlines()
                valid = [p.strip() for p in lines if is_valid_proxy(p.strip())]
                ptype = detect_proxy_type(src)
                proxies_by_type[ptype].update(valid)
                print(f"  → {len(valid)} valid {ptype.upper()} proxies")
        except Exception as e:
            print(f"  → Error: {e}")
    return proxies_by_type

def get_proxy_config(proxy, proxy_type):
    scheme = {
        "http": "http",
        "socks4": "socks4",
        "socks5": "socks5"
    }.get(proxy_type, "http")
    return {
        "http": f"{scheme}://{proxy}",
        "https": f"{scheme}://{proxy}"
    }

def quick_test_proxy(proxy, proxy_type):
    try:
        config = get_proxy_config(proxy, proxy_type)
        r = requests.get(random.choice(TEST_URLS), proxies=config,
                         headers={'User-Agent': get_random_user_agent()},
                         timeout=PHASE1_TIMEOUT)
        return r.status_code == 200
    except:
        return False

def stability_test_proxy(proxy, proxy_type):
    config = get_proxy_config(proxy, proxy_type)
    end_time = time.time() + PHASE2_TIMEOUT
    while time.time() < end_time:
        try:
            r = requests.get(random.choice(TEST_URLS), proxies=config,
                             headers={'User-Agent': get_random_user_agent()},
                             timeout=5)
            if r.status_code != 200:
                return False
        except:
            return False
        time.sleep(random.uniform(1, 2))
    return True

def update_proxies():
    global working_proxies
    start = time.time()
    proxies_by_type = fetch_proxies()

    for ptype, proxies in proxies_by_type.items():
        if ptype == "unknown":
            continue

        print(f"\n🧪 Phase 1: {ptype.upper()} - Quick test {len(proxies)} proxies...\n")
        phase1 = []
        lock1 = threading.Lock()

        def phase1_worker(proxy):
            if quick_test_proxy(proxy, ptype):
                with lock1:
                    phase1.append(proxy)
                    print(f"[✓] Phase 1 ({ptype}): {proxy}")

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            executor.map(phase1_worker, proxies)

        print(f"\n✅ {ptype.upper()} Phase 1 done: {len(phase1)} passed quick check\n")

        print(f"⏳ Phase 2: {ptype.upper()} - Stability test (30s each)\n")
        final = []
        lock2 = threading.Lock()

        def phase2_worker(proxy):
            if len(final) >= MAX_FINAL_PROXIES:
                return
            if stability_test_proxy(proxy, ptype):
                with lock2:
                    if len(final) < MAX_FINAL_PROXIES:
                        final.append(proxy)
                        print(f"[★] {ptype.upper()} Stable ({len(final)}/{MAX_FINAL_PROXIES}): {proxy}")

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            executor.map(phase2_worker, phase1)

        working_proxies[ptype] = final

        with open(f"proxies_{ptype}.json", "w") as f:
            json.dump(final, f, indent=2)

        print(f"✔️ Final working {ptype.upper()} proxies: {len(final)} saved to proxies_{ptype}.json")

    print(f"\n🎉 All done in {time.time() - start:.2f}s")

# API Endpoints
@app.route('/')
def index():
    return """
    <h1>Proxy Scraper API</h1>
    <p>Available endpoints:</p>
    <ul>
        <li><a href="/proxies">/proxies</a> - Get all proxies</li>
        <li><a href="/proxies/http">/proxies/http</a> - Get HTTP proxies</li>
        <li><a href="/proxies/socks4">/proxies/socks4</a> - Get SOCKS4 proxies</li>
        <li><a href="/proxies/socks5">/proxies/socks5</a> - Get SOCKS5 proxies</li>
        <li><a href="/update">/update</a> - Update proxy list</li>
    </ul>
    """

@app.route('/proxies')
def get_all_proxies():
    return jsonify({
        "http": working_proxies["http"],
        "socks4": working_proxies["socks4"],
        "socks5": working_proxies["socks5"],
        "count": {
            "http": len(working_proxies["http"]),
            "socks4": len(working_proxies["socks4"]),
            "socks5": len(working_proxies["socks5"]),
            "total": len(working_proxies["http"]) + len(working_proxies["socks4"]) + len(working_proxies["socks5"])
        }
    })

@app.route('/proxies/<proxy_type>')
def get_proxies_by_type(proxy_type):
    if proxy_type not in working_proxies:
        return jsonify({"error": "Invalid proxy type. Use http, socks4, or socks5"}), 400
    return jsonify({
        "type": proxy_type,
        "proxies": working_proxies[proxy_type],
        "count": len(working_proxies[proxy_type])
    })

@app.route('/update')
def update_proxy_list():
    threading.Thread(target=update_proxies).start()
    return jsonify({"status": "Proxy update started in background"})

def run_api():
    app.run(host='0.0.0.0', port=API_PORT)

if __name__ == "__main__":
    # Start the proxy updater in background
    threading.Thread(target=update_proxies).start()
    
    # Start the API
    run_api()
