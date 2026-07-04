#!/usr/bin/env python3
"""Gera a planilha Carteira Bancária RJ (importável no Google Sheets)."""
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.utils import get_column_letter

NAVY = "24384E"; BRASS = "8F6F1F"; SOFT = "E8ECF1"; CREAM = "F0E8D2"
hdr_fill = PatternFill("solid", fgColor=NAVY)
hdr_font = Font(color="FFFFFF", bold=True, size=10)
sub_fill = PatternFill("solid", fgColor=SOFT)
title_font = Font(bold=True, size=14, color=NAVY)
note_font = Font(size=10, color="565B66")
thin = Border(bottom=Side(style="thin", color="DDDCD4"))

wb = Workbook()

# ---------- LEIA-ME ----------
ws = wb.active; ws.title = "LEIA-ME"
ws.column_dimensions["A"].width = 118
rows = [
    ("CARTEIRA BANCÁRIA RJ — Planilha de triagem e gestão de ações", title_font),
    ("Companheira do Analisador de Teses (analisador-teses-rj.html). Data-base: julho/2026.", note_font),
    ("", None),
    ("COMO USAR NO GOOGLE SHEETS (recomendado):", Font(bold=True)),
    ("1. No Google Drive: Novo > Upload de arquivo > selecione este .xlsx.", None),
    ("2. Abra o arquivo e clique em Arquivo > Salvar como Planilha Google.", None),
    ("3. A aba 'Taxas BACEN' passa a atualizar sozinha (IMPORTDATA) — no Excel ela não funciona.", None),
    ("", None),
    ("FLUXO DE TRABALHO:", Font(bold=True)),
    ("1. Cadastre o cliente na aba CLIENTES (checklists de gratuidade e blindagem embutidos).", None),
    ("2. Rode a análise da tese no Analisador (HTML) — se VIÁVEL, lance uma linha na aba CARTEIRA.", None),
    ("3. A CARTEIRA calcula sozinha: parcelas simples (até 03/2021) × em dobro (após), compensação,", None),
    ("   proveito líquido, honorários contratuais e sucumbência (só vara cível). Prescrição decenal: ", None),
    ("   a coluna AVISO acende se o 1º desconto tiver mais de 10 anos.", None),
    ("4. O PAINEL consolida tudo por status e por tese (funil e projeção de honorários).", None),
    ("", None),
    ("REGRAS JURÍDICAS EMBUTIDAS NAS FÓRMULAS:", Font(bold=True)),
    ("• Marco da restituição em dobro: 30/03/2021 (STJ, EAREsp 676.608/RS). Antes: simples; depois: dobro.", None),
    ("• Compensação de valores creditados na conta é abatida (praxe TJRJ, art. 368 CC).", None),
    ("• Sucumbência estimada em 15% apenas quando Foro = Vara Cível (JEC não tem no 1º grau).", None),
    ("• Dano moral: faixas praticadas pelo TJRJ (R$ 4–15 mil) — selecione no dropdown.", None),
    ("", None),
    ("APIS / FONTES EXTERNAS:", Font(bold=True)),
    ("• BACEN/SGS (aba Taxas BACEN): taxa média de mercado p/ Teses 5 e 6 — valide a série da modalidade", None),
    ("  em bcb.gov.br/estatisticas/txjuros e anexe print à inicial.", None),
    ("• Meu INSS (HISCRE + Extrato de Pagamento) e Registrato/BCB: acesso com gov.br do cliente (sem API pública).", None),
    ("• SUSEP/SAFE: apólices do cliente (Tese 2) — gov.br/susep.", None),
    ("• DataJud/CNJ: consulta processual pública por nº CNJ (integração futura).", None),
    ("", None),
    ("Este arquivo é ferramenta de apoio; a decisão de ajuizar é ato privativo do advogado responsável.", note_font),
]
for i, (txt, ft) in enumerate(rows, 1):
    c = ws.cell(row=i, column=1, value=txt)
    if ft: c.font = ft
    c.alignment = Alignment(wrap_text=True, vertical="top")

# ---------- LISTAS ----------
wl = wb.create_sheet("Listas")
teses = ["T1 Consignado fraudado", "T2 Prestamista", "T3 RMC/RCC nulidade",
         "T4 Conversão RMC/RCC", "T5 Juros pessoais", "T6 Financ. veículo", "T7 Descontos em conta"]
foros = ["Vara Cível", "JEC"]
status = ["Triagem", "Docs pendentes", "Req. administrativo", "Pronta p/ ajuizar", "Ajuizada",
          "Liminar deferida", "Contestada", "Sentença procedente", "Sentença improcedente",
          "Recurso", "Acordo", "Cumprimento", "Encerrada — recebida", "Arquivada/Inviável"]
dm = [0, 4000, 5000, 8000, 10000, 15000]
sn = ["SIM", "NÃO"]
for i, v in enumerate(teses, 1): wl.cell(row=i, column=1, value=v)
for i, v in enumerate(foros, 1): wl.cell(row=i, column=2, value=v)
for i, v in enumerate(status, 1): wl.cell(row=i, column=3, value=v)
for i, v in enumerate(dm, 1): wl.cell(row=i, column=4, value=v)
for i, v in enumerate(sn, 1): wl.cell(row=i, column=5, value=v)
wl.sheet_state = "hidden"

# ---------- CLIENTES ----------
wc = wb.create_sheet("Clientes")
ch = ["Cliente", "CPF", "NB (benefício)", "Telefone/WhatsApp", "Comarca", "Origem (indicação/palestra/digital)",
      "HISCRE obtido?", "Extrato pagamento obtido?", "Extrato conta obtido?", "SUSEP/SAFE consultado?",
      "Procuração específica?", "Termo de ciência?", "Req. administrativo?", "Dossiê gratuidade completo?",
      "Teses identificadas", "Observações"]
for j, h in enumerate(ch, 1):
    c = wc.cell(row=1, column=j, value=h); c.fill = hdr_fill; c.font = hdr_font
    c.alignment = Alignment(wrap_text=True, vertical="center")
    wc.column_dimensions[get_column_letter(j)].width = 16 if j > 6 else 22
wc.freeze_panes = "A2"
dv_sn = DataValidation(type="list", formula1="=Listas!$E$1:$E$2", allow_blank=True)
wc.add_data_validation(dv_sn); dv_sn.add("G2:N400")
wc.cell(row=2, column=1, value="(exemplo) Maria da Silva"); wc.cell(row=2, column=5, value="Duque de Caxias")
wc.cell(row=2, column=15, value="T3, T2, T7")

# ---------- CARTEIRA ----------
w = wb.create_sheet("Carteira")
headers = [
    ("Cliente", 20), ("Tese", 20), ("Banco réu", 14), ("Nº contrato", 14), ("Foro", 12),
    ("Parcela mensal (R$)", 13), ("1º desconto", 12), ("Último desconto", 12),
    ("Meses simples (até 03/21)", 12), ("Meses dobro (após 03/21)", 12),
    ("Restituição simples (R$)", 14), ("Restituição dobro (R$)", 14),
    ("Compensação — creditado (R$)", 14), ("Dano moral (R$)", 12),
    ("PROVEITO LÍQUIDO (R$)", 15), ("% honor. contratual", 10),
    ("Honor. contratuais (R$)", 14), ("Sucumbência 15% (vara) (R$)", 14), ("HONORÁRIOS TOTAIS (R$)", 15),
    ("AVISO prescrição", 16), ("Status", 16), ("Nº processo (CNJ)", 22), ("Próximo prazo", 12), ("Observações", 26),
]
for j, (h, wdt) in enumerate(headers, 1):
    c = w.cell(row=1, column=j, value=h); c.fill = hdr_fill; c.font = hdr_font
    c.alignment = Alignment(wrap_text=True, vertical="center")
    w.column_dimensions[get_column_letter(j)].width = wdt
w.freeze_panes = "C2"
w.row_dimensions[1].height = 42

N = 302  # linhas 2..302
for r in range(2, N + 1):
    # I: meses simples ; J: meses dobro (marco 31/03/2021)
    w.cell(row=r, column=9,  value=f'=IF(OR(G{r}="",H{r}=""),"",IF(G{r}>DATE(2021,3,31),0,DATEDIF(G{r},MIN(H{r},DATE(2021,3,31)),"m")+1))')
    w.cell(row=r, column=10, value=f'=IF(OR(G{r}="",H{r}=""),"",IF(H{r}<DATE(2021,4,1),0,DATEDIF(MAX(G{r},DATE(2021,4,1)),H{r},"m")+1))')
    w.cell(row=r, column=11, value=f'=IF(I{r}="","",I{r}*F{r})')
    w.cell(row=r, column=12, value=f'=IF(J{r}="","",J{r}*F{r}*2)')
    w.cell(row=r, column=15, value=f'=IF(K{r}="","",MAX(0,K{r}+L{r}-N(M{r}))+N(N{r}))')
    w.cell(row=r, column=16, value=f'=IF(A{r}="","",0.3)')
    w.cell(row=r, column=17, value=f'=IF(O{r}="","",O{r}*P{r})')
    w.cell(row=r, column=18, value=f'=IF(O{r}="","",IF(E{r}="Vara Cível",O{r}*0.15,0))')
    w.cell(row=r, column=19, value=f'=IF(O{r}="","",Q{r}+R{r})')
    w.cell(row=r, column=20, value=f'=IF(G{r}="","",IF(G{r}<EDATE(TODAY(),-120),"⚠ mais de 10 anos — cortar janela",""))')
    for col in (6, 11, 12, 13, 14, 15, 17, 18, 19):
        w.cell(row=r, column=col).number_format = '#,##0.00'
    w.cell(row=r, column=16).number_format = '0%'
    w.cell(row=r, column=7).number_format = 'mm/yyyy'
    w.cell(row=r, column=8).number_format = 'mm/yyyy'

dv_tese = DataValidation(type="list", formula1="=Listas!$A$1:$A$7", allow_blank=True)
dv_foro = DataValidation(type="list", formula1="=Listas!$B$1:$B$2", allow_blank=True)
dv_stat = DataValidation(type="list", formula1="=Listas!$C$1:$C$14", allow_blank=True)
dv_dm   = DataValidation(type="list", formula1="=Listas!$D$1:$D$6", allow_blank=True)
for dv, rng in ((dv_tese, "B2:B302"), (dv_foro, "E2:E302"), (dv_stat, "U2:U302"), (dv_dm, "N2:N302")):
    w.add_data_validation(dv); dv.add(rng)

# Exemplo
import datetime as _dt
ex = ["(exemplo) Maria da Silva", "T3 RMC/RCC nulidade", "BMG", "41070364", "Vara Cível", 81.05,
      _dt.date(2017, 2, 1), _dt.date(2026, 6, 1)]
for j, v in enumerate(ex, 1): w.cell(row=2, column=j, value=v)
w.cell(row=2, column=13, value=1100.0); w.cell(row=2, column=14, value=5000)
w.cell(row=2, column=21, value="Triagem")

# ---------- PAINEL ----------
wp = wb.create_sheet("Painel")
wp.column_dimensions["A"].width = 34
for col in "BCD": wp.column_dimensions[col].width = 18
wp["A1"] = "PAINEL DA OPERAÇÃO"; wp["A1"].font = title_font
wp["A3"] = "Por status"; wp["A3"].font = Font(bold=True)
wp["A4"] = "Status"; wp["B4"] = "Ações"; wp["C4"] = "Proveito líquido (R$)"; wp["D4"] = "Honorários proj. (R$)"
for c in ("A4", "B4", "C4", "D4"): wp[c].fill = hdr_fill; wp[c].font = hdr_font
for i, st in enumerate(status, start=5):
    wp.cell(row=i, column=1, value=st)
    wp.cell(row=i, column=2, value=f'=COUNTIF(Carteira!U:U,A{i})')
    wp.cell(row=i, column=3, value=f'=SUMIF(Carteira!U:U,A{i},Carteira!O:O)')
    wp.cell(row=i, column=4, value=f'=SUMIF(Carteira!U:U,A{i},Carteira!S:S)')
    wp.cell(row=i, column=3).number_format = '#,##0.00'; wp.cell(row=i, column=4).number_format = '#,##0.00'
r0 = 5 + len(status) + 2
wp.cell(row=r0, column=1, value="Por tese").font = Font(bold=True)
wp.cell(row=r0+1, column=1, value="Tese"); wp.cell(row=r0+1, column=2, value="Ações")
wp.cell(row=r0+1, column=3, value="Proveito (R$)"); wp.cell(row=r0+1, column=4, value="Honorários (R$)")
for c in range(1, 5): wp.cell(row=r0+1, column=c).fill = hdr_fill; wp.cell(row=r0+1, column=c).font = hdr_font
for i, t in enumerate(teses, start=r0+2):
    wp.cell(row=i, column=1, value=t)
    wp.cell(row=i, column=2, value=f'=COUNTIF(Carteira!B:B,A{i})')
    wp.cell(row=i, column=3, value=f'=SUMIF(Carteira!B:B,A{i},Carteira!O:O)')
    wp.cell(row=i, column=4, value=f'=SUMIF(Carteira!B:B,A{i},Carteira!S:S)')
    wp.cell(row=i, column=3).number_format = '#,##0.00'; wp.cell(row=i, column=4).number_format = '#,##0.00'
rt = r0 + 2 + len(teses) + 1
wp.cell(row=rt, column=1, value="TOTAL GERAL").font = Font(bold=True, color=BRASS)
wp.cell(row=rt, column=2, value='=COUNTA(Carteira!A2:A302)-COUNTBLANK(Carteira!A2:A302)')
wp.cell(row=rt, column=2, value='=SUMPRODUCT(--(Carteira!A2:A302<>""))')
wp.cell(row=rt, column=3, value='=SUM(Carteira!O2:O302)'); wp.cell(row=rt, column=3).number_format = '#,##0.00'
wp.cell(row=rt, column=4, value='=SUM(Carteira!S2:S302)'); wp.cell(row=rt, column=4).number_format = '#,##0.00'

# ---------- TAXAS BACEN ----------
wt = wb.create_sheet("Taxas BACEN")
wt.column_dimensions["A"].width = 62; wt.column_dimensions["B"].width = 14; wt.column_dimensions["C"].width = 50
wt["A1"] = "TAXAS MÉDIAS BACEN (API SGS — funciona no Google Sheets)"; wt["A1"].font = title_font
wt["A2"] = ("Preencha o código da série da modalidade (valide em bcb.gov.br/estatisticas/txjuros) e a fórmula "
            "IMPORTDATA busca o último valor. Compare: taxa do contrato > 1,5 × média = abusiva (REsp 1.061.530/RS). "
            "Se aparecer erro no Excel, ignore — use após converter em Planilha Google.")
wt["A2"].font = note_font; wt["A2"].alignment = Alignment(wrap_text=True); wt.row_dimensions[2].height = 45
wt["A4"] = "Modalidade (edite)"; wt["B4"] = "Série SGS"; wt["C4"] = "Último valor divulgado"
for c in ("A4", "B4", "C4"): wt[c].fill = hdr_fill; wt[c].font = hdr_font
mods = [("Crédito pessoal não consignado — PF (% a.m.) [CONFIRA a série]", ""),
        ("Aquisição de veículos — PF (% a.m.) [CONFIRA a série]", ""),
        ("Consignado INSS — PF (% a.m.) [CONFIRA a série]", "")]
for i, (m, s) in enumerate(mods, start=5):
    wt.cell(row=i, column=1, value=m)
    wt.cell(row=i, column=2, value=s)
    wt.cell(row=i, column=3, value=f'=IF(B{i}="","← informe a série",IFERROR(INDEX(IMPORTDATA("https://api.bcb.gov.br/dados/serie/bcdata.sgs."&B{i}&"/dados/ultimos/1?formato=csv"),2,2),"série inválida ou sem acesso"))')
wt["A9"] = "Série histórica (mês da contratação): use no navegador —"
wt["A10"] = 'https://api.bcb.gov.br/dados/serie/bcdata.sgs.CODIGO/dados?formato=json&dataInicial=01/MM/AAAA&dataFinal=28/MM/AAAA'
wt["A10"].font = note_font

wb.save("/home/user/Teste-/docs/carteira-bancaria-rj.xlsx")
print("ok")
