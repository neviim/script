echo "Testando múltiplos domínios..."
for domain in google.com comunidade.cn vovojosefa.com.br cancaonova.org; do
    days=$(python3 check_domain_expiry.py "$domain")
    echo "$domain: $days"
done