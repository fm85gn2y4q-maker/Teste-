const ENDPOINT =
  'https://transparencia.mesquita.rj.gov.br/sincronias/apidados.rule?sys=LAI';

export interface SalarioServidor {
  NOME: string;
  MATRICULA: string;
  CARGO: string;
  LIQUIDO: string;
  TIPO: string;
  BRUTO: string;
  Concursado: string;
  Numero_ATO: string | null;
  Data_Publicacao: string | null;
  Comissionado: string;
  Funcao_Confianca: string;
  DATA_ADMISSAO: string;
  Local_Trabalho: string;
  SECRETARIA: string;
  IMPOSTODERENDA: string;
  Desconto_Previdenciario: string;
  Outros_descontos: string;
  DESCRICAO_REGIME: string;
  Contratado: string;
  ANO: string;
  MES: string;
  FONTE_RECURSOS: string;
  BASE_SALARIAL: string;
  GENERO: string;
  RACA: string;
  DEFICIENCIA: string | null;
}

interface ApiResponse {
  status: string;
  dados?: SalarioServidor[];
  retorno?: string;
}

export async function fetchSalariosAno(ano: number): Promise<SalarioServidor[]> {
  const response = await fetch(ENDPOINT, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ api: 'salarios_servidores_bruto_liquido', ano }),
  });

  if (!response.ok) {
    throw new Error(`Erro HTTP ${response.status}`);
  }

  const data: ApiResponse = await response.json();

  if (data.status !== 'sucesso') {
    throw new Error(data.retorno ?? 'Erro desconhecido na API');
  }

  return data.dados ?? [];
}

export async function fetchSalariosServidor(
  nome: string,
  ano: number,
): Promise<SalarioServidor[]> {
  const todos = await fetchSalariosAno(ano);
  const nomeLower = nome.toLowerCase();
  return todos.filter((s) => s.NOME.toLowerCase().includes(nomeLower));
}
