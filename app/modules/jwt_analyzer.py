"""JWT token tespiti ve analizi modulu."""
import base64
import json
import re
from datetime import datetime


def extract_jwts(text: str) -> list:
    pattern = r'eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]*'
    return list(set(re.findall(pattern, text)))


def decode_jwt(token: str) -> dict:
    parts = token.split('.')
    if len(parts) != 3:
        return {}

    def b64_decode(s):
        s += '=' * (4 - len(s) % 4)
        try:
            return json.loads(base64.urlsafe_b64decode(s).decode('utf-8', errors='ignore'))
        except Exception:
            return {}

    header = b64_decode(parts[0])
    payload = b64_decode(parts[1])

    issues = []
    alg = header.get('alg', 'unknown')

    if alg.lower() == 'none':
        issues.append({'level': 'critical', 'msg': 'Algorithm is none — imza bypass mumkun olabilir'})
    if alg in ('HS256', 'HS384', 'HS512'):
        issues.append({'level': 'info', 'msg': 'Simetrik algoritma — zayif secret bruteforce edilebilir'})
    if 'RS256' not in alg and 'ES' not in alg and alg != 'none':
        issues.append({'level': 'info', 'msg': f'Algoritma: {alg}'})

    sensitive_keys = ['password', 'secret', 'token', 'api_key', 'private']
    for k in payload:
        if any(s in k.lower() for s in sensitive_keys):
            issues.append({'level': 'high', 'msg': f'Hassas veri payload icinde: {k}'})

    exp_info = None
    expired = False
    if 'exp' in payload:
        try:
            exp_dt = datetime.fromtimestamp(payload['exp'])
            expired = exp_dt < datetime.now()
            exp_info = str(exp_dt)
            if expired:
                issues.append({'level': 'info', 'msg': f'Token suresi dolmus: {exp_info}'})
        except Exception:
            pass

    return {
        'token_preview': token[:60] + '...',
        'header': header,
        'payload': payload,
        'algorithm': alg,
        'expired': expired,
        'exp_date': exp_info,
        'issues': issues,
    }


def analyze_exchange_for_jwts(exchange: dict) -> list:
    try:
        req = base64.b64decode(exchange.get('request_b64', '')).decode('utf-8', errors='ignore')
        res = base64.b64decode(exchange.get('response_b64', '')).decode('utf-8', errors='ignore')
    except Exception:
        req, res = '', ''

    tokens = extract_jwts(req + '\n' + res)
    return [decode_jwt(t) for t in tokens if t]
