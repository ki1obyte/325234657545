# check_proxies.py (финальная версия со счетчиком в логах)

import requests
import subprocess
import tempfile
import os
import time
import json
from urllib.parse import urlparse, parse_qs, unquote
import sys
import random
import re
import base64

# --- Словарь COUNTRY_CODES ---
COUNTRY_CODES = {
    "AD": "Andorra", "AE": "United Arab Emirates", "AF": "Afghanistan", "AG": "Antigua and Barbuda",
    "AI": "Anguilla", "AL": "Albania", "AM": "Armenia", "AO": "Angola", "AQ": "Antarctica",
    "AR": "Argentina", "AS": "American Samoa", "AT": "Austria", "AU": "Australia", "AW": "Aruba",
    "AX": "Aland Islands", "AZ": "Azerbaijan", "BA": "Bosnia and Herzegovina", "BB": "Barbados",
    "BD": "Bangladesh", "BE": "Belgium", "BF": "Burkina Faso", "BG": "Bulgaria", "BH": "Bahrain",
    "BI": "Burundi", "BJ": "Benin", "BL": "Saint Barthelemy", "BM": "Bermuda", "BN": "Brunei Darussalam",
    "BO": "Bolivia", "BQ": "Bonaire, Sint Eustatius and Saba", "BR": "Brazil", "BS": "Bahamas",
    "BT": "Bhutan", "BV": "Bouvet Island", "BW": "Botswana", "BY": "Belarus", "BZ": "Belize",
    "CA": "Canada", "CC": "Cocos (Keeling) Islands", "CD": "Congo, Democratic Republic of the",
    "CF": "Central African Republic", "CG": "Congo", "CH": "Switzerland", "CI": "Cote d'Ivoire",
    "CK": "Cook Islands", "CL": "Chile", "CM": "Cameroon", "CN": "China", "CO": "Colombia",
    "CR": "Costa Rica", "CU": "Cuba", "CV": "Cabo Verde", "CW": "Curacao", "CX": "Christmas Island",
    "CY": "Cyprus", "CZ": "Czechia", "DE": "Germany", "DJ": "Djibouti", "DK": "Denmark",
    "DM": "Dominica", "DO": "Dominican Republic", "DZ": "Algeria", "EC": "Ecuador", "EE": "Estonia",
    "EG": "Egypt", "EH": "Western Sahara", "ER": "Eritrea", "ES": "Spain", "ET": "Ethiopia",
    "FI": "Finland", "FJ": "Fiji", "FK": "Falkland Islands (Malvinas)", "FM": "Micronesia (Federated States of)",
    "FO": "Faroe Islands", "FR": "France", "GA": "Gabon", "GB": "United Kingdom", "GD": "Grenada",
    "GE": "Georgia", "GF": "French Guiana", "GG": "Guernsey", "GH": "Ghana", "GI": "Gibraltar",
    "GL": "Greenland", "GM": "Gambia", "GN": "Guinea", "GP": "Guadeloupe", "GQ": "Equatorial Guinea",
    "GR": "Greece", "GS": "South Georgia and the South Sandwich Islands", "GT": "Guatemala",
    "GU": "Guam", "GW": "Guinea-Bissau", "GY": "Guyana", "HK": "Hong Kong", "HM": "Heard Island and McDonald Islands",
    "HN": "Honduras", "HR": "Croatia", "HT": "Haiti", "HU": "Hungary", "ID": "Indonesia",
    "IE": "Ireland", "IL": "Israel", "IM": "Isle of Man", "IN": "India", "IO": "British Indian Ocean Territory",
    "IQ": "Iraq", "IR": "Iran", "IS": "Iceland", "IT": "Italy", "JE": "Jersey",
    "JM": "Jamaica", "JO": "Jordan", "JP": "Japan", "KE": "Kenya", "KG": "Kyrgyzstan",
    "KH": "Cambodia", "KI": "Kiribati", "KM": "Comoros", "KN": "Saint Kitts and Nevis",
    "KP": "Korea (Democratic People's Republic of)", "KR": "Korea, Republic of", "KW": "Kuwait",
    "KY": "Cayman Islands", "KZ": "Kazakhstan", "LA": "Lao People's Democratic Republic", "LB": "Lebanon",
    "LC": "Saint Lucia", "LI": "Liechtenstein", "LK": "Sri Lanka", "LR": "Liberia", "LS": "Lesotho",
    "LT": "Lithuania", "LU": "Luxembourg", "LV": "Latvia", "LY": "Libya", "MA": "Morocco",
    "MC": "Monaco", "MD": "Moldova, Republic of", "ME": "Montenegro", "MF": "Saint Martin (French part)",
    "MG": "Madagascar", "MH": "Marshall Islands", "MK": "North Macedonia", "ML": "Mali", "MM": "Myanmar",
    "MN": "Mongolia", "MO": "Macao", "MP": "Northern Mariana Islands", "MQ": "Martinique",
    "MR": "Mauritania", "MS": "Montserrat", "MT": "Malta", "MU": "Mauritius", "MV": "Maldives",
    "MW": "Malawi", "MX": "Mexico", "MY": "Malaysia", "MZ": "Mozambique", "NA": "Namibia",
    "NC": "New Caledonia", "NE": "Niger", "NF": "Norfolk Island", "NG": "Nigeria", "NI": "Nicaragua",
    "NL": "Netherlands", "NO": "Norway", "NP": "Nepal", "NR": "Nauru", "NU": "Niue",
    "NZ": "New Zealand", "OM": "Oman", "PA": "Panama", "PE": "Peru", "PF": "French Polynesia",
    "PG": "Papua New Guinea", "PH": "Philippines", "PK": "Pakistan", "PL": "Poland",
    "PM": "Saint Pierre and Miquelon", "PN": "Pitcairn", "PR": "Puerto Rico", "PS": "Palestine, State of",
    "PT": "Portugal", "PW": "Palau", "PY": "Paraguay", "QA": "Qatar", "RE": "Reunion",
    "RO": "Romania", "RS": "Serbia", "RU": "Russian Federation", "RW": "Rwanda", "SA": "Saudi Arabia",
    "SB": "Solomon Islands", "SC": "Seychelles", "SD": "Sudan", "SE": "Sweden", "SG": "Singapore",
    "SH": "Saint Helena, Ascension and Tristan da Cunha", "SI": "Slovenia", "SJ": "Svalbard and Jan Mayen",
    "SK": "Slovakia", "SL": "Sierra Leone", "SM": "San Marino", "SN": "Senegal", "SO": "Somalia",
    "SR": "Suriname", "SS": "South Sudan", "ST": "Sao Tome and Principe", "SV": "El Salvador",
    "SX": "Sint Maarten (Dutch part)", "SY": "Syrian Arab Republic", "SZ": "Eswatini",
    "TC": "Turks and Caicos Islands", "TD": "Chad", "TF": "French Southern Territories", "TG": "Togo",
    "TH": "Thailand", "TJ": "Tajikistan", "TK": "Tokelau", "TL": "Timor-Leste", "TM": "Turkmenistan",
    "TN": "Tunisia", "TO": "Tonga", "TR": "Turkey", "TT": "Trinidad and Tobago", "TV": "Tuvalu",
    "TW": "Taiwan", "TZ": "Tanzania, United Republic of", "UA": "Ukraine", "UG": "Uganda",
    "UM": "United States Minor Outlying Islands", "US": "United States", "UY": "Uruguay",
    "UZ": "Uzbekistan", "VA": "Holy See", "VC": "Saint Vincent and the Grenadines", "VE": "Venezuela",
    "VG": "Virgin Islands (British)", "VI": "Virgin Islands (U.S.)", "VN": "Viet Nam", "VU": "Vanuatu",
    "WF": "Wallis and Futuna", "WS": "Samoa", "YE": "Yemen", "YT": "Mayotte", "ZA": "South Africa",
    "ZM": "Zambia", "ZW": "Zimbabwe"
}

