#!/usr/bin/env bash
# Regenera 01-knowledge/INDEX.md a partir do cabeçalho YAML das notas.
# Marca com (!) o que está vencido ou com revisão em atraso.

set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
K="$RAIZ/01-knowledge"
INDEX="$K/INDEX.md"
HOJE=$(date +%F)
MES=$(date +%Y-%m)

campo() { # campo <arquivo> <nome>
  sed -n '2,20p' "$1" | sed -n -E "s/^$2:[[:space:]]*(.*)$/\1/p" | head -1
}

{
  echo "# Índice do conhecimento"
  echo
  echo "Gerado por \`scripts/indexar.sh\` em $HOJE. Não edite à mão."
  echo

  total=0
  alerta=0

  for pasta in perfil dominios decisoes; do
    [ -d "$K/$pasta" ] || continue
    linhas=""
    while IFS= read -r arq; do
      base=$(basename "$arq")
      case "$base" in _*) continue;; esac

      titulo=$(campo "$arq" titulo);      : "${titulo:=$base}"
      tags=$(campo "$arq" tags)
      atualizado=$(campo "$arq" atualizado)
      validade=$(campo "$arq" validade)

      marca=""
      case "$validade" in
        vencida) marca=" **(!)**";;
        *"revisar em"*)
          quando=$(printf '%s' "$validade" | sed -E 's/.*revisar em[[:space:]]*//')
          if [ -n "$quando" ] && [ "$quando" \< "$MES" ]; then marca=" **(!)**"; fi
          ;;
      esac
      [ -n "$marca" ] && alerta=$((alerta + 1))

      linhas="$linhas| [$titulo]($pasta/$base)$marca | ${tags:--} | ${atualizado:--} | ${validade:--} |
"
      total=$((total + 1))
    done < <(find "$K/$pasta" -maxdepth 1 -name '*.md' | sort)

    [ -n "$linhas" ] || continue
    echo "## $pasta"
    echo
    echo "| Nota | Tags | Atualizado | Validade |"
    echo "|---|---|---|---|"
    printf '%s' "$linhas"
    echo
  done

  pendentes=$(find "$RAIZ/00-raw/inbox" -maxdepth 1 -name '*.md' 2>/dev/null | wc -l | tr -d ' ')

  echo "---"
  echo
  echo "$total notas · $alerta precisando de revisão **(!)** · $pendentes no inbox por destilar."
} > "$INDEX"

echo "índice gerado: $INDEX"
