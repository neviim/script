#!/bin/bash
#
# Verifica a sincronização de hora em múltiplos servidores com chrony
# Exibe: hora local, estado do NTP, sincronização e offset
#
# by: neviim jads
#

# --- Lista de servidores (pode ser nomes ou IPs)
# servers=(
#    10.10.0.5
#    10.10.0.6
# )
servers=(
    10.10.0.5
)

# --- Função para verificar um servidor
check_server() {
    local host="$1"
    echo "=== $host ==="

    # Executa os comandos remotos via SSH
    output=$(ssh -q -o ConnectTimeout=10 "$host" "
        echo '## Local time:'
        date '+%F %T %z (%Z)'
        echo
        echo '## timedatectl:'
        timedatectl status --no-pager | grep -E 'Local time|NTP service|System clock synchronized'
        echo
        echo '## chronyc tracking:'
        chronyc tracking | grep -E '^(Reference ID|Stratum|System time)'
        echo
        echo '## chronyc sources:'
        chronyc sources -v | head -5
    " 2>&1)

    # Verifica se houve erro (SSH falhou, chrony não existe, etc)
    if [ $? -ne 0 ]; then
        echo -e "\033[0;31mERRO: Falha ao acessar ou obter dados de $host\033[0m"
    else
        echo "$output"
    fi

    echo  # linha em branco
}

# --- Executa para cada servidor
for server in "${servers[@]}"; do
    check_server "$server"
done