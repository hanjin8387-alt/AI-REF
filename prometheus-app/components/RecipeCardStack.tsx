import React, { useCallback, useRef, useState } from 'react';
import { Animated, Dimensions, PanResponder, StyleSheet, Text, View } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';

import Colors from '@/constants/Colors';
import { ApiRecipe } from '@/services/api';

const { width: SCREEN_WIDTH } = Dimensions.get('window');
const CARD_WIDTH = SCREEN_WIDTH * 0.85;
const CARD_HEIGHT = CARD_WIDTH * 1.3;
const SWIPE_THRESHOLD = SCREEN_WIDTH * 0.24;

type RecipeCardStackProps = {
  recipes: ApiRecipe[];
  onSwipeLeft?: (recipe: ApiRecipe) => void;
  onSwipeRight?: (recipe: ApiRecipe) => void;
  onCardPress?: (recipe: ApiRecipe) => void;
};

type FadingRecipeImageProps = {
  imageUrl?: string;
};

function FadingRecipeImage({ imageUrl }: FadingRecipeImageProps) {
  const [failed, setFailed] = useState(false);
  const imageOpacity = useRef(new Animated.Value(imageUrl ? 0 : 1)).current;
  const placeholderOpacity = useRef(new Animated.Value(imageUrl ? 1 : 0)).current;

  const handleLoaded = useCallback(() => {
    Animated.parallel([
      Animated.timing(imageOpacity, {
        toValue: 1,
        duration: 240,
        useNativeDriver: true,
      }),
      Animated.timing(placeholderOpacity, {
        toValue: 0,
        duration: 180,
        useNativeDriver: true,
      }),
    ]).start();
  }, [imageOpacity, placeholderOpacity]);

  const handleError = useCallback(() => {
    setFailed(true);
    imageOpacity.setValue(0);
    placeholderOpacity.setValue(1);
  }, [imageOpacity, placeholderOpacity]);

  if (!imageUrl || failed) {
    return (
      <View style={styles.imageFallback}>
        <Text style={styles.imageFallbackText}>레시피</Text>
      </View>
    );
  }

  return (
    <View style={styles.imageWrap}>
      <Animated.View style={[styles.imagePlaceholder, { opacity: placeholderOpacity }]}>
        <Text style={styles.imagePlaceholderText}>이미지 로딩 중</Text>
      </Animated.View>
      <Animated.Image
        source={{ uri: imageUrl }}
        style={[styles.cardImage, { opacity: imageOpacity }]}
        onLoad={handleLoaded}
        onError={handleError}
      />
    </View>
  );
}

function toKoreanDifficulty(value: string) {
  const normalized = value.toLowerCase();
  if (normalized === 'easy') return '쉬움';
  if (normalized === 'medium') return '보통';
  if (normalized === 'hard') return '어려움';
  return value;
}

