import React, { useCallback, useMemo, useState } from 'react';
import {
  Alert,
  Modal,
  ScrollView,
  StatusBar,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { useFocusEffect, useRouter } from 'expo-router';

import Colors from '@/constants/Colors';
import { RecipeCardStack } from '@/components/RecipeCardStack';
import { SkeletonCard } from '@/components/SkeletonCard';
import { ApiRecipe, InventoryItem, api } from '@/services/api';
import { fireAndForget } from '@/utils/async';

type FeedMode = 'recommended' | 'favorites';

function toDisplayUnit(unit?: string): string {
  const normalized = (unit || '').trim();
  if (!normalized || normalized.toLowerCase() === 'unit') {
    return '개';
  }
  return normalized;
}

function getDaysUntil(expiryDate?: string): number | null {
  if (!expiryDate) return null;
  const expiry = new Date(expiryDate);
  if (Number.isNaN(expiry.getTime())) return null;
  const diffMs = expiry.getTime() - Date.now();
  return Math.ceil(diffMs / (1000 * 60 * 60 * 24));
}

export default function HomeScreen() {
  const router = useRouter();
  const [feedMode, setFeedMode] = useState<FeedMode>('recommended');
  const [recipes, setRecipes] = useState<ApiRecipe[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [expiringItems, setExpiringItems] = useState<InventoryItem[]>([]);

  const [isCooking, setIsCooking] = useState(false);
  const [favoriteBusy, setFavoriteBusy] = useState(false);
  const [addingMissing, setAddingMissing] = useState(false);
  const [addingMissingToShopping, setAddingMissingToShopping] = useState(false);
  const [selectedRecipe, setSelectedRecipe] = useState<ApiRecipe | null>(null);
  const [selectedServings, setSelectedServings] = useState(1);

  const missingIngredients = useMemo(
    () => selectedRecipe?.ingredients.filter(ingredient => !ingredient.available) || [],
    [selectedRecipe]
  );

  const setRecipeFavoriteLocally = useCallback((recipeId: string, isFavorite: boolean) => {
    setRecipes(prev => {
      const updated = prev.map(recipe => (recipe.id === recipeId ? { ...recipe, is_favorite: isFavorite } : recipe));
      if (feedMode === 'favorites') {
        return updated.filter(recipe => recipe.is_favorite);
      }
      return updated;
    });
    setSelectedRecipe(prev => (prev && prev.id === recipeId ? { ...prev, is_favorite: isFavorite } : prev));
  }, [feedMode]);

  const loadFeed = useCallback(async (forceRefresh = false) => {
    if (feedMode === 'recommended') {
      return api.getRecommendations(7, forceRefresh);
    }
    return api.getFavoriteRecipes(60, 0);
  }, [feedMode]);

  const loadHomeSummary = useCallback(async () => {
    const [inventoryResult, notificationResult] = await Promise.all([
      api.getInventory(undefined, 'expiry_date', 200, 0),
      api.getNotifications(1, 0, true),
    ]);

    if (notificationResult.data) {
      setUnreadCount(notificationResult.data.unread_count);
    }

    if (!inventoryResult.data) {
      setExpiringItems([]);
      return;
    }

    const soonest = inventoryResult.data.items
      .map(item => ({ item, days: getDaysUntil(item.expiry_date) }))
      .filter(entry => entry.days !== null && entry.days! >= 0)
      .sort((a, b) => (a.days! - b.days!))
      .slice(0, 3)
      .map(entry => entry.item);

    setExpiringItems(soonest);
  }, []);

  const refreshAll = useCallback(async (forceRefresh = false) => {
    if (!loading) setRefreshing(true);
    const [feedResult] = await Promise.all([loadFeed(forceRefresh), loadHomeSummary()]);

    if (feedResult.data) {
      setRecipes(feedResult.data.recipes);
      setLoadError(null);
    } else {
      setLoadError(feedResult.error || '레시피를 불러오지 못했어요.');
      setRecipes([]);
    }

    setLoading(false);
    setRefreshing(false);
  }, [loadFeed, loadHomeSummary, loading]);

  const prefetchAdjacentTabs = useCallback(() => {
    fireAndForget(
      Promise.all([
        api.getInventory(undefined, 'expiry_date', 30, 0),
        api.getShoppingItems('pending', 30, 0),
      ]),
      () => { },
      '인접 탭 프리페치 실패'
    );
  }, []);

  useFocusEffect(
    useCallback(() => {
      fireAndForget(refreshAll(false), message => Alert.alert('새로고침 실패', message), '홈 새로고침 실패');
      prefetchAdjacentTabs();
    }, [prefetchAdjacentTabs, refreshAll])
  );

  const openRecipeDetail = useCallback((recipe: ApiRecipe) => {
    setSelectedRecipe(recipe);
    setSelectedServings(Math.max(1, recipe.servings || 1));
    fireAndForget(
      (async () => {
        const detail = await api.getRecipe(recipe.id);
        if (detail.data) {
          setSelectedRecipe(detail.data);
        }
      })(),
      () => { },
      '레시피 상세 로드 실패'
    );
  }, []);

  const closeRecipeDetail = useCallback(() => {
    setSelectedRecipe(null);
    setSelectedServings(1);
  }, []);

  const cookRecipe = useCallback(async (recipe: ApiRecipe, servings = 1) => {
    if (isCooking) return;
    setIsCooking(true);
    try {
      const result = await api.completeCooking(recipe.id, servings);
      if (result.data?.success) {
        Alert.alert('요리가 완료되었어요', result.data.message);
        closeRecipeDetail();
        await refreshAll(true);
      } else {
        Alert.alert('요리 실패', result.error || '알 수 없는 오류가 발생했어요.');
      }
    } finally {
      setIsCooking(false);
    }
  }, [closeRecipeDetail, isCooking, refreshAll]);

  const toggleFavorite = useCallback(async (recipe: ApiRecipe) => {
    if (favoriteBusy) return;
    setFavoriteBusy(true);
    try {
      if (recipe.is_favorite) {
        const result = await api.removeFavoriteRecipe(recipe.id);
        if (result.data?.success) {
          setRecipeFavoriteLocally(recipe.id, false);
        } else {
          Alert.alert('즐겨찾기 변경 실패', result.error || '즐겨찾기 해제에 실패했어요.');
        }
      } else {
        const result = await api.addFavoriteRecipe(recipe);
        if (result.data?.success) {
          setRecipeFavoriteLocally(recipe.id, true);
        } else {
          Alert.alert('즐겨찾기 변경 실패', result.error || '즐겨찾기 추가에 실패했어요.');
        }
      }
    } finally {
      setFavoriteBusy(false);
    }
  }, [favoriteBusy, setRecipeFavoriteLocally]);

  const addMissingIngredients = useCallback(async () => {
    if (!selectedRecipe || !missingIngredients.length || addingMissing) return;
    setAddingMissing(true);
    try {
      const baseServings = selectedRecipe.servings > 0 ? selectedRecipe.servings : 1;
      const multiplier = selectedServings / baseServings;
      const items = missingIngredients.map(ingredient => ({
        name: ingredient.name,
        quantity: Math.max(ingredient.quantity * multiplier, 0.01),
        unit: ingredient.unit || '개',
      }));
      const result = await api.bulkAddInventory(items);
      if (result.data?.success) {
        Alert.alert('추가 완료', `부족한 재료 ${items.length}개를 인벤토리에 추가했어요.`);
        await refreshAll(true);
      } else {
        Alert.alert('추가 실패', result.error || '부족한 재료를 추가하지 못했어요.');
      }
    } finally {
      setAddingMissing(false);
    }
  }, [addingMissing, missingIngredients, refreshAll, selectedRecipe, selectedServings]);

  const addMissingIngredientsToShopping = useCallback(async () => {
    if (!selectedRecipe || !missingIngredients.length || addingMissingToShopping) return;
    setAddingMissingToShopping(true);
    try {
      const baseServings = selectedRecipe.servings > 0 ? selectedRecipe.servings : 1;
      const multiplier = selectedServings / baseServings;
      const ingredients = missingIngredients.map(ingredient => ({
        name: ingredient.name,
        quantity: Math.max(ingredient.quantity * multiplier, 0.01),
        unit: ingredient.unit || '개',
      }));

      const result = await api.addShoppingFromRecipe(
        selectedRecipe.id,
        selectedRecipe.title,
        selectedServings,
        ingredients
      );

      if (result.data?.success) {
        Alert.alert('추가 완료', `부족한 재료 ${ingredients.length}개를 장보기 목록에 추가했어요.`);
      } else {
        Alert.alert('추가 실패', result.error || '장보기 목록에 추가하지 못했어요.');
      }
    } finally {
      setAddingMissingToShopping(false);
    }
  }, [addingMissingToShopping, missingIngredients, selectedRecipe, selectedServings]);

  const openAlerts = useCallback(() => {
    router.push('/(tabs)/alerts');
  }, [router]);

  const openInventory = useCallback(() => {
    router.push('/(tabs)/inventory');
  }, [router]);

  const setRecommendedMode = useCallback(() => {
    setFeedMode('recommended');
  }, []);

  const setFavoritesMode = useCallback(() => {
    setFeedMode('favorites');
  }, []);

  const handleSwipeCook = useCallback((recipe: ApiRecipe) => {
    fireAndForget(cookRecipe(recipe, 1), message => Alert.alert('요리 실패', message), '요리 처리 실패');
  }, [cookRecipe]);

  const retryRecipes = useCallback(() => {
    setLoading(true);
    fireAndForget(refreshAll(true), message => Alert.alert('새로고침 실패', message), '홈 새로고침 실패');
  }, [refreshAll]);

  const refreshHome = useCallback(() => {
    fireAndForget(refreshAll(true), message => Alert.alert('새로고침 실패', message), '홈 새로고침 실패');
  }, [refreshAll]);

  const toggleFavoriteForSelected = useCallback(() => {
    if (!selectedRecipe) return;
    fireAndForget(toggleFavorite(selectedRecipe), message => Alert.alert('즐겨찾기 변경 실패', message), '즐겨찾기 변경 실패');
  }, [selectedRecipe, toggleFavorite]);

  const addMissingToInventory = useCallback(() => {
    fireAndForget(addMissingIngredients(), message => Alert.alert('추가 실패', message), '부족 재료 추가 실패');
  }, [addMissingIngredients]);

  const addMissingToShopping = useCallback(() => {
    fireAndForget(addMissingIngredientsToShopping(), message => Alert.alert('추가 실패', message), '장보기 추가 실패');
  }, [addMissingIngredientsToShopping]);

  const decreaseServings = useCallback(() => {
    setSelectedServings(prev => Math.max(1, prev - 1));
  }, []);

  const increaseServings = useCallback(() => {
    setSelectedServings(prev => prev + 1);
  }, []);

  const cookSelectedRecipe = useCallback(() => {
    if (!selectedRecipe) return;
    fireAndForget(cookRecipe(selectedRecipe, selectedServings), message => Alert.alert('요리 실패', message), '요리 처리 실패');
  }, [cookRecipe, selectedRecipe, selectedServings]);

  return (
    <View style={styles.container}>
      <StatusBar barStyle="dark-content" />

      <View style={styles.header}>
        <View>
          <Text style={styles.greeting}>오늘의 키친</Text>
          <Text style={styles.title}>무엇을 요리할까요?</Text>
        </View>
        <TouchableOpacity
          style={styles.alertButton}
          onPress={openAlerts}
          accessibilityRole="button"
          accessibilityLabel="알림 화면으로 이동"
          hitSlop={10}
        >
          <Text style={styles.alertButtonText}>알림 {unreadCount > 0 ? `(${unreadCount})` : ''}</Text>
        </TouchableOpacity>
      </View>

      {expiringItems.length > 0 ? (
        <View style={styles.expiringWrap}>
          <LinearGradient
            colors={['rgba(255, 184, 0, 0.16)', 'rgba(255, 184, 0, 0.06)']}
            start={{ x: 0, y: 0 }}
            end={{ x: 1, y: 0 }}
            style={styles.expiringCard}
          >
            <Text style={styles.expiringTitle}>오늘 먼저 써야 할 재료 TOP 3</Text>
            {expiringItems.map(item => {
              const dday = getDaysUntil(item.expiry_date);
              return (
                <Text key={item.id} style={styles.expiringItemText}>
                  - {item.name} ({dday === 0 ? 'D-day' : `D-${dday}`})
                </Text>
              );
            })}
            <TouchableOpacity
              style={styles.expiringAction}
              onPress={openInventory}
              accessibilityLabel="인벤토리에서 임박 재료 확인"
            >
              <Text style={styles.expiringActionText}>인벤토리에서 확인</Text>
            </TouchableOpacity>
          </LinearGradient>
        </View>
      ) : null}

      <View style={styles.feedToggle}>
        <TouchableOpacity
          style={[styles.feedButton, feedMode === 'recommended' && styles.feedButtonActive]}
          onPress={setRecommendedMode}
          accessibilityRole="button"
          accessibilityLabel="추천 레시피 보기"
        >
          <Text style={[styles.feedButtonText, feedMode === 'recommended' && styles.feedButtonTextActive]}>추천</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.feedButton, feedMode === 'favorites' && styles.feedButtonActive]}
          onPress={setFavoritesMode}
          accessibilityRole="button"
          accessibilityLabel="즐겨찾기 레시피 보기"
        >
          <Text style={[styles.feedButtonText, feedMode === 'favorites' && styles.feedButtonTextActive]}>즐겨찾기</Text>
        </TouchableOpacity>
      </View>

      <View style={styles.cardContainer}>
        {loading ? (
          <View style={styles.loadingWrap}>
            <SkeletonCard count={3} height={156} />
          </View>
        ) : recipes.length > 0 ? (
          <RecipeCardStack
            recipes={recipes}
            onCardPress={openRecipeDetail}
            onSwipeRight={handleSwipeCook}
          />
        ) : (
          <View style={styles.centered}>
            <Text style={styles.emptyTitle}>{feedMode === 'favorites' ? '즐겨찾기 레시피가 없어요' : '레시피가 없어요'}</Text>
            <Text style={styles.emptyText}>{loadError || '재료를 스캔하면 추천 레시피를 볼 수 있어요.'}</Text>
            <TouchableOpacity
              style={styles.retryButton}
              onPress={retryRecipes}
              accessibilityLabel="홈 레시피 다시 시도"
            >
              <Text style={styles.retryButtonText}>다시 시도</Text>
            </TouchableOpacity>
          </View>
        )}
      </View>

      <View style={styles.footerActions}>
        <TouchableOpacity
          style={styles.footerButton}
          onPress={refreshHome}
          disabled={refreshing}
          accessibilityLabel="홈 새로고침"
        >
          <Text style={styles.footerButtonText}>{refreshing ? '새로고침 중...' : '새로고침'}</Text>
        </TouchableOpacity>
      </View>

      <Modal visible={Boolean(selectedRecipe)} transparent animationType="slide" onRequestClose={closeRecipeDetail}>
        <View style={styles.modalOverlay}>
          <View style={styles.modalCard}>
            {selectedRecipe ? (
              <ScrollView showsVerticalScrollIndicator={false}>
                <View style={styles.modalHeaderRow}>
                  <Text style={styles.modalTitle}>{selectedRecipe.title}</Text>
                  <TouchableOpacity
                    style={styles.favoriteButton}
                    onPress={toggleFavoriteForSelected}
                    disabled={favoriteBusy}
                    accessibilityLabel={selectedRecipe.is_favorite ? '즐겨찾기 해제' : '즐겨찾기 추가'}
                  >
                    <Text style={styles.favoriteButtonText}>{selectedRecipe.is_favorite ? '즐겨찾기 해제' : '즐겨찾기'}</Text>
                  </TouchableOpacity>
                </View>
                <Text style={styles.modalDesc}>{selectedRecipe.description}</Text>
                {selectedRecipe.recommendation_reason ? (
                  <View style={styles.reasonBox}>
                    <Text style={styles.reasonTitle}>추천 이유</Text>
                    <Text style={styles.reasonText}>{selectedRecipe.recommendation_reason}</Text>
                  </View>
                ) : null}

                <Text style={styles.sectionTitle}>재료</Text>
                {selectedRecipe.ingredients.map((ingredient, idx) => (
                  <Text key={`${ingredient.name}-${idx}`} style={[styles.listText, !ingredient.available && styles.missingIngredientText]}>
                    - {ingredient.name} {ingredient.quantity}
                    {toDisplayUnit(ingredient.unit)} {ingredient.available ? '(있음)' : '(부족)'}
                  </Text>
                ))}

                {missingIngredients.length > 0 ? (
                  <>
                    <TouchableOpacity
                      style={styles.addMissingButton}
                      onPress={addMissingToInventory}
                      disabled={addingMissing}
                      accessibilityLabel={`부족한 재료 ${missingIngredients.length}개 인벤토리에 추가`}
                    >
                      <Text style={styles.addMissingButtonText}>
                        {addingMissing ? '추가 중...' : `부족한 재료 ${missingIngredients.length}개 인벤토리 추가`}
                      </Text>
                    </TouchableOpacity>
                    <TouchableOpacity
                      style={styles.addShoppingButton}
                      onPress={addMissingToShopping}
                      disabled={addingMissingToShopping}
                      accessibilityLabel={`부족한 재료 ${missingIngredients.length}개 장보기에 추가`}
                    >
                      <Text style={styles.addShoppingButtonText}>
                        {addingMissingToShopping ? '추가 중...' : `부족한 재료 ${missingIngredients.length}개 장보기 추가`}
                      </Text>
                    </TouchableOpacity>
                  </>
                ) : null}

                <Text style={styles.sectionTitle}>조리 순서</Text>
                {selectedRecipe.instructions.map((step, idx) => (
                  <Text key={`${idx}-${step}`} style={styles.listText}>
                    {idx + 1}. {step}
                  </Text>
                ))}

                <View style={styles.servingsRow}>
                  <TouchableOpacity
                    style={styles.servingsButton}
                    onPress={decreaseServings}
                    accessibilityLabel="인분 감소"
                  >
                    <Text style={styles.servingsButtonText}>-</Text>
                  </TouchableOpacity>
                  <Text style={styles.servingsText}>인분: {selectedServings}</Text>
                  <TouchableOpacity
                    style={styles.servingsButton}
                    onPress={increaseServings}
                    accessibilityLabel="인분 증가"
                  >
                    <Text style={styles.servingsButtonText}>+</Text>
                  </TouchableOpacity>
                </View>

                <View style={styles.modalActions}>
                  <TouchableOpacity
                    style={styles.cancelButton}
                    onPress={closeRecipeDetail}
                    disabled={isCooking}
                    accessibilityLabel="레시피 상세 닫기"
                  >
                    <Text style={styles.cancelButtonText}>닫기</Text>
                  </TouchableOpacity>
                  <TouchableOpacity
                    style={styles.cookButton}
                    onPress={cookSelectedRecipe}
                    disabled={isCooking}
                    accessibilityLabel="선택한 인분으로 요리 시작"
                  >
                    <Text style={styles.cookButtonText}>{isCooking ? '요리 중...' : '지금 요리'}</Text>
                  </TouchableOpacity>
                </View>
              </ScrollView>
            ) : null}
          </View>
        </View>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F5F8F7' },
  header: {
    paddingTop: 58,
    paddingHorizontal: 24,
    paddingBottom: 10,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  greeting: { color: Colors.gray600, fontSize: 13, fontWeight: '600' },
  title: { color: '#132018', fontSize: 28, fontWeight: '700', marginTop: 4 },
  alertButton: {
    borderRadius: 10,
    borderWidth: 1,
    borderColor: '#DDE6E1',
    backgroundColor: Colors.white,
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  alertButtonText: { color: '#22352B', fontWeight: '700', fontSize: 12 },
  expiringWrap: { paddingHorizontal: 24, marginBottom: 12 },
  expiringCard: { borderRadius: 14, borderWidth: 1, borderColor: 'rgba(255,184,0,0.3)', padding: 12 },
  expiringTitle: { color: '#132018', fontWeight: '700', marginBottom: 8 },
  expiringItemText: { color: '#6C4A00', fontSize: 12, marginBottom: 2 },
  expiringAction: { marginTop: 8, alignSelf: 'flex-start', backgroundColor: 'rgba(255,255,255,0.7)', borderRadius: 8, paddingHorizontal: 10, paddingVertical: 6 },
  expiringActionText: { color: '#22352B', fontWeight: '700', fontSize: 12 },
  feedToggle: { flexDirection: 'row', paddingHorizontal: 24, gap: 8, marginBottom: 12 },
  feedButton: {
    flex: 1,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: '#DDE6E1',
    backgroundColor: Colors.white,
    alignItems: 'center',
    paddingVertical: 9,
  },
  feedButtonActive: { backgroundColor: Colors.primary, borderColor: Colors.primary },
  feedButtonText: { color: '#22352B', fontWeight: '700' },
  feedButtonTextActive: { color: Colors.white },
  cardContainer: { flex: 1, paddingHorizontal: 8 },
  loadingWrap: { paddingHorizontal: 16, paddingTop: 8 },
  centered: { flex: 1, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 24 },
  emptyTitle: { color: '#132018', fontSize: 18, fontWeight: '700', marginBottom: 8 },
  emptyText: { color: Colors.gray600, textAlign: 'center' },
  retryButton: { marginTop: 12, backgroundColor: Colors.primary, borderRadius: 10, paddingHorizontal: 16, paddingVertical: 10 },
  retryButtonText: { color: Colors.white, fontWeight: '700' },
  footerActions: { paddingHorizontal: 24, paddingBottom: 16, paddingTop: 8 },
  footerButton: { borderRadius: 10, alignItems: 'center', backgroundColor: '#E8EFEC', paddingVertical: 10 },
  footerButtonText: { color: '#22352B', fontWeight: '700' },
  modalOverlay: { flex: 1, backgroundColor: 'rgba(17, 33, 24, 0.34)', justifyContent: 'flex-end' },
  modalCard: {
    maxHeight: '88%',
    backgroundColor: Colors.white,
    borderTopLeftRadius: 18,
    borderTopRightRadius: 18,
    paddingHorizontal: 16,
    paddingTop: 14,
    paddingBottom: 22,
  },
  modalHeaderRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', gap: 10 },
  modalTitle: { flex: 1, color: '#132018', fontSize: 22, fontWeight: '700' },
  favoriteButton: { borderRadius: 8, borderWidth: 1, borderColor: '#DDE6E1', backgroundColor: '#F9FBFA', paddingHorizontal: 10, paddingVertical: 6 },
  favoriteButtonText: { color: '#22352B', fontWeight: '700', fontSize: 12 },
  modalDesc: { marginTop: 8, color: Colors.gray700, lineHeight: 20 },
  reasonBox: { marginTop: 10, padding: 10, borderRadius: 10, backgroundColor: '#E8F8F2' },
  reasonTitle: { color: Colors.primaryDark, fontWeight: '700', marginBottom: 4 },
  reasonText: { color: '#17402F', lineHeight: 18 },
  sectionTitle: { marginTop: 14, marginBottom: 6, color: '#132018', fontWeight: '700', fontSize: 16 },
  listText: { color: Colors.gray700, marginBottom: 4, lineHeight: 20 },
  missingIngredientText: { color: Colors.danger },
  addMissingButton: { marginTop: 10, borderRadius: 10, backgroundColor: '#E8EFEC', alignItems: 'center', paddingVertical: 10 },
  addMissingButtonText: { color: '#22352B', fontWeight: '700' },
  addShoppingButton: { marginTop: 8, borderRadius: 10, backgroundColor: '#E8F8F2', alignItems: 'center', paddingVertical: 10, borderWidth: 1, borderColor: '#A5DFC4' },
  addShoppingButtonText: { color: Colors.primaryDark, fontWeight: '700' },
  servingsRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 10, marginTop: 16 },
  servingsButton: { width: 36, height: 36, borderRadius: 18, backgroundColor: '#E8EFEC', alignItems: 'center', justifyContent: 'center' },
  servingsButtonText: { color: '#22352B', fontSize: 20, fontWeight: '700' },
  servingsText: { color: '#132018', fontWeight: '700' },
  modalActions: { flexDirection: 'row', gap: 10, marginTop: 18 },
  cancelButton: { flex: 1, borderRadius: 10, backgroundColor: '#E8EFEC', alignItems: 'center', paddingVertical: 12 },
  cancelButtonText: { color: '#22352B', fontWeight: '700' },
  cookButton: { flex: 1, borderRadius: 10, backgroundColor: Colors.primary, alignItems: 'center', paddingVertical: 12 },
  cookButtonText: { color: Colors.white, fontWeight: '700' },
});


