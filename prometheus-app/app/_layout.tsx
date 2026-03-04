import FontAwesome from '@expo/vector-icons/FontAwesome';
import { DefaultTheme, ThemeProvider } from '@react-navigation/native';
import { useFonts } from 'expo-font';
import { Stack } from 'expo-router';
import * as SplashScreen from 'expo-splash-screen';
import { useEffect, useMemo, useRef, useState } from 'react';
import { ActivityIndicator, Platform, StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import 'react-native-reanimated';

import { api } from '@/services/api';

export {
  // Catch any errors thrown by the Layout component.
  ErrorBoundary,
} from 'expo-router';

export const unstable_settings = {
  // Ensure that reloading on `/modal` keeps a back button present.
  initialRouteName: '(tabs)',
};

const OFFLINE_CTA_DELAY_MS = 5000;
const BOOTSTRAP_TIMEOUT_MS = 15000;
const PERF_ENV_FLAG = process.env.EXPO_PUBLIC_ENABLE_PERF_LOGS === 'true';

type BootstrapIssue = {
  title: string;
  detail: string;
};

type BootUiState = 'loading' | 'error';

function nowMs() {
  const perf = (globalThis as unknown as { performance?: { now?: () => number } }).performance;
  if (perf && typeof perf.now === 'function') return perf.now();
  return Date.now();
}

function logBootPerf(field: string, valueMs: number) {
  if (!__DEV__ && !PERF_ENV_FLAG) return;
  const safeValue = Number.isFinite(valueMs) ? valueMs.toFixed(1) : '0.0';
  console.info(`[perf.boot] ${field}=${safeValue}`);
}

function removeWebShellLoader() {
  const doc = (globalThis as unknown as { document?: { getElementById?: (id: string) => unknown } }).document;
  if (!doc || typeof doc.getElementById !== 'function') return;

  const loader = doc.getElementById('app-shell-loader') as { remove?: () => void } | null;
  loader?.remove?.();

  const style = doc.getElementById('app-shell-loader-style') as { remove?: () => void } | null;
  style?.remove?.();
}

function classifyBootstrapIssue(error: string): BootstrapIssue {
  const normalized = (error || '').toLowerCase();

  if (normalized.includes('app token') || normalized.includes('app-id') || normalized.includes('x-app-id')) {
    return {
      title: '앱 인증 토큰 설정 필요',
      detail: '앱 식별자 설정이 맞지 않습니다. EXPO_PUBLIC_APP_ID와 서버 APP_IDS 설정을 확인해 주세요.',
    };
  }

  if (normalized.includes('device') || normalized.includes('register')) {
    return {
      title: '디바이스 등록 확인 필요',
      detail: '디바이스 식별자 등록에 실패했습니다. 잠시 후 다시 시도하거나 앱을 재시작해 주세요.',
    };
  }

  if (
    normalized.includes('failed to fetch') ||
    normalized.includes('network') ||
    normalized.includes('load failed') ||
    normalized.includes('timeout') ||
    normalized.includes('초과') ||
    normalized.includes('연결')
  ) {
    return {
      title: '서버 연결 문제',
      detail: '네트워크 연결 또는 서버 상태를 확인해 주세요. 오프라인으로 계속 진행할 수도 있습니다.',
    };
  }

  return {
    title: '초기 진단 실패',
    detail: '앱 초기화 중 문제가 발생했습니다. 다시 시도해 주세요.',
  };
}

function BootScreen(props: {
  state: BootUiState;
  issue: BootstrapIssue | null;
  rawError: string | null;
  offlineCtaReady: boolean;
  onRetry: () => void;
  onOffline: () => void;
}) {
  const { state, issue, rawError, offlineCtaReady, onRetry, onOffline } = props;
  const showIssue = state === 'error' && issue;

  return (
    <View style={styles.bootContainer} testID="boot-screen">
      <Text style={styles.bootBrand}>PROMETHEUS</Text>

      {showIssue ? (
        <>
          <Text style={styles.issueTitle}>{issue.title}</Text>
          <Text style={styles.issueDetail}>{issue.detail}</Text>
          <Text style={styles.issueRaw}>오류: {rawError}</Text>

          <TouchableOpacity
            style={styles.primaryButton}
            onPress={onRetry}
            accessibilityLabel="초기 진단 재시도"
            testID="boot-retry-button"
          >
            <Text style={styles.primaryButtonText}>다시 시도</Text>
          </TouchableOpacity>

          {offlineCtaReady ? (
            <TouchableOpacity
              style={styles.secondaryButton}
              onPress={onOffline}
              accessibilityLabel="오프라인 모드로 계속"
              testID="boot-offline-button"
            >
              <Text style={styles.secondaryButtonText}>오프라인으로 계속</Text>
            </TouchableOpacity>
          ) : null}
        </>
      ) : (
        <>
          <View style={styles.loadingRow}>
            <ActivityIndicator size="large" color="#00D084" />
            <View style={styles.loadingTextGroup}>
              <Text style={styles.loadingTitle}>앱을 준비 중...</Text>
              <Text style={styles.loadingDetail}>첫 실행은 네트워크 상태에 따라 시간이 걸릴 수 있어요.</Text>
            </View>
          </View>

          {offlineCtaReady ? (
            <TouchableOpacity
              style={styles.secondaryButton}
              onPress={onOffline}
              accessibilityLabel="오프라인 모드로 계속"
              testID="boot-offline-button"
            >
              <Text style={styles.secondaryButtonText}>오프라인으로 계속</Text>
            </TouchableOpacity>
          ) : null}
        </>
      )}
    </View>
  );
}

export default function RootLayout() {
  const [apiReady, setApiReady] = useState(false);
  const [allowOfflineMode, setAllowOfflineMode] = useState(false);
  const [bootstrapError, setBootstrapError] = useState<string | null>(null);
  const [fontLoadError, setFontLoadError] = useState<string | null>(null);
  const [retrySeq, setRetrySeq] = useState(0);
  const [offlineCtaReady, setOfflineCtaReady] = useState(false);

  const bootStartedAtRef = useRef(nowMs());
  const firstUiLoggedRef = useRef(false);

  const [fontsLoaded, fontsError] = useFonts({
    SpaceMono: require('../assets/fonts/SpaceMono-Regular.ttf'),
    ...FontAwesome.font,
  });

  const effectiveError = fontLoadError || bootstrapError;
  const issue = useMemo(() => (effectiveError ? classifyBootstrapIssue(effectiveError) : null), [effectiveError]);

  useEffect(() => {
    if (firstUiLoggedRef.current) return;
    firstUiLoggedRef.current = true;
    logBootPerf('time_to_first_ui_ms', nowMs() - bootStartedAtRef.current);
    if (Platform.OS === 'web') {
      removeWebShellLoader();
    }
  }, []);

  useEffect(() => {
    if (!fontsLoaded) return;
    logBootPerf('fonts_loaded_ms', nowMs() - bootStartedAtRef.current);
  }, [fontsLoaded]);

  useEffect(() => {
    const timer = setTimeout(() => setOfflineCtaReady(true), OFFLINE_CTA_DELAY_MS);
    return () => clearTimeout(timer);
  }, []);

  useEffect(() => {
    if (!fontsError) return;
    console.error('[boot] font load failed', fontsError);
    setFontLoadError(fontsError instanceof Error ? fontsError.message : String(fontsError));
  }, [fontsError]);

  useEffect(() => {
    if (Platform.OS === 'web') return;
    SplashScreen.preventAutoHideAsync().catch(() => undefined);
  }, []);

  useEffect(() => {
    if (Platform.OS === 'web') return;
    if (!fontsLoaded) return;
    // Hide splash as soon as we can render our own loading UI (do not wait for API).
    SplashScreen.hideAsync().catch(() => undefined);
  }, [fontsLoaded]);

  useEffect(() => {
    let cancelled = false;

    const bootstrap = async () => {
      setApiReady(false);
      setBootstrapError(null);
      logBootPerf('bootstrap_start_ms', nowMs() - bootStartedAtRef.current);

      try {
        const result = await api.bootstrap({ timeoutMs: BOOTSTRAP_TIMEOUT_MS });
        if (!result.data?.api_ok) {
          throw new Error(result.error || 'Bootstrap check failed');
        }

        if (cancelled) return;
        setApiReady(true);
        setBootstrapError(null);
        logBootPerf('bootstrap_done_ms', nowMs() - bootStartedAtRef.current);
      } catch (initError) {
        if (cancelled) return;
        const message = initError instanceof Error ? initError.message : '앱 초기화에 실패했어요.';
        setBootstrapError(message);
        logBootPerf('bootstrap_error_ms', nowMs() - bootStartedAtRef.current);
      }
    };

    bootstrap();

    return () => {
      cancelled = true;
    };
  }, [retrySeq]);

  const canEnterApp = fontsLoaded && (apiReady || allowOfflineMode);
  if (canEnterApp) {
    return <RootLayoutNav />;
  }

  const uiState: BootUiState =
    fontsLoaded && !apiReady && !allowOfflineMode && effectiveError ? 'error' : effectiveError ? 'error' : 'loading';

  return (
    <BootScreen
      state={uiState}
      issue={issue}
      rawError={effectiveError}
      offlineCtaReady={offlineCtaReady}
      onRetry={() => setRetrySeq(prev => prev + 1)}
      onOffline={() => setAllowOfflineMode(true)}
    />
  );
}

function RootLayoutNav() {
  return (
    <ThemeProvider value={DefaultTheme}>
      <Stack>
        <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
        <Stack.Screen name="modal" options={{ presentation: 'modal' }} />
      </Stack>
    </ThemeProvider>
  );
}

const styles = StyleSheet.create({
  bootContainer: {
    flex: 1,
    justifyContent: 'center',
    paddingHorizontal: 24,
    backgroundColor: '#F5F8F7',
  },
  bootBrand: {
    color: '#132018',
    fontSize: 22,
    fontWeight: '800',
    letterSpacing: 1.2,
    marginBottom: 16,
  },
  loadingRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  loadingTextGroup: {
    flex: 1,
    marginLeft: 14,
  },
  loadingTitle: {
    color: '#132018',
    fontSize: 18,
    fontWeight: '700',
  },
  loadingDetail: {
    marginTop: 6,
    color: '#2A3C33',
    lineHeight: 20,
  },
  issueTitle: {
    color: '#132018',
    fontSize: 26,
    fontWeight: '700',
    marginTop: 6,
  },
  issueDetail: {
    marginTop: 10,
    color: '#2A3C33',
    lineHeight: 21,
  },
  issueRaw: {
    marginTop: 10,
    color: '#5B6F65',
    fontSize: 12,
  },
  primaryButton: {
    marginTop: 18,
    borderRadius: 10,
    alignItems: 'center',
    paddingVertical: 12,
    backgroundColor: '#00D084',
  },
  primaryButtonText: {
    color: '#FFFFFF',
    fontWeight: '700',
  },
  secondaryButton: {
    marginTop: 12,
    borderRadius: 10,
    alignItems: 'center',
    paddingVertical: 12,
    backgroundColor: '#E8EFEC',
  },
  secondaryButtonText: {
    color: '#22352B',
    fontWeight: '700',
  },
});
