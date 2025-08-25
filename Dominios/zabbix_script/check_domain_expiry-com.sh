#!/bin/bash
# Script: /scripts/check_domain_expiry-com.sh
# Uso: ./check_domain_expiry-com.sh <domínio>
# by: neviim jads

DOMAIN="$1"

# Verifica se o domínio foi fornecido
if [ -z "$DOMAIN" ]; then
    echo -1
    exit 1
fi

# Usa whois para obter a data de expiração
EXPIRY=$(whois "$DOMAIN" 2>/dev/null | grep -iE 'Expiry|Expira|Registry Expiry Date|Expiration' | head -1 | awk '{print $NF}' | cut -d'T' -f1 | cut -d' ' -f1)

# Se não encontrou data
if [ -z "$EXPIRY" ]; then
    echo -1
    exit 1
fi

# Calcula os dias restantes
SECONDS_LEFT=$(( $(date -d "$EXPIRY" +%s) - $(date +%s) ))
DAYS_LEFT=$(( SECONDS_LEFT / 86400 ))

echo $DAYS_LEFT
