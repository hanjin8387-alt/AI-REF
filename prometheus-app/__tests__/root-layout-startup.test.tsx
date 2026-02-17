import React from 'react';
import { act, render, waitFor } from '@testing-library/react-native';

const mockBootstrap = jest.fn();

jest.mock('@/services/api', () => ({
  api: {
    bootstrap: (...args: unknown[]) => mockBootstrap(...args),
  },
}));

jest.mock('expo-font', () => ({
  useFonts: () => [true, null],
}));

jest.mock('expo-splash-screen', () => ({
  preventAutoHideAsync: jest.fn().mockResolvedValue(undefined),
  hideAsync: jest.fn().mockResolvedValue(undefined),
}));

jest.mock('@expo/vector-icons/FontAwesome', () => ({
  font: {},
}));

jest.mock('expo-router', () => {
  const ReactLocal = require('react');
  const Stack = ({ children }: { children: React.ReactNode }) => ReactLocal.createElement(ReactLocal.Fragment, null, children);
  Stack.Screen = () => null;
  return {
    Stack,
    ErrorBoundary: ({ children }: { children: React.ReactNode }) =>
      ReactLocal.createElement(ReactLocal.Fragment, null, children),
  };
});

import RootLayout from '../app/_layout';

describe('RootLayout startup', () => {
  beforeEach(() => {
    mockBootstrap.mockReset();
    jest.restoreAllMocks();
  });

  it('renders a boot screen immediately (no null white screen)', () => {
    jest.useFakeTimers();
    mockBootstrap.mockReturnValue(new Promise(() => undefined));

    const screen = render(<RootLayout />);

    expect(screen.getByTestId('boot-screen')).toBeTruthy();
    expect(screen.queryByTestId('boot-offline-button')).toBeNull();

    act(() => {
      jest.advanceTimersByTime(5000);
    });

    expect(screen.getByTestId('boot-offline-button')).toBeTruthy();

    screen.unmount();
    jest.useRealTimers();
  });

  it('shows an error UI when bootstrap fails', async () => {
    mockBootstrap.mockRejectedValue(new Error('Failed to fetch'));

    const screen = render(<RootLayout />);

    await waitFor(() => {
      expect(screen.getByTestId('boot-retry-button')).toBeTruthy();
    });

    screen.unmount();
  });
});

