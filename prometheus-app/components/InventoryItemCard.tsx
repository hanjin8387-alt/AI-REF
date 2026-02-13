import React from 'react';
import { StyleSheet, Text, TouchableOpacity, View } from 'react-native';

import Colors from '@/constants/Colors';
import { InventoryItem } from '@/services/api';

type InventoryItemCardProps = {
  item: InventoryItem;
  onEdit?: (item: InventoryItem) => void;
  onDelete?: (item: InventoryItem) => void;
};

function getDaysUntilExpiry(expiryDate?: string): number | null {
  if (!expiryDate) return null;
  const expiry = new Date(expiryDate);
  if (Number.isNaN(expiry.getTime())) return null;
  const now = new Date();
  return Math.ceil((expiry.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
}

function getStatusMeta(daysUntilExpiry: number | null) {
  if (daysUntilExpiry === null) {
    return { text: '기한 없음', color: Colors.gray400 };
  }
  if (daysUntilExpiry <= 0) {
    return { text: '만료', color: Colors.danger };
  }
  if (daysUntilExpiry <= 3) {
    return { text: `D-${daysUntilExpiry}`, color: Colors.warning };
  }
  return { text: `D-${daysUntilExpiry}`, color: Colors.primary };
}

function getStorageLabel(category?: string) {
  const normalized = (category || '').trim().toLowerCase();
  if (!normalized) return '미분류';
  if (normalized.includes('냉동') || normalized.includes('frozen') || normalized.includes('freezer')) return '냉동';
  if (normalized.includes('냉장') || normalized.includes('fridge') || normalized.includes('refriger')) return '냉장';
  if (normalized.includes('상온') || normalized.includes('실온') || normalized.includes('ambient') || normalized.includes('pantry')) return '상온';
  return '미분류';
}

function InventoryItemCardComponent({ item, onEdit, onDelete }: InventoryItemCardProps) {
  const daysUntilExpiry = getDaysUntilExpiry(item.expiry_date);
  const status = getStatusMeta(daysUntilExpiry);
  const storageLabel = getStorageLabel(item.category);
  const unitLabel = item.unit === 'unit' ? '개' : item.unit;

  return (
    <View style={styles.container}>
      <View style={styles.left}>
        <Text style={styles.name}>{item.name}</Text>
        <Text style={styles.quantity}>
          {item.quantity} {unitLabel}
        </Text>
        <Text style={styles.category}>보관: {storageLabel}</Text>
      </View>

      <View style={styles.right}>
        <View style={[styles.badge, { backgroundColor: `${status.color}22` }]}>
          <Text style={[styles.badgeText, { color: status.color }]}>{status.text}</Text>
        </View>
        <View style={styles.actions}>
          <TouchableOpacity
            style={styles.actionButton}
            onPress={() => onEdit?.(item)}
            accessibilityRole="button"
            accessibilityLabel={`${item.name} 수정`}
            hitSlop={8}
          >
            <Text style={styles.actionText}>수정</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.actionButton, styles.deleteButton]}
            onPress={() => onDelete?.(item)}
            accessibilityRole="button"
            accessibilityLabel={`${item.name} 삭제`}
            hitSlop={8}
          >
            <Text style={[styles.actionText, styles.deleteText]}>삭제</Text>
          </TouchableOpacity>
        </View>
      </View>
    </View>
  );
}

export const InventoryItemCard = React.memo(InventoryItemCardComponent);
InventoryItemCard.displayName = 'InventoryItemCard';

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Colors.white,
    borderRadius: 16,
    padding: 14,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: '#DDE6E1',
  },
  left: {
    flex: 1,
  },
  right: {
    alignItems: 'flex-end',
    gap: 8,
  },
  name: {
    color: '#132018',
    fontSize: 16,
    fontWeight: '700',
  },
  quantity: {
    marginTop: 4,
    color: Colors.gray600,
    fontSize: 13,
  },
  category: {
    marginTop: 2,
    color: Colors.gray500,
    fontSize: 12,
    fontWeight: '600',
  },
  badge: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 999,
  },
  badgeText: {
    fontSize: 12,
    fontWeight: '700',
  },
  actions: {
    flexDirection: 'row',
    gap: 8,
  },
  actionButton: {
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 8,
    backgroundColor: '#E8EFEC',
  },
  deleteButton: {
    backgroundColor: 'rgba(255, 71, 87, 0.1)',
  },
  actionText: {
    color: '#22352B',
    fontSize: 12,
    fontWeight: '700',
  },
  deleteText: {
    color: Colors.danger,
  },
});

export default InventoryItemCard;


