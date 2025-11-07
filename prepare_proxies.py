# prepare_proxies.py (финальная версия с дедупликацией по IP:PORT)

import sys
import os
import requests
import base64
import random
from urllib.parse import urlparse, parse_qs, unquote

# ... (парсеры parse_vless_trojan, parse_vmess, parse_ss остаются без изменений) ...

def parse_vless_trojan(proxy_url):
    try:
        parsed_url = urlparse(proxy_url)
        params = parse_qs(parsed_url.query)
        host, port_str = parsed_url.netloc.split('@')[1].rsplit(':', 1)
        return {
            'protocol': parsed_url.scheme, 'id': parsed_url.netloc.split('@')[0],
            'address': host, 'port': int(port_str),
            'network': params.get('type', ['tcp'])[0],
            'security': params.get('security', ['none'])[0],
            'sni': params.get('sni', [params.get('host', [''])[0]])[0] or host,
            'pbk': params.get('pbk', [''])[0],
            'grpc_serviceName': params.get('serviceName', [''])[0]
        }
    except Exception: return None

def parse_vmess(proxy_url):
    try:
        b64_data = proxy_url.replace("vmess://", "") + '=' * (-len(proxy_url.replace("vmess://", "")) % 4)
        json_data = json.loads(base64.b64decode(b64_data).decode('utf-8'))
        return {
            'protocol': 'vmess', 'address': json_data.get('add', ''),
            'port': int(json_data.get('port', 0)), 'id': json_data.get('id', ''),
            'security': 'tls' if json_data.get('tls') == 'tls' else 'none',
            'network': json_data.get('net', 'tcp'),
            'sni': json_data.get('sni', json_data.get('host', '')),
            'ws_path': json_data.get('path', '/')
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
    """Создает подпись для прокси, группируя SS по IP:PORT."""
    url_part = proxy_url.split('#')[0]
    parsed = None
    if url_part.startswith("vless://"): parsed = parse_vless_trojan(url_part)
    elif url_part.startswith("trojan://"): parsed = parse_vless_trojan(url_part)
    elif url_part.startswith("vmess://"): parsed = parse_vmess(url_part)
    elif url_part.startswith("ss://"): parsed = parse_ss(url_part)
    
    if not parsed: return None

    protocol = parsed.get('protocol')
    
    # --- ИЗМЕНЕНИЕ ЗДЕСЬ ---
    if protocol == 'shadowsocks':
        # Для SS уникальность определяется только по адресу и порту
        return (
            protocol,
            parsed.get('address'),
            parsed.get('port')
        )
    # -----------------------

    elif protocol in ['vless', 'trojan']:
        # Для VLESS и Trojan оставляем детальную проверку
        return (protocol, parsed.get('address'), parsed.get('port'), parsed.get('id'),
                parsed.get('network'), parsed.get('security'), parsed.get('sni'),
                parsed.get('pbk'), parsed.get('grpc_serviceName'))
    elif protocol == 'vmess':
        # Для VMESS тоже оставляем детальную проверку
        return (protocol, parsed.get('address'), parsed.get('port'), parsed.get('id'),
                parsed.get('network'), parsed.get('security'), parsed.get('sni'), parsed.get('ws_path'))
    
    return None

if __name__ == "__main__":
    # ... (вся остальная часть скрипта prepare_proxies.py остается БЕЗ ИЗМЕНЕНИЙ) ...
    sources_str = os.getenv('PROXY_SOURCES', '')
    check_all = os.getenv('CHECK_ALL_PROXIES', 'false').lower() == 'true'
    num_jobs = int(sys.argv[1]) if len(sys.argv) > 1 else 15

    print("Fetching proxies from multiple sources...")
    all_lines = []
    for url in sources_str.strip().split('\n'):
        if url and not url.startswith('#'):
            try:
                print(f"-> Downloading from: {url}")
                response = requests.get(url, timeout=30)
                content = response.text
                if '://' in content:
                    all_lines.extend(content.strip().split('\n'))
                else:
                    print("   Format: Looks like Base64. Decoding...")
                    decoded_content = base64.b64decode(content).decode('utf-8')
                    all_lines.extend(decoded_content.strip().split('\n'))
            except Exception as e:
                print(f"   Failed to process source {url}: {e}")

    print("\nDeduplicating proxies...")
    seen_signatures = set()
    unique_proxies = []
    for line in all_lines:
        line = line.strip()
        if not line: continue
        signature = get_proxy_signature(line)
        if signature and signature not in seen_signatures:
            seen_signatures.add(signature)
            unique_proxies.append(line)
    
    print(f"Found {len(all_lines)} raw proxies, of which {len(unique_proxies)} are unique.")

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
        chunk_size = (len(proxies_to_split) + num_jobs - 1) // num_jobs
        for i in range(num_jobs):
            chunk = proxies_to_split[i * chunk_size:(i + 1) * chunk_size]
            if chunk:
                with open(f'proxies_chunk_{i:02d}.txt', 'w', encoding='utf-8') as f:
                    f.write('\n'.join(chunk) + '\n')
        print(f"Split proxies into {num_jobs} chunks.")
