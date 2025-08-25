#!/usr/bin/env python3
"""
Verifica expiração de domínios sem API.
Suporta: .com, .cn, .com.br, .org, .com.uy, etc.
Usa whois com servidores específicos.
"""

import sys
import re
import subprocess
import argparse
from datetime import datetime, timezone
import time

# Mapeamento de TLDs para servidores WHOIS oficiais
WHOIS_SERVERS = {
    '.com': 'whois.verisign-grs.com',
    '.net': 'whois.verisign-grs.com',
    '.org': 'whois.pir.org',
    '.info': 'whois.afilias.net',
    '.cn': 'whois.cnnic.cn',
    '.com.cn': 'whois.cnnic.cn',
    '.net.cn': 'whois.cnnic.cn',
    '.org.cn': 'whois.cnnic.cn',
    '.com.br': 'whois.registro.br',
    '.org.br': 'whois.registro.br',
    '.net.br': 'whois.registro.br',
    '.com.uy': 'whois.anteldata.com.uy',
}

# Mapeamento de meses
MONTH_MAP = {
    'jan': 1, 'fev': 2, 'mar': 3, 'abr': 4, 'mai': 5, 'jun': 6,
    'jul': 7, 'ago': 8, 'set': 9, 'out': 10, 'nov': 11, 'dez': 12,
    'feb': 2, 'apr': 4, 'may': 5, 'aug': 8, 'sep': 9, 'oct': 10,
    'nov': 11, 'dec': 12,
    'janeiro': 1, 'fevereiro': 2, 'março': 3, 'abril': 4, 'maio': 5, 'junho': 6,
    'julho': 7, 'agosto': 8, 'setembro': 9, 'outubro': 10, 'novembro': 11, 'dezembro': 12
}

def parse_date(date_str):
    """Converte string de data em datetime."""
    if not date_str:
        return None
    # Remove hora, fuso, parênteses
    date_str = re.sub(r'[Tt][0-9:]+.*', '', date_str)
    date_str = re.sub(r'\(.*?\)', '', date_str)
    date_str = re.sub(r'[^\w\-/.]', ' ', date_str).strip()

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

    # Padrão: 21-fev-2025
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


def get_whois_server(domain):
    """Retorna servidor WHOIS com base no TLD."""
    domain = domain.lower()
    for tld, server in sorted(WHOIS_SERVERS.items(), key=lambda x: len(x[0]), reverse=True):
        if domain.endswith(tld):
            return server
    return None


def query_whois(domain, server=None):
    """Executa whois com servidor específico."""
    try:
        cmd = ['whois']
        if server:
            cmd += ['-h', server]
        cmd.append(domain)

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            encoding='utf-8',
            errors='replace'  # Substitui caracteres inválidos
        )

        if result.returncode != 0:
            return None

        output = result.stdout

        # Verifica se foi bloqueado
        blocked = [
            'not allowed', 'blocked', 'rate limit', 'exceeded', 'não permitido',
            'query rejected', 'too many requests', 'access denied'
        ]
        if any(msg in output.lower() for msg in blocked):
            return None

        return output

    except Exception as e:
        return None


def extract_expiry(text, domain):
    """Extrai data de expiração com múltiplos padrões."""
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
        r'expire-date:\s*(.+)',
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
    if not domain or '.' not in domain:
        return -1

    # Extração do domínio base (sem subdomínios)
    parts = domain.split('.')
    if len(parts) >= 3 and parts[-2] in ['com', 'net', 'org', 'co'] and len(parts[-1]) == 2:
        base_domain = '.'.join(parts[-3:])
    else:
        base_domain = '.'.join(parts[-2:])

    # 1. Tentar com servidor específico
    server = get_whois_server(domain)
    if server:
        text = query_whois(base_domain, server)
        if text:
            expiry = extract_expiry(text, domain)
            if expiry:
                now = datetime.now(timezone.utc)
                return (expiry - now).days

    # 2. Tentar whois padrão
    text = query_whois(base_domain)
    if text:
        expiry = extract_expiry(text, domain)
        if expiry:
            now = datetime.now(timezone.utc)
            return (expiry - now).days

    return -1


def read_domains(file_path):
    """Lê domínios de um arquivo."""
    domains = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    domain = re.sub(r'https?://|www\.', '', line).split('/')[0].strip()
                    if domain:
                        domains.append(domain)
    except Exception as e:
        print(f"Erro ao ler {file_path}: {e}", file=sys.stderr)
        sys.exit(1)
    return domains


def main():
    parser = argparse.ArgumentParser(description="Verifica expiração de domínios.")
    parser.add_argument('file', help="Arquivo com lista de domínios")

    args = parser.parse_args()
    domains = read_domains(args.file)

    for domain in domains:
        days = days_until_expiry(domain)
        print(f"{domain}: {days}")
        time.sleep(1.5)  # Evita bloqueio por rate limit (crucial para .com.br e .cn)


if __name__ == '__main__':
    main()