# prepare_proxies.py (финальная версия с максимально агрессивной дедупликацией)

import sys
import os
import requests
import base64
import random
import json
from urllib.parse import urlparse, parse_qs, unquote

def parse_vmess(proxy_url):
    try:
        if not proxy_url.startswith("vmess://"): return None
        b64_data = proxy_url.replace("vmess://", "")
        json_data = None
        try:
            json_data = json.loads(base64.b64decode(b64_data).decode('utf-8'))
        except Exception:
            try:
                b64_data += '=' * (-len(b64_data) % 4)
                json_data = json.loads(base64.b64decode(b64_data).decode('utf-8'))
            except Exception: return None
        if not json_data: return None
        return {
            'protocol': 'vmess', 'address': json_data.get('add', ''), 'port': int(json_data.get('port', 0)), 'id': json_data.get('id', ''),
            'security': 'tls' if json_data.get('tls') == 'tls' else 'none', 'network': json_data.get('net', 'tcp'),
            'sni': json_data.get('sni', json_data.get('host', '')), 'ws_path': json_data.get('path', '/')
        }
    except Exception: return None

def parse_vless_trojan(proxy_url):
    try:
        parsed_url = urlparse(proxy_url)
        params = parse_qs(parsed_url.query)
        host, port_str = parsed_url.netloc.split('@')[1].rsplit(':', 1)
        return {
            'protocol': parsed_url.scheme, 'id': parsed_url.netloc.split('@')[0], 'address': host, 'port': int(port_str),
            'network': params.get('type', ['tcp'])[0], 'security': params.get('security', ['none'])[0],
            'sni': params.get('sni', [params.get('host', [''])[0]])[0] or host, 'pbk': params.get('pbk', [''])[0],
            'grpc_serviceName': params.get('serviceName', [''])[0]
        }
    except Exception: return None

def parse_ss(proxy_url):
    try:
        parsed_uri = urlparse(proxy_url)
        if '@' not in parsed_uri.netloc: return None
        credentials_part_url_encoded = parsed_uri.netloc.split('@')[0]
        credentials_part = unquote(credentials_part_url_encoded)
        credentials_b64 = credentials_part + '=' * (-len(credentials_part) % 4)
        credentials_decoded = base64.b64decode(credentials_b64).decode('utf-8')
        method, password = credentials_decoded.split(':', 1)
        address, port = parsed_uri.hostname, parsed_uri.port
        if not address or not port: return None
        return {'protocol': 'shadowsocks', 'address': address, 'port': port, 'method': method, 'password': password}
    except Exception: return None

def get_proxy_signature(proxy_url):
    url_part = proxy_url.split('#')[0]
    parsed = None
    if url_part.startswith("vless://"): parsed = parse_vless_trojan(url_part)
    elif url_part.startswith("trojan://"): parsed = parse_vless_trojan(url_part)
    elif url_part.startswith("vmess://"): parsed = parse_vmess(url_part)
    elif url_part.startswith("ss://"): parsed = parse_ss(url_part)
    
    if not parsed: return None
    protocol = parsed.get('protocol')
    
    # --- ИЗМЕНЕНИЕ ЗДЕСЬ: Максимально упрощенная подпись ---
    # Для Shadowsocks оставляем как есть, т.к. там нет таких вариаций
    if protocol == 'shadowsocks':
        return (protocol, parsed.get('address'), parsed.get('port'))
    
    # Для всех остальных протоколов используем только адрес, порт и тип сети
    return (protocol, parsed.get('address'), parsed.get('port'), parsed.get('network'))

if __name__ == "__main__":
    sources_str = os.getenv('PROXY_SOURCES', '')
    check_all = os.getenv('CHECK_ALL_PROXIES', 'false').lower() == 'true'
    num_jobs = int(sys.argv[1]) if len(sys.argv) > 1 else 15

    print("Fetching and processing proxies from multiple sources...")
    all_unique_proxies = {} # Словарь для хранения уникальных прокси {подпись: ссылка}
    total_raw_proxies = 0

    for url in sources_str.strip().split('\n'):
        if not url or url.startswith('#'):
            continue
        
        source_raw_lines = []
        try:
            print(f"\n-> Processing source: {url}")
            response = requests.get(url, timeout=30)
            content = response.text
            if '://' in content:
                source_raw_lines.extend(content.strip().split('\n'))
            else:
                clean_content = "".join(content.split())
                decoded_content = base64.b64decode(clean_content).decode('utf-8')
                source_raw_lines.extend(decoded_content.strip().split('\n'))
        except Exception as e:
            print(f"   [ERROR] Failed to process source: {e}")
            continue

        source_raw_count = len(source_raw_lines)
        total_raw_proxies += source_raw_count
        newly_added_count = 0
        
        for line in source_raw_lines:
            line = line.strip()
            if not line: continue
            signature = get_proxy_signature(line)
            if signature and signature not in all_unique_proxies:
                all_unique_proxies[signature] = line
                newly_added_count += 1
        
        print(f"   Found: {source_raw_count} raw proxies.")
        print(f"   Added: {newly_added_count} new unique proxies.")
        
    print("\n----------------------------------------")
    print("Total Summary:")
    print(f"  - Total raw proxies found: {total_raw_proxies}")
    print(f"  - Total unique proxies found: {len(all_unique_proxies)}")
    print("----------------------------------------\n")
    
    unique_proxies = list(all_unique_proxies.values())
    
    random.shuffle(unique_proxies)
    
    if check_all:
        proxies_to_split = unique_proxies
        print(f"РЕЖИМ: Проверка ВСЕХ {len(proxies_to_split)} уникальных прокси.")
    else:
        proxies_to_split = unique_proxies[:100]
        print(f"РЕЖИМ: Проверка ПЕРВЫХ 100 из {len(unique_proxies)} уникальных прокси.")

    if not proxies_to_split:
        print("No proxies to split. Exiting.")
    else:
        total_proxies = len(proxies_to_split)
        base_chunk_size = total_proxies // num_jobs
        remainder = total_proxies % num_jobs
        start_index = 0
        for i in range(num_jobs):
            chunk_size = base_chunk_size + (1 if i < remainder else 0)
            chunk_end = start_index + chunk_size
            chunk = proxies_to_split[start_index:chunk_end]
            with open(f'proxies_chunk_{i:02d}.txt', 'w', encoding='utf-8') as f:
                if chunk:
                    f.write('\n'.join(chunk) + '\n')
            start_index = chunk_end
        print(f"Split proxies into {num_jobs} chunks more evenly.")
