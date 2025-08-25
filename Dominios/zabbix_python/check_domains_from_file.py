#!/usr/bin/ python3
"""
Verifica a expiração de múltiplos domínios listados em um arquivo.
Cada domínio deve estar em uma linha (sem espaços extras).

Uso:
  python3 check_domains_from_file.py /caminho/para/domains.txt

Saída:
  dominio.com: 123
  outro.com.br: 45
  invalido.cn: -1

By: neviim jads
"""

import sys
import re
import subprocess
import argparse
from datetime import datetime, timezone

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
    """Converte string de data em datetime."""
    date_str = re.sub(r'[Tt][0-9:]+.*', '', date_str)  # Remove hora
    date_str = re.sub(r'\s*\(.*\)', '', date_str)      # Remove parênteses
    date_str = date_str.strip()

    formats = [
        '%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y', '%d.%m.%Y',
        '%d-%b-%Y', '%d-%b-%y', '%d %b %Y', '%d %b %y',
        '%Y.%m.%d', '%Y/%m/%d', '%d-%B-%Y', '%d %B %Y'
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue

    # Formato: 21-fev-2025
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
    """Consulta whois e extrai a data de expiração."""
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

        # Verifica se domínio não existe
        not_found_patterns = [
            'not found', 'no match', 'no data', 'error', 'invalid', 'malformed',
            'não encontrado', 'domínio não encontrado', 'não existe', 'no entries found'
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

    except Exception:
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


def read_domains(file_path):
    """Lê domínios de um arquivo, uma por linha."""
    domains = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                domain = line.strip()
                if domain and not domain.startswith('#'):  # Ignora linhas vazias e comentários
                    # Remove http://, https://, www.
                    domain = re.sub(r'https?://', '', domain)
                    domain = domain.split('/')[0].split()[0]
                    domain = domain.replace('www.', '')
                    domains.append(domain)
    except Exception as e:
        print(f"Erro ao ler arquivo {file_path}: {e}", file=sys.stderr)
        sys.exit(1)
    return domains


def main():
    parser = argparse.ArgumentParser(description="Verifica expiração de domínios a partir de um arquivo.")
    parser.add_argument('file', help="Caminho para o arquivo com lista de domínios")

    args = parser.parse_args()

    domains = read_domains(args.file)

    for domain in domains:
        days = days_until_expiry(domain)
        print(f"{domain}: {days}")


if __name__ == '__main__':
    main()