import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Alert,
  Modal,
  Platform,
  RefreshControl,
  SectionList,
  StatusBar,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';
import { useFocusEffect } from 'expo-router';

import Colors from '@/constants/Colors';
import { InventoryItemCard } from '@/components/InventoryItemCard';
import { InventoryItem, SortOption, api } from '@/services/api';
import { fireAndForget } from '@/utils/async';
import { confirmDeleteItem } from '@/utils/confirmDelete';

const PAGE_SIZE = 40;
const INVENTORY_ROW_HEIGHT = 96;
const STORAGE_GROUPS = ['냉장', '냉동', '상온', '미분류'] as const;
type StorageGroup = (typeof STORAGE_GROUPS)[number];

type InventorySection = {
  title: StorageGroup;
  data: InventoryItem[];
};

type InventoryFilter = 'all' | StorageGroup | 'expiring';

function normalizeStorageCategory(value?: string): StorageGroup {
  const normalized = (value || '').trim().toLowerCase().replace(/[_\-\s]/g, '');
  if (!normalized) return '미분류';

  if (normalized.includes('냉동') || normalized.includes('ëë') || normalized.includes('freezer') || normalized.includes('frozen')) return '냉동';
  if (normalized.includes('냉장') || normalized.includes('ëì¥') || normalized.includes('fridge') || normalized.includes('refriger')) return '냉장';
  if (normalized.includes('상온') || normalized.includes('ìì¨') || normalized.includes('실온') || normalized.includes('ambient') || normalized.includes('pantry')) return '상온';

  return '미분류';
}

function compareInventory(a: InventoryItem, b: InventoryItem, sortBy: SortOption): number {
  if (sortBy === 'name') {
    return a.name.localeCompare(b.name, 'ko');
  }

  if (sortBy === 'created_at') {
    const aTime = new Date(a.created_at || 0).getTime();
    const bTime = new Date(b.created_at || 0).getTime();
    return bTime - aTime;
  }

  const aExpiry = a.expiry_date ? new Date(a.expiry_date).getTime() : Number.POSITIVE_INFINITY;
  const bExpiry = b.expiry_date ? new Date(b.expiry_date).getTime() : Number.POSITIVE_INFINITY;
  return aExpiry - bExpiry;
}

function dedupeById(items: InventoryItem[]): InventoryItem[] {
  const seen = new Set<string>();
  const out: InventoryItem[] = [];
  for (const item of items) {
    const key = item.id || `${item.name}::${item.created_at || ''}`;
    if (seen.has(key)) continue;
    seen.add(key);
    out.push(item);
  }
  return out;
}

export default function InventoryScreen() {
  const [items, setItems] = useState<InventoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [hasMore, setHasMore] = useState(false);
  const [sortBy, setSortBy] = useState<SortOption>('expiry_date');
  const [activeFilter, setActiveFilter] = useState<InventoryFilter>('all');
  const [loadError, setLoadError] = useState<string | null>(null);
  const [offlineMode, setOfflineMode] = useState(false);
  const [cacheTimestamp, setCacheTimestamp] = useState<number | null>(null);

  const [editingItem, setEditingItem] = useState<InventoryItem | null>(null);
  const [editName, setEditName] = useState('');
  const [editQuantity, setEditQuantity] = useState('');
  const [editUnit, setEditUnit] = useState('');
  const [editCategory, setEditCategory] = useState<StorageGroup>('미분류');

  const [undoItem, setUndoItem] = useState<InventoryItem | null>(null);
  const [undoVisible, setUndoVisible] = useState(false);
  const undoTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const requestSeq = useRef(0);

  const clearUndoTimer = () => {
    if (!undoTimer.current) return;
    clearTimeout(undoTimer.current);
    undoTimer.current = null;
  };

  const showUndo = (item: InventoryItem) => {
    clearUndoTimer();
    setUndoItem(item);
    setUndoVisible(true);
    undoTimer.current = setTimeout(() => {
      setUndoVisible(false);
      setUndoItem(null);
    }, 5000);
  };

  useEffect(() => () => clearUndoTimer(), []);

  const fetchInventory = async (reset: boolean) => {
    const seq = ++requestSeq.current;
    const offset = reset ? 0 : items.length;
    const result = await api.getInventory(undefined, sortBy, PAGE_SIZE, offset);
    if (seq !== requestSeq.current) {
      return;
    }

    if (result.data) {
      setOfflineMode(Boolean(result.data.offline));
      setCacheTimestamp(result.data.cache_timestamp ?? null);
      setItems(prev => {
        const merged = reset ? result.data!.items : [...prev, ...result.data!.items];
        return dedupeById(merged);
      });
      setHasMore(result.data.has_more);
      setLoadError(null);
    } else if (reset) {
      setOfflineMode(false);
      setCacheTimestamp(null);
      setItems([]);
      setLoadError(result.error || '재고를 불러오지 못했어요.');
    }

    setLoading(false);
    setRefreshing(false);
    setLoadingMore(false);
  };

  useFocusEffect(
    useCallback(() => {
      setLoading(true);
      fireAndForget(fetchInventory(true), message => setLoadError(message), '재고 로드 실패');
    }, [sortBy])
  );

  const onRefresh = () => {
    setRefreshing(true);
    fireAndForget(fetchInventory(true), message => setLoadError(message), '재고 새로고침 실패');
  };

  const onLoadMore = () => {
    if (!hasMore || loading || loadingMore || refreshing) return;
    setLoadingMore(true);
    fireAndForget(fetchInventory(false), message => setLoadError(message), '재고 추가 로드 실패');
  };

  const openEditModal = (item: InventoryItem) => {
    setEditingItem(item);
    setEditName(item.name);
    setEditQuantity(String(item.quantity));
    setEditUnit(item.unit);
    setEditCategory(normalizeStorageCategory(item.category));
  };

  const closeEditModal = () => {
    setEditingItem(null);
    setEditName('');
    setEditQuantity('');
    setEditUnit('');
    setEditCategory('미분류');
  };

  const saveEdit = async () => {
    if (!editingItem) return;
    const quantity = Number(editQuantity);
    if (!editName.trim() || Number.isNaN(quantity) || quantity < 0) {
      Alert.alert('입력값 오류', '올바른 이름과 수량을 입력해주세요.');
      return;
    }

    const result = await api.updateInventoryItem(editingItem.id, {
      name: editName.trim(),
      quantity,
      unit: editUnit.trim() || '개',
      category: editCategory === '미분류' ? undefined : editCategory,
    });

    if (!result.data) {
      Alert.alert('수정 실패', result.error || '항목을 저장하지 못했어요.');
      return;
    }

    setItems(prev => prev.map(item => (item.id === editingItem.id ? result.data! : item)));
    closeEditModal();
  };

  const performDelete = async (item: InventoryItem) => {
    try {
      const result = await api.deleteInventoryItem(item.id);
      if (!result.data?.success) {
        const msg = result.error || '항목을 삭제하지 못했어요.';
        if (Platform.OS === 'web') {
          window.alert(`삭제 실패: ${msg}`);
        } else {
          Alert.alert('삭제 실패', msg);
        }
        return;
      }

      setItems(prev =>
        prev.filter(current => {
          if (current.id && item.id) return current.id !== item.id;
          return !(current.name === item.name && current.created_at === item.created_at);
        })
      );
      showUndo(item);
    } catch (error) {
      const msg = error instanceof Error ? error.message : '항목을 삭제하지 못했어요.';
      if (Platform.OS === 'web') {
        window.alert(`삭제 실패: ${msg}`);
      } else {
        Alert.alert('삭제 실패', msg);
      }
    }
  };

  const undoDelete = async () => {
    if (!undoItem) return;

    clearUndoTimer();
    const restorePayload = {
      name: undoItem.name,
      quantity: Number(undoItem.quantity) || 1,
      unit: undoItem.unit || '개',
      expiry_date: undoItem.expiry_date,
      category: undoItem.category,
    };

    const result = await api.restoreInventoryItem(restorePayload);
    if (!result.data) {
      Alert.alert('복원 실패', result.error || '삭제 취소를 완료하지 못했어요.');
      setUndoVisible(false);
      setUndoItem(null);
      return;
    }

    setItems(prev => {
      const merged = [...prev, result.data!];
      return dedupeById(merged).sort((a, b) => compareInventory(a, b, sortBy));
    });
    setUndoVisible(false);
    setUndoItem(null);
  };

  const deleteItem = (item: InventoryItem) => {
    confirmDeleteItem(item.name, () => {
      fireAndForget(performDelete(item), () => { }, '삭제 실패');
    });
  };

  const today = new Date();
  const stats = items.reduce(
    (acc, item) => {
      if (item.expiry_date) {
        const expiry = new Date(item.expiry_date);
        const diffDays = Math.ceil((expiry.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
        if (diffDays <= 0) acc.expired += 1;
        else if (diffDays <= 3) acc.expiringSoon += 1;
      }
      return acc;
    },
    { total: items.length, expiringSoon: 0, expired: 0 }
  );

  const storageCounts = useMemo(() => {
    const counts: Record<StorageGroup, number> = {
      냉장: 0,
      냉동: 0,
      상온: 0,
      미분류: 0,
    };
    for (const item of items) {
      counts[normalizeStorageCategory(item.category)] += 1;
    }
    return counts;
  }, [items]);

  const sections = useMemo<InventorySection[]>(() => {
    const sorted = [...items].sort((a, b) => compareInventory(a, b, sortBy));
    const now = Date.now();
    const filtered = sorted.filter(item => {
      if (activeFilter === 'all') return true;
      if (activeFilter === 'expiring') {
        if (!item.expiry_date) return false;
        const expiry = new Date(item.expiry_date);
        const diffDays = Math.ceil((expiry.getTime() - now) / (1000 * 60 * 60 * 24));
        return diffDays <= 3;
      }
      return normalizeStorageCategory(item.category) === activeFilter;
    });

    const grouped: Record<StorageGroup, InventoryItem[]> = {
      냉장: [],
      냉동: [],
      상온: [],
      미분류: [],
    };

    for (const item of filtered) {
      grouped[normalizeStorageCategory(item.category)].push(item);
    }

    return STORAGE_GROUPS.filter(group => grouped[group].length > 0).map(group => ({
      title: group,
      data: grouped[group],
    }));
  }, [items, sortBy, activeFilter]);

  const sortOptions: { key: SortOption; label: string }[] = [
    { key: 'expiry_date', label: '유통기한' },
    { key: 'name', label: '이름' },
    { key: 'created_at', label: '최근' },
  ];

  const getItemLayout = useCallback((_: unknown, index: number) => {
    return {
      length: INVENTORY_ROW_HEIGHT,
      offset: INVENTORY_ROW_HEIGHT * index,
      index,
    };
  }, []);

  return (
    <View style={styles.container}>
      <StatusBar barStyle="dark-content" />

      <View style={styles.header}>
        <Text style={styles.title}>인벤토리</Text>
        <Text style={styles.subtitle}>{stats.total}개</Text>
      </View>

      {offlineMode ? (
        <View style={styles.offlineBanner}>
          <Text style={styles.offlineBannerText}>
            오프라인 캐시 표시 중
            {cacheTimestamp ? ` / 기준: ${new Date(cacheTimestamp).toLocaleString()}` : ''}
          </Text>
        </View>
      ) : null}

      <View style={styles.statsContainer}>
        <View style={styles.statCard}>
          <Text style={styles.statValue}>{stats.total}</Text>
          <Text style={styles.statLabel}>전체</Text>
        </View>
        <View style={[styles.statCard, stats.expiringSoon > 0 && styles.warningCard]}>
          <Text style={[styles.statValue, stats.expiringSoon > 0 && styles.warningText]}>{stats.expiringSoon}</Text>
          <Text style={styles.statLabel}>임박</Text>
        </View>
        <View style={[styles.statCard, stats.expired > 0 && styles.dangerCard]}>
          <Text style={[styles.statValue, stats.expired > 0 && styles.dangerText]}>{stats.expired}</Text>
          <Text style={styles.statLabel}>만료</Text>
        </View>
      </View>

      <View style={styles.storageSummaryRow}>
        {STORAGE_GROUPS.map(group => (
          <View key={group} style={styles.storageChip}>
            <Text style={styles.storageChipText}>{group}</Text>
            <Text style={styles.storageChipCount}>{storageCounts[group]}</Text>
          </View>
        ))}
      </View>

      <View style={styles.filterRow}>
        {([
          { key: 'all', label: '전체' },
          { key: 'expiring', label: '임박/만료' },
          { key: '냉장', label: '냉장' },
          { key: '냉동', label: '냉동' },
          { key: '상온', label: '상온' },
        ] as Array<{ key: InventoryFilter; label: string }>).map(option => (
          <TouchableOpacity
            key={option.key}
            style={[styles.filterChip, activeFilter === option.key && styles.filterChipActive]}
            onPress={() => setActiveFilter(option.key)}
            accessibilityLabel={`${option.label} 필터`}
          >
            <Text style={[styles.filterChipText, activeFilter === option.key && styles.filterChipTextActive]}>
              {option.label}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      <View style={styles.sortContainer}>
        {sortOptions.map(option => (
          <TouchableOpacity
            key={option.key}
            style={[styles.sortButton, sortBy === option.key && styles.sortButtonActive]}
            onPress={() => setSortBy(option.key)}
            accessibilityLabel={`${option.label} 정렬`}
          >
            <Text style={[styles.sortButtonText, sortBy === option.key && styles.sortButtonTextActive]}>
              {option.label}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      {loading ? (
        <View style={styles.loadingWrap}>
          {[0, 1, 2, 3].map(index => (
            <View key={index} style={styles.skeletonRow} />
          ))}
        </View>
      ) : sections.length > 0 ? (
        <SectionList
          sections={sections}
          keyExtractor={item => item.id || `${item.name}-${item.created_at || ''}`}
          renderItem={({ item }) => <InventoryItemCard item={item} onEdit={openEditModal} onDelete={deleteItem} />}
          renderSectionHeader={({ section }) => (
            <View style={styles.sectionHeader}>
              <Text style={styles.sectionTitle}>{section.title}</Text>
              <Text style={styles.sectionCount}>{section.data.length}개</Text>
            </View>
          )}
          contentContainerStyle={styles.listContent}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={Colors.primary} />}
          showsVerticalScrollIndicator={false}
          stickySectionHeadersEnabled={false}
          initialNumToRender={10}
          maxToRenderPerBatch={10}
          windowSize={5}
          updateCellsBatchingPeriod={50}
          removeClippedSubviews
          getItemLayout={getItemLayout}
          onEndReachedThreshold={0.3}
          onEndReached={onLoadMore}
          ListFooterComponent={
            loadingMore ? (
              <Text style={styles.footerText}>더 불러오는 중...</Text>
            ) : hasMore ? (
              <Text style={styles.footerText}>아래로 내려 더 보기</Text>
            ) : (
              <Text style={styles.footerText}>모든 항목을 불러왔어요</Text>
            )
          }
        />
      ) : (
        <View style={styles.centered}>
          <Text style={styles.messageTitle}>{items.length === 0 ? '인벤토리가 비어 있어요' : '선택한 조건의 항목이 없어요'}</Text>
          <Text style={styles.messageText}>
            {items.length === 0 ? loadError || '스캔 탭에서 재료를 추가해보세요.' : '필터를 바꾸거나 정렬을 확인해 보세요.'}
          </Text>
          <TouchableOpacity
            style={styles.retryButton}
            onPress={() => fireAndForget(fetchInventory(true), message => setLoadError(message), '재고 로드 실패')}
            accessibilityLabel="인벤토리 다시 시도"
          >
            <Text style={styles.retryButtonText}>다시 시도</Text>
          </TouchableOpacity>
        </View>
      )}

      {undoVisible && undoItem ? (
        <View style={styles.undoBar}>
          <Text style={styles.undoText}>{undoItem.name} 항목을 삭제했어요.</Text>
          <TouchableOpacity
            style={styles.undoButton}
            onPress={() => fireAndForget(undoDelete(), () => { }, '삭제 복원 실패')}
            accessibilityLabel="삭제 실행 취소"
          >
            <Text style={styles.undoButtonText}>실행 취소</Text>
          </TouchableOpacity>
        </View>
      ) : null}

      <Modal visible={Boolean(editingItem)} transparent animationType="fade" onRequestClose={closeEditModal}>
        <View style={styles.modalOverlay}>
          <View style={styles.modalCard}>
            <Text style={styles.modalTitle}>항목 수정</Text>
            <TextInput
              style={styles.input}
              value={editName}
              onChangeText={setEditName}
              placeholder="이름"
              placeholderTextColor={Colors.gray500}
            />
            <TextInput
              style={styles.input}
              value={editQuantity}
              onChangeText={setEditQuantity}
              placeholder="수량"
              keyboardType="decimal-pad"
              placeholderTextColor={Colors.gray500}
            />
            <TextInput
              style={styles.input}
              value={editUnit}
              onChangeText={setEditUnit}
              placeholder="단위"
              placeholderTextColor={Colors.gray500}
            />

            <Text style={styles.modalSectionLabel}>보관 분류</Text>
            <View style={styles.categoryOptionsRow}>
              {STORAGE_GROUPS.map(group => (
                <TouchableOpacity
                  key={group}
                  style={[styles.categoryOption, editCategory === group && styles.categoryOptionActive]}
                  onPress={() => setEditCategory(group)}
                  accessibilityLabel={`${group} 보관 분류 선택`}
                >
                  <Text style={[styles.categoryOptionText, editCategory === group && styles.categoryOptionTextActive]}>
                    {group}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>

            <View style={styles.modalActions}>
              <TouchableOpacity style={styles.modalCancelButton} onPress={closeEditModal} accessibilityLabel="수정 취소">
                <Text style={styles.modalCancelButtonText}>취소</Text>
              </TouchableOpacity>
              <TouchableOpacity style={styles.modalSaveButton} onPress={saveEdit} accessibilityLabel="수정 저장">
                <Text style={styles.modalSaveButtonText}>저장</Text>
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
  header: { paddingHorizontal: 24, paddingTop: 60, paddingBottom: 16 },
  title: { fontSize: 28, fontWeight: '700', color: '#132018' },
  subtitle: { fontSize: 14, color: Colors.gray600, marginTop: 4 },

  statsContainer: { flexDirection: 'row', paddingHorizontal: 24, gap: 12, marginBottom: 12 },
  offlineBanner: {
    marginHorizontal: 24,
    marginBottom: 10,
    borderRadius: 10,
    backgroundColor: '#FFF4D9',
    borderWidth: 1,
    borderColor: '#F3D38C',
    paddingHorizontal: 10,
    paddingVertical: 8,
  },
  offlineBannerText: {
    color: '#8A5B00',
    fontSize: 12,
    fontWeight: '700',
  },
  statCard: {
    flex: 1,
    backgroundColor: Colors.white,
    borderRadius: 14,
    padding: 14,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#DDE6E1',
  },
  warningCard: { borderWidth: 1, borderColor: 'rgba(255, 184, 0, 0.3)' },
  dangerCard: { borderWidth: 1, borderColor: 'rgba(255, 71, 87, 0.3)' },
  statValue: { fontSize: 24, fontWeight: '700', color: '#132018' },
  warningText: { color: Colors.warning },
  dangerText: { color: Colors.danger },
  statLabel: { fontSize: 12, color: Colors.gray600, marginTop: 4 },

  storageSummaryRow: {
    flexDirection: 'row',
    paddingHorizontal: 24,
    gap: 8,
    marginBottom: 12,
  },
  storageChip: {
    flex: 1,
    paddingVertical: 8,
    borderRadius: 10,
    alignItems: 'center',
    backgroundColor: Colors.white,
    borderWidth: 1,
    borderColor: '#DDE6E1',
  },
  storageChipText: {
    color: '#22352B',
    fontSize: 12,
    fontWeight: '700',
  },
  storageChipCount: {
    marginTop: 2,
    color: Colors.gray600,
    fontSize: 12,
  },
  filterRow: {
    flexDirection: 'row',
    paddingHorizontal: 24,
    gap: 8,
    marginBottom: 10,
    flexWrap: 'wrap',
  },
  filterChip: {
    borderRadius: 999,
    backgroundColor: Colors.white,
    borderWidth: 1,
    borderColor: '#DDE6E1',
    paddingHorizontal: 10,
    paddingVertical: 6,
  },
  filterChipActive: {
    backgroundColor: Colors.primary,
    borderColor: Colors.primary,
  },
  filterChipText: {
    color: '#22352B',
    fontSize: 12,
    fontWeight: '700',
  },
  filterChipTextActive: {
    color: Colors.white,
  },

  sortContainer: { flexDirection: 'row', paddingHorizontal: 24, gap: 10, marginBottom: 8 },
  sortButton: {
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 18,
    backgroundColor: Colors.white,
    borderWidth: 1,
    borderColor: '#DDE6E1',
  },
  sortButtonActive: { backgroundColor: Colors.primary },
  sortButtonText: { color: Colors.gray700, fontSize: 13, fontWeight: '600' },
  sortButtonTextActive: { color: Colors.white },

  listContent: { paddingHorizontal: 24, paddingBottom: 100 },
  sectionHeader: {
    marginTop: 6,
    marginBottom: 8,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  sectionTitle: {
    color: '#132018',
    fontWeight: '800',
    fontSize: 16,
  },
  sectionCount: {
    color: Colors.gray600,
    fontSize: 12,
    fontWeight: '700',
  },

  loadingWrap: { paddingHorizontal: 24, gap: 12 },
  skeletonRow: {
    height: 84,
    borderRadius: 16,
    backgroundColor: '#E8EFEC',
    borderWidth: 1,
    borderColor: '#DDE6E1',
  },
  centered: { flex: 1, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 24 },
  messageTitle: { color: '#132018', fontSize: 20, fontWeight: '700', marginBottom: 8 },
  messageText: { color: Colors.gray600, textAlign: 'center' },
  retryButton: {
    marginTop: 14,
    backgroundColor: Colors.primary,
    borderRadius: 10,
    paddingHorizontal: 16,
    paddingVertical: 10,
  },
  retryButtonText: { color: Colors.white, fontWeight: '700' },
  footerText: { textAlign: 'center', color: Colors.gray600, marginVertical: 14 },
  undoBar: {
    position: 'absolute',
    left: 16,
    right: 16,
    bottom: 104,
    borderRadius: 12,
    backgroundColor: '#1E2E24',
    paddingHorizontal: 14,
    paddingVertical: 10,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: 8,
  },
  undoText: {
    color: Colors.white,
    flex: 1,
    fontSize: 12,
  },
  undoButton: {
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 8,
    backgroundColor: 'rgba(255,255,255,0.16)',
  },
  undoButtonText: {
    color: '#D6FFEA',
    fontWeight: '700',
    fontSize: 12,
  },

  modalOverlay: {
    flex: 1,
    justifyContent: 'center',
    padding: 24,
    backgroundColor: 'rgba(17, 33, 24, 0.34)',
  },
  modalCard: {
    borderRadius: 14,
    backgroundColor: Colors.white,
    padding: 16,
    borderWidth: 1,
    borderColor: '#DDE6E1',
  },
  modalTitle: { color: '#132018', fontSize: 18, fontWeight: '700', marginBottom: 12 },
  input: {
    height: 42,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: '#DDE6E1',
    color: '#132018',
    paddingHorizontal: 12,
    marginBottom: 10,
    backgroundColor: '#F9FBFA',
  },
  modalSectionLabel: {
    color: Colors.gray700,
    fontSize: 12,
    fontWeight: '700',
    marginBottom: 6,
    marginTop: 2,
  },
  categoryOptionsRow: {
    flexDirection: 'row',
    gap: 8,
    marginBottom: 10,
  },
  categoryOption: {
    flex: 1,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: '#DDE6E1',
    backgroundColor: '#F9FBFA',
    paddingVertical: 8,
    alignItems: 'center',
  },
  categoryOptionActive: {
    backgroundColor: '#E8F8F2',
    borderColor: Colors.primary,
  },
  categoryOptionText: {
    color: Colors.gray700,
    fontSize: 12,
    fontWeight: '700',
  },
  categoryOptionTextActive: {
    color: Colors.primaryDark,
  },
  modalActions: { flexDirection: 'row', gap: 10, marginTop: 4 },
  modalCancelButton: {
    flex: 1,
    borderRadius: 10,
    paddingVertical: 11,
    alignItems: 'center',
    backgroundColor: '#E8EFEC',
  },
  modalCancelButtonText: { color: '#22352B', fontWeight: '700' },
  modalSaveButton: {
    flex: 1,
    borderRadius: 10,
    paddingVertical: 11,
    alignItems: 'center',
    backgroundColor: Colors.primary,
  },
  modalSaveButtonText: { color: Colors.white, fontWeight: '700' },
});








