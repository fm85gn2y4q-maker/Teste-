# Instalador do Banco MCP para Windows (PowerShell).
#
#   irm https://raw.githubusercontent.com/fm85gn2y4q-maker/Teste-/refs/heads/claude/create-iphone-app-9YNOb/banco-mcp/instalar.ps1 | iex
#
# Nao precisa de WSL nem de bash: usa Node e git direto no Windows.

$ErrorActionPreference = 'Stop'

$Repo   = 'https://github.com/fm85gn2y4q-maker/Teste-.git'
$Branch = 'claude/create-iphone-app-9YNOb'

function Passo($texto) { Write-Host "`n==> $texto" -ForegroundColor Cyan }
function Erro($texto)  { Write-Host $texto -ForegroundColor Red }
function Ok($texto)    { Write-Host $texto -ForegroundColor Green }

# --- 1. Node ---------------------------------------------------------------
Passo 'Conferindo o Node'
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
  Erro 'Node nao encontrado.'
  Write-Host 'Instale com:  winget install OpenJS.NodeJS.LTS'
  Write-Host 'Depois FECHE e reabra o terminal, e rode este comando de novo.'
  return
}
# Le a versao em PowerShell puro. Passar JavaScript entre aspas para o node
# nao sobrevive a forma como o PowerShell repassa argumentos para executavel
# nativo: as aspas internas somem no caminho.
$versaoTexto = (node -v)
$maior = 0
if ($versaoTexto -match '^v?(\d+)\.') { $maior = [int]$Matches[1] }

if ($maior -eq 0) {
  Write-Host "Nao consegui identificar a versao do Node (recebi: $versaoTexto). Seguindo assim mesmo."
} elseif ($maior -lt 20) {
  Erro "Node $versaoTexto e antigo demais. Precisa da versao 20 ou mais nova."
  Write-Host 'Atualize com:  winget install OpenJS.NodeJS.LTS'
  return
} else {
  Write-Host "Node $versaoTexto, ok."
}

# --- 2. git ----------------------------------------------------------------
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
  Erro 'git nao encontrado.'
  Write-Host 'Instale com:  winget install Git.Git'
  Write-Host 'Depois FECHE e reabra o terminal, e rode este comando de novo.'
  return
}

# --- 2b. npm -----------------------------------------------------------------
# O npm vem junto com o Node, mas pode ficar corrompido por atualizacao
# interrompida ou por antivirus que poe um arquivo em quarentena. Melhor
# descobrir isso agora do que no meio da instalacao.
$npmVersao = ''
try { $npmVersao = (npm -v 2>&1 | Out-String).Trim() } catch { $npmVersao = '' }
if ($LASTEXITCODE -ne 0 -or $npmVersao -notmatch '^\d+\.') {
  Erro 'O npm desta maquina esta quebrado.'
  Write-Host 'Ele veio junto com o Node e nao esta conseguindo nem informar a propria versao.'
  Write-Host ''
  Write-Host 'Conserto: reinstale o Node, o que repara o npm junto.'
  Write-Host '  winget install --id OpenJS.NodeJS.LTS --force'
  Write-Host ''
  Write-Host 'Ou baixe o instalador em https://nodejs.org e escolha Repair.'
  Write-Host 'Depois FECHE e reabra o terminal, e rode este comando de novo.'
  return
}
Write-Host "npm $npmVersao, ok."

# --- 3. Codigo -------------------------------------------------------------
if (Test-Path 'banco-mcp\package.json') {
  $Dir = (Resolve-Path 'banco-mcp').Path
} elseif ((Test-Path 'package.json') -and (Test-Path 'src\providers')) {
  $Dir = (Get-Location).Path
} else {
  Passo 'Baixando o codigo'
  $Destino = Join-Path $HOME 'banco-mcp'
  if (Test-Path (Join-Path $Destino '.git')) {
    git -C $Destino fetch origin $Branch --quiet
    git -C $Destino checkout --quiet $Branch
    git -C $Destino pull --quiet origin $Branch
  } else {
    git clone --quiet --branch $Branch $Repo $Destino
  }
  $Dir = Join-Path $Destino 'banco-mcp'
  Write-Host "Clonado em $Destino"
}
Set-Location $Dir

