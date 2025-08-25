#!/usr/bin/env python3
"""
Verifica expiração de domínios com suporte a .cn, .com.br, .com, etc.
Usa curl em serviços públicos de whois quando necessário.
"""

import sys
import re
import subprocess
import argparse
from datetime import datetime, timezone
import time

MONTH_MAP = {
    'jan': 1, 'fev': 2, 'mar': 3, 'abr': 4, 'mai': 5, 'jun': 6,
    'jul': 7, 'ago': 8, 'set': 9, 'out': 10, 'nov': 11, 'dez': 12,
    'feb': 2, 'apr': 4, 'may': 5, 'aug': 8, 'sep': 9, 'oct': 10,
    'nov': 11, 'dec': 12,
    'janeiro': 1, 'fevereiro': 2, 'março': 3, 'abril': 4, 'maio': 5, 'junho': 6,
    'julho': 7, 'agosto': 8, 'setembro': 9, 'outubro': 10, 'novembro': 11, 'dezembro': 12
}

def parse_date(date_str):
    if not date_str:
        return None
    date_str = re.sub(r'[Tt][0-9:]+.*', '', date_str)
    date_str = re.sub(r'\s*\(.*\)', '', date_str)
    date_str = re.sub(r'[^\w\-/.:]', ' ', date_str).strip()

    formats = [
        '%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y', '%d.%m.%Y',
        '%Y.%m.%d', '%Y/%m/%d', '%d %b %Y', '%d-%b-%Y',
        '%d %B %Y', '%d-%B-%Y'
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue

    match = re.match(r'(\d{1,2})[-\.\s]+([a-zA-Zç]+)[-\.\s]+(\d{2,4})', date_str, re.IGNORECASE)
    if match:
        day = int(match.group(1))
        month_str = match.group(2).lower()[:3]
        year = int(match.group(3))
        if year < 100:
            year += 2000
        for key, num in MONTH_MAP.items():
            if key.startswith(month_str):
                try:
                    return datetime(year, num, day).replace(tzinfo=timezone.utc)
                except ValueError:
                    return None
    return None


def whois_cli(domain):
    """Tenta whois via linha de comando."""
    try:
        result = subprocess.run(['whois', domain], capture_output=True, text=True, timeout=15, encoding='utf-8', errors='ignore')
        if any(kw in result.stdout.lower() for kw in ['not found', 'no match', 'error', 'invalid']):
            return None
        return result.stdout
    except Exception:
        return None


def whois_registro_br(domain):
    """Consulta whois do .com.br via curl no whoisweb."""
    try:
        # Usa o whoisweb.registro.br
        cmd = ['curl', '-s', f'https://whoisweb.registro.br/?qr={domain}']
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=20, encoding='utf-8')
        if 'Domínio não encontrado' in result.stdout or result.returncode != 0:
            return None
        return result.stdout
    except Exception:
        return None


def whois_cnnic_cn(domain):
    """Consulta whois do .cn via página oficial."""
    try:
        # Página de consulta CNNIC (pode mudar, mas é estável)
        cmd = ['curl', '-s', f'https://cwhois.cnnic.cn/whois-cgi/english/searchDomain?domainName={domain}&button=Search']
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=20, encoding='utf-8')
        if domain not in result.stdout:
            return None
        return result.stdout
    except Exception:
        return None


def extract_expiry(text, domain):
    """Extrai data de expiração do texto."""
    patterns = [
        r'Expiry\s*Date:\s*(.+)',
        r'Expiration:\s*(.+)',
        r'Expires:\s*(.+)',
        r'Registry Expiry Date:\s*(.+)',
        r'paid-till:\s*(.+)',
        r'valid-to:\s*(.+)',
        r'fecha de vencimiento:\s*(.+)',
        r'data de expiração:\s*(.+)',
        r'vencimento:\s*(.+)',
        r'Expire:\s*(.+)',
        r'Expiration Time:\s*(.+)',
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            date_str = match.group(1).strip()
            expiry_date = parse_date(date_str)
            if expiry_date:
                return expiry_date

    return None


def days_until_expiry(domain):
    """Retorna dias até expiração com múltiplos métodos."""
    domain = domain.strip().lower()

    # Método 1: whois padrão
    text = whois_cli(domain)
    if text:
        expiry = extract_expiry(text, domain)
        if expiry:
            now = datetime.now(timezone.utc)
            return (expiry - now).days

    # Método 2: .com.br via whoisweb.registro.br
    if domain.endswith('.com.br'):
        text = whois_registro_br(domain)
        if text:
            expiry = extract_expiry(text, domain)
            if expiry:
                now = datetime.now(timezone.utc)
                return (expiry - now).days

    # Método 3: .cn via cwhois.cnnic.cn
    if domain.endswith('.cn'):
        text = whois_cnnic_cn(domain)
        if text:
            # Procurar padrão como "Expiration Date: 2025-12-31"
            match = re.search(r'Expiration\s*Date:\s*(\S+)', text, re.IGNORECASE)
            if match:
                date_str = match.group(1)
                expiry = parse_date(date_str)
                if expiry:
                    now = datetime.now(timezone.utc)
                    return (expiry - now).days

    return -1  # Falha em todos os métodos


def main():
    parser = argparse.ArgumentParser(description="Verifica expiração de domínio.")
    parser.add_argument('domain', nargs='?', help="Domínio")
    parser.add_argument('--domains', nargs='+', help="Vários domínios")
    args = parser.parse_args()

    domains = args.domains or ([args.domain] if args.domain else [])

    if not domains:
        print(-1)
        return

    for domain in domains:
        days = days_until_expiry(domain)
        if len(domains) == 1:
            print(days)
            return
        else:
            print(f"{domain}: {days}")


if __name__ == '__main__':
    main()