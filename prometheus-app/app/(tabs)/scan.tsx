import React, { useEffect, useRef, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  Image,
  ScrollView,
  StatusBar,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';

import Colors from '@/constants/Colors';
import { RoundButton } from '@/components/RoundButton';
import { ScanResultPayload, ScanSourceType, api } from '@/services/api';
import {
  STORAGE_CATEGORIES,
  normalizeDisplayUnit,
  normalizeStorageCategory,
} from './storage-utils';
import type { StorageCategory } from './storage-utils';

type ScanState = 'camera' | 'preview' | 'analyzing' | 'result';
type ScanMode = 'ingredient' | 'receipt';

function toFixedQuantity(value: number): number {
  return Math.max(0.01, Math.round(value * 100) / 100);
}

function toIsoDateFromNow(days?: number): string | undefined {
  if (!days || days <= 0) return undefined;
  const date = new Date();
  date.setDate(date.getDate() + Math.round(days));
  return date.toISOString().slice(0, 10);
}

async function promptWebImage(capture: boolean): Promise<File | null> {
  if (typeof document === 'undefined') {
    throw new Error('???뚯씪 ?좏깮湲곕? ?ъ슜?????놁뼱??');
  }

  return new Promise(resolve => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'image/*';
    if (capture) {
      // Hint mobile browsers to open camera.
      (input as unknown as { capture?: string }).capture = 'environment';
    }

    input.onchange = () => {
      const file = input.files?.[0] || null;
      resolve(file);
    };

    input.click();
  });
}