# --- 4. Dependencias e build ----------------------------------------------
Passo 'Instalando dependencias e compilando'
Write-Host 'Isso leva de um a varios minutos — no Windows o antivirus costuma'
Write-Host 'inspecionar cada arquivo baixado. A saida do npm aparece abaixo.'
Write-Host ''
npm install --no-audit --no-fund
if ($LASTEXITCODE -ne 0) {
  Erro 'npm install falhou.'
  Write-Host 'Se o erro acima menciona arquivos dentro de "Program Files\nodejs", o npm da'
  Write-Host 'maquina esta corrompido — reinstale o Node para repara-lo:'
  Write-Host '  winget install --id OpenJS.NodeJS.LTS --force'
  return
}
npm run build --silent
if ($LASTEXITCODE -ne 0) { Erro 'A compilacao falhou.'; return }
Write-Host 'Compilado.'

# --- 5. O servidor responde? ----------------------------------------------
Passo 'Testando o servidor em modo demonstracao'
# Roda o proprio diagnostico: prova mais que um teste inventado, e evita
# depender de como o PowerShell repassa JavaScript embutido para o node.
$env:BANCO_MCP_PROVEDOR = 'mock'
node dist\diagnostico.js
# Limpa: variavel de ambiente vence o .env por desenho, entao deixa-la aqui
# faria o servidor continuar em modo demonstracao mesmo depois de configurado.
Remove-Item Env:\BANCO_MCP_PROVEDOR -ErrorAction SilentlyContinue

# --- 6. Dados reais? -------------------------------------------------------
Passo 'Dados reais do seu banco?'
Write-Host @'
Para ligar nos seus bancos voce precisa de:
  - conta em meu.pluggy.ai com os bancos ja conectados
  - clientId e clientSecret do dashboard.pluggy.ai

Isso e gratuito para uso pessoal. Se ainda nao tiver, tudo bem: o servidor
funciona em modo demonstracao e voce liga depois rodando "npm run configurar".
'@

$resposta = Read-Host "`nConfigurar credenciais agora? [s/N]"
if ($resposta -eq 's' -or $resposta -eq 'S') {
  # O PowerShell pergunta, nao o Node: quando o instalador chega por "irm | iex"
  # a entrada padrao ja foi consumida pelo cano, e um prompt do Node leria vazio.
  Write-Host ''
  Write-Host 'As credenciais ficam so neste computador, no arquivo .env.'
  Write-Host 'Nao cole clientSecret em chat, ticket ou commit.'
  Write-Host ''
  $clientId = Read-Host '  clientId'
  $segredo  = Read-Host '  clientSecret (nao aparece enquanto voce digita)' -AsSecureString
  $clientSecret = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
    [Runtime.InteropServices.Marshal]::SecureStringToBSTR($segredo))

  if ([string]::IsNullOrWhiteSpace($clientId) -or [string]::IsNullOrWhiteSpace($clientSecret)) {
    Erro 'clientId ou clientSecret vazio — pulando a configuracao.'
    Write-Host "Para configurar depois:  cd $Dir ; npm run configurar"
    $resposta = 'n'
  } else {
    $env:PLUGGY_CLIENT_ID = $clientId
    $env:PLUGGY_CLIENT_SECRET = $clientSecret
    node dist\configurar.js --do-ambiente
  }
}
if ($resposta -eq 's' -or $resposta -eq 'S') {
  Passo 'Buscando as conexoes ja existentes na sua conta'
  node dist\conectar.js --listar
  if ($LASTEXITCODE -ne 0) {
    Write-Host 'Nao consegui listar automaticamente. Para conectar pelo navegador:'
    Write-Host "  cd $Dir ; npm run conectar"
  }
  Passo 'Diagnostico'
  node dist\diagnostico.js
}

# --- 7. Registro no Claude -------------------------------------------------
Passo 'Ultimo passo'
$indexJs = Join-Path $Dir 'dist\index.js'
if (Get-Command claude -ErrorAction SilentlyContinue) {
  claude mcp add banco -- node $indexJs
  Ok 'Servidor registrado. Abra o Claude Code e pergunte: como estao minhas financas?'
} else {
  Write-Host @"
O comando "claude" nao esta no PATH. Quando instalar o Claude Code, rode:

  claude mcp add banco -- node $indexJs

Ou, no app de desktop / Cursor, acrescente ao arquivo de configuracao MCP:

  "banco": { "command": "node", "args": [$($indexJs | ConvertTo-Json)] }
"@
}
