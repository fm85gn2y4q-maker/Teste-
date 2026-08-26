import { create } from 'zustand';
import { ShoppingItem } from '../types';
import { DEFAULT_PLANNER_OPTIONS } from '../engine/planner';

interface AppState {
  bairroId: string;
  items: ShoppingItem[];
  maxStops: number;
  costPerKm: number;

  setBairro: (bairroId: string) => void;
  addItem: (productId: string, quantity?: number) => void;
  removeItem: (productId: string) => void;
  setQuantity: (productId: string, quantity: number) => void;
  mergeItems: (items: ShoppingItem[]) => void;
  clearList: () => void;
  setMaxStops: (value: number) => void;
  setCostPerKm: (value: number) => void;
}

export const useStore = create<AppState>((set) => ({
  bairroId: 'barra',
  items: [],
  maxStops: DEFAULT_PLANNER_OPTIONS.maxStops,
  costPerKm: DEFAULT_PLANNER_OPTIONS.costPerKm,

  setBairro: (bairroId) => set({ bairroId }),

  addItem: (productId, quantity = 1) =>
    set((state) => {
      const existing = state.items.find((i) => i.productId === productId);
      if (existing) {
        return {
          items: state.items.map((i) =>
            i.productId === productId ? { ...i, quantity: i.quantity + quantity } : i,
          ),
        };
      }
      return { items: [...state.items, { productId, quantity }] };
    }),

  removeItem: (productId) =>
    set((state) => ({ items: state.items.filter((i) => i.productId !== productId) })),

  setQuantity: (productId, quantity) =>
    set((state) => ({
      items:
        quantity <= 0
          ? state.items.filter((i) => i.productId !== productId)
          : state.items.map((i) => (i.productId === productId ? { ...i, quantity } : i)),
    })),

  mergeItems: (incoming) =>
    set((state) => {
      const merged = new Map(state.items.map((i) => [i.productId, i.quantity]));
      for (const item of incoming) {
        merged.set(item.productId, (merged.get(item.productId) ?? 0) + item.quantity);
      }
      return {
        items: [...merged.entries()].map(([productId, quantity]) => ({ productId, quantity })),
      };
    }),

  clearList: () => set({ items: [] }),
  setMaxStops: (value) => set({ maxStops: Math.min(4, Math.max(1, value)) }),
  setCostPerKm: (value) => set({ costPerKm: Math.max(0, Math.round(value * 100) / 100) }),
}));
