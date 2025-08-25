#!/usr/bin/env bash
# Uso: whois_days_left.sh dominio.com
# by: neviim jads

set -euo pipefail

DOMAIN="${1:?Uso: $0 dominio.com}"

DATE_BIN="date"
if command -v gdate >/dev/null 2>&1; then DATE_BIN="gdate"; fi

WHOIS_RAW="$(whois "$DOMAIN" 2>/dev/null || true)"
LINE="$(printf "%s" "$WHOIS_RAW" | grep -iE 'Registry Expiry Date|Expiration Date|Expiry Date|paid-till' | head -n1 || true)"

if [[ -z "$LINE" ]]; then
  echo 0; exit 1
fi

EXP_RAW="$(printf "%s" "$LINE" | sed -E 's/^.*(Date|paid-till):[[:space:]]*//I' | tr -d '\r' | xargs)"
[[ "$EXP_RAW" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]] && EXP_RAW="${EXP_RAW}T00:00:00Z"
[[ "$EXP_RAW" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}$ ]] && EXP_RAW="${EXP_RAW}Z"

if ! EXP_TS=$(TZ=UTC "$DATE_BIN" -d "$EXP_RAW" +%s 2>/dev/null); then
  echo 0; exit 2
fi

NOW_TS=$("$DATE_BIN" -u +%s)
echo $(( (EXP_TS - NOW_TS) / 86400 ))

