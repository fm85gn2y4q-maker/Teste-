/**
 * Cliente HTTP da Pluggy, com uma trava: o unico POST autorizado e o de
 * autenticacao. Qualquer outro metodo de escrita e recusado dentro do processo,
 * antes de virar requisicao. Read-only aqui e invariante de codigo, nao promessa
 * de documentacao.
 */
const POST_PERMITIDO = new Set(['/auth', '/connect_token']);

export interface OpcoesCliente {
  clientId: string;
  clientSecret: string;
  baseUrl: string;
  /** Injetavel para teste. */
  fetchImpl?: typeof fetch;
}

export class ErroPluggy extends Error {
  constructor(readonly status: number, readonly corpo: string, url: string) {
    super(`Pluggy respondeu ${status} em ${url}: ${corpo.slice(0, 300)}`);
    this.name = 'ErroPluggy';
  }
}

export class ClientePluggy {
  private apiKey: string | null = null;
  private expiraEm = 0;
  private readonly fetchImpl: typeof fetch;

  constructor(private readonly opcoes: OpcoesCliente) {
    this.fetchImpl = opcoes.fetchImpl ?? fetch;
  }

  private async autenticar(): Promise<string> {
    // A apiKey da Pluggy vale 2 horas; renovamos com folga.
    if (this.apiKey && Date.now() < this.expiraEm) return this.apiKey;

    const resposta = await this.requisicao('POST', '/auth', {
      corpo: { clientId: this.opcoes.clientId, clientSecret: this.opcoes.clientSecret },
      semChave: true,
    });
    const chave = (resposta as { apiKey?: string }).apiKey;
    if (!chave) throw new Error('Pluggy nao devolveu apiKey na autenticacao.');
    this.apiKey = chave;
    this.expiraEm = Date.now() + 100 * 60 * 1000;
    return chave;
  }

  private async requisicao(
    metodo: 'GET' | 'POST',
    caminho: string,
    opcoes: { corpo?: unknown; query?: Record<string, string | number | undefined>; semChave?: boolean } = {},
  ): Promise<unknown> {
    if (metodo !== 'GET' && !POST_PERMITIDO.has(caminho)) {
      throw new Error(
        `Bloqueado: ${metodo} ${caminho}. Este servidor e somente leitura e nao emite requisicao de escrita.`,
      );
    }

    const url = new URL(this.opcoes.baseUrl + caminho);
    for (const [k, v] of Object.entries(opcoes.query ?? {})) {
      if (v !== undefined && v !== '') url.searchParams.set(k, String(v));
    }

    const headers: Record<string, string> = { accept: 'application/json' };
    if (opcoes.corpo) headers['content-type'] = 'application/json';
    if (!opcoes.semChave) headers['X-API-KEY'] = await this.autenticar();

    const r = await this.fetchImpl(url.toString(), {
      method: metodo,
      headers,
      ...(opcoes.corpo ? { body: JSON.stringify(opcoes.corpo) } : {}),
    });

    const texto = await r.text();
    if (!r.ok) throw new ErroPluggy(r.status, texto, url.pathname);
    return texto ? JSON.parse(texto) : null;
  }

  /** Confere se clientId e clientSecret sao aceitos. Lanca com o motivo se nao. */
  async verificarCredenciais(): Promise<void> {
    await this.autenticar();
  }

  /**
   * Cria o token de curta duracao que o widget Pluggy Connect usa no navegador.
   * E o unico POST alem do /auth: nao movimenta nada, so abre a tela em que o
   * proprio usuario autoriza o banco.
   */
  async criarConnectToken(itemId?: string): Promise<string> {
    const r = await this.requisicao('POST', '/connect_token', {
      corpo: itemId ? { itemId } : {},
    }) as { accessToken?: string; connectToken?: string };
    const token = r.accessToken ?? r.connectToken;
    if (!token) throw new Error('Pluggy nao devolveu o token de conexao.');
    return token;
  }

  get<T>(caminho: string, query?: Record<string, string | number | undefined>): Promise<T> {
    return this.requisicao('GET', caminho, query ? { query } : {}) as Promise<T>;
  }

  /** Percorre todas as paginas de um endpoint paginado da Pluggy. */
  async paginar<T>(caminho: string, query: Record<string, string | number | undefined> = {}): Promise<T[]> {
    const itens: T[] = [];
    let pagina = 1;
    const pageSize = 500;
    // Teto de seguranca: 100 paginas ja sao 50 mil lancamentos.
    for (; pagina <= 100; pagina++) {
      const r = await this.get<{ results?: T[]; totalPages?: number }>(caminho, {
        ...query, page: pagina, pageSize,
      });
      itens.push(...(r.results ?? []));
      if (!r.totalPages || pagina >= r.totalPages) break;
    }
    return itens;
  }
}
