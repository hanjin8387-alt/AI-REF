import * as FileSystem from 'expo-file-system/legacy';
import React, { useCallback, useMemo, useState } from 'react';
import {
  Alert,
  FlatList,
  Modal,
  Platform,
  RefreshControl,
  StatusBar,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';
import { useFocusEffect } from 'expo-router';

import Colors from '@/constants/Colors';
import { NotificationItem, api } from '@/services/api';
import { fireAndForget } from '@/utils/async';

const PAGE_SIZE = 20;

function getTypeLabel(type: NotificationItem['type']) {
  switch (type) {
    case 'inventory':
      return '인벤토리';
    case 'cooking':
      return '요리';
    case 'expiry':
      return '유통기한';
    default:
      return '시스템';
  }
}

function formatAge(ms?: number): string {
  if (!ms || ms <= 0) return '0분';
  const minutes = Math.floor(ms / (1000 * 60));
  if (minutes < 60) return `${minutes}분`;
  const hours = Math.floor(minutes / 60);
  return `${hours}시간`;
}

function summarizeBackupPayload(payload: Record<string, unknown>): Array<{ table: string; count: number }> {
  const data = payload?.data;
  if (!data || typeof data !== 'object') return [];

  return Object.entries(data as Record<string, unknown>)
    .map(([table, rows]) => ({
      table,
      count: Array.isArray(rows) ? rows.length : 0,
    }))
    .sort((a, b) => b.count - a.count);
}

async function pickWebBackupText(): Promise<string> {
  if (typeof document === 'undefined') {
    throw new Error('웹 파일 선택기를 사용할 수 없어요.');
  }

  return new Promise((resolve, reject) => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json,application/json';

    input.onchange = () => {
      const file = input.files?.[0];
      if (!file) {
        reject(new Error('선택된 파일이 없어요.'));
        return;
      }

      const reader = new FileReader();
      reader.onload = () => resolve(String(reader.result || ''));
      reader.onerror = () => reject(new Error('파일을 읽지 못했어요.'));
      reader.readAsText(file, 'utf-8');
    };

    input.click();
  });
}

export default function AlertsScreen() {
  const [items, setItems] = useState<NotificationItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [hasMore, setHasMore] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const [syncPendingCount, setSyncPendingCount] = useState(0);
  const [lastSyncAt, setLastSyncAt] = useState<number | null>(null);
  const [syncOnline, setSyncOnline] = useState(true);
  const [queueHealth, setQueueHealth] = useState<'healthy' | 'warning' | 'critical'>('healthy');
  const [oldestPendingAgeMs, setOldestPendingAgeMs] = useState(0);
  const [staleCacheAgeMs, setStaleCacheAgeMs] = useState(0);

  const [backupModalVisible, setBackupModalVisible] = useState(false);
  const [backupJson, setBackupJson] = useState('');
  const [backupMode, setBackupMode] = useState<'merge' | 'replace'>('merge');
  const [backupFilePath, setBackupFilePath] = useState('');

  const backupSummary = useMemo(() => {
    if (!backupJson) return [];
    try {
      const parsed = JSON.parse(backupJson) as Record<string, unknown>;
      return summarizeBackupPayload(parsed);
    } catch {
      return [];
    }
  }, [backupJson]);

  const loadNotifications = async (reset: boolean) => {
    const offset = reset ? 0 : items.length;
    const result = await api.getNotifications(PAGE_SIZE, offset, false);
    if (result.data) {
      const nextItems = Array.isArray(result.data.items) ? result.data.items : [];
      setItems(prev => (reset ? nextItems : [...prev, ...nextItems]));
      setHasMore(Boolean(result.data.has_more));
      setUnreadCount(Number(result.data.unread_count || 0));
      setError(null);
    } else if (reset) {
      setItems([]);
      setError(result.error || '알림을 불러오지 못했어요.');
    }

    setLoading(false);
    setRefreshing(false);
    setLoadingMore(false);
  };

  const loadSyncStatus = async () => {
    const result = await api.getSyncStatus();
    setSyncPendingCount(result.pending_count || 0);
    setLastSyncAt(result.last_sync_at ?? null);
    setSyncOnline(Boolean(result.online));
    setQueueHealth(result.queue_health || 'healthy');
    setOldestPendingAgeMs(result.oldest_pending_age_ms || 0);
    setStaleCacheAgeMs(result.stale_cache_age_ms || 0);
  };

  useFocusEffect(
    useCallback(() => {
      setLoading(true);
      fireAndForget(loadNotifications(true), message => setError(message), '알림 로드 실패');
      fireAndForget(loadSyncStatus(), () => { }, '동기화 상태 로드 실패');
    }, [])
  );

  const onRefresh = () => {
    setRefreshing(true);
    fireAndForget(loadNotifications(true), message => setError(message), '알림 새로고침 실패');
    fireAndForget(loadSyncStatus(), () => { }, '동기화 상태 로드 실패');
  };

  const onLoadMore = () => {
    if (!hasMore || loading || loadingMore || refreshing) return;
    setLoadingMore(true);
    fireAndForget(loadNotifications(false), message => setError(message), '알림 추가 로드 실패');
  };

  const markAllRead = async () => {
    const result = await api.markNotificationsRead([]);
    if (result.data?.success) {
      setItems(prev => prev.map(item => ({ ...item, is_read: true })));
      setUnreadCount(0);
      return;
    }
    Alert.alert('처리 실패', result.error || '모든 알림을 읽음 처리하지 못했어요.');
  };

  const markOneRead = async (notificationId: string) => {
    const result = await api.markNotificationsRead([notificationId]);
    if (result.data?.success) {
      setItems(prev => prev.map(item => (item.id === notificationId ? { ...item, is_read: true } : item)));
      setUnreadCount(prev => Math.max(0, prev - 1));
      return;
    }
    Alert.alert('처리 실패', result.error || '알림을 읽음 처리하지 못했어요.');
  };

  const retryPendingSync = async () => {
    const result = await api.retryPendingSync();
    Alert.alert(
      '동기화 결과',
      `성공 ${result.success_count}건 / 실패 ${result.failed_count}건 / 남음 ${result.remaining_count}건`
    );
    await loadSyncStatus();
  };

  const exportBackup = async () => {
    const result = await api.exportBackup();
    if (!result.data?.success) {
      Alert.alert('백업 실패', result.error || '백업 데이터를 내보내지 못했어요.');
      return;
    }

    const jsonText = JSON.stringify(result.data.payload, null, 2);
    setBackupJson(jsonText);
    setBackupMode('merge');
    setBackupModalVisible(true);
  };

  const saveBackupAsFile = async () => {
    if (!backupJson) {
      Alert.alert('백업 없음', '먼저 백업 데이터를 생성해 주세요.');
      return;
    }

    const filename = `prometheus-backup-${new Date().toISOString().slice(0, 10)}.json`;

    if (Platform.OS === 'web') {
      if (typeof document === 'undefined') {
        Alert.alert('저장 실패', '웹 다운로드를 사용할 수 없어요.');
        return;
      }

      const blob = new Blob([backupJson], { type: 'application/json;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = filename;
      anchor.click();
      URL.revokeObjectURL(url);
      return;
    }

    const basePath = FileSystem.documentDirectory;
    if (!basePath) {
      Alert.alert('저장 실패', '로컬 문서 디렉터리를 찾을 수 없어요.');
      return;
    }

    const fileUri = `${basePath}${filename}`;
    await FileSystem.writeAsStringAsync(fileUri, backupJson, { encoding: FileSystem.EncodingType.UTF8 });
    setBackupFilePath(fileUri);
    Alert.alert('저장 완료', `백업 파일을 저장했어요.\n${fileUri}`);
  };

  const loadBackupFromFile = async () => {
    try {
      let text = '';

      if (Platform.OS === 'web') {
        text = await pickWebBackupText();
      } else {
        const path = backupFilePath.trim();
        if (!path) {
          Alert.alert('경로 필요', '백업 파일 경로를 입력해 주세요.');
          return;
        }
        text = await FileSystem.readAsStringAsync(path, { encoding: FileSystem.EncodingType.UTF8 });
      }

      JSON.parse(text);
      setBackupJson(text);
      Alert.alert('불러오기 완료', '백업 파일을 불러왔어요.');
    } catch (loadError) {
      const message = loadError instanceof Error ? loadError.message : '백업 파일을 불러오지 못했어요.';
      Alert.alert('불러오기 실패', message);
    }
  };

  const restoreBackup = async () => {
    try {
      const payload = JSON.parse(backupJson);
      const result = await api.restoreBackup(payload, backupMode);
      if (!result.data?.success) {
        Alert.alert('복원 실패', result.error || '복원에 실패했어요.');
        return;
      }
      Alert.alert('복원 완료', result.data.message || '복원을 완료했어요.');
      setBackupModalVisible(false);
      fireAndForget(loadNotifications(true), message => setError(message), '알림 로드 실패');
      fireAndForget(loadSyncStatus(), () => { }, '동기화 상태 로드 실패');
    } catch {
      Alert.alert('형식 오류', '유효한 JSON 형식의 백업 파일을 불러와 주세요.');
    }
  };

  return (
    <View style={styles.container}>
      <StatusBar barStyle="dark-content" />

      <View style={styles.header}>
        <View>
          <Text style={styles.title}>알림</Text>
          <Text style={styles.subtitle}>읽지 않음: {unreadCount}</Text>
        </View>
        <TouchableOpacity
          style={[styles.markAllButton, unreadCount <= 0 && styles.disabledButton]}
          onPress={() =>
            fireAndForget(markAllRead(), message => Alert.alert('처리 실패', message), '알림 읽음 처리 실패')
          }
          disabled={unreadCount <= 0}
          accessibilityLabel="모든 알림 읽음 처리"
        >
          <Text style={styles.markAllText}>모두 읽음</Text>
        </TouchableOpacity>
      </View>

      <View style={styles.quickPanel}>
        <Text style={styles.quickTitle}>동기화 센터</Text>
        <Text style={styles.quickMeta}>
          네트워크: {syncOnline ? '연결됨' : '오프라인'} / 대기 요청: {syncPendingCount}
          {lastSyncAt ? ` / 마지막 동기화: ${new Date(lastSyncAt).toLocaleString()}` : ''}
        </Text>
        <Text style={styles.quickMeta}>
          큐 상태: {queueHealth} / 가장 오래된 대기: {formatAge(oldestPendingAgeMs)} / 캐시 경과: {formatAge(staleCacheAgeMs)}
        </Text>
        <View style={styles.quickButtons}>
          <TouchableOpacity
            style={styles.quickButton}
            onPress={() => fireAndForget(retryPendingSync(), () => { }, '동기화 재시도 실패')}
            accessibilityLabel="대기 요청 재시도"
          >
            <Text style={styles.quickButtonText}>대기 요청 재시도</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={styles.quickButton}
            onPress={() => fireAndForget(exportBackup(), () => { }, '백업 내보내기 실패')}
            accessibilityLabel="백업 창 열기"
          >
            <Text style={styles.quickButtonText}>백업 열기</Text>
          </TouchableOpacity>
        </View>
      </View>

      {loading ? (
        <View style={styles.loadingWrap}>
          {[0, 1, 2].map(index => (
            <View key={index} style={styles.skeleton} />
          ))}
        </View>
      ) : items.length === 0 ? (
        <View style={styles.centered}>
          <Text style={styles.emptyText}>{error || '표시할 알림이 없어요.'}</Text>
          <TouchableOpacity
            style={styles.retryButton}
            onPress={() => fireAndForget(loadNotifications(true), message => setError(message), '알림 로드 실패')}
            accessibilityLabel="알림 다시 시도"
          >
            <Text style={styles.retryText}>다시 시도</Text>
          </TouchableOpacity>
        </View>
      ) : (
        <FlatList
          data={items}
          keyExtractor={item => item.id}
          contentContainerStyle={styles.listContent}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={Colors.primary} />}
          onEndReachedThreshold={0.3}
          onEndReached={onLoadMore}
          renderItem={({ item }) => (
            <TouchableOpacity
              style={[styles.card, !item.is_read && styles.unreadCard]}
              onPress={() => {
                if (!item.is_read) {
                  fireAndForget(
                    markOneRead(item.id),
                    message => Alert.alert('처리 실패', message),
                    '알림 읽음 처리 실패'
                  );
                }
              }}
              accessibilityLabel={`${item.title || '알림'} 상세 보기`}
            >
              {(() => {
                const itemType = (item.type || 'system') as NotificationItem['type'];
                const title = item.title || '제목 없는 알림';
                const message = item.message || '';
                return (
                  <>
                    <View style={styles.cardHeader}>
                      <Text style={styles.typeBadge}>{getTypeLabel(itemType)}</Text>
                      <Text style={styles.timeText}>{new Date(item.created_at).toLocaleString()}</Text>
                    </View>
                    <Text style={styles.cardTitle}>{title}</Text>
                    <Text style={styles.cardMessage}>{message}</Text>
                  </>
                );
              })()}
            </TouchableOpacity>
          )}
          ListFooterComponent={
            loadingMore ? (
              <Text style={styles.footerText}>더 불러오는 중...</Text>
            ) : hasMore ? (
              <Text style={styles.footerText}>아래로 내려 더 보기</Text>
            ) : (
              <Text style={styles.footerText}>모든 알림을 불러왔어요</Text>
            )
          }
        />
      )}

      <Modal visible={backupModalVisible} transparent animationType="slide" onRequestClose={() => setBackupModalVisible(false)}>
        <View style={styles.modalOverlay}>
          <View style={styles.modalCard}>
            <Text style={styles.modalTitle}>백업 / 복원</Text>

            <View style={styles.modeRow}>
              <TouchableOpacity
                style={[styles.modeButton, backupMode === 'merge' && styles.modeButtonActive]}
                onPress={() => setBackupMode('merge')}
                accessibilityLabel="백업 복원 병합 모드 선택"
              >
                <Text style={[styles.modeButtonText, backupMode === 'merge' && styles.modeButtonTextActive]}>병합</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[styles.modeButton, backupMode === 'replace' && styles.modeButtonActive]}
                onPress={() => setBackupMode('replace')}
                accessibilityLabel="백업 복원 교체 모드 선택"
              >
                <Text style={[styles.modeButtonText, backupMode === 'replace' && styles.modeButtonTextActive]}>교체</Text>
              </TouchableOpacity>
            </View>

            <View style={styles.fileActionsRow}>
              <TouchableOpacity
                style={styles.fileActionButton}
                onPress={() => fireAndForget(saveBackupAsFile(), () => { }, '백업 파일 저장 실패')}
                accessibilityLabel="백업 파일 저장"
              >
                <Text style={styles.fileActionText}>파일로 저장</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={styles.fileActionButton}
                onPress={() => fireAndForget(loadBackupFromFile(), () => { }, '백업 파일 불러오기 실패')}
                accessibilityLabel="백업 파일 불러오기"
              >
                <Text style={styles.fileActionText}>파일 불러오기</Text>
              </TouchableOpacity>
            </View>

            {Platform.OS !== 'web' ? (
              <TextInput
                style={styles.filePathInput}
                value={backupFilePath}
                onChangeText={setBackupFilePath}
                placeholder="백업 파일 경로를 입력하세요"
                placeholderTextColor={Colors.gray500}
                autoCapitalize="none"
                accessibilityLabel="백업 파일 경로 입력"
              />
            ) : null}

            <View style={styles.summaryBox}>
              <Text style={styles.summaryTitle}>복원 미리보기</Text>
              {backupSummary.length > 0 ? (
                backupSummary.slice(0, 7).map(row => (
                  <Text key={row.table} style={styles.summaryLine}>
                    - {row.table}: {row.count}건
                  </Text>
                ))
              ) : (
                <Text style={styles.summaryLine}>아직 불러온 백업 파일이 없어요.</Text>
              )}
            </View>

            <TextInput
              style={styles.backupInput}
              multiline
              editable={false}
              value={backupJson}
              placeholder="백업 데이터를 파일로 저장하거나 파일에서 불러오세요."
              placeholderTextColor={Colors.gray500}
            />

            <View style={styles.modalActions}>
              <TouchableOpacity
                style={styles.modalCancelButton}
                onPress={() => setBackupModalVisible(false)}
                accessibilityLabel="백업 모달 닫기"
              >
                <Text style={styles.modalCancelText}>닫기</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={styles.modalApplyButton}
                onPress={() => fireAndForget(restoreBackup(), () => { }, '백업 복원 실패')}
                accessibilityLabel="백업 복원 실행"
              >
                <Text style={styles.modalApplyText}>복원 실행</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F5F8F7' },
  header: {
    paddingTop: 60,
    paddingHorizontal: 24,
    paddingBottom: 12,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: 8,
  },
  title: {
    color: '#132018',
    fontSize: 28,
    fontWeight: '700',
  },
  subtitle: {
    color: Colors.gray600,
    marginTop: 4,
  },
  markAllButton: {
    borderRadius: 10,
    paddingVertical: 8,
    paddingHorizontal: 12,
    backgroundColor: Colors.white,
    borderWidth: 1,
    borderColor: '#DDE6E1',
  },
  markAllText: {
    color: '#22352B',
    fontSize: 12,
    fontWeight: '700',
  },
  quickPanel: {
    marginHorizontal: 24,
    marginBottom: 10,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#DDE6E1',
    backgroundColor: '#F9FBFA',
    padding: 10,
  },
  quickTitle: { color: '#132018', fontWeight: '700', fontSize: 14 },
  quickMeta: { color: Colors.gray600, marginTop: 6, fontSize: 12, lineHeight: 17 },
  quickButtons: { flexDirection: 'row', gap: 8, marginTop: 10 },
  quickButton: {
    flex: 1,
    borderRadius: 10,
    backgroundColor: Colors.white,
    borderWidth: 1,
    borderColor: '#DDE6E1',
    alignItems: 'center',
    paddingVertical: 9,
  },
  quickButtonText: { color: '#22352B', fontSize: 12, fontWeight: '700' },
  disabledButton: {
    opacity: 0.45,
  },
  loadingWrap: {
    paddingHorizontal: 24,
    gap: 12,
  },
  skeleton: {
    height: 110,
    borderRadius: 14,
    backgroundColor: '#E8EFEC',
    borderWidth: 1,
    borderColor: '#DDE6E1',
  },
  centered: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 24,
  },
  emptyText: {
    color: Colors.gray600,
    textAlign: 'center',
  },
  retryButton: {
    marginTop: 12,
    backgroundColor: Colors.primary,
    borderRadius: 10,
    paddingHorizontal: 16,
    paddingVertical: 10,
  },
  retryText: {
    color: Colors.white,
    fontWeight: '700',
  },
  listContent: {
    paddingHorizontal: 24,
    paddingBottom: 100,
  },
  card: {
    backgroundColor: Colors.white,
    borderRadius: 14,
    padding: 14,
    marginBottom: 10,
    borderWidth: 1,
    borderColor: '#DDE6E1',
  },
  unreadCard: {
    borderColor: '#A5DFC4',
    backgroundColor: '#F7FFFB',
  },
  cardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 6,
  },
  typeBadge: {
    color: Colors.primaryDark,
    backgroundColor: 'rgba(0, 208, 132, 0.14)',
    borderRadius: 999,
    paddingHorizontal: 8,
    paddingVertical: 3,
    fontSize: 11,
    fontWeight: '700',
  },
  timeText: {
    color: Colors.gray500,
    fontSize: 11,
  },
  cardTitle: {
    color: '#132018',
    fontSize: 15,
    fontWeight: '700',
    marginBottom: 4,
  },
  cardMessage: {
    color: Colors.gray700,
    fontSize: 13,
    lineHeight: 18,
  },
  footerText: {
    textAlign: 'center',
    color: Colors.gray600,
    marginVertical: 14,
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(17, 33, 24, 0.34)',
    justifyContent: 'flex-end',
  },
  modalCard: {
    backgroundColor: Colors.white,
    borderTopLeftRadius: 18,
    borderTopRightRadius: 18,
    padding: 16,
    maxHeight: '86%',
  },
  modalTitle: {
    color: '#132018',
    fontSize: 20,
    fontWeight: '700',
    marginBottom: 10,
  },
  modeRow: {
    flexDirection: 'row',
    gap: 8,
    marginBottom: 10,
  },
  modeButton: {
    flex: 1,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: '#DDE6E1',
    backgroundColor: '#F9FBFA',
    alignItems: 'center',
    paddingVertical: 8,
  },
  modeButtonActive: {
    backgroundColor: Colors.primary,
    borderColor: Colors.primary,
  },
  modeButtonText: {
    color: '#22352B',
    fontWeight: '700',
  },
  modeButtonTextActive: {
    color: Colors.white,
  },
  fileActionsRow: {
    flexDirection: 'row',
    gap: 8,
    marginBottom: 8,
  },
  fileActionButton: {
    flex: 1,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: '#DDE6E1',
    backgroundColor: '#F9FBFA',
    alignItems: 'center',
    paddingVertical: 8,
  },
  fileActionText: {
    color: '#22352B',
    fontSize: 12,
    fontWeight: '700',
  },
  filePathInput: {
    borderRadius: 10,
    borderWidth: 1,
    borderColor: '#DDE6E1',
    backgroundColor: '#F9FBFA',
    color: '#132018',
    paddingHorizontal: 10,
    paddingVertical: 8,
    marginBottom: 8,
  },
  summaryBox: {
    borderRadius: 10,
    borderWidth: 1,
    borderColor: '#DDE6E1',
    backgroundColor: '#F9FBFA',
    padding: 10,
    marginBottom: 8,
  },
  summaryTitle: {
    color: '#132018',
    fontWeight: '700',
    marginBottom: 6,
  },
  summaryLine: {
    color: Colors.gray700,
    fontSize: 12,
    marginBottom: 2,
  },
  backupInput: {
    minHeight: 180,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#DDE6E1',
    backgroundColor: '#F9FBFA',
    color: '#132018',
    padding: 12,
    textAlignVertical: 'top',
  },
  modalActions: {
    flexDirection: 'row',
    gap: 10,
    marginTop: 12,
  },
  modalCancelButton: {
    flex: 1,
    borderRadius: 10,
    backgroundColor: '#E8EFEC',
    alignItems: 'center',
    paddingVertical: 11,
  },
  modalCancelText: { color: '#22352B', fontWeight: '700' },
  modalApplyButton: {
    flex: 1,
    borderRadius: 10,
    backgroundColor: Colors.primary,
    alignItems: 'center',
    paddingVertical: 11,
  },
  modalApplyText: { color: Colors.white, fontWeight: '700' },
});