def get_country_name(code): return COUNTRY_CODES.get(code.upper(), code.upper())

def read_proxies_from_file(filepath):
    print(f"Reading proxies from {filepath}...")
    try:
        with open(filepath, 'r', encoding='utf-8') as f: lines = f.read().strip().split('\n')
        valid_lines = [line for line in lines if line.strip().startswith(('vless://', 'vmess://', 'ss://', 'trojan://'))]
        print(f"Successfully read {len(valid_lines)} supported proxy links.")
        return valid_lines
    except Exception as e:
        print(f"Error reading proxies from file: {e}"); return []

def parse_vless_trojan(proxy_url):
    try:
        parsed_url = urlparse(proxy_url)
        params = parse_qs(parsed_url.query)
        host, port_str = parsed_url.netloc.split('@')[1].rsplit(':', 1)
        return {
            'protocol': parsed_url.scheme, 'id': parsed_url.netloc.split('@')[0], 'address': host, 'port': int(port_str),
            'network': params.get('type', ['tcp'])[0], 'security': params.get('security', ['none'])[0], 'flow': params.get('flow', [''])[0],
            'sni': params.get('sni', [params.get('host', [''])[0]])[0] or host, 'fp': params.get('fp', [''])[0],
            'pbk': params.get('pbk', [''])[0], 'sid': params.get('sid', [''])[0], 'spx': params.get('spx', [''])[0],
            'ws_path': params.get('path', ['/'])[0], 'ws_host': params.get('host', [''])[0] or host,
            'grpc_serviceName': params.get('serviceName', [''])[0]
        }
    except Exception: return None

def parse_vmess(proxy_url):
    try:
        if not proxy_url.startswith("vmess://"): return None
        b64_data = proxy_url.replace("vmess://", "") + '=' * (-len(proxy_url.replace("vmess://", "")) % 4)
        json_data = json.loads(base64.b64decode(b64_data).decode('utf-8'))
        return {
            'protocol': 'vmess', 'address': json_data.get('add', ''), 'port': int(json_data.get('port', 0)), 'id': json_data.get('id', ''),
            'security': 'tls' if json_data.get('tls') == 'tls' else 'none', 'network': json_data.get('net', 'tcp'),
            'ws_path': json_data.get('path', '/'), 'ws_host': json_data.get('host', ''),
            'sni': json_data.get('sni', json_data.get('host', '')), 'alterId': json_data.get('aid', 0)
        }
    except Exception: return None

def parse_ss(proxy_url):
    try:
        if not proxy_url.startswith("ss://"): return None
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

def parse_proxy_url(proxy_url):
    url_part = proxy_url.split('#')[0]
    remark = unquote(proxy_url.split('#')[1]) if '#' in proxy_url else ''
    data = None
    if url_part.startswith("vless://"): data = parse_vless_trojan(url_part)
    elif url_part.startswith("trojan://"): data = parse_vless_trojan(url_part)
    elif url_part.startswith("vmess://"): data = parse_vmess(url_part)
    elif url_part.startswith("ss://"): data = parse_ss(url_part)
    if data: data['remark'] = remark
    return data

def setup_xray():
    if not os.path.exists('xray'):
        print("Xray not found, downloading...")
        url = 'https://github.com/XTLS/Xray-core/releases/latest/download/Xray-linux-64.zip'
        try:
            with open('xray.zip', 'wb') as f: f.write(requests.get(url, timeout=30).content)
            subprocess.run(['unzip', '-o', 'xray.zip', '-d', '.'], check=True, stdout=subprocess.DEVNULL)
            os.chmod('xray', 0o755); os.remove('xray.zip')
            print("Xray downloaded and set up successfully.")
        except Exception as e: print(f"Failed to setup Xray: {e}"); return None
    return './xray'

def check_proxy(proxy_url, counter_str=""):
    parsed = parse_proxy_url(proxy_url)
    if not parsed:
        print(f"{counter_str}Failed to parse proxy URL: {proxy_url.split('#')[0]}#...")
        return None

    protocol = parsed.get('protocol')
    remark = parsed.get('remark') or parsed.get('address')
    ip_port = f"{parsed.get('address')}:{parsed.get('port')}"
    print(f"\n--- {counter_str}Checking {protocol.upper()} proxy: {ip_port} {remark[:50]}")

    max_retries = 2
    retry_delay = 2

    for attempt in range(max_retries):
        outbound = {"protocol": protocol, "settings": {}}
        if protocol == 'vless':
            outbound['settings']['vnext'] = [{"address": parsed['address'], "port": parsed['port'], "users": [{"id": parsed['id'], "encryption": "none", "flow": parsed.get('flow', '')}] }]
            stream_settings = {"network": parsed['network'], "security": parsed['security']}
            if parsed['security'] in ['tls', 'reality']:
                tls_settings = {"serverName": parsed['sni']}
                if parsed.get('fp'): tls_settings["utls"] = {"enabled": True, "fingerprint": parsed['fp']}
                if parsed.get('security') == 'reality' and parsed.get('pbk'):
                    stream_settings["security"] = "reality"
                    stream_settings["realitySettings"] = {"show": False, "fingerprint": parsed.get('fp') or "chrome", "serverName": parsed['sni'], "publicKey": parsed['pbk'], "shortId": parsed.get('sid', ''), "spiderX": parsed.get('spx', '')}
                else:
                    stream_settings["security"] = "tls"
                    stream_settings["tlsSettings"] = tls_settings
            if parsed['network'] == 'ws': stream_settings["wsSettings"] = {"path": parsed['ws_path'], "headers": {"Host": parsed['ws_host']}}
            if parsed['network'] == 'grpc': stream_settings["grpcSettings"] = {"serviceName": parsed['grpc_serviceName']}
            outbound['streamSettings'] = stream_settings
        elif protocol == 'vmess':
            outbound['settings']['vnext'] = [{"address": parsed['address'], "port": parsed['port'], "users": [{"id": parsed['id'], "alterId": parsed.get('alterId', 0), "security": "auto"}] }]
            outbound['streamSettings'] = {"network": parsed['network'], "security": parsed['security']}
            if parsed['security'] == 'tls':
                outbound['streamSettings']['tlsSettings'] = {"serverName": parsed['sni']}
            if parsed['network'] == 'ws':
                outbound['streamSettings']['wsSettings'] = {"path": parsed['ws_path'], "headers": {"Host": parsed['ws_host']}}
        elif protocol == 'trojan':
            outbound['settings']['servers'] = [{"address": parsed['address'], "port": parsed['port'], "password": parsed['id']}]
            outbound['streamSettings'] = {"network": parsed['network'], "security": parsed['security']}
            if parsed['security'] == 'tls':
                outbound['streamSettings']['tlsSettings'] = {"serverName": parsed['sni']}
            if parsed['network'] == 'ws':
                outbound['streamSettings']['wsSettings'] = {"path": parsed['ws_path'], "headers": {"Host": parsed['ws_host']}}
        elif protocol == 'shadowsocks':
            outbound['settings']['servers'] = [{"address": parsed['address'], "port": parsed['port'], "method": parsed['method'], "password": parsed['password']}]

        local_port = random.randint(20000, 40000)
        config = {"log": {"loglevel": "warning"}, "inbounds": [{"port": local_port, "listen": "127.0.0.1", "protocol": "socks"}], "outbounds": [outbound]}
        config_path, process = '', None
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
                json.dump(config, f, indent=2); config_path = f.name
            xray_path = setup_xray()
            if not xray_path: return None
            process = subprocess.Popen([xray_path, 'run', '-c', config_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            time.sleep(2)
            start_time = time.time()
            curl_cmd = ['curl', '--socks5-hostname', f'127.0.0.1:{local_port}', 'https://www.cloudflare.com/cdn-cgi/trace', '-s', '--max-time', '10']
            result = subprocess.run(curl_cmd, capture_output=True, timeout=15)
            latency = (time.time() - start_time) * 1000
            stdout_str = result.stdout.decode('utf-8', errors='ignore')
            if result.returncode == 0 and 'fl=' in stdout_str:
                country_match = re.search(r'loc=([A-Z]{2})', stdout_str)
                country_code = country_match.group(1) if country_match else "Unknown"
                print(f"SUCCESS (Attempt {attempt + 1}): Proxy is working. Latency: {latency:.2f} ms. Country: {country_code}")
                return (proxy_url, country_code)
            else:
                stderr_str = result.stderr.decode('utf-8', errors='ignore').strip()
                print(f"FAILURE (Attempt {attempt + 1}/{max_retries}): Proxy check failed. Stderr: {stderr_str}")
        except Exception as e:
            print(f"FAILURE (Attempt {attempt + 1}/{max_retries}): An error occurred: {e}")
        finally:
            if process: process.terminate(); process.wait()
            if os.path.exists(config_path): os.unlink(config_path)
        if attempt < max_retries - 1:
            print(f"--- Waiting {retry_delay}s before retrying... ---")
            time.sleep(retry_delay)
    print(f"--- All {max_retries} attempts failed for this proxy. ---")
    return None

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python check_proxies.py <input_file> <output_directory>")
        sys.exit(1)

    input_file, output_dir = sys.argv[1], sys.argv[2]
    os.makedirs(output_dir, exist_ok=True)
    
    proxies_to_check = read_proxies_from_file(input_file)
    total_proxies = len(proxies_to_check)
    print(f"Starting check on {total_proxies} proxies from {input_file}...")

    proxies_by_country = {}
    total_working = 0
    for i, proxy_url in enumerate(proxies_to_check):
        counter_str = f"[{i + 1}/{total_proxies}] "
        res = check_proxy(proxy_url, counter_str)
        if res:
            url, country_code = res
            country_name = get_country_name(country_code)
            if country_name not in proxies_by_country:
                proxies_by_country[country_name] = []
            proxies_by_country[country_name].append(url)
    
    for country, proxies in proxies_by_country.items():
        total_working += len(proxies)
        with open(os.path.join(output_dir, f"{country}.txt"), 'w', encoding='utf-8') as f:
            f.write('\n'.join(proxies) + '\n')
    
    print(f"\n======================================")
    print(f"Check complete. Found {total_working} working proxies in this batch.")
    print(f"Results saved to directory: {output_dir}")
    print(f"======================================")