function RecipeCardStackComponent({ recipes, onSwipeLeft, onSwipeRight, onCardPress }: RecipeCardStackProps) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const position = useRef(new Animated.ValueXY()).current;
  const rotate = position.x.interpolate({
    inputRange: [-SCREEN_WIDTH / 2, 0, SCREEN_WIDTH / 2],
    outputRange: ['-14deg', '0deg', '14deg'],
    extrapolate: 'clamp',
  });

  const resetPosition = () => {
    Animated.spring(position, {
      toValue: { x: 0, y: 0 },
      useNativeDriver: false,
      tension: 90,
      friction: 10,
    }).start();
  };

  const swipeCard = (direction: 'left' | 'right') => {
    const targetX = direction === 'right' ? SCREEN_WIDTH * 1.3 : -SCREEN_WIDTH * 1.3;
    Animated.timing(position, {
      toValue: { x: targetX, y: 0 },
      duration: 220,
      useNativeDriver: false,
    }).start(() => {
      const recipe = recipes[currentIndex];
      if (!recipe) return;
      if (direction === 'right') onSwipeRight?.(recipe);
      else onSwipeLeft?.(recipe);
      position.setValue({ x: 0, y: 0 });
      setCurrentIndex(prev => prev + 1);
    });
  };

  const panResponder = PanResponder.create({
    onStartShouldSetPanResponder: () => true,
    onPanResponderMove: (_, gesture) => {
      position.setValue({ x: gesture.dx, y: gesture.dy });
    },
    onPanResponderRelease: (_, gesture) => {
      if (Math.abs(gesture.dx) < 10 && Math.abs(gesture.dy) < 10) {
        const recipe = recipes[currentIndex];
        if (recipe) onCardPress?.(recipe);
        resetPosition();
        return;
      }

      if (gesture.dx > SWIPE_THRESHOLD) {
        swipeCard('right');
      } else if (gesture.dx < -SWIPE_THRESHOLD) {
        swipeCard('left');
      } else {
        resetPosition();
      }
    },
  });

  const renderCard = (recipe: ApiRecipe, index: number) => {
    if (index < currentIndex || index > currentIndex + 2) return null;
    const isTop = index === currentIndex;

    const missingCount = recipe.ingredients.filter(ingredient => !ingredient.available).length;
    const expiringIngredients = recipe.ingredients.filter(
      ingredient => ingredient.expiry_days !== undefined && ingredient.expiry_days <= 3
    );

    const cardStyle = isTop
      ? {
          transform: [{ translateX: position.x }, { translateY: position.y }, { rotate }],
        }
      : {
          transform: [{ scale: 1 - (index - currentIndex) * 0.05 }, { translateY: (index - currentIndex) * -10 }],
          opacity: 1 - (index - currentIndex) * 0.2,
        };

    return (
      <Animated.View
        key={recipe.id}
        style={[styles.card, cardStyle]}
        accessible={isTop}
        accessibilityRole={isTop ? 'button' : undefined}
        accessibilityLabel={isTop ? `${recipe.title} 레시피 카드` : undefined}
        accessibilityHint={isTop ? '탭하여 상세를 보고, 좌우로 밀어 다음 레시피를 볼 수 있습니다.' : undefined}
        {...(isTop ? panResponder.panHandlers : {})}
      >
        <LinearGradient colors={['#FFFFFF', '#F3F7F5']} style={styles.cardGradient}>
          <FadingRecipeImage imageUrl={recipe.image_url} />

          <View style={styles.cardContent}>
            <View style={styles.badgeRow}>
              {recipe.priority_score > 0.7 && (
                <View style={styles.priorityBadge}>
                  <Text style={styles.priorityBadgeText}>추천</Text>
                </View>
              )}
              {recipe.is_favorite && (
                <View style={styles.favoriteBadge}>
                  <Text style={styles.favoriteBadgeText}>즐겨찾기</Text>
                </View>
              )}
            </View>

            <Text style={styles.title} numberOfLines={2}>
              {recipe.title}
            </Text>
            <Text style={styles.description} numberOfLines={2}>
              {recipe.description}
            </Text>
            {recipe.recommendation_reason ? (
              <Text style={styles.reasonText} numberOfLines={2}>
                추천 이유: {recipe.recommendation_reason}
              </Text>
            ) : null}

            <View style={styles.metaRow}>
              <Text style={styles.metaText}>{recipe.cooking_time_minutes}분</Text>
              <Text style={styles.metaDot}>|</Text>
              <Text style={styles.metaText}>{toKoreanDifficulty(recipe.difficulty)}</Text>
              <Text style={styles.metaDot}>|</Text>
              <Text style={styles.metaText}>{recipe.servings}인분</Text>
            </View>

            {missingCount > 0 && (
              <View style={styles.missingBadge}>
                <Text style={styles.missingBadgeText}>부족한 재료 {missingCount}개</Text>
              </View>
            )}
            {expiringIngredients.length > 0 && (
              <View style={styles.expiringBadge}>
                <Text style={styles.expiringBadgeText}>
                  먼저 사용: {expiringIngredients.slice(0, 3).map(item => item.name).join(', ')}
                </Text>
              </View>
            )}
          </View>

          <Animated.View
            style={[
              styles.swipeOverlay,
              styles.swipeLeft,
              {
                opacity: position.x.interpolate({
                  inputRange: [-SWIPE_THRESHOLD, 0],
                  outputRange: [1, 0],
                  extrapolate: 'clamp',
                }),
              },
            ]}
          >
            <Text style={styles.swipeLeftText}>건너뜀</Text>
          </Animated.View>
          <Animated.View
            style={[
              styles.swipeOverlay,
              styles.swipeRight,
              {
                opacity: position.x.interpolate({
                  inputRange: [0, SWIPE_THRESHOLD],
                  outputRange: [0, 1],
                  extrapolate: 'clamp',
                }),
              },
            ]}
          >
            <Text style={styles.swipeRightText}>요리</Text>
          </Animated.View>
        </LinearGradient>
      </Animated.View>
    );
  };

  if (currentIndex >= recipes.length) {
    return (
      <View style={styles.emptyState}>
        <Text style={styles.emptyTitle}>더 이상 레시피가 없어요</Text>
        <Text style={styles.emptyText}>재고를 변경한 뒤 새로고침해보세요.</Text>
      </View>
    );
  }

  return <View style={styles.container}>{recipes.map((recipe, index) => renderCard(recipe, index)).reverse()}</View>;
}

