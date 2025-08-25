#!/bin/bash
# ---------------------------------------------------------
# Nome: check_domain_expiry.sh
# Descrição: Verifica dias restantes para expiração de domínios
# Suporta: .com, .cn, .com.br, .org, .net, .info, etc.
# Modo 1: ./check_domain_expiry.sh dominio.com
#         → Retorna: 123  (ou -1 se erro)
# Modo 2: ./check_domain_expiry.sh arquivo.txt
#         → Retorna: dominio.com: 123
#                   outro.com.br: 45
# by: neviim jads (versão estendida)
# ---------------------------------------------------------

DOMAIN_OR_FILE="$1"

# Verifica se foi passado argumento
if [ -z "$DOMAIN_OR_FILE" ]; then
    echo -1
    exit 1
fi

# Função: normaliza domínio
normalize_domain() {
    local d="$1"
    echo "$d" | sed -E 's|https?://||i' | sed 's|/.*$||' | sed 's|www\.||' | tr -d ' ' | tr '[:upper:]' '[:lower:]'
}

# Função: extrai e formata data de expiração
extract_expiry() {
    local whois_output="$1"
    local expiry=""

    # Extrai possíveis datas com múltiplos formatos
    expiry=$(echo "$whois_output" | \
             grep -iE 'Expiry|Expiration|Expires|Registry Expiry|renewal date|paid-till|validity|fecha de vencimiento|data de expiração|vencimento|Expiration Time' | \
             grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}([T ]?[0-9]{2}:[0-9]{2}:[0-9]{2})?|[0-9]{2}-[A-Za-z]{3}-[0-9]{4}|[0-9]{2}/[0-9]{2}/[0-9]{4}|[0-9]{8}' | \
             head -1 | \
             sed 's/T.*$//' | sed 's/ .*$//' | sed 's|/|-|g')

    [ -z "$expiry" ] && return 1

    # Converte para YYYY-MM-DD
    case "$expiry" in
        *[A-Za-z]*)
            # Formato: 21-feb-2025
            echo "$expiry" | awk '{
                split($0, a, /[-\.]/); 
                day = a[1]; 
                year = a[3]; 
                if (year < 100) year += 2000;
                month_str = tolower(substr(a[2],1,3)); 
                map["jan"]=1; map["fev"]=2; map["mar"]=3; map["abr"]=4; map["mai"]=5; map["jun"]=6;
                map["jul"]=7; map["ago"]=8; map["set"]=9; map["out"]=10; map["nov"]=11; map["dez"]=12;
                map["feb"]=2; map["apr"]=4; map["may"]=5; map["aug"]=8; map["sep"]=9; map["oct"]=10; 
                map["nov"]=11; map["dec"]=12;
                if (map[month_str]) printf "%d-%02d-%02d", year, map[month_str], day; else exit 1
            }'
            ;;
        [0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9])
            # Já é YYYY-MM-DD
            echo "$expiry"
            ;;
        [0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9])
            # YYYYMMDD → YYYY-MM-DD
            echo "$expiry" | sed 's/\([0-9]\{4\}\)\([0-9]\{2\}\)\([0-9]\{2\}\)/\1-\2-\3/'
            ;;
        *)
            return 1
            ;;
    esac
}

# Função: verifica um único domínio e retorna dias
check_single_domain() {
    local domain="$1"
    local output expiry_date expiry_ts now_ts days

    # Normaliza
    domain=$(normalize_domain "$domain")
    [ -z "$domain" ] && echo -1 && return

    # Força whois para .cn
    if [[ "$domain" == *.cn ]]; then
        WHOIS_CMD="whois -h whois.cnnic.cn '$domain'"
    else
        WHOIS_CMD="whois '$domain'"
    fi

    # Executa whois com timeout
    local whois_output
    whois_output=$(timeout 15 bash -c "$WHOIS_CMD" 2>&1) || true

    # Verifica erros
    if echo "$whois_output" | grep -qiE 'not found|no match|no data|error|invalid|malformed|não encontrado|no entries found'; then
        echo -1
        return
    fi

    # Extrai data
    expiry_date=$(extract_expiry "$whois_output")
    if [ -z "$expiry_date" ]; then
        echo -1
        return
    fi

    # Valida data
    if ! date -d "$expiry_date" >/dev/null 2>&1; then
        echo -1
        return
    fi

    # Calcula dias
    expiry_ts=$(date -d "$expiry_date" +%s)
    now_ts=$(date +%s)
    days=$(( (expiry_ts - now_ts) / 86400 ))
    echo "$days"
}

# Decisão: arquivo ou domínio?
if [ -f "$DOMAIN_OR_FILE" ]; then
    # Modo: arquivo
    while IFS= read -r line || [ -n "$line" ]; do
        trimmed=$(echo "$line" | sed 's/^[[:space:]]*//; s/[[:space:]]*$//')
        [ -z "$trimmed" ] && continue
        [ "${trimmed:0:1}" = "#" ] && continue

        domain=$(normalize_domain "$trimmed")
        days=$(check_single_domain "$domain")
        echo "$domain: $days"
    done < "$DOMAIN_OR_FILE"
else
    # Modo: domínio único
    result=$(check_single_domain "$DOMAIN_OR_FILE")
    echo "$result"
fi