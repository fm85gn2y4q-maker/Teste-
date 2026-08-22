import { createInterface } from 'node:readline/promises';

const CTRL_C = 3;
const CTRL_D = 4;
const BACKSPACE = 8;
const DELETE = 127;

/**
 * Pergunta no terminal. Com `oculto`, nao ecoa o que for digitado — segredo nao
 * fica no scrollback do terminal nem em captura de tela.
 */
export async function perguntar(rotulo: string, oculto = false): Promise<string> {
  if (!oculto || !process.stdin.isTTY) {
    const rl = createInterface({ input: process.stdin, output: process.stdout });
    try {
      return (await rl.question(rotulo)).trim();
    } finally {
      rl.close();
    }
  }

  process.stdout.write(rotulo);
  process.stdin.setRawMode(true);
  process.stdin.resume();

  return new Promise((resolve, reject) => {
    let buffer = '';

    const encerrar = (): void => {
      process.stdin.off('data', aoDigitar);
      process.stdin.setRawMode(false);
      process.stdin.pause();
      // Solta o descritor: sem isso o libuv do Windows quebra com
      // "Assertion failed: !(handle->flags & UV_HANDLE_CLOSING)" quando o
      // processo termina com o handle ainda ativo.
      process.stdin.unref();
      process.stdout.write('\n');
    };

    function aoDigitar(dado: Buffer): void {
      const codigo = dado[0];
      const texto = dado.toString('utf8');

      if (texto === '\n' || texto === '\r' || codigo === CTRL_D) {
        encerrar();
        resolve(buffer.trim());
        return;
      }
      if (codigo === CTRL_C) {
        encerrar();
        reject(new Error('cancelado'));
        return;
      }
      if (codigo === DELETE || codigo === BACKSPACE) {
        if (buffer.length > 0) {
          buffer = buffer.slice(0, -1);
          // Apaga um asterisco da tela.
          process.stdout.write('\b \b');
        }
        return;
      }
      // Ignora sequencia de controle (setas, escape) e aceita o resto.
      if (codigo !== undefined && codigo >= 32) {
        buffer += texto;
        // Um asterisco por caractere: o valor continua escondido, mas quem
        // digita ve que esta sendo recebido. Campo mudo parece travado.
        process.stdout.write('*'.repeat(texto.length));
      }
    }

    process.stdin.on('data', aoDigitar);
  });
}
