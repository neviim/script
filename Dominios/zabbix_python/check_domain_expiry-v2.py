#!/usr/bin/env python3
"""
Verifica expiração de domínios com suporte a .com, .cn, .com.br, etc.
Usa servidores whois específicos para cada TLD.
"""

import sys
import re
import subprocess
import argparse
from datetime import datetime, timezone

# Mapeamento de TLDs para servidores WHOIS específicos
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
    '.gov.br': 'whois.registro.br',
    '.edu.br': 'whois.registro.br',
    '.int.br': 'whois.registro.br',
    '.imb.br': 'whois.registro.br',
    '.ind.br': 'whois.registro.br',
    '.esp.br': 'whois.registro.br',
    '.rec.br': 'whois.registro.br',
    '.tur.br': 'whois.registro.br',
    '.pro.br': 'whois.registro.br',
    '.psi.br': 'whois.registro.br',
    '.imb.br': 'whois.registro.br',
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

    # Limpeza básica
    date_str = re.sub(r'[Tt][0-9:]+.*', '', date_str)
    date_str = re.sub(r'\s*\(.*\)', '', date_str)
    date_str = re.sub(r'[^\w\-/.:]', ' ', date_str).strip()

    formats = [
        '%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y', '%d.%m.%Y',
        '%Y.%m.%d', '%Y/%m/%d', '%d %b %Y', '%d-%b-%Y',
        '%d %B %Y', '%d-%B-%Y', '%Y-%m-%d %H:%M:%S'
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
    """Retorna o servidor WHOIS apropriado com base no TLD."""
    domain = domain.lower()
    for tld, server in sorted(WHOIS_SERVERS.items(), key=lambda x: len(x[0]), reverse=True):
        if domain.endswith(tld):
            return server
    return None  # whois padrão do sistema


def get_expiry_date(domain):
    """Consulta whois com servidor apropriado e extrai data de expiração."""
    try:
        # Extrai domínio base (sem subdomínios)
        base_domain = re.sub(r'^.*?(\w+\.\w+\.\w+|\w+\.\w+)$', r'\1', domain)
        if '.' not in base_domain:
            base_domain = domain

        # Define o servidor WHOIS
        server = get_whois_server(base_domain)

        # Comando WHOIS
        cmd = ['whois']
        if server:
            cmd += ['-h', server]
        cmd.append(base_domain)

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=20,
            encoding='utf-8',
            errors='ignore'
        )

        output = result.stdout

        # Verifica se domínio não existe
        not_found_patterns = [
            'not found', 'no match', 'no data', 'error', 'invalid', 'malformed',
            'não encontrado', 'domínio não encontrado', 'não existe', 'no entries found',
            'no such domain', 'object does not exist'
        ]
        if any(pattern in output.lower() for pattern in not_found_patterns):
            return None

        # Padrões de expiração por TLD
        expiry_patterns = [
            r'Expiry\s*Date:\s*(.+)',
            r'Expiration:\s*(.+)',
            r'Expires:\s*(.+)',
            r'Registry Expiry Date:\s*(.+)',
            r'paid-till:\s*(.+)',
            r'valid-to:\s*(.+)',
            r'fecha de vencimiento:\s*(.+)',
            r'data de expiração:\s*(.+)',
            r'vencimento:\s*(.+)',
            r'Expiration Time:\s*(.+)',
            r'expire:\s*(.+)',
        ]

        for pattern in expiry_patterns:
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                date_str = match.group(1).strip()
                expiry_date = parse_date(date_str)
                if expiry_date:
                    return expiry_date

    except Exception as e:
        print(f"Erro ao consultar {domain}: {e}", file=sys.stderr)
        return None

    return None


def days_until_expiry(domain):
    """Retorna dias até expiração. -1 se erro."""
    try:
        expiry_date = get_expiry_date(domain)
        if not expiry_date:
            return -1
        now = datetime.now(timezone.utc)
        delta = expiry_date - now
        return delta.days
    except Exception:
        return -1


def main():
    parser = argparse.ArgumentParser(description="Verifica dias até expiração de domínio.")
    parser.add_argument('domain', nargs='?', help="Domínio a verificar")
    parser.add_argument('--domains', nargs='+', help="Vários domínios")
    args = parser.parse_args()

    domains = []
    if args.domains:
        domains = args.domains
    elif args.domain:
        domains = [args.domain]
    else:
        print(-1)
        sys.exit(0)

    for domain in domains:
        days = days_until_expiry(domain)
        if len(domains) == 1:
            print(days)
            break
        else:
            print(f"{domain}: {days}")


if __name__ == '__main__':
    main()