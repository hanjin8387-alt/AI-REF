import React, { useCallback, useState } from 'react';
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
import { CookingHistoryItem, PriceHistoryItem, StatsSummaryResponse, api } from '@/services/api';
import { fireAndForget } from '@/utils/async';

const PAGE_SIZE = 20;
const HISTORY_ITEM_HEIGHT_ESTIMATE = 140;

type StatsPeriod = 'week' | 'month' | 'all';

export default function HistoryScreen() {
  const [items, setItems] = useState<CookingHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [hasMore, setHasMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [detailItem, setDetailItem] = useState<CookingHistoryItem | null>(null);

  const [period, setPeriod] = useState<StatsPeriod>('month');
  const [statsSummary, setStatsSummary] = useState<StatsSummaryResponse | null>(null);
  const [priceHistory, setPriceHistory] = useState<PriceHistoryItem[]>([]);
  const [priceQueryInput, setPriceQueryInput] = useState('');
  const [priceQueryApplied, setPriceQueryApplied] = useState('');
  const [insightLoading, setInsightLoading] = useState(false);
  const [insightError, setInsightError] = useState<string | null>(null);

  const loadHistory = async (reset: boolean) => {
    const offset = reset ? 0 : items.length;
    const result = await api.getCookingHistory(PAGE_SIZE, offset);
    if (result.data) {
      const nextItems = Array.isArray(result.data.items) ? result.data.items : [];
      setItems(prev => (reset ? nextItems : [...prev, ...nextItems]));
      setHasMore(Boolean(result.data.has_more));
      setError(null);
    } else if (reset) {
      setItems([]);
      setError(result.error || '요리 이력을 불러오지 못했어요.');
    }
    setLoading(false);
    setRefreshing(false);
    setLoadingMore(false);
  };

  const loadInsights = async () => {
    setInsightLoading(true);
    const [statsResult, priceResult] = await Promise.all([
      api.getStatsSummary(period),
      api.getPriceHistory(priceQueryApplied || undefined, 90, 30, 0),
    ]);

    if (statsResult.data) {
      setStatsSummary(statsResult.data);
      setInsightError(null);
    } else {
      setStatsSummary(null);
      setInsightError(statsResult.error || '통계 요약을 불러오지 못했어요.');
    }

    if (priceResult.data) {
      setPriceHistory(priceResult.data.items || []);
      setInsightError(null);
    } else {
      setPriceHistory([]);
      if (!insightError) {
        setInsightError(priceResult.error || '가격 이력을 불러오지 못했어요.');
      }
    }
    setInsightLoading(false);
  };

  useFocusEffect(
    useCallback(() => {
      setLoading(true);
      fireAndForget(loadHistory(true), message => setError(message), '요리 이력 로드 실패');
      fireAndForget(loadInsights(), message => setInsightError(message), '통계 로드 실패');
    }, [period, priceQueryApplied])
  );

  const onRefresh = () => {
    setRefreshing(true);
    fireAndForget(loadHistory(true), message => setError(message), '요리 이력 새로고침 실패');
    fireAndForget(loadInsights(), message => setInsightError(message), '통계 새로고침 실패');
  };

  const onLoadMore = () => {
    if (!hasMore || loading || loadingMore || refreshing) return;
    setLoadingMore(true);
    fireAndForget(loadHistory(false), message => setError(message), '요리 이력 추가 로드 실패');
  };

  const openDetail = async (historyItem: CookingHistoryItem) => {
    setDetailItem(historyItem);
    const result = await api.getCookingHistoryDetail(historyItem.id);
    if (result.data) {
      const normalizedDeducted = Array.isArray(result.data.deducted_items) ? result.data.deducted_items : [];
      setDetailItem({ ...result.data, deducted_items: normalizedDeducted });
      return;
    }
    Alert.alert('불러오기 실패', result.error || '상세 이력을 불러오지 못했어요.');
  };

  const runPriceSearch = () => {
    setPriceQueryApplied(priceQueryInput.trim());
  };

  const wasteRatePercent = Math.round(((statsSummary?.inventory.waste_rate || 0) * 1000)) / 10;

  return (
    <View style={styles.container}>
      <StatusBar barStyle="dark-content" />

      <View style={styles.header}>
        <Text style={styles.title}>요리 이력</Text>
        <Text style={styles.subtitle}>이전에 요리한 기록과 소비 통계를 확인하세요</Text>
      </View>

      <View style={styles.insightCard}>
        <View style={styles.periodRow}>
          {([
            { key: 'week', label: '1주' },
            { key: 'month', label: '1개월' },
            { key: 'all', label: '전체' },
          ] as Array<{ key: StatsPeriod; label: string }>).map(option => (
            <TouchableOpacity
              key={option.key}
              style={[styles.periodButton, period === option.key && styles.periodButtonActive]}
              onPress={() => setPeriod(option.key)}
              accessibilityLabel={`${option.label} 기간 보기`}
            >
              <Text style={[styles.periodButtonText, period === option.key && styles.periodButtonTextActive]}>
                {option.label}
              </Text>
            </TouchableOpacity>
          ))}
        </View>

        <View style={styles.summaryRow}>
          <View style={styles.summaryItem}>
            <Text style={styles.summaryValue}>{statsSummary?.cooking.total_cooked ?? 0}</Text>
            <Text style={styles.summaryLabel}>요리 횟수</Text>
          </View>
          <View style={styles.summaryItem}>
            <Text style={styles.summaryValue}>{wasteRatePercent}%</Text>
            <Text style={styles.summaryLabel}>폐기율</Text>
          </View>
          <View style={styles.summaryItem}>
            <Text style={styles.summaryValue}>{statsSummary?.shopping.total_purchased ?? 0}</Text>
            <Text style={styles.summaryLabel}>구매 완료</Text>
          </View>
        </View>

        <Text style={styles.insightMeta}>
          {statsSummary?.inventory.most_used_ingredient
            ? `가장 자주 사용한 재료: ${statsSummary.inventory.most_used_ingredient}`
            : '아직 충분한 통계 데이터가 없어요.'}
        </Text>

        <View style={styles.priceSearchRow}>
          <TextInput
            value={priceQueryInput}
            onChangeText={setPriceQueryInput}
            placeholder="가격 이력 검색 (예: 우유)"
            placeholderTextColor={Colors.gray500}
            style={styles.priceSearchInput}
          />
          <TouchableOpacity style={styles.priceSearchButton} onPress={runPriceSearch} accessibilityLabel="가격 이력 조회">
            <Text style={styles.priceSearchButtonText}>조회</Text>
          </TouchableOpacity>
        </View>

        {insightLoading ? (
          <Text style={styles.loadingText}>통계를 불러오는 중...</Text>
        ) : priceHistory.length > 0 ? (
          <View style={styles.priceList}>
            {priceHistory.slice(0, 5).map(item => (
              <View key={item.id} style={styles.priceRow}>
                <Text style={styles.priceItemName}>{item.item_name}</Text>
                <Text style={styles.priceItemValue}>
                  {Math.round(item.unit_price).toLocaleString()} {item.currency || 'KRW'}
                </Text>
              </View>
            ))}
          </View>
        ) : (
          <Text style={styles.loadingText}>{insightError || '최근 가격 이력이 없어요.'}</Text>
        )}
      </View>

      {loading ? (
        <View style={styles.loadingWrap}>
          {[0, 1, 2].map(index => (
            <View key={index} style={styles.skeletonCard} />
          ))}
        </View>
      ) : items.length === 0 ? (
        <View style={styles.centered}>
          <Text style={styles.message}>{error || '아직 요리 이력이 없어요.'}</Text>
          <TouchableOpacity
            style={styles.retryButton}
            onPress={() => fireAndForget(loadHistory(true), message => setError(message), '요리 이력 로드 실패')}
            accessibilityLabel="요리 이력 다시 시도"
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
          getItemLayout={(_, index) => ({
            length: HISTORY_ITEM_HEIGHT_ESTIMATE,
            offset: HISTORY_ITEM_HEIGHT_ESTIMATE * index,
            index,
          })}
          initialNumToRender={8}
          maxToRenderPerBatch={8}
          windowSize={9}
          updateCellsBatchingPeriod={50}
          removeClippedSubviews
          onEndReachedThreshold={0.3}
          onEndReached={onLoadMore}
          renderItem={({ item }) => (
            <TouchableOpacity
              style={styles.card}
              onPress={() => fireAndForget(
                  openDetail(item),
                  message => Alert.alert('불러오기 실패', message),
                  '요리 이력 상세 로드 실패'
                )
              }
              accessibilityLabel={`${item.recipe_title} 이력 상세 보기`}
            >
              {(() => {
                const deductedItems = Array.isArray(item.deducted_items) ? item.deducted_items : [];
                return (
                  <>
                    <Text style={styles.recipeTitle}>{item.recipe_title}</Text>
                    <Text style={styles.metaText}>
                      인분: {item.servings} / {new Date(item.cooked_at).toLocaleString()}
                    </Text>
                    {deductedItems.slice(0, 3).map((deducted, idx) => (
                      <Text key={`${item.id}-${idx}`} style={styles.deductedText}>
                        - {deducted.name}: -{Math.round(deducted.deducted * 100) / 100}
                      </Text>
                    ))}
                    {deductedItems.length > 3 && (
                      <Text style={styles.moreText}>+{deductedItems.length - 3}개 더 있음</Text>
                    )}
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
              <Text style={styles.footerText}>모든 기록을 불러왔어요</Text>
            )
          }
        />
      )}

      <Modal visible={Boolean(detailItem)} transparent animationType="fade" onRequestClose={() => setDetailItem(null)}>
        <View style={styles.modalOverlay}>
          <View style={styles.modalCard}>
            {detailItem && (
              <>
                {(() => {
                  const deductedItems = Array.isArray(detailItem.deducted_items) ? detailItem.deducted_items : [];
                  return (
                    <>
                      <Text style={styles.modalTitle}>{detailItem.recipe_title}</Text>
                      <Text style={styles.modalMeta}>인분: {detailItem.servings}</Text>
                      <Text style={styles.modalMeta}>요리 시각: {new Date(detailItem.cooked_at).toLocaleString()}</Text>
                      <Text style={styles.modalSection}>사용한 재료</Text>
                      {deductedItems.length > 0 ? (
                        deductedItems.map((deducted, idx) => (
                          <Text key={`${detailItem.id}-${idx}`} style={styles.modalLine}>
                            - {deducted.name}: 사용 {Math.round(deducted.deducted * 100) / 100}, 남음{' '}
                            {Math.round(deducted.remaining * 100) / 100}
                            {deducted.deleted ? ' (인벤토리에서 삭제됨)' : ''}
                          </Text>
                        ))
                      ) : (
                        <Text style={styles.modalLine}>차감된 인벤토리 항목이 없어요.</Text>
                      )}
                      <TouchableOpacity style={styles.modalCloseButton} onPress={() => setDetailItem(null)} accessibilityLabel="요리 이력 상세 닫기">
                        <Text style={styles.modalCloseText}>닫기</Text>
                      </TouchableOpacity>
                    </>
                  );
                })()}
              </>
            )}
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
  insightCard: {
    marginHorizontal: 24,
    marginBottom: 12,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: '#DDE6E1',
    backgroundColor: '#F9FBFA',
    padding: 12,
  },
  periodRow: {
    flexDirection: 'row',
    gap: 8,
    marginBottom: 10,
  },
  periodButton: {
    flex: 1,
    borderRadius: 999,
    borderWidth: 1,
    borderColor: '#DDE6E1',
    backgroundColor: Colors.white,
    alignItems: 'center',
    paddingVertical: 7,
  },
  periodButtonActive: {
    backgroundColor: Colors.primary,
    borderColor: Colors.primary,
  },
  periodButtonText: { color: '#22352B', fontWeight: '700', fontSize: 12 },
  periodButtonTextActive: { color: Colors.white },
  summaryRow: {
    flexDirection: 'row',
    gap: 8,
  },
  summaryItem: {
    flex: 1,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: '#DDE6E1',
    backgroundColor: Colors.white,
    alignItems: 'center',
    paddingVertical: 10,
  },
  summaryValue: { color: '#132018', fontWeight: '800', fontSize: 18 },
  summaryLabel: { color: Colors.gray600, fontSize: 11, marginTop: 2 },
  insightMeta: { marginTop: 8, color: Colors.gray700, fontSize: 12 },
  priceSearchRow: { marginTop: 10, flexDirection: 'row', gap: 8 },
  priceSearchInput: {
    flex: 1,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: '#DDE6E1',
    backgroundColor: Colors.white,
    color: '#132018',
    paddingHorizontal: 10,
    paddingVertical: 8,
  },
  priceSearchButton: {
    borderRadius: 10,
    backgroundColor: Colors.primary,
    justifyContent: 'center',
    paddingHorizontal: 12,
  },
  priceSearchButtonText: { color: Colors.white, fontWeight: '700', fontSize: 12 },
  priceList: { marginTop: 10, gap: 6 },
  priceRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    borderRadius: 8,
    backgroundColor: Colors.white,
    borderWidth: 1,
    borderColor: '#DDE6E1',
    paddingHorizontal: 10,
    paddingVertical: 8,
  },
  priceItemName: { color: '#132018', fontWeight: '600' },
  priceItemValue: { color: Colors.primaryDark, fontWeight: '700' },
  loadingText: { marginTop: 8, color: Colors.gray600, fontSize: 12 },
  loadingWrap: { paddingHorizontal: 24, gap: 12 },
  skeletonCard: {
    height: 128,
    borderRadius: 14,
    backgroundColor: '#E8EFEC',
    borderWidth: 1,
    borderColor: '#DDE6E1',
  },
  centered: { flex: 1, justifyContent: 'center', alignItems: 'center', paddingHorizontal: 24 },
  message: { color: Colors.gray600, textAlign: 'center' },
  retryButton: {
    marginTop: 12,
    backgroundColor: Colors.primary,
    borderRadius: 10,
    paddingHorizontal: 16,
    paddingVertical: 10,
  },
  retryText: { color: Colors.white, fontWeight: '700' },
  listContent: { paddingHorizontal: 24, paddingBottom: 100, gap: 12 },
  card: {
    backgroundColor: Colors.white,
    borderRadius: 14,
    padding: 14,
    marginBottom: 10,
    borderWidth: 1,
    borderColor: '#DDE6E1',
  },
  recipeTitle: { color: '#132018', fontWeight: '700', fontSize: 16 },
  metaText: { color: Colors.gray600, fontSize: 12, marginTop: 4, marginBottom: 8 },
  deductedText: { color: Colors.gray700, fontSize: 13, marginBottom: 3 },
  moreText: { color: Colors.gray600, marginTop: 4, fontSize: 12 },
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
  modalTitle: {
    color: '#132018',
    fontSize: 19,
    fontWeight: '700',
    marginBottom: 8,
  },
  modalMeta: {
    color: Colors.gray700,
    fontSize: 13,
    marginBottom: 2,
  },
  modalSection: {
    marginTop: 10,
    marginBottom: 6,
    color: Colors.primaryDark,
    fontWeight: '700',
  },
  modalLine: {
    color: '#22352B',
    fontSize: 13,
    marginBottom: 4,
  },
  modalCloseButton: {
    marginTop: 14,
    borderRadius: 10,
    backgroundColor: Colors.primary,
    paddingVertical: 10,
    alignItems: 'center',
  },
  modalCloseText: {
    color: Colors.white,
    fontWeight: '700',
  },
});