export default function ScanScreen() {
  const [scanState, setScanState] = useState<ScanState>('camera');
  const [capturedImage, setCapturedImage] = useState<string | null>(null);
  const [scanResult, setScanResult] = useState<ScanResultPayload | null>(null);
  const [scanMode, setScanMode] = useState<ScanMode>('ingredient');
  const [sourceType, setSourceType] = useState<ScanSourceType>('camera');
  const [savingInventory, setSavingInventory] = useState(false);
  const [analyzeError, setAnalyzeError] = useState<string | null>(null);
  const [analyzeProgress, setAnalyzeProgress] = useState(0);
  const [analyzeProgressLabel, setAnalyzeProgressLabel] = useState('');
  const [bulkCategory, setBulkCategory] = useState<StorageCategory>('?곸삩');
  const [bulkUnit, setBulkUnit] = useState('媛?);
  const [bulkMultiplier, setBulkMultiplier] = useState('1');
  const [barcodeInput, setBarcodeInput] = useState('');
  const [barcodeLoading, setBarcodeLoading] = useState(false);
  const [barcodeProduct, setBarcodeProduct] = useState<{
    name: string;
    category?: string;
    suggested_expiry_days?: number;
    image_url?: string;
  } | null>(null);
  const [addingBarcodeItem, setAddingBarcodeItem] = useState(false);

  const objectUrlRef = useRef<string | null>(null);

  useEffect(() => {
    return () => {
      if (objectUrlRef.current) {
        try {
          URL.revokeObjectURL(objectUrlRef.current);
        } catch {
          // ignore
        }
        objectUrlRef.current = null;
      }
    };
  }, []);

  const resolveSourceType = (inputSource: 'camera' | 'gallery', mode: ScanMode): ScanSourceType => {
    if (mode === 'receipt') return 'receipt';
    return inputSource;
  };

  const setCapturedObjectUrl = (nextUri: string | null) => {
    if (objectUrlRef.current && objectUrlRef.current !== nextUri) {
      try {
        URL.revokeObjectURL(objectUrlRef.current);
      } catch {
        // ignore
      }
      objectUrlRef.current = null;
    }

    objectUrlRef.current = nextUri;
    setCapturedImage(nextUri);
  };

  const pickImage = async (capture: boolean) => {
    try {
      const file = await promptWebImage(capture);
      if (!file) return;

      const objectUrl = URL.createObjectURL(file);
      setCapturedObjectUrl(objectUrl);
      setSourceType(resolveSourceType(capture ? 'camera' : 'gallery', scanMode));
      setAnalyzeError(null);
      setScanState('preview');
    } catch (error) {
      const message = error instanceof Error ? error.message : '?대?吏瑜??좏깮?섏? 紐삵뻽?댁슂.';
      Alert.alert('?좏깮 ?ㅽ뙣', message);
    }
  };

  const pollScanResult = async (
    scanId: string,
    maxAttempts = 45,
    onProgress?: (attempt: number, total: number, status?: string) => void
  ) => {
    for (let attempt = 0; attempt < maxAttempts; attempt++) {
      const resultResponse = await api.getScanResult(scanId);
      if (resultResponse.error) {
        return { error: resultResponse.error };
      }

      const status = resultResponse.data?.status;
      if (status === 'completed' || status === 'failed') {
        return resultResponse;
      }

      onProgress?.(attempt + 1, maxAttempts, status);
      await new Promise(resolve => setTimeout(resolve, 1000));
    }

    return { error: '遺꾩꽍 ?쒓컙??湲몄뼱吏怨??덉뼱?? ?ㅼ떆 ?쒕룄??二쇱꽭??' };
  };

  const analyzeScan = async () => {
    if (!capturedImage) return;

    setScanState('analyzing');
    setAnalyzeError(null);
    setAnalyzeProgress(0.08);
    setAnalyzeProgressLabel('?대?吏瑜?以鍮꾪븯怨??덉뼱??..');

    try {
      setAnalyzeProgress(0.32);
      setAnalyzeProgressLabel('?대?吏瑜??낅줈?쒗븯怨??덉뼱??..');
      const uploadResult = await api.uploadScan(capturedImage, sourceType);
      if (uploadResult.error || !uploadResult.data) {
        const message = uploadResult.error || '?낅줈?쒖뿉 ?ㅽ뙣?덉뼱??';
        setAnalyzeProgress(0);
        setAnalyzeProgressLabel('');
        setAnalyzeError(message);
        setScanState('preview');
        Alert.alert('?ㅼ틪 ?ㅽ뙣', message);
        return;
      }

      setAnalyzeProgress(0.55);
      setAnalyzeProgressLabel('AI媛 ?대?吏瑜?遺꾩꽍?섍퀬 ?덉뼱??..');
      const resultResponse = await pollScanResult(uploadResult.data.scan_id, 45, (attempt, total, status) => {
        const normalized = Math.min(0.95, 0.55 + (attempt / total) * 0.4);
        setAnalyzeProgress(normalized);
        if (status === 'processing') {
          setAnalyzeProgressLabel('?щ즺瑜??몄떇?섍퀬 ?덉뼱??..');
        } else {
          setAnalyzeProgressLabel('寃곌낵瑜??뺣━?섍퀬 ?덉뼱??..');
        }
      });
      if (resultResponse.error || !resultResponse.data) {
        const message = resultResponse.error || '遺꾩꽍???ㅽ뙣?덉뼱??';
        setAnalyzeProgress(0);
        setAnalyzeProgressLabel('');
        setAnalyzeError(message);
        setScanState('preview');
        Alert.alert('遺꾩꽍 ?ㅽ뙣', message);
        return;
      }

      if (resultResponse.data.status === 'failed') {
        const message = resultResponse.data.error_message || '?대?吏 遺꾩꽍???ㅽ뙣?덉뼱??';
        setAnalyzeProgress(0);
        setAnalyzeProgressLabel('');
        setAnalyzeError(message);
        setScanState('preview');
        Alert.alert('遺꾩꽍 ?ㅽ뙣', message);
        return;
      }

      const normalizedItems = (resultResponse.data.items || []).map(item => ({
        ...item,
        unit: normalizeDisplayUnit(item.unit),
        category: normalizeStorageCategory(item.category, item.name),
      }));

      setScanResult({ ...resultResponse.data, items: normalizedItems });
      setBulkUnit('媛?);
      setBulkCategory('?곸삩');
      setBulkMultiplier('1');
      setAnalyzeProgress(1);
      setAnalyzeProgressLabel('遺꾩꽍 ?꾨즺! 寃곌낵瑜??쒖떆?댁슂...');
      setScanState('result');
    } catch {
      setAnalyzeProgress(0);
      setAnalyzeProgressLabel('');
      setAnalyzeError('?ㅼ틪 以??ㅻ쪟媛 諛쒖깮?덉뼱??');
      setScanState('preview');
      Alert.alert('?ㅻ쪟', '?ㅼ틪 以??덇린移?紐삵븳 ?ㅻ쪟媛 諛쒖깮?덉뼱??');
    }
  };

  const updateItemCategory = (index: number, category: StorageCategory) => {
    setScanResult(prev => {
      if (!prev) return prev;
      const nextItems = prev.items.map((item, currentIndex) => (currentIndex === index ? { ...item, category } : item));
      return { ...prev, items: nextItems };
    });
  };

  const updateItemQuantity = (index: number, quantity: number) => {
    setScanResult(prev => {
      if (!prev) return prev;
      const nextItems = prev.items.map((item, currentIndex) =>
        currentIndex === index ? { ...item, quantity: toFixedQuantity(quantity) } : item
      );
      return { ...prev, items: nextItems };
    });
  };

  const applyBulkEdit = () => {
    const multiplier = Number(bulkMultiplier);
    if (!scanResult) return;
    if (Number.isNaN(multiplier) || multiplier <= 0) {
      Alert.alert('?낅젰 ?ㅻ쪟', '?섎웾 諛곗쑉? 0蹂대떎 ???レ옄?ъ빞 ?댁슂.');
      return;
    }

    setScanResult(prev => {
      if (!prev) return prev;
      return {
        ...prev,
        items: prev.items.map(item => ({
          ...item,
          category: bulkCategory,
          unit: normalizeDisplayUnit(bulkUnit),
          quantity: toFixedQuantity(item.quantity * multiplier),
        })),
      };
    });
  };

  const addToInventory = async () => {
    if (!scanResult || savingInventory) return;
    setSavingInventory(true);

    try {
      const result = await api.bulkAddInventory(
        scanResult.items.map(item => ({
          name: item.name,
          quantity: item.quantity,
          unit: normalizeDisplayUnit(item.unit),
          category: item.category,
        }))
      );

      if (result.data?.success) {
        Alert.alert('????꾨즺', `${result.data.added_count}媛?異붽?, ${result.data.updated_count}媛??낅뜲?댄듃?덉뼱??`, [
          { text: '?뺤씤', onPress: () => resetScan() },
        ]);
      } else {
        Alert.alert('????ㅽ뙣', result.error || '?몃깽?좊━ ??μ뿉 ?ㅽ뙣?덉뼱??');
      }
    } catch {
      Alert.alert('?ㅻ쪟', '?몃깽?좊━ ??μ뿉 ?ㅽ뙣?덉뼱??');
    } finally {
      setSavingInventory(false);
    }
  };

  const resetScan = () => {
    setCapturedObjectUrl(null);
    setScanResult(null);
    setAnalyzeError(null);
    setScanState('camera');
  };

  const lookupBarcode = async () => {
    const code = barcodeInput.trim();
    if (!code) {
      Alert.alert('?낅젰 ?ㅻ쪟', '諛붿퐫?쒕? ?낅젰??二쇱꽭??');
      return;
    }

    setBarcodeLoading(true);
    try {
      const result = await api.lookupBarcode(code);
      if (!result.data?.found || !result.data.product) {
        setBarcodeProduct(null);
        Alert.alert('議고쉶 寃곌낵', '?대떦 諛붿퐫???곹뭹??李얠? 紐삵뻽?댁슂.');
        return;
      }
      setBarcodeProduct(result.data.product);
    } finally {
      setBarcodeLoading(false);
    }
  };

  const addBarcodeProductToInventory = async () => {
    if (!barcodeProduct || addingBarcodeItem) return;

    setAddingBarcodeItem(true);
    try {
      const storageCategory = normalizeStorageCategory(barcodeProduct.category, barcodeProduct.name);
      const result = await api.bulkAddInventory([
        {
          name: barcodeProduct.name,
          quantity: 1,
          unit: '媛?,
          category: storageCategory,
          expiry_date: toIsoDateFromNow(barcodeProduct.suggested_expiry_days),
        },
      ]);

      if (!result.data?.success) {
        Alert.alert('異붽? ?ㅽ뙣', result.error || '諛붿퐫???곹뭹???몃깽?좊━??異붽??섏? 紐삵뻽?댁슂.');
        return;
      }

      Alert.alert('異붽? ?꾨즺', `${barcodeProduct.name} ??ぉ???몃깽?좊━??諛섏쁺?덉뼱??`);
      setBarcodeInput('');
      setBarcodeProduct(null);
    } finally {
      setAddingBarcodeItem(false);
    }
  };

  const renderResultItem = (item: ScanResultPayload['items'][number], index: number) => (
    <View key={`${item.name}-${index}`} style={styles.resultItem}>
      <View style={styles.resultItemInfo}>
        <Text style={styles.resultItemName}>{item.name}</Text>
        <Text style={styles.resultItemQty}>
          {item.quantity} {normalizeDisplayUnit(item.unit)}
        </Text>
        {typeof item.total_price === 'number' ? (
          <Text style={styles.priceText}>?덉긽 媛寃? {Math.round(item.total_price).toLocaleString()}??/Text>
        ) : null}

        <View style={styles.qtyControlRow}>
          <TouchableOpacity
            style={styles.qtyButton}
            onPress={() => updateItemQuantity(index, item.quantity - 1)}
            accessibilityLabel={`${item.name} ?섎웾 媛먯냼`}
          >
            <Text style={styles.qtyButtonText}>-</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={styles.qtyButton}
            onPress={() => updateItemQuantity(index, item.quantity + 1)}
            accessibilityLabel={`${item.name} ?섎웾 利앷?`}
          >
            <Text style={styles.qtyButtonText}>+</Text>
          </TouchableOpacity>
        </View>

        <View style={styles.categorySelectorRow}>
          {STORAGE_CATEGORIES.map(category => {
            const isActive = (item.category || '?곸삩') === category;
            return (
              <TouchableOpacity
                key={`${item.name}-${index}-${category}`}
                style={[styles.categoryChip, isActive && styles.categoryChipActive]}
                onPress={() => updateItemCategory(index, category)}
                accessibilityLabel={`${item.name} 蹂닿? 遺꾨쪟 ${category} ?좏깮`}
              >
                <Text style={[styles.categoryChipText, isActive && styles.categoryChipTextActive]}>{category}</Text>
              </TouchableOpacity>
            );
          })}
        </View>
      </View>
      <View style={styles.confidenceBadge}>
        <Text style={styles.confidenceText}>{Math.round((item.confidence || 0) * 100)}%</Text>
      </View>
    </View>
  );

  if (scanState === 'camera') {
    return (
      <View style={styles.container}>
        <StatusBar barStyle="dark-content" />

        <View style={styles.webIntro}>
          <Text style={styles.webTitle}>?ㅼ틪</Text>
          <Text style={styles.webSubtitle}>?щ즺 ?먮뒗 ?곸닔利??ъ쭊??珥ъ쁺?섍굅???좏깮??二쇱꽭??</Text>

          <View style={styles.scanTypeContainer}>
            <TouchableOpacity
              style={[styles.scanTypeButton, scanMode === 'ingredient' && styles.scanTypeButtonActive]}
              onPress={() => setScanMode('ingredient')}
              accessibilityLabel="?щ즺 ?ㅼ틪 紐⑤뱶 ?좏깮"
            >
              <Text style={[styles.scanTypeText, scanMode === 'ingredient' && styles.scanTypeTextActive]}>?щ즺</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={[styles.scanTypeButton, scanMode === 'receipt' && styles.scanTypeButtonActive]}
              onPress={() => setScanMode('receipt')}
              accessibilityLabel="?곸닔利??ㅼ틪 紐⑤뱶 ?좏깮"
            >
              <Text style={[styles.scanTypeText, scanMode === 'receipt' && styles.scanTypeTextActive]}>?곸닔利?/Text>
            </TouchableOpacity>
          </View>

          <View style={styles.webButtonStack}>
            <RoundButton title="移대찓?쇰줈 珥ъ쁺" onPress={() => pickImage(true)} size="large" />
            <View style={{ height: 12 }} />
            <RoundButton title="媛ㅻ윭由ъ뿉???좏깮" onPress={() => pickImage(false)} size="large" variant="outline" />
          </View>
        </View>

        <View style={styles.barcodePanel}>
          <Text style={styles.barcodeTitle}>諛붿퐫??鍮좊Ⅸ 異붽?</Text>
          <View style={styles.barcodeRow}>
            <TextInput
              value={barcodeInput}
              onChangeText={setBarcodeInput}
              placeholder="諛붿퐫??踰덊샇"
              placeholderTextColor={Colors.gray500}
              style={styles.barcodeInput}
              keyboardType="number-pad"
            />
            <TouchableOpacity
              style={styles.barcodeLookupButton}
              onPress={lookupBarcode}
              disabled={barcodeLoading}
              accessibilityLabel="諛붿퐫??議고쉶"
            >
              <Text style={styles.barcodeLookupButtonText}>{barcodeLoading ? '議고쉶 以?..' : '議고쉶'}</Text>
            </TouchableOpacity>
          </View>
          {barcodeProduct ? (
            <View style={styles.barcodeResultBox}>
              <Text style={styles.barcodeResultName}>{barcodeProduct.name}</Text>
              <Text style={styles.barcodeResultMeta}>
                {barcodeProduct.category || '移댄뀒怨좊━ ?놁쓬'}
                {barcodeProduct.suggested_expiry_days ? ` / 沅뚯옣 ?좏넻 ${barcodeProduct.suggested_expiry_days}?? : ''}
              </Text>
              <TouchableOpacity
                style={styles.barcodeAddButton}
                onPress={addBarcodeProductToInventory}
                disabled={addingBarcodeItem}
                accessibilityLabel={`${barcodeProduct.name} ?몃깽?좊━??1媛?異붽?`}
              >
                <Text style={styles.barcodeAddButtonText}>{addingBarcodeItem ? '異붽? 以?..' : '?몃깽?좊━??1媛?異붽?'}</Text>
              </TouchableOpacity>
            </View>
          ) : null}
        </View>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <StatusBar barStyle="dark-content" />

      <View style={styles.header}>
        <TouchableOpacity onPress={resetScan} accessibilityLabel="?ㅼ떆 珥ъ쁺">
          <Text style={styles.backButton}>?ㅼ떆 珥ъ쁺</Text>
        </TouchableOpacity>
        <Text style={styles.headerTitle}>
          {scanState === 'preview' && '誘몃━蹂닿린'}
          {scanState === 'analyzing' && '遺꾩꽍 以?..'}
          {scanState === 'result' && '寃곌낵'}
        </Text>
        <View style={{ width: 70 }} />
      </View>

      <View style={styles.previewContainer}>
        {capturedImage ? <Image source={{ uri: capturedImage }} style={styles.previewImage} /> : null}
        {scanState === 'analyzing' ? (
          <View style={styles.analyzingOverlay}>
            <ActivityIndicator size="large" color={Colors.primary} />
            <Text style={styles.analyzingText}>{analyzeProgressLabel || 'AI媛 ?대?吏瑜?遺꾩꽍?섍퀬 ?덉뼱??..'}</Text>
            <View style={styles.progressTrack}>
              <View style={[styles.progressFill, { width: `${Math.round(analyzeProgress * 100)}%` }]} />
            </View>
            <Text style={styles.progressPercent}>{Math.round(analyzeProgress * 100)}%</Text>
          </View>
        ) : null}
      </View>

      {analyzeError && scanState === 'preview' ? (
        <View style={styles.errorBanner}>
          <Text style={styles.errorText}>{analyzeError}</Text>
          <TouchableOpacity style={styles.errorRetryButton} onPress={analyzeScan} accessibilityLabel="?ㅼ틪 遺꾩꽍 ?ㅼ떆 ?쒕룄">
            <Text style={styles.errorRetryText}>?ㅼ떆 ?쒕룄</Text>
          </TouchableOpacity>
        </View>
      ) : null}

      {scanState === 'result' && scanResult ? (
        <View style={styles.resultContainer}>
          <Text style={styles.resultTitle}>媛먯?????ぉ ({scanResult.items.length})</Text>

          <View style={styles.bulkPanel}>
            <Text style={styles.bulkTitle}>?쇨큵 ?섏젙</Text>
            <View style={styles.bulkCategoryRow}>
              {STORAGE_CATEGORIES.map(category => (
                <TouchableOpacity
                  key={`bulk-${category}`}
                  style={[styles.categoryChip, bulkCategory === category && styles.categoryChipActive]}
                  onPress={() => setBulkCategory(category)}
                  accessibilityLabel={`?쇨큵 蹂닿? 遺꾨쪟 ${category} ?좏깮`}
                >
                  <Text style={[styles.categoryChipText, bulkCategory === category && styles.categoryChipTextActive]}>{category}</Text>
                </TouchableOpacity>
              ))}
            </View>
            <View style={styles.bulkInputRow}>
              <TextInput
                value={bulkUnit}
                onChangeText={setBulkUnit}
                placeholder="?⑥쐞"
                style={styles.bulkInput}
                placeholderTextColor={Colors.gray500}
              />
              <TextInput
                value={bulkMultiplier}
                onChangeText={setBulkMultiplier}
                placeholder="?섎웾 諛곗쑉"
                style={styles.bulkInput}
                keyboardType="decimal-pad"
                placeholderTextColor={Colors.gray500}
              />
              <TouchableOpacity style={styles.bulkApplyButton} onPress={applyBulkEdit} accessibilityLabel="?쇨큵 ?섏젙 ?곸슜">
                <Text style={styles.bulkApplyText}>?꾩껜 ?곸슜</Text>
              </TouchableOpacity>
            </View>
          </View>

          {scanResult.receipt_store || scanResult.receipt_purchased_at ? (
            <View style={styles.receiptMetaBox}>
              <Text style={styles.receiptMetaTitle}>?곸닔利?硫뷀?</Text>
              {scanResult.receipt_store ? <Text style={styles.receiptMetaText}>留ㅼ옣: {scanResult.receipt_store}</Text> : null}
              {scanResult.receipt_purchased_at ? (
                <Text style={styles.receiptMetaText}>援щℓ?? {scanResult.receipt_purchased_at}</Text>
              ) : null}
            </View>
          ) : null}

          <ScrollView style={styles.resultScroll} contentContainerStyle={styles.resultScrollContent}>
            {scanResult.items.map((item, index) => renderResultItem(item, index))}

            {scanResult.raw_text ? (
              <View style={styles.rawTextBox}>
                <Text style={styles.rawTextTitle}>?곸닔利??띿뒪??/Text>
                <Text style={styles.rawText}>{scanResult.raw_text}</Text>
              </View>
            ) : null}
          </ScrollView>
        </View>
      ) : null}

      <View style={styles.actionContainer}>
        {scanState === 'preview' ? <RoundButton title="遺꾩꽍?섍린" onPress={analyzeScan} size="large" /> : null}
        {scanState === 'result' ? (
          <>
            <RoundButton title="?몃깽?좊━????? onPress={addToInventory} size="large" loading={savingInventory} />
            <View style={styles.actionSpacer} />
            <RoundButton title="?ㅼ떆 ?ㅼ틪" onPress={resetScan} size="small" variant="outline" />
          </>
        ) : null}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F5F8F7' },
  webIntro: {
    marginTop: 54,
    marginHorizontal: 16,
    borderRadius: 16,
    padding: 16,
    backgroundColor: '#132018',
  },
  webTitle: { color: Colors.white, fontSize: 28, fontWeight: '700' },
  webSubtitle: { color: 'rgba(255,255,255,0.9)', marginTop: 6, marginBottom: 12 },
  scanTypeContainer: {
    flexDirection: 'row',
    backgroundColor: 'rgba(255,255,255,0.16)',
    borderRadius: 12,
    padding: 4,
  },
  scanTypeButton: { flex: 1, alignItems: 'center', paddingVertical: 8, borderRadius: 10 },
  scanTypeButtonActive: { backgroundColor: Colors.white },
  scanTypeText: { color: Colors.white, fontWeight: '700' },
  scanTypeTextActive: { color: '#22352B' },
  webButtonStack: { marginTop: 14 },
  barcodePanel: {
    marginHorizontal: 16,
    marginTop: 12,
    borderRadius: 12,
    backgroundColor: Colors.white,
    borderWidth: 1,
    borderColor: '#DDE6E1',
    padding: 12,
  },
  barcodeTitle: {
    color: '#132018',
    fontWeight: '700',
    marginBottom: 8,
    fontSize: 12,
  },
  barcodeRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  barcodeInput: {
    flex: 1,
    borderRadius: 9,
    borderWidth: 1,
    borderColor: '#DDE6E1',
    backgroundColor: '#F9FBFA',
    color: '#132018',
    paddingHorizontal: 10,
    paddingVertical: 8,
  },
  barcodeLookupButton: {
    borderRadius: 9,
    backgroundColor: Colors.primary,
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  barcodeLookupButtonText: {
    color: Colors.white,
    fontWeight: '700',
    fontSize: 12,
  },
  barcodeResultBox: {
    marginTop: 10,
    borderRadius: 10,
    backgroundColor: '#F9FBFA',
    borderWidth: 1,
    borderColor: '#DDE6E1',
    padding: 10,
  },
  barcodeResultName: {
    color: '#132018',
    fontWeight: '700',
  },
  barcodeResultMeta: {
    color: Colors.gray700,
    fontSize: 12,
    marginTop: 3,
  },
  barcodeAddButton: {
    marginTop: 10,
    borderRadius: 8,
    backgroundColor: Colors.primary,
    alignItems: 'center',
    paddingVertical: 10,
  },
  barcodeAddButtonText: {
    color: Colors.white,
    fontWeight: '700',
    fontSize: 12,
  },
  header: {
    paddingTop: 54,
    paddingHorizontal: 16,
    paddingBottom: 8,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  backButton: { color: Colors.primary, fontWeight: '700' },
  headerTitle: { color: '#132018', fontWeight: '700', fontSize: 18 },
  previewContainer: { height: 210, marginHorizontal: 16, borderRadius: 12, overflow: 'hidden', backgroundColor: '#DDE6E1' },
  previewImage: { width: '100%', height: '100%' },
  analyzingOverlay: { ...StyleSheet.absoluteFillObject, backgroundColor: 'rgba(0,0,0,0.4)', alignItems: 'center', justifyContent: 'center' },
  analyzingText: { color: Colors.white, marginTop: 10, fontWeight: '600' },
  progressTrack: { marginTop: 12, width: 180, height: 8, borderRadius: 999, backgroundColor: 'rgba(255,255,255,0.25)', overflow: 'hidden' },
  progressFill: { height: '100%', backgroundColor: Colors.primary },
  progressPercent: { color: Colors.white, marginTop: 6, fontWeight: '700', fontSize: 12 },
  errorBanner: { marginHorizontal: 16, marginTop: 10, borderRadius: 10, backgroundColor: 'rgba(255,71,87,0.12)', borderWidth: 1, borderColor: 'rgba(255,71,87,0.3)', padding: 10, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', gap: 8 },
  errorText: { color: Colors.danger, flex: 1 },
  errorRetryButton: { borderRadius: 8, backgroundColor: Colors.white, paddingHorizontal: 10, paddingVertical: 6 },
  errorRetryText: { color: '#22352B', fontWeight: '700' },
  resultContainer: { flex: 1, marginTop: 10 },
  resultTitle: { fontSize: 16, fontWeight: '700', color: '#132018', marginHorizontal: 16, marginBottom: 8 },
  bulkPanel: { marginHorizontal: 16, borderRadius: 12, backgroundColor: '#E8EFEC', borderWidth: 1, borderColor: '#DDE6E1', padding: 10, marginBottom: 8 },
  bulkTitle: { color: '#132018', fontWeight: '700', marginBottom: 8 },
  bulkCategoryRow: { flexDirection: 'row', gap: 8, marginBottom: 8 },
  bulkInputRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  bulkInput: { flex: 1, borderRadius: 8, borderWidth: 1, borderColor: '#DDE6E1', backgroundColor: Colors.white, paddingHorizontal: 10, paddingVertical: 8, color: '#132018' },
  bulkApplyButton: { borderRadius: 8, backgroundColor: Colors.primary, paddingHorizontal: 10, paddingVertical: 10 },
  bulkApplyText: { color: Colors.white, fontWeight: '700', fontSize: 12 },
  receiptMetaBox: { marginHorizontal: 16, borderRadius: 10, backgroundColor: '#F9FBFA', borderWidth: 1, borderColor: '#DDE6E1', padding: 10, marginBottom: 8 },
  receiptMetaTitle: { color: '#132018', fontWeight: '700', marginBottom: 4 },
  receiptMetaText: { color: Colors.gray700, fontSize: 12 },
  resultScroll: { flex: 1 },
  resultScrollContent: { paddingHorizontal: 16, paddingBottom: 130, gap: 10 },
  resultItem: { borderRadius: 12, borderWidth: 1, borderColor: '#DDE6E1', backgroundColor: Colors.white, padding: 10, flexDirection: 'row', gap: 8 },
  resultItemInfo: { flex: 1 },
  resultItemName: { color: '#132018', fontWeight: '700', fontSize: 15 },
  resultItemQty: { color: Colors.gray700, marginTop: 2 },
  priceText: { color: Colors.primaryDark, marginTop: 2, fontSize: 12, fontWeight: '600' },
  qtyControlRow: { flexDirection: 'row', gap: 8, marginTop: 8 },
  qtyButton: { width: 30, height: 30, borderRadius: 8, backgroundColor: '#E8EFEC', alignItems: 'center', justifyContent: 'center' },
  qtyButtonText: { color: '#22352B', fontWeight: '700', fontSize: 18 },
  categorySelectorRow: { flexDirection: 'row', gap: 6, marginTop: 8, flexWrap: 'wrap' },
  categoryChip: { borderRadius: 999, borderWidth: 1, borderColor: '#DDE6E1', paddingHorizontal: 10, paddingVertical: 5, backgroundColor: '#F9FBFA' },
  categoryChipActive: { backgroundColor: Colors.primary, borderColor: Colors.primary },
  categoryChipText: { color: '#22352B', fontSize: 12, fontWeight: '700' },
  categoryChipTextActive: { color: Colors.white },
  confidenceBadge: { alignSelf: 'flex-start', borderRadius: 8, backgroundColor: '#E8F8F2', paddingHorizontal: 8, paddingVertical: 4 },
  confidenceText: { color: Colors.primaryDark, fontWeight: '700', fontSize: 11 },
  rawTextBox: { borderRadius: 12, backgroundColor: '#F9FBFA', borderWidth: 1, borderColor: '#DDE6E1', padding: 10 },
  rawTextTitle: { color: '#132018', fontWeight: '700', marginBottom: 6 },
  rawText: { color: Colors.gray700, fontSize: 12, lineHeight: 18 },
  actionContainer: {
    position: 'absolute',
    left: 0,
    right: 0,
    bottom: 0,
    paddingHorizontal: 20,
    paddingBottom: 18,
    paddingTop: 10,
    backgroundColor: 'rgba(245,248,247,0.96)',
    borderTopWidth: 1,
    borderTopColor: '#DDE6E1',
  },
  actionSpacer: { height: 10 },
});

