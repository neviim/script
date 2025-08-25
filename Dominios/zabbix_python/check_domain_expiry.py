#!/usr/bin/env python3
"""
Verifica a data de expiração de domínios (qualquer TLD).
Suporta: .com, .cn, .com.br, .org, .net, .info, .xyz, etc.

Uso:
  python3 check_domain_expiry.py dominio.com
  python3 check_domain_expiry.py dominio.com.br
  python3 check_domain_expiry.py comunidade.cn

Retorno:
  Número de dias restantes (ex: 123)
  -1 se erro, domínio não encontrado ou não puder ser verificado

By: neviim jads
"""

import sys
import re
import subprocess
import argparse
from datetime import datetime, timezone
import logging

# Configurar logging silencioso (sem mensagens, a não ser em modo debug)
logging.basicConfig(level=logging.ERROR)

# Mapeamento de meses abreviados para números
MONTH_MAP = {
    'jan': 1, 'fev': 2, 'mar': 3, 'abr': 4, 'mai': 5, 'jun': 6,
    'jul': 7, 'ago': 8, 'set': 9, 'out': 10, 'nov': 11, 'dez': 12,
    'feb': 2, 'apr': 4, 'may': 5, 'aug': 8, 'sep': 9, 'oct': 10,
    'nov': 11, 'dec': 12, 'janeiro': 1, 'fevereiro': 2, 'março': 3,
    'abril': 4, 'maio': 5, 'junho': 6, 'julho': 7, 'agosto': 8,
    'setembro': 9, 'outubro': 10, 'novembro': 11, 'dezembro': 12
}

def parse_date(date_str):
    """
    Converte string de data em objeto datetime.
    Suporta vários formatos comuns.
    """
    date_str = re.sub(r'[Tt][0-9:]+.*', '', date_str)  # Remove hora
    date_str = re.sub(r'\s*\(.*\)', '', date_str)      # Remove parênteses
    date_str = date_str.strip()

    formats = [
        '%Y-%m-%d',
        '%d-%m-%Y', '%d/%m/%Y', '%d.%m.%Y',
        '%d-%b-%Y', '%d-%b-%y', '%d %b %Y', '%d %b %y',
        '%Y.%m.%d', '%Y/%m/%d',
        '%d-%B-%Y', '%d %B %Y',  # com nome completo do mês
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue

    # Formato com nome do mês abreviado (ex: 21-fev-2025)
    match = re.match(r'(\d{1,2})[-\.\s]+([a-zA-Zç]+)[-\.\s]+(\d{2,4})', date_str, re.IGNORECASE)
    if match:
        day = int(match.group(1))
        month_str = match.group(2).lower()[:3]
        year = int(match.group(3))
        if year < 100:
            year += 2000
        for key, num in MONTH_MAP.items():
            if key.startswith(month_str):
                month = num
                try:
                    return datetime(year, month, day).replace(tzinfo=timezone.utc)
                except ValueError:
                    return None

    return None


def get_expiry_date(domain):
    """
    Consulta whois e extrai a data de expiração.
    Retorna datetime ou None.
    """
    try:
        result = subprocess.run(
            ['whois', domain],
            capture_output=True,
            text=True,
            timeout=15,
            encoding='utf-8',
            errors='ignore'
        )
        output = result.stdout.lower()

        # Casos de erro comuns
        not_found_patterns = [
            'not found', 'no match', 'no data', 'error', 'invalid', 'malformed',
            'não encontrado', 'domínio não encontrado', 'não existe'
        ]
        if any(pattern in output for pattern in not_found_patterns):
            return None

        # Padrões comuns de expiração
        expiry_patterns = [
            r'expiry.?date:?\s*(\S+)',
            r'expiration:?\s*(\S+)',
            r'expires:?\s*(\S+)',
            r'registry expiry date:?\s*(\S+)',
            r'paid-till:?\s*(\S+)',
            r'valid-to:?\s*(\S+)',
            r'fecha de vencimiento:?\s*(\S+)',
            r'data de expiração:?\s*(\S+)',
            r'vencimento:?\s*(\S+)',
            r'expires on:?\s*(\S+)',
        ]

        for pattern in expiry_patterns:
            match = re.search(pattern, result.stdout, re.IGNORECASE)
            if match:
                date_str = match.group(1)
                expiry_date = parse_date(date_str)
                if expiry_date:
                    return expiry_date

    except (subprocess.TimeoutExpired, Exception):
        return None

    return None


def days_until_expiry(domain):
    """
    Retorna o número de dias até a expiração do domínio.
    Negativo se já expirou.
    -1 se não puder verificar.
    """
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
    parser.add_argument('domain', nargs='?', help="Domínio a verificar (ex: google.com)")
    parser.add_argument('--domains', nargs='+', help="Vários domínios")
    args = parser.parse_args()

    if args.domains:
        domains = args.domains
    elif args.domain:
        domains = [args.domain]
    else:
        print(-1)
        sys.exit(0)

    # Se for chamado por Zabbix (um único domínio), retorna só o número
    if len(domains) == 1:
        print(days_until_expiry(domains[0]))
    else:
        # Modo batch: imprime domínio + dias
        for domain in domains:
            days = days_until_expiry(domain)
            print(f"{domain}: {days}")

    sys.exit(0)


if __name__ == '__main__':
    main()