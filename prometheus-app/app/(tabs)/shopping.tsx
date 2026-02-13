import React, { useCallback, useMemo, useState } from 'react';
import {
  Alert,
  FlatList,
  Modal,
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
import { SkeletonCard } from '@/components/SkeletonCard';
import { ShoppingItem, ShoppingItemStatus, api } from '@/services/api';
import { fireAndForget } from '@/utils/async';
import { confirmDeleteItem } from '@/utils/confirmDelete';

const PAGE_SIZE = 30;

type FilterKey = 'pending' | 'purchased' | 'all';

const FILTER_LABELS: Record<FilterKey, string> = {
  pending: '구매 예정',
  purchased: '구매 완료',
  all: '전체',
};

function toRoundedQuantity(value: number): number {
  return Math.round(value * 100) / 100;
}

export default function ShoppingScreen() {
  const [filter, setFilter] = useState<FilterKey>('pending');
  const [items, setItems] = useState<ShoppingItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [hasMore, setHasMore] = useState(false);
  const [pendingCount, setPendingCount] = useState(0);
  const [purchasedCount, setPurchasedCount] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [storeMode, setStoreMode] = useState(false);
  const [loadingSuggestions, setLoadingSuggestions] = useState(false);
  const [applyingSuggestions, setApplyingSuggestions] = useState(false);
  const [lowStockItems, setLowStockItems] = useState<
    Array<{
      name: string;
      current_quantity: number;
      unit: string;
      predicted_days_left: number;
      recommended_quantity: number;
    }>
  >([]);

  const [showAddModal, setShowAddModal] = useState(false);
  const [newName, setNewName] = useState('');
  const [newQuantity, setNewQuantity] = useState('1');
  const [newUnit, setNewUnit] = useState('개');
  const [submitting, setSubmitting] = useState(false);

  const statusFilter: ShoppingItemStatus | undefined = useMemo(() => {
    if (filter === 'all') return undefined;
    return filter;
  }, [filter]);

  const loadShopping = async (reset: boolean) => {
    const offset = reset ? 0 : items.length;
    const result = await api.getShoppingItems(statusFilter, PAGE_SIZE, offset);
    if (result.data) {
      setItems(prev => (reset ? result.data!.items : [...prev, ...result.data!.items]));
      setHasMore(result.data.has_more);
      setPendingCount(result.data.pending_count);
      setPurchasedCount(result.data.purchased_count);
      setError(null);
    } else if (reset) {
      setItems([]);
      setError(result.error || '장보기 목록을 불러오지 못했어요.');
    }

    setLoading(false);
    setRefreshing(false);
    setLoadingMore(false);
  };

  const loadLowStockSuggestions = async () => {
    setLoadingSuggestions(true);
    try {
      const result = await api.getLowStockSuggestions(14, 7);
      if (!result.data) {
        Alert.alert('불러오기 실패', result.error || '저재고 추천을 불러오지 못했어요.');
        return;
      }
      setLowStockItems(result.data.items || []);
    } finally {
      setLoadingSuggestions(false);
    }
  };

  const addLowStockSuggestions = async () => {
    setApplyingSuggestions(true);
    try {
      const result = await api.addLowStockSuggestions(14, 7);
      if (!result.data?.success) {
        Alert.alert('추가 실패', result.error || '저재고 추천 항목을 추가하지 못했어요.');
        return;
      }

      Alert.alert('추가 완료', `${result.data.added_count}개 추가, ${result.data.updated_count}개 업데이트했어요.`);
      await loadShopping(true);
      await loadLowStockSuggestions();
    } finally {
      setApplyingSuggestions(false);
    }
  };

  useFocusEffect(
    useCallback(() => {
      setLoading(true);
      fireAndForget(loadShopping(true), message => setError(message), '장보기 목록 로드 실패');
      fireAndForget(loadLowStockSuggestions(), () => { }, '저재고 추천 로드 실패');
    }, [statusFilter])
  );

  const onRefresh = () => {
    setRefreshing(true);
    fireAndForget(loadShopping(true), message => setError(message), '장보기 새로고침 실패');
  };

  const onLoadMore = () => {
    if (!hasMore || loading || loadingMore || refreshing) return;
    setLoadingMore(true);
    fireAndForget(loadShopping(false), message => setError(message), '장보기 추가 로드 실패');
  };

  const resetAddForm = () => {
    setNewName('');
    setNewQuantity('1');
    setNewUnit('개');
  };

  const addManualItem = async () => {
    if (submitting) return;
    const name = newName.trim();
    const quantity = Number(newQuantity);
    const unit = newUnit.trim() || '개';

    if (!name) {
      Alert.alert('입력 오류', '항목 이름을 입력해 주세요.');
      return;
    }
    if (Number.isNaN(quantity) || quantity <= 0) {
      Alert.alert('입력 오류', '수량은 0보다 커야 해요.');
      return;
    }

    setSubmitting(true);
    try {
      const result = await api.addShoppingItems([{ name, quantity, unit }], { source: 'manual' });
      if (!result.data?.success) {
        Alert.alert('추가 실패', result.error || '장보기 항목을 추가하지 못했어요.');
        return;
      }

      setShowAddModal(false);
      resetAddForm();
      await loadShopping(true);
    } finally {
      setSubmitting(false);
    }
  };

  const checkoutItems = async (ids: string[], addToInventory: boolean) => {
    const result = await api.checkoutShoppingItems(ids, addToInventory);
    if (!result.data?.success) {
      Alert.alert('처리 실패', result.error || '장보기 항목을 처리하지 못했어요.');
      return;
    }

    if (addToInventory) {
      Alert.alert(
        '처리 완료',
        `${result.data.checked_out_count}개를 구매 완료로 처리했어요. 인벤토리에 ${result.data.added_count}개 추가, ${result.data.updated_count}개 업데이트했어요.`
      );
    } else {
      Alert.alert('처리 완료', `${result.data.checked_out_count}개를 구매 완료로 표시했어요.`);
    }

    await loadShopping(true);
  };

  const updateItemQuantity = async (item: ShoppingItem, delta: number) => {
    const nextQuantity = toRoundedQuantity(Math.max(0.1, item.quantity + delta));
    const result = await api.updateShoppingItem(item.id, { quantity: nextQuantity });
    if (!result.data) {
      Alert.alert('수정 실패', result.error || '수량을 수정하지 못했어요.');
      return;
    }
    setItems(prev => prev.map(row => (row.id === item.id ? result.data! : row)));
  };

  const checkoutSingle = (item: ShoppingItem, addToInventory: boolean) => {
    fireAndForget(
      checkoutItems([item.id], addToInventory),
      message => Alert.alert('처리 실패', message),
      '장보기 처리 실패'
    );
  };

  const checkoutAllPending = () => {
    if (pendingCount <= 0) return;
    Alert.alert('전체 구매 처리', '구매 예정 항목을 모두 구매 완료로 바꾸고 인벤토리까지 반영할까요?', [
      { text: '취소', style: 'cancel' },
      {
        text: '전체 처리',
        onPress: () =>
          fireAndForget(
            checkoutItems([], true),
            message => Alert.alert('처리 실패', message),
            '전체 구매 처리 실패'
          ),
      },
    ]);
  };

  const deleteItem = (item: ShoppingItem) => {
    confirmDeleteItem(item.name, () => {
      fireAndForget(
        (async () => {
          const result = await api.deleteShoppingItem(item.id);
          if (!result.data?.success) {
            Alert.alert('삭제 실패', result.error || '항목을 삭제하지 못했어요.');
            return;
          }
          await loadShopping(true);
        })(),
        message => Alert.alert('삭제 실패', message),
        '장보기 삭제 실패'
      );
    });
  };

  const renderItem = ({ item }: { item: ShoppingItem }) => {
    const isPending = item.status === 'pending';
    const unitLabel = item.unit === 'unit' ? '개' : item.unit;
    return (
      <View style={[styles.card, !isPending && styles.cardMuted]}>
        <View style={styles.rowBetween}>
          <Text style={styles.cardTitle}>{item.name}</Text>
          <Text style={[styles.statusBadge, isPending ? styles.pendingBadge : styles.purchasedBadge]}>
            {item.status === 'pending' ? '구매 예정' : item.status === 'purchased' ? '구매 완료' : '취소'}
          </Text>
        </View>
        <Text style={styles.cardMeta}>
          {Math.round(item.quantity * 100) / 100} {unitLabel} / {item.source === 'manual' ? '직접추가' : item.source === 'recipe' ? '레시피' : '부족재료'}
        </Text>
        {item.recipe_title ? <Text style={styles.recipeMeta}>레시피: {item.recipe_title}</Text> : null}
        {isPending ? (
          <View style={styles.qtyEditorRow}>
            <TouchableOpacity
              style={styles.qtyEditorButton}
              onPress={() => fireAndForget(
                  updateItemQuantity(item, -1),
                  message => Alert.alert('수정 실패', message),
                  '장보기 수량 수정 실패'
                )
              }
              accessibilityLabel={`${item.name} 수량 감소`}
            >
              <Text style={styles.qtyEditorButtonText}>-</Text>
            </TouchableOpacity>
            <Text style={styles.qtyEditorValue}>수량 {Math.round(item.quantity * 100) / 100}</Text>
            <TouchableOpacity
              style={styles.qtyEditorButton}
              onPress={() => fireAndForget(
                  updateItemQuantity(item, 1),
                  message => Alert.alert('수정 실패', message),
                  '장보기 수량 수정 실패'
                )
              }
              accessibilityLabel={`${item.name} 수량 증가`}
            >
              <Text style={styles.qtyEditorButtonText}>+</Text>
            </TouchableOpacity>
          </View>
        ) : null}

        {isPending && (
          <View style={styles.cardActions}>
            {storeMode ? (
              <TouchableOpacity
                style={styles.storeModeCheck}
                onPress={() => checkoutSingle(item, true)}
                accessibilityLabel={`${item.name} 구매 완료 체크`}
              >
                <Text style={styles.storeModeCheckText}>구매 완료 체크</Text>
              </TouchableOpacity>
            ) : (
              <>
                <TouchableOpacity
                  style={styles.actionPrimary}
                  onPress={() => checkoutSingle(item, true)}
                  accessibilityLabel={`${item.name} 구매 후 인벤토리 반영`}
                >
                  <Text style={styles.actionPrimaryText}>구매 + 인벤토리 반영</Text>
                </TouchableOpacity>
                <TouchableOpacity
                  style={styles.actionSecondary}
                  onPress={() => checkoutSingle(item, false)}
                  accessibilityLabel={`${item.name} 구매만 처리`}
                >
                  <Text style={styles.actionSecondaryText}>구매만 처리</Text>
                </TouchableOpacity>
                <TouchableOpacity
                  style={styles.actionDanger}
                  onPress={() => deleteItem(item)}
                  accessibilityLabel={`${item.name} 장보기에서 삭제`}
                >
                  <Text style={styles.actionDangerText}>삭제</Text>
                </TouchableOpacity>
              </>
            )}
          </View>
        )}
      </View>
    );
  };

  return (
    <View style={styles.container}>
      <StatusBar barStyle="dark-content" />

      <View style={styles.header}>
        <Text style={styles.title}>장보기</Text>
        <Text style={styles.subtitle}>구매 예정 {pendingCount} / 구매 완료 {purchasedCount}</Text>
      </View>

      <View style={styles.toolbar}>
        <View style={styles.filterRow}>
          {(Object.keys(FILTER_LABELS) as FilterKey[]).map(key => (
            <TouchableOpacity
              key={key}
              style={[styles.filterButton, filter === key && styles.filterButtonActive]}
              onPress={() => setFilter(key)}
              accessibilityLabel={`${FILTER_LABELS[key]} 필터`}
            >
              <Text style={[styles.filterText, filter === key && styles.filterTextActive]}>{FILTER_LABELS[key]}</Text>
            </TouchableOpacity>
          ))}
        </View>
        <View style={styles.toolButtons}>
          <TouchableOpacity style={styles.addButton} onPress={() => setShowAddModal(true)} accessibilityLabel="장보기 항목 추가 열기">
            <Text style={styles.addButtonText}>+ 항목 추가</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.checkoutButton, pendingCount <= 0 && styles.disabledButton]}
            onPress={checkoutAllPending}
            disabled={pendingCount <= 0}
            accessibilityLabel="전체 구매 처리"
          >
            <Text style={styles.checkoutButtonText}>전체 구매 처리</Text>
          </TouchableOpacity>
        </View>
      </View>

      <View style={styles.storeModeRow}>
        <TouchableOpacity
          style={[styles.storeModeToggle, storeMode && styles.storeModeToggleActive]}
          onPress={() => setStoreMode(prev => !prev)}
          accessibilityLabel={storeMode ? '매장 모드 끄기' : '매장 모드 켜기'}
        >
          <Text style={[styles.storeModeToggleText, storeMode && styles.storeModeToggleTextActive]}>
            {storeMode ? '매장 모드 ON' : '매장 모드 OFF'}
          </Text>
        </TouchableOpacity>
        <Text style={styles.storeModeHint}>매장 모드에서는 큰 버튼으로 빠르게 체크할 수 있어요.</Text>
      </View>

      <View style={styles.suggestionPanel}>
        <View style={styles.rowBetween}>
          <Text style={styles.suggestionTitle}>AI 저재고 추천</Text>
          <TouchableOpacity
            style={styles.suggestionReload}
            onPress={loadLowStockSuggestions}
            disabled={loadingSuggestions}
            accessibilityLabel="저재고 추천 다시 계산"
          >
            <Text style={styles.suggestionReloadText}>{loadingSuggestions ? '불러오는 중...' : '다시 계산'}</Text>
          </TouchableOpacity>
        </View>
        {lowStockItems.length > 0 ? (
          <>
            {lowStockItems.slice(0, 3).map(item => (
              <Text key={item.name} style={styles.suggestionItemText}>
                - {item.name}: 약 {item.predicted_days_left}일 남음 / 권장 {item.recommended_quantity}
                {item.unit}
              </Text>
            ))}
            <TouchableOpacity
              style={[styles.suggestionApplyButton, applyingSuggestions && styles.disabledButton]}
              onPress={addLowStockSuggestions}
              disabled={applyingSuggestions}
              accessibilityLabel="추천 항목 장보기에 반영"
            >
              <Text style={styles.suggestionApplyText}>{applyingSuggestions ? '추가 중...' : '추천 항목 장보기에 반영'}</Text>
            </TouchableOpacity>
          </>
        ) : (
          <Text style={styles.suggestionEmptyText}>현재 추천할 저재고 항목이 없어요.</Text>
        )}
      </View>

      {loading ? (
        <View style={styles.loadingWrap}>
          <SkeletonCard count={5} />
        </View>
      ) : items.length === 0 ? (
        <View style={styles.centered}>
          <Text style={styles.infoTitle}>장보기 항목이 없어요</Text>
          <Text style={styles.infoText}>{error || '레시피 또는 직접 입력으로 항목을 추가해보세요.'}</Text>
        </View>
      ) : (
        <FlatList
          data={items}
          keyExtractor={item => item.id}
          renderItem={renderItem}
          contentContainerStyle={styles.listContent}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={Colors.primary} />}
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
      )}

      <Modal visible={showAddModal} transparent animationType="fade" onRequestClose={() => setShowAddModal(false)}>
        <View style={styles.modalOverlay}>
          <View style={styles.modalCard}>
            <Text style={styles.modalTitle}>장보기 항목 추가</Text>
            <TextInput
              style={styles.input}
              placeholder="이름"
              placeholderTextColor={Colors.gray500}
              value={newName}
              onChangeText={setNewName}
            />
            <TextInput
              style={styles.input}
              placeholder="수량"
              keyboardType="decimal-pad"
              placeholderTextColor={Colors.gray500}
              value={newQuantity}
              onChangeText={setNewQuantity}
            />
            <TextInput
              style={styles.input}
              placeholder="단위"
              placeholderTextColor={Colors.gray500}
              value={newUnit}
              onChangeText={setNewUnit}
            />
            <View style={styles.modalActions}>
              <TouchableOpacity
                style={styles.modalCancel}
                onPress={() => {
                  setShowAddModal(false);
                  resetAddForm();
                }}
                disabled={submitting}
                accessibilityLabel="장보기 추가 취소"
              >
                <Text style={styles.modalCancelText}>취소</Text>
              </TouchableOpacity>
              <TouchableOpacity style={styles.modalSave} onPress={addManualItem} disabled={submitting} accessibilityLabel="장보기 항목 저장">
                <Text style={styles.modalSaveText}>{submitting ? '저장 중...' : '저장'}</Text>
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
  header: { paddingTop: 60, paddingHorizontal: 24, paddingBottom: 12 },
  title: { color: '#132018', fontSize: 28, fontWeight: '700' },
  subtitle: { color: Colors.gray600, marginTop: 4 },
  toolbar: { paddingHorizontal: 24, gap: 10, marginBottom: 8 },
  filterRow: { flexDirection: 'row', gap: 8 },
  filterButton: {
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 16,
    backgroundColor: Colors.white,
    borderWidth: 1,
    borderColor: '#DDE6E1',
  },
  filterButtonActive: { backgroundColor: Colors.primary, borderColor: Colors.primary },
  filterText: { color: Colors.gray700, fontSize: 12, fontWeight: '700' },
  filterTextActive: { color: Colors.white },
  toolButtons: { flexDirection: 'row', gap: 10 },
  addButton: {
    flex: 1,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: '#DDE6E1',
    backgroundColor: Colors.white,
    alignItems: 'center',
    paddingVertical: 10,
  },
  addButtonText: { color: '#22352B', fontWeight: '700' },
  checkoutButton: {
    flex: 1,
    borderRadius: 10,
    backgroundColor: Colors.primary,
    alignItems: 'center',
    paddingVertical: 10,
  },
  checkoutButtonText: { color: Colors.white, fontWeight: '700' },
  disabledButton: { opacity: 0.4 },
  storeModeRow: { paddingHorizontal: 24, marginBottom: 8 },
  storeModeToggle: {
    borderRadius: 10,
    borderWidth: 1,
    borderColor: '#DDE6E1',
    backgroundColor: Colors.white,
    alignItems: 'center',
    paddingVertical: 9,
  },
  storeModeToggleActive: {
    backgroundColor: '#E8F8F2',
    borderColor: '#A5DFC4',
  },
  storeModeToggleText: {
    color: '#22352B',
    fontWeight: '700',
  },
  storeModeToggleTextActive: {
    color: Colors.primaryDark,
  },
  storeModeHint: {
    marginTop: 5,
    color: Colors.gray600,
    fontSize: 12,
  },
  suggestionPanel: {
    marginHorizontal: 24,
    marginBottom: 10,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#DDE6E1',
    backgroundColor: '#F9FBFA',
    padding: 10,
  },
  suggestionTitle: { color: '#132018', fontWeight: '700', fontSize: 14 },
  suggestionReload: {
    borderRadius: 8,
    backgroundColor: Colors.white,
    borderWidth: 1,
    borderColor: '#DDE6E1',
    paddingHorizontal: 10,
    paddingVertical: 6,
  },
  suggestionReloadText: { color: '#22352B', fontSize: 12, fontWeight: '700' },
  suggestionItemText: { marginTop: 6, color: Colors.gray700, fontSize: 12 },
  suggestionEmptyText: { marginTop: 6, color: Colors.gray600, fontSize: 12 },
  suggestionApplyButton: {
    marginTop: 10,
    borderRadius: 10,
    backgroundColor: Colors.primary,
    alignItems: 'center',
    paddingVertical: 9,
  },
  suggestionApplyText: { color: Colors.white, fontWeight: '700', fontSize: 12 },
  loadingWrap: { paddingHorizontal: 24, paddingTop: 8 },
  listContent: { paddingHorizontal: 24, paddingBottom: 100, gap: 10 },
  card: {
    backgroundColor: Colors.white,
    borderWidth: 1,
    borderColor: '#DDE6E1',
    borderRadius: 14,
    padding: 12,
    marginBottom: 10,
  },
  cardMuted: { opacity: 0.8 },
  rowBetween: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', gap: 8 },
  cardTitle: { color: '#132018', fontWeight: '700', fontSize: 16, flex: 1 },
  cardMeta: { color: Colors.gray700, marginTop: 4, fontSize: 12 },
  recipeMeta: { color: Colors.gray600, marginTop: 4, fontSize: 12 },
  qtyEditorRow: {
    marginTop: 10,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  qtyEditorButton: {
    width: 30,
    height: 30,
    borderRadius: 8,
    backgroundColor: '#E8EFEC',
    borderWidth: 1,
    borderColor: '#DDE6E1',
    alignItems: 'center',
    justifyContent: 'center',
  },
  qtyEditorButtonText: {
    color: '#22352B',
    fontWeight: '700',
    fontSize: 18,
  },
  qtyEditorValue: {
    color: Colors.gray700,
    fontSize: 12,
    fontWeight: '700',
  },
  statusBadge: {
    fontSize: 10,
    fontWeight: '700',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 999,
    overflow: 'hidden',
  },
  pendingBadge: {
    color: '#A96400',
    backgroundColor: 'rgba(255, 184, 0, 0.14)',
  },
  purchasedBadge: {
    color: Colors.primaryDark,
    backgroundColor: 'rgba(0, 208, 132, 0.14)',
  },
  cardActions: { flexDirection: 'row', gap: 8, marginTop: 10 },
  actionPrimary: {
    flex: 1,
    borderRadius: 8,
    backgroundColor: Colors.primary,
    alignItems: 'center',
    paddingVertical: 8,
  },
  actionPrimaryText: { color: Colors.white, fontSize: 12, fontWeight: '700' },
  actionSecondary: {
    flex: 1,
    borderRadius: 8,
    backgroundColor: '#E8EFEC',
    borderWidth: 1,
    borderColor: '#DDE6E1',
    alignItems: 'center',
    paddingVertical: 8,
  },
  actionSecondaryText: { color: '#22352B', fontSize: 12, fontWeight: '700' },
  actionDanger: {
    borderRadius: 8,
    borderWidth: 1,
    borderColor: 'rgba(255, 71, 87, 0.35)',
    backgroundColor: 'rgba(255, 71, 87, 0.1)',
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 10,
  },
  actionDangerText: { color: Colors.danger, fontSize: 12, fontWeight: '700' },
  storeModeCheck: {
    flex: 1,
    borderRadius: 10,
    backgroundColor: '#E8F8F2',
    borderWidth: 1,
    borderColor: '#A5DFC4',
    alignItems: 'center',
    paddingVertical: 10,
  },
  storeModeCheckText: {
    color: Colors.primaryDark,
    fontWeight: '800',
  },
  centered: { flex: 1, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 24 },
  infoTitle: { color: '#132018', fontSize: 20, fontWeight: '700', marginBottom: 8 },
  infoText: { color: Colors.gray600, textAlign: 'center' },
  footerText: { textAlign: 'center', color: Colors.gray600, marginVertical: 14 },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(17, 33, 24, 0.34)',
    justifyContent: 'center',
    padding: 20,
  },
  modalCard: {
    backgroundColor: Colors.white,
    borderRadius: 16,
    padding: 16,
    borderWidth: 1,
    borderColor: '#DDE6E1',
  },
  modalTitle: { color: '#132018', fontSize: 18, fontWeight: '700', marginBottom: 10 },
  input: {
    borderRadius: 10,
    borderWidth: 1,
    borderColor: '#DDE6E1',
    backgroundColor: '#F9FBFA',
    color: '#132018',
    paddingHorizontal: 12,
    paddingVertical: 10,
    marginBottom: 10,
  },
  modalActions: { flexDirection: 'row', gap: 10, marginTop: 4 },
  modalCancel: {
    flex: 1,
    borderRadius: 10,
    backgroundColor: '#E8EFEC',
    alignItems: 'center',
    paddingVertical: 10,
  },
  modalCancelText: { color: '#22352B', fontWeight: '700' },
  modalSave: {
    flex: 1,
    borderRadius: 10,
    backgroundColor: Colors.primary,
    alignItems: 'center',
    paddingVertical: 10,
  },
  modalSaveText: { color: Colors.white, fontWeight: '700' },
});


