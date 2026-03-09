import React from 'react';
import { StyleSheet, View, ViewStyle, StyleProp } from 'react-native';
import { BlurView } from 'expo-blur';
import Colors from '@/constants/Colors';

interface GlassCardProps {
    children: React.ReactNode;
    style?: StyleProp<ViewStyle>;
    intensity?: number;
    tint?: 'light' | 'dark' | 'default';
    noPadding?: boolean;
}

/**
 * Glassmorphism Card Component
 * 
 * A beautiful frosted glass effect card with blur background.
 * Works best on colorful or image backgrounds.
 */
export function GlassCard({
    children,
    style,
    intensity = 50,
    tint = 'light',
    noPadding = false,
}: GlassCardProps) {
    return (
        <View style={[styles.container, style]}>
            <BlurView intensity={intensity} tint={tint} style={styles.blur}>
                <View style={[styles.content, noPadding && styles.noPadding]}>
                    {children}
                </View>
            </BlurView>
        </View>
    );
}

const styles = StyleSheet.create({
    container: {
        borderRadius: 20,
        overflow: 'hidden',
        borderWidth: 1,
        borderColor: Colors.glassBorder,
    },
    blur: {
        width: '100%',
        height: '100%',
    },
    content: {
        padding: 16,
    },
    noPadding: {
        padding: 0,
    },
});

export default GlassCard;
