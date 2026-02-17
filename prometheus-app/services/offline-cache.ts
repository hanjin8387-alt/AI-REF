/**
 * Offline cache using AsyncStorage for inventory/favorites/shopping.
 * Also stores pending mutation queue and last sync timestamp.
 */
import AsyncStorage from '@react-native-async-storage/async-storage';

import type { ApiRecipe, InventoryItem, ShoppingListResponse } from './api.types';

const KEYS = {
  INVENTORY: 'prometheus_offline_inventory',
  FAVORITES: 'prometheus_offline_favorites',
  SHOPPING: 'prometheus_offline_shopping',
  PENDING_MUTATIONS: 'prometheus_pending_mutations',
  LAST_SYNC: 'prometheus_last_sync',
} as const;

const MAX_PENDING_MUTATIONS = 200;

export type PendingMutation = {
  id: string;
  endpoint: string;
  method: string;
  body?: string;
  created_at: number;
  attempt_count: number;
  next_retry_at: number;
  idempotency_key: string;
};

type PendingMutationInput = Omit<PendingMutation, 'id' | 'created_at' | 'attempt_count' | 'next_retry_at'> & {
  attempt_count?: number;
  next_retry_at?: number;
};

type CacheEnvelope<T> = {
  value: T;
  cache_timestamp: number;
};

function isObject(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === 'object';
}

function normalizeCacheEnvelope<T>(raw: unknown, fallbackValue: T): CacheEnvelope<T> | null {
  if (raw === null || raw === undefined) return null;

  if (isObject(raw) && 'value' in raw) {
    const value = (raw as { value: unknown }).value;
    const timestampValue = Number((raw as { cache_timestamp?: unknown }).cache_timestamp);
    return {
      value: (value as T) ?? fallbackValue,
      cache_timestamp: Number.isFinite(timestampValue) ? timestampValue : Date.now(),
    };
  }

  return {
    value: raw as T,
    cache_timestamp: Date.now(),
  };
}

class OfflineCache {
  async saveInventory(items: InventoryItem[]): Promise<void> {
    try {
      const payload: CacheEnvelope<InventoryItem[]> = {
        value: items,
        cache_timestamp: Date.now(),
      };
      await AsyncStorage.setItem(KEYS.INVENTORY, JSON.stringify(payload));
    } catch {
      // best effort
    }
  }

  async getInventoryEnvelope(): Promise<{ items: InventoryItem[]; cache_timestamp: number } | null> {
    try {
      const raw = await AsyncStorage.getItem(KEYS.INVENTORY);
      if (!raw) return null;

      const parsed = normalizeCacheEnvelope<InventoryItem[]>(JSON.parse(raw), []);
      if (!parsed) return null;

      return {
        items: Array.isArray(parsed.value) ? parsed.value : [],
        cache_timestamp: parsed.cache_timestamp,
      };
    } catch {
      return null;
    }
  }

  async getInventory(): Promise<InventoryItem[] | null> {
    const envelope = await this.getInventoryEnvelope();
    return envelope?.items || null;
  }

  async saveFavorites(recipes: ApiRecipe[]): Promise<void> {
    try {
      const payload: CacheEnvelope<ApiRecipe[]> = {
        value: recipes,
        cache_timestamp: Date.now(),
      };
      await AsyncStorage.setItem(KEYS.FAVORITES, JSON.stringify(payload));
    } catch {
      // best effort
    }
  }

  async getFavoritesEnvelope(): Promise<{ recipes: ApiRecipe[]; cache_timestamp: number } | null> {
    try {
      const raw = await AsyncStorage.getItem(KEYS.FAVORITES);
      if (!raw) return null;

      const parsed = normalizeCacheEnvelope<ApiRecipe[]>(JSON.parse(raw), []);
      if (!parsed) return null;

      return {
        recipes: Array.isArray(parsed.value) ? parsed.value : [],
        cache_timestamp: parsed.cache_timestamp,
      };
    } catch {
      return null;
    }
  }

  async getFavorites(): Promise<ApiRecipe[] | null> {
    const envelope = await this.getFavoritesEnvelope();
    return envelope?.recipes || null;
  }

  async saveShopping(payload: ShoppingListResponse): Promise<void> {
    try {
      const wrapped: CacheEnvelope<ShoppingListResponse> = {
        value: payload,
        cache_timestamp: Date.now(),
      };
      await AsyncStorage.setItem(KEYS.SHOPPING, JSON.stringify(wrapped));
    } catch {
      // best effort
    }
  }

