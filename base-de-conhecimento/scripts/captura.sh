#!/usr/bin/env bash
# Cria um arquivo em 00-raw/inbox/ com cabeçalho e data.
#
#   captura.sh "titulo curto"          -> cria e abre no $EDITOR
#   pbpaste | captura.sh "titulo"      -> cria com o conteúdo da entrada padrão
#   captura.sh                         -> pede o título

set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INBOX="$RAIZ/00-raw/inbox"

titulo="${*:-}"
if [ -z "$titulo" ]; then
  read -r -p "Título: " titulo
fi
[ -n "$titulo" ] || { echo "captura: título vazio" >&2; exit 1; }

# slug: minúsculas, sem acento, separado por hífen
slug=$(printf '%s' "$titulo" \
  | sed 's/á/a/g; s/à/a/g; s/â/a/g; s/ã/a/g; s/ä/a/g; s/é/e/g; s/è/e/g; s/ê/e/g; s/ë/e/g; s/í/i/g' \
  | sed 's/ì/i/g; s/î/i/g; s/ï/i/g; s/ó/o/g; s/ò/o/g; s/ô/o/g; s/õ/o/g; s/ö/o/g; s/ú/u/g; s/ù/u/g' \
  | sed 's/û/u/g; s/ü/u/g; s/ç/c/g; s/ñ/n/g; s/Á/A/g; s/À/A/g; s/Â/A/g; s/Ã/A/g; s/Ä/A/g; s/É/E/g; s/È/E/g; s/Ê/E/g; s/Ë/E/g; s/Í/I/g; s/Ì/I/g; s/Î/I/g; s/Ï/I/g; s/Ó/O/g; s/Ò/O/g; s/Ô/O/g; s/Õ/O/g; s/Ö/O/g; s/Ú/U/g; s/Ù/U/g; s/Û/U/g; s/Ü/U/g; s/Ç/C/g; s/Ñ/N/g' \
  | tr '[:upper:]' '[:lower:]' \
  | sed -E 's/[^a-z0-9]+/-/g; s/^-+|-+$//g' \
  | cut -c1-60)
[ -n "$slug" ] || slug="nota"

hoje=$(date +%F)
arquivo="$INBOX/$hoje-$slug.md"

# não sobrescreve: acrescenta -2, -3...
n=2
while [ -e "$arquivo" ]; do
  arquivo="$INBOX/$hoje-$slug-$n.md"
  n=$((n + 1))
done

mkdir -p "$INBOX"
{
  echo "---"
  echo "titulo: $titulo"
  echo "capturado: $(date '+%F %H:%M')"
  echo "fonte: "
  echo "destilado: nao"
  echo "---"
  echo
} > "$arquivo"

if [ ! -t 0 ]; then
  cat >> "$arquivo"          # veio por pipe
  echo "capturado: $arquivo"
  exit 0
fi

echo "capturado: $arquivo"
if [ -n "${EDITOR:-}" ]; then
  "$EDITOR" "$arquivo"
fi
