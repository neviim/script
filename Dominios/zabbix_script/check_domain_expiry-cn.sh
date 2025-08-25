#!/bin/bash
# Script: /scripts/check_domain_expiry-cn.sh
# Uso: ./check_domain_expiry-cn.sh <domínio>
# by: neviim jads

DOMAIN=$1
WHOIS_SERVER="whois.cnnic.cn"

# Executa a consulta whois e extrai a data de expiração
EXPIRATION_DATE=$(whois -h $WHOIS_SERVER $DOMAIN | grep "Expiration Time" | awk -F': ' '{print $2}')

if [ -n "$EXPIRATION_DATE" ]; then
  # Converte a data de expiração para segundos desde a época
  EXPIRY_SECONDS=$(date -d "$EXPIRATION_DATE" +%s)
  # Obtém a data atual em segundos desde a época
  CURRENT_SECONDS=$(date +%s)
  # Calcula a diferença em dias
  DAYS_LEFT=$(( ($EXPIRY_SECONDS - $CURRENT_SECONDS) / 86400 ))
  echo $DAYS_LEFT
else
  # Retorna um valor que indica erro na obtenção da data
  echo -1
fi