  async getShoppingEnvelope(): Promise<{ payload: ShoppingListResponse; cache_timestamp: number } | null> {
    try {
      const raw = await AsyncStorage.getItem(KEYS.SHOPPING);
      if (!raw) return null;

      const parsed = normalizeCacheEnvelope<ShoppingListResponse>(JSON.parse(raw), {
        items: [],
        total_count: 0,
        pending_count: 0,
        purchased_count: 0,
        limit: 30,
        offset: 0,
        has_more: false,
      });
      if (!parsed) return null;

      return {
        payload: parsed.value,
        cache_timestamp: parsed.cache_timestamp,
      };
    } catch {
      return null;
    }
  }

  async getShopping(): Promise<ShoppingListResponse | null> {
    const envelope = await this.getShoppingEnvelope();
    return envelope?.payload || null;
  }

  async getLatestCacheTimestamp(): Promise<number | null> {
    const [inventory, favorites, shopping] = await Promise.all([
      this.getInventoryEnvelope(),
      this.getFavoritesEnvelope(),
      this.getShoppingEnvelope(),
    ]);

    const timestamps = [inventory?.cache_timestamp, favorites?.cache_timestamp, shopping?.cache_timestamp].filter(
      (value): value is number => Number.isFinite(value)
    );

    if (!timestamps.length) return null;
    return Math.max(...timestamps);
  }

  async enqueueMutation(action: PendingMutationInput): Promise<void> {
    try {
      const queue = await this.getPendingMutations();
      const idempotencyKey = (action.idempotency_key || '').trim();

      const dedupedQueue = idempotencyKey ? queue.filter(item => item.idempotency_key !== idempotencyKey) : [...queue];
      dedupedQueue.push({
        id: `pm-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
        created_at: Date.now(),
        attempt_count: action.attempt_count ?? 0,
        next_retry_at: action.next_retry_at ?? Date.now(),
        ...action,
      });

      const limitedQueue = dedupedQueue.slice(-MAX_PENDING_MUTATIONS);
      await AsyncStorage.setItem(KEYS.PENDING_MUTATIONS, JSON.stringify(limitedQueue));
    } catch {
      // best effort
    }
  }

  async getPendingMutations(): Promise<PendingMutation[]> {
    try {
      const raw = await AsyncStorage.getItem(KEYS.PENDING_MUTATIONS);
      if (!raw) return [];

      const parsed = JSON.parse(raw);
      if (!Array.isArray(parsed)) return [];

      return parsed
        .filter(isObject)
        .map((item, index) => ({
          id: String(item.id || `pm-recovered-${index}`),
          endpoint: String(item.endpoint || ''),
          method: String(item.method || 'POST').toUpperCase(),
          body: typeof item.body === 'string' ? item.body : undefined,
          created_at: Number(item.created_at) || Date.now(),
          attempt_count: Number(item.attempt_count) || 0,
          next_retry_at: Number(item.next_retry_at) || Date.now(),
          idempotency_key: String(item.idempotency_key || ''),
        }))
        .filter(item => Boolean(item.endpoint) && Boolean(item.idempotency_key));
    } catch {
      return [];
    }
  }

  async updatePendingMutation(id: string, patch: Partial<Pick<PendingMutation, 'attempt_count' | 'next_retry_at'>>): Promise<void> {
    try {
      const queue = await this.getPendingMutations();
      const next = queue.map(item => {
        if (item.id !== id) return item;
        return {
          ...item,
          attempt_count: patch.attempt_count ?? item.attempt_count,
          next_retry_at: patch.next_retry_at ?? item.next_retry_at,
        };
      });
      await AsyncStorage.setItem(KEYS.PENDING_MUTATIONS, JSON.stringify(next));
    } catch {
      // best effort
    }
  }

  async removePendingMutation(id: string): Promise<void> {
    try {
      const queue = await this.getPendingMutations();
      const next = queue.filter(item => item.id !== id);
      await AsyncStorage.setItem(KEYS.PENDING_MUTATIONS, JSON.stringify(next));
    } catch {
      // best effort
    }
  }

  async clearPendingMutations(): Promise<void> {
    try {
      await AsyncStorage.removeItem(KEYS.PENDING_MUTATIONS);
    } catch {
      // best effort
    }
  }

  async setLastSync(timestamp = Date.now()): Promise<void> {
    try {
      await AsyncStorage.setItem(KEYS.LAST_SYNC, String(timestamp));
    } catch {
      // best effort
    }
  }

  async getLastSync(): Promise<number | null> {
    try {
      const raw = await AsyncStorage.getItem(KEYS.LAST_SYNC);
      if (!raw) return null;
      const value = Number(raw);
      return Number.isFinite(value) ? value : null;
    } catch {
      return null;
    }
  }
}

export const offlineCache = new OfflineCache();
export default offlineCache;
