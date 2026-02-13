import React, { useEffect, useMemo, useRef } from 'react';
import { Animated, StyleProp, StyleSheet, View, ViewStyle } from 'react-native';

import Colors from '@/constants/Colors';
import { GlassCard } from '@/components/GlassCard';

type SkeletonCardProps = {
  count?: number;
  height?: number;
  style?: StyleProp<ViewStyle>;
};

export function SkeletonCard({ count = 5, height = 92, style }: SkeletonCardProps) {
  const shimmer = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    const loop = Animated.loop(
      Animated.timing(shimmer, {
        toValue: 1,
        duration: 1100,
        useNativeDriver: true,
      })
    );
    loop.start();
    return () => {
      loop.stop();
      shimmer.setValue(0);
    };
  }, [shimmer]);

  const translateX = shimmer.interpolate({
    inputRange: [0, 1],
    outputRange: [-280, 280],
  });

  const items = useMemo(() => Array.from({ length: count }, (_, index) => index), [count]);

  return (
    <View style={styles.wrap}>
      {items.map(index => (
        <GlassCard key={index} style={[styles.card, { height }, style]} intensity={20} tint="light">
          <View style={styles.base} />
          <Animated.View
            style={[
              styles.shimmer,
              {
                transform: [{ translateX }],
              },
            ]}
          />
        </GlassCard>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    gap: 12,
  },
  card: {
    borderColor: '#DDE6E1',
    borderRadius: 16,
    overflow: 'hidden',
    backgroundColor: '#E8EFEC',
  },
  base: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: '#E8EFEC',
  },
  shimmer: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(255,255,255,0.45)',
    width: '45%',
  },
});

export default SkeletonCard;
