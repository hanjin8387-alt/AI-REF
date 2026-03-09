import React from 'react';
import {
    StyleSheet,
    TouchableOpacity,
    Text,
    ActivityIndicator,
    ViewStyle,
    TextStyle,
    StyleProp,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import Colors from '@/constants/Colors';

interface RoundButtonProps {
    title?: string;
    onPress: () => void;
    size?: 'small' | 'medium' | 'large' | 'xlarge';
    variant?: 'primary' | 'secondary' | 'outline' | 'danger';
    icon?: React.ReactNode;
    loading?: boolean;
    disabled?: boolean;
    style?: StyleProp<ViewStyle>;
    textStyle?: StyleProp<TextStyle>;
    accessibilityLabel?: string;
}

/**
 * Round Button Component
 * 
 * A circular or pill-shaped button with gradient background.
 * Supports icons, loading state, and multiple variants.
 */
export function RoundButton({
    title,
    onPress,
    size = 'medium',
    variant = 'primary',
    icon,
    loading = false,
    disabled = false,
    style,
    textStyle,
    accessibilityLabel,
}: RoundButtonProps) {
    const sizeStyles = sizes[size];
    const variantColors = variants[variant];

    const isIconOnly = Boolean(!title && icon);
    const hasIcon = Boolean(icon);

    return (
        <TouchableOpacity
            onPress={onPress}
            disabled={disabled || loading}
            activeOpacity={0.8}
            style={[
                styles.button,
                sizeStyles.button,
                isIconOnly && { width: sizeStyles.button.height },
                disabled && styles.disabled,
                style,
            ]}
            accessibilityRole="button"
            accessibilityLabel={accessibilityLabel ?? title ?? '버튼'}
        >
            <LinearGradient
                colors={disabled ? [Colors.gray400, Colors.gray500] : variantColors.gradient}
                start={{ x: 0, y: 0 }}
                end={{ x: 1, y: 1 }}
                style={[
                    styles.gradient,
                    isIconOnly && styles.iconOnlyGradient,
                    variant === 'outline' && styles.outlineGradient,
                ]}
            >
                {loading ? (
                    <ActivityIndicator color={variantColors.text} size="small" />
                ) : (
                    <>
                        {icon}
                        {title && (
                            <Text
                                style={[
                                    styles.text,
                                    sizeStyles.text,
                                    { color: variantColors.text },
                                    hasIcon ? styles.textWithIcon : undefined,
                                    textStyle,
                                ]}
                            >
                                {title}
                            </Text>
                        )}
                    </>
                )}
            </LinearGradient>
        </TouchableOpacity>
    );
}

const sizes = {
    small: {
        button: { height: 36, borderRadius: 18, paddingHorizontal: 16 },
        text: { fontSize: 14 },
    },
    medium: {
        button: { height: 48, borderRadius: 24, paddingHorizontal: 24 },
        text: { fontSize: 16 },
    },
    large: {
        button: { height: 56, borderRadius: 28, paddingHorizontal: 32 },
        text: { fontSize: 18 },
    },
    xlarge: {
        button: { height: 72, borderRadius: 36, paddingHorizontal: 40 },
        text: { fontSize: 20 },
    },
};

const variants = {
    primary: {
        gradient: [Colors.primary, Colors.primaryDark] as const,
        text: Colors.white,
    },
    secondary: {
        gradient: [Colors.gray600, Colors.gray700] as const,
        text: Colors.white,
    },
    outline: {
        gradient: ['transparent', 'transparent'] as const,
        text: Colors.primary,
    },
    danger: {
        gradient: [Colors.danger, '#CC3A47'] as const,
        text: Colors.white,
    },
};

const styles = StyleSheet.create({
    button: {
        overflow: 'hidden',
    },
    gradient: {
        flex: 1,
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'center',
        paddingHorizontal: 24,
    },
    iconOnlyGradient: {
        paddingHorizontal: 0,
    },
    outlineGradient: {
        borderWidth: 2,
        borderColor: Colors.primary,
    },
    text: {
        fontWeight: '600',
    },
    textWithIcon: {
        marginLeft: 8,
    },
    disabled: {
        opacity: 0.6,
    },
});

export default RoundButton;