export const RecipeCardStack = React.memo(RecipeCardStackComponent);
RecipeCardStack.displayName = 'RecipeCardStack';

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  card: {
    position: 'absolute',
    width: CARD_WIDTH,
    height: CARD_HEIGHT,
    borderRadius: 24,
    overflow: 'hidden',
    shadowColor: '#0E1D16',
    shadowOffset: { width: 0, height: 10 },
    shadowOpacity: 0.14,
    shadowRadius: 20,
    elevation: 6,
    borderWidth: 1,
    borderColor: '#DDE6E1',
  },
  cardGradient: {
    flex: 1,
  },
  cardImage: {
    ...StyleSheet.absoluteFillObject,
  },
  imageWrap: {
    width: '100%',
    height: '50%',
    position: 'relative',
    overflow: 'hidden',
    backgroundColor: '#ECF2EF',
  },
  imagePlaceholder: {
    ...StyleSheet.absoluteFillObject,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#DDE8E2',
  },
  imagePlaceholderText: {
    color: Colors.gray600,
    fontSize: 12,
    fontWeight: '700',
    letterSpacing: 0.4,
  },
  imageFallback: {
    width: '100%',
    height: '50%',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#E8EFEC',
  },
  imageFallbackText: {
    color: Colors.gray700,
    fontWeight: '600',
    fontSize: 20,
  },
  cardContent: {
    flex: 1,
    padding: 18,
  },
  badgeRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 8,
  },
  priorityBadge: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 999,
    backgroundColor: 'rgba(0, 208, 132, 0.2)',
  },
  priorityBadgeText: {
    color: Colors.primaryDark,
    fontSize: 11,
    fontWeight: '700',
  },
  favoriteBadge: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 999,
    backgroundColor: 'rgba(255, 184, 0, 0.2)',
  },
  favoriteBadgeText: {
    color: Colors.warning,
    fontSize: 11,
    fontWeight: '700',
  },
  title: {
    color: '#132018',
    fontSize: 23,
    fontWeight: '700',
    marginBottom: 6,
  },
  description: {
    color: Colors.gray700,
    fontSize: 14,
    lineHeight: 20,
  },
  reasonText: {
    color: Colors.primaryDark,
    fontSize: 12,
    lineHeight: 18,
    marginTop: 6,
    fontWeight: '600',
  },
  metaRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginTop: 14,
  },
  metaText: {
    color: Colors.gray700,
    fontSize: 13,
    fontWeight: '600',
  },
  metaDot: {
    color: Colors.gray500,
    fontSize: 14,
  },
  missingBadge: {
    marginTop: 12,
    borderRadius: 8,
    paddingHorizontal: 10,
    paddingVertical: 6,
    backgroundColor: 'rgba(255, 71, 87, 0.14)',
  },
  missingBadgeText: {
    color: Colors.danger,
    fontSize: 12,
    fontWeight: '600',
  },
  expiringBadge: {
    marginTop: 8,
    borderRadius: 8,
    paddingHorizontal: 10,
    paddingVertical: 6,
    backgroundColor: 'rgba(255, 184, 0, 0.12)',
  },
  expiringBadgeText: {
    color: Colors.warning,
    fontSize: 12,
    fontWeight: '600',
  },
  swipeOverlay: {
    position: 'absolute',
    top: 36,
    borderWidth: 3,
    borderRadius: 10,
    paddingHorizontal: 14,
    paddingVertical: 6,
  },
  swipeLeft: {
    right: 22,
    borderColor: Colors.danger,
    transform: [{ rotate: '14deg' }],
  },
  swipeRight: {
    left: 22,
    borderColor: Colors.primary,
    transform: [{ rotate: '-14deg' }],
  },
  swipeLeftText: {
    color: Colors.danger,
    fontSize: 22,
    fontWeight: '800',
  },
  swipeRightText: {
    color: Colors.primary,
    fontSize: 22,
    fontWeight: '800',
  },
  emptyState: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 24,
  },
  emptyTitle: {
    color: '#132018',
    fontSize: 22,
    fontWeight: '700',
  },
  emptyText: {
    color: Colors.gray600,
    marginTop: 8,
  },
});

export default RecipeCardStack;
