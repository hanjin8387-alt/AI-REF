import React from 'react';
import { render, waitFor } from '@testing-library/react-native';

import InventoryScreen from '../app/(tabs)/inventory';

const mockGetInventory = jest.fn();

jest.mock('expo-router', () => ({
  useFocusEffect: (callback: () => void | (() => void)) => {
    const ReactLocal = require('react');
    ReactLocal.useEffect(() => callback(), [callback]);
  },
  useRouter: () => ({
    push: jest.fn(),
  }),
}));

jest.mock('@/components/InventoryItemCard', () => {
  const ReactLocal = require('react');
  const { Text } = require('react-native');
  return {
    InventoryItemCard: ({ item }: { item: { name: string } }) => ReactLocal.createElement(Text, null, item.name),
  };
});

jest.mock('@/utils/confirmDelete', () => ({
  confirmDeleteItem: (_name: string, onConfirm: () => void) => onConfirm(),
}));

jest.mock('@/services/api', () => ({
  api: {
    getInventory: (...args: unknown[]) => mockGetInventory(...args),
    getShoppingItems: jest.fn().mockResolvedValue({ data: { items: [], has_more: false, pending_count: 0, purchased_count: 0 } }),
    getRecommendations: jest.fn().mockResolvedValue({ data: { recipes: [], total_count: 0 } }),
    updateInventoryItem: jest.fn(),
    deleteInventoryItem: jest.fn().mockResolvedValue({ data: { success: true } }),
    restoreInventoryItem: jest.fn(),
  },
}));

describe('inventory screen offline badge', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('shows offline cache banner when inventory comes from offline data', async () => {
    mockGetInventory.mockResolvedValue({
      data: {
        items: [],
        total_count: 0,
        limit: 40,
        offset: 0,
        has_more: false,
        offline: true,
        cache_timestamp: Date.now(),
      },
    });

    const screen = render(<InventoryScreen />);

    await waitFor(() => {
      expect(screen.getByText(/오프라인 캐시 표시 중/)).toBeTruthy();
    });
  });

  it('does not show offline cache banner for online inventory data', async () => {
    mockGetInventory.mockResolvedValue({
      data: {
        items: [],
        total_count: 0,
        limit: 40,
        offset: 0,
        has_more: false,
        offline: false,
        cache_timestamp: null,
      },
    });

    const screen = render(<InventoryScreen />);

    await waitFor(() => {
      expect(screen.getByText('인벤토리가 비어 있어요')).toBeTruthy();
    });

    expect(screen.queryByText(/오프라인 캐시 표시 중/)).toBeNull();
  });
});
