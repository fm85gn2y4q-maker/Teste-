import { create } from 'zustand';
import { WatchlistAsset, MarketData } from '../analysis/types';
import { fetchMarketData, setApiToken } from '../api/brapi';
import { runConvergenceAnalysis } from '../analysis/convergence';

const DEFAULT_WATCHLIST = ['PETR4', 'VALE3', 'ITUB4', 'BBDC4', 'WEGE3'];

interface StoreState {
  // Configuração
  apiToken: string;
  setApiToken: (token: string) => void;

  // Watchlist
  watchlist: WatchlistAsset[];
  addTicker: (ticker: string) => void;
  removeTicker: (ticker: string) => void;

  // Dados de mercado carregados
  marketDataMap: Record<string, MarketData>;

  // Loading / error
  loadingTickers: Set<string>;
  errors: Record<string, string>;

  // Ações
  refreshTicker: (ticker: string) => Promise<void>;
  refreshAll: () => Promise<void>;
  initWatchlist: () => void;
}

export const useStore = create<StoreState>((set, get) => ({
  apiToken: '',
  setApiToken: (token) => {
    setApiToken(token);
    set({ apiToken: token });
  },

  watchlist: DEFAULT_WATCHLIST.map((ticker) => ({
    ticker,
    name: ticker,
    currentPrice: 0,
    change: 0,
  })),

  marketDataMap: {},
  loadingTickers: new Set(),
  errors: {},

  addTicker: (ticker) => {
    const { watchlist } = get();
    if (watchlist.find((a) => a.ticker === ticker)) return;
    set((s) => ({
      watchlist: [
        ...s.watchlist,
        { ticker, name: ticker, currentPrice: 0, change: 0 },
      ],
    }));
    get().refreshTicker(ticker);
  },

  removeTicker: (ticker) => {
    set((s) => ({
      watchlist: s.watchlist.filter((a) => a.ticker !== ticker),
    }));
  },

  refreshTicker: async (ticker) => {
    set((s) => {
      const loading = new Set(s.loadingTickers);
      loading.add(ticker);
      return { loadingTickers: loading };
    });

    try {
      const data = await fetchMarketData(ticker, '6mo', '1d');
      const convergence = data.candles.length >= 30
        ? runConvergenceAnalysis(ticker, data.candles)
        : undefined;

      set((s) => {
        const loading = new Set(s.loadingTickers);
        loading.delete(ticker);
        const errors = { ...s.errors };
        delete errors[ticker];

        return {
          loadingTickers: loading,
          errors,
          marketDataMap: { ...s.marketDataMap, [ticker]: data },
          watchlist: s.watchlist.map((a) =>
            a.ticker === ticker
              ? {
                  ...a,
                  name: data.name,
                  currentPrice: data.currentPrice,
                  change: data.change,
                  convergence,
                  lastUpdated: Date.now(),
                }
              : a,
          ),
        };
      });
    } catch (err: any) {
      set((s) => {
        const loading = new Set(s.loadingTickers);
        loading.delete(ticker);
        return {
          loadingTickers: loading,
          errors: { ...s.errors, [ticker]: err.message ?? 'Erro desconhecido' },
        };
      });
    }
  },

  refreshAll: async () => {
    const { watchlist, refreshTicker } = get();
    // Sequencial para não sobrecarregar a API (sem WebSocket)
    for (const asset of watchlist) {
      await refreshTicker(asset.ticker);
    }
  },

  initWatchlist: () => {
    get().refreshAll();
  },
}));
