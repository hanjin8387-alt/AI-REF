import '@testing-library/jest-native/extend-expect';

jest.mock('@react-native-async-storage/async-storage', () =>
  require('@react-native-async-storage/async-storage/jest/async-storage-mock')
);

jest.mock('expo-constants', () => ({
  expoConfig: {
    extra: {
      apiUrl: 'http://localhost:8000',
      appId: 'prometheus-app',
      legacyAppToken: '',
    },
  },
}));

jest.mock('expo-file-system', () => ({
  documentDirectory: 'file:///tmp/',
  writeAsStringAsync: jest.fn(),
  readAsStringAsync: jest.fn(),
  deleteAsync: jest.fn(),
  getInfoAsync: jest.fn(async () => ({ exists: false })),
}));

jest.mock('react-native/Libraries/EventEmitter/NativeEventEmitter');
