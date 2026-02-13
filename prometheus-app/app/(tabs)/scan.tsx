import React, { useRef, useState } from 'react';
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
import { CameraView, useCameraPermissions } from 'expo-camera';
import * as ImagePicker from 'expo-image-picker';

import Colors from '@/constants/Colors';
import { RoundButton } from '@/components/RoundButton';
import { ScanResultPayload, ScanSourceType, api } from '@/services/api';

type ScanState = 'camera' | 'preview' | 'analyzing' | 'result';
type StorageCategory = '냉장' | '냉동' | '상온';
type ScanMode = 'ingredient' | 'receipt';

const STORAGE_CATEGORIES: StorageCategory[] = ['냉장', '냉동', '상온'];

function normalizeDisplayUnit(value?: string): string {
  const unit = (value || '').trim();
  if (!unit) return '개';
  if (unit.toLowerCase() === 'unit') return '개';
  return unit;
}

function normalizeStorageCategory(value?: string, fallbackName?: string): StorageCategory {
  const normalized = (value || '').trim().toLowerCase().replace(/[_\-\s]/g, '');
  if (normalized.includes('냉동') || normalized.includes('freezer') || normalized.includes('frozen')) return '냉동';
  if (normalized.includes('냉장') || normalized.includes('fridge') || normalized.includes('refriger')) return '냉장';
  if (normalized.includes('상온') || normalized.includes('실온') || normalized.includes('ambient') || normalized.includes('pantry')) return '상온';

  const byName = (fallbackName || '').toLowerCase();
  if (/(냉동|아이스|ice|frozen|만두|피자)/.test(byName)) return '냉동';
  if (/(우유|치즈|요거트|계란|두부|고기|생선|milk|egg|cheese|yogurt|tofu)/.test(byName)) return '냉장';
  return '상온';
}

function toFixedQuantity(value: number): number {
  return Math.max(0.01, Math.round(value * 100) / 100);
}

function toIsoDateFromNow(days?: number): string | undefined {
  if (!days || days <= 0) return undefined;
  const date = new Date();
  date.setDate(date.getDate() + Math.round(days));
  return date.toISOString().slice(0, 10);
}

export default function ScanScreen() {
  const [permission, requestPermission] = useCameraPermissions();
  const [scanState, setScanState] = useState<ScanState>('camera');
  const [capturedImage, setCapturedImage] = useState<string | null>(null);
  const [scanResult, setScanResult] = useState<ScanResultPayload | null>(null);
  const [scanMode, setScanMode] = useState<ScanMode>('ingredient');
  const [sourceType, setSourceType] = useState<ScanSourceType>('camera');
  const [savingInventory, setSavingInventory] = useState(false);
  const [analyzeError, setAnalyzeError] = useState<string | null>(null);
  const [bulkCategory, setBulkCategory] = useState<StorageCategory>('상온');
  const [bulkUnit, setBulkUnit] = useState('개');
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

  const cameraRef = useRef<CameraView>(null);

  const resolveSourceType = (inputSource: 'camera' | 'gallery', mode: ScanMode): ScanSourceType => {
    if (mode === 'receipt') return 'receipt';
    return inputSource;
  };

  if (!permission) {
    return <View style={styles.container} />;
  }

  if (!permission.granted) {
    return (
      <View style={styles.permissionContainer}>
        <Text style={styles.permissionTitle}>카메라 권한이 필요해요</Text>
        <Text style={styles.permissionText}>재료 또는 영수증을 스캔하려면 카메라 접근을 허용해 주세요.</Text>
        <RoundButton title="카메라 권한 허용" onPress={requestPermission} size="large" />
      </View>
    );
  }

  const takePicture = async () => {
    if (!cameraRef.current) return;
    const photo = await cameraRef.current.takePictureAsync({
      quality: 0.65,
      skipProcessing: true,
    });
    if (!photo) return;
    setCapturedImage(photo.uri);
    setSourceType(resolveSourceType('camera', scanMode));
    setAnalyzeError(null);
    setScanState('preview');
  };

  const pickImage = async () => {
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      quality: 0.7,
    });
    if (result.canceled || !result.assets[0]) return;

    setCapturedImage(result.assets[0].uri);
    setSourceType(resolveSourceType('gallery', scanMode));
    setAnalyzeError(null);
    setScanState('preview');
  };

  const pollScanResult = async (scanId: string, maxAttempts = 45) => {
    for (let attempt = 0; attempt < maxAttempts; attempt++) {
      const resultResponse = await api.getScanResult(scanId);
      if (resultResponse.error) {
        return { error: resultResponse.error };
      }

      const status = resultResponse.data?.status;
      if (status === 'completed' || status === 'failed') {
        return resultResponse;
      }

      await new Promise(resolve => setTimeout(resolve, 1000));
    }

    return { error: '분석 시간이 길어지고 있어요. 다시 시도해 주세요.' };
  };

  const analyzeScan = async () => {
    if (!capturedImage) return;

    setScanState('analyzing');
    setAnalyzeError(null);

    try {
      const uploadResult = await api.uploadScan(capturedImage, sourceType);
      if (uploadResult.error || !uploadResult.data) {
        const message = uploadResult.error || '업로드에 실패했어요.';
        setAnalyzeError(message);
        setScanState('preview');
        Alert.alert('스캔 실패', message);
        return;
      }

      const resultResponse = await pollScanResult(uploadResult.data.scan_id);
      if (resultResponse.error || !resultResponse.data) {
        const message = resultResponse.error || '분석에 실패했어요.';
        setAnalyzeError(message);
        setScanState('preview');
        Alert.alert('분석 실패', message);
        return;
      }

      if (resultResponse.data.status === 'failed') {
        const message = resultResponse.data.error_message || '이미지 분석에 실패했어요.';
        setAnalyzeError(message);
        setScanState('preview');
        Alert.alert('분석 실패', message);
        return;
      }

      const normalizedItems = (resultResponse.data.items || []).map(item => ({
        ...item,
        unit: normalizeDisplayUnit(item.unit),
        category: normalizeStorageCategory(item.category, item.name),
      }));

      setScanResult({ ...resultResponse.data, items: normalizedItems });
      setBulkUnit('개');
      setBulkCategory('상온');
      setBulkMultiplier('1');
      setScanState('result');
    } catch {
      setAnalyzeError('스캔 중 오류가 발생했어요.');
      setScanState('preview');
      Alert.alert('오류', '스캔 중 예기치 못한 오류가 발생했어요.');
    }
  };

  const updateItemCategory = (index: number, category: StorageCategory) => {
    setScanResult(prev => {
      if (!prev) return prev;
      const nextItems = prev.items.map((item, currentIndex) =>
        currentIndex === index ? { ...item, category } : item
      );
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
      Alert.alert('입력 오류', '수량 배율은 0보다 큰 숫자여야 해요.');
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
        Alert.alert('저장 완료', `${result.data.added_count}개 추가, ${result.data.updated_count}개 업데이트했어요.`, [
          { text: '확인', onPress: () => resetScan() },
        ]);
      } else {
        Alert.alert('저장 실패', result.error || '인벤토리 저장에 실패했어요.');
      }
    } catch {
      Alert.alert('오류', '인벤토리 저장에 실패했어요.');
    } finally {
      setSavingInventory(false);
    }
  };

  const resetScan = () => {
    setCapturedImage(null);
    setScanResult(null);
    setAnalyzeError(null);
    setScanState('camera');
  };

  const lookupBarcode = async () => {
    const code = barcodeInput.trim();
    if (!code) {
      Alert.alert('입력 오류', '바코드를 입력해 주세요.');
      return;
    }

    setBarcodeLoading(true);
    try {
      const result = await api.lookupBarcode(code);
      if (!result.data?.found || !result.data.product) {
        setBarcodeProduct(null);
        Alert.alert('조회 결과', '해당 바코드 상품을 찾지 못했어요.');
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
          unit: '개',
          category: storageCategory,
          expiry_date: toIsoDateFromNow(barcodeProduct.suggested_expiry_days),
        },
      ]);

      if (!result.data?.success) {
        Alert.alert('추가 실패', result.error || '바코드 상품을 인벤토리에 추가하지 못했어요.');
        return;
      }

      Alert.alert('추가 완료', `${barcodeProduct.name} 항목을 인벤토리에 반영했어요.`);
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
          <Text style={styles.priceText}>예상 가격: {Math.round(item.total_price).toLocaleString()}원</Text>
        ) : null}

        <View style={styles.qtyControlRow}>
          <TouchableOpacity
            style={styles.qtyButton}
            onPress={() => updateItemQuantity(index, item.quantity - 1)}
            accessibilityLabel={`${item.name} 수량 감소`}
          >
            <Text style={styles.qtyButtonText}>-</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={styles.qtyButton}
            onPress={() => updateItemQuantity(index, item.quantity + 1)}
            accessibilityLabel={`${item.name} 수량 증가`}
          >
            <Text style={styles.qtyButtonText}>+</Text>
          </TouchableOpacity>
        </View>

        <View style={styles.categorySelectorRow}>
          {STORAGE_CATEGORIES.map(category => {
            const isActive = (item.category || '상온') === category;
            return (
              <TouchableOpacity
                key={`${item.name}-${index}-${category}`}
                style={[styles.categoryChip, isActive && styles.categoryChipActive]}
                onPress={() => updateItemCategory(index, category)}
                accessibilityLabel={`${item.name} 보관 분류 ${category} 선택`}
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
        <StatusBar barStyle="light-content" />
        <CameraView ref={cameraRef} style={styles.camera} facing="back">
          <View style={styles.cameraHeader}>
            <Text style={styles.cameraTitle}>스캔</Text>
            <Text style={styles.cameraSubtitle}>재료 또는 장보기 영수증을 촬영해 주세요.</Text>
          </View>

          <View style={styles.scanTypeContainer}>
            <TouchableOpacity
              style={[styles.scanTypeButton, scanMode === 'ingredient' && styles.scanTypeButtonActive]}
              onPress={() => setScanMode('ingredient')}
              accessibilityLabel="재료 스캔 모드 선택"
            >
              <Text style={[styles.scanTypeText, scanMode === 'ingredient' && styles.scanTypeTextActive]}>재료</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={[styles.scanTypeButton, scanMode === 'receipt' && styles.scanTypeButtonActive]}
              onPress={() => setScanMode('receipt')}
              accessibilityLabel="영수증 스캔 모드 선택"
            >
              <Text style={[styles.scanTypeText, scanMode === 'receipt' && styles.scanTypeTextActive]}>영수증</Text>
            </TouchableOpacity>
          </View>

          <View style={styles.barcodePanel}>
            <Text style={styles.barcodeTitle}>바코드 빠른 추가</Text>
            <View style={styles.barcodeRow}>
              <TextInput
                value={barcodeInput}
                onChangeText={setBarcodeInput}
                placeholder="바코드 번호"
                placeholderTextColor="rgba(255,255,255,0.65)"
                style={styles.barcodeInput}
                keyboardType="number-pad"
              />
              <TouchableOpacity
                style={styles.barcodeLookupButton}
                onPress={lookupBarcode}
                disabled={barcodeLoading}
                accessibilityLabel="바코드 조회"
              >
                <Text style={styles.barcodeLookupButtonText}>{barcodeLoading ? '조회 중...' : '조회'}</Text>
              </TouchableOpacity>
            </View>
            {barcodeProduct ? (
              <View style={styles.barcodeResultBox}>
                <Text style={styles.barcodeResultName}>{barcodeProduct.name}</Text>
                <Text style={styles.barcodeResultMeta}>
                  {barcodeProduct.category || '카테고리 없음'}
                  {barcodeProduct.suggested_expiry_days ? ` / 권장 유통 ${barcodeProduct.suggested_expiry_days}일` : ''}
                </Text>
                <TouchableOpacity
                  style={styles.barcodeAddButton}
                  onPress={addBarcodeProductToInventory}
                  disabled={addingBarcodeItem}
                  accessibilityLabel={`${barcodeProduct.name} 인벤토리에 1개 추가`}
                >
                  <Text style={styles.barcodeAddButtonText}>
                    {addingBarcodeItem ? '추가 중...' : '인벤토리에 1개 추가'}
                  </Text>
                </TouchableOpacity>
              </View>
            ) : null}
          </View>

          <View style={styles.cameraControls}>
            <TouchableOpacity style={styles.galleryButton} onPress={pickImage} accessibilityLabel="갤러리에서 이미지 선택">
              <Text style={styles.galleryText}>갤러리</Text>
            </TouchableOpacity>

            <TouchableOpacity style={styles.captureButton} onPress={takePicture} accessibilityLabel="카메라 촬영">
              <View style={styles.captureButtonInner} />
            </TouchableOpacity>

            <View style={styles.galleryButton} />
          </View>
        </CameraView>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <StatusBar barStyle="dark-content" />

      <View style={styles.header}>
        <TouchableOpacity onPress={resetScan} accessibilityLabel="다시 촬영">
          <Text style={styles.backButton}>다시 촬영</Text>
        </TouchableOpacity>
        <Text style={styles.headerTitle}>
          {scanState === 'preview' && '미리보기'}
          {scanState === 'analyzing' && '분석 중...'}
          {scanState === 'result' && '결과'}
        </Text>
        <View style={{ width: 70 }} />
      </View>

      <View style={styles.previewContainer}>
        {capturedImage ? <Image source={{ uri: capturedImage }} style={styles.previewImage} /> : null}
        {scanState === 'analyzing' ? (
          <View style={styles.analyzingOverlay}>
            <ActivityIndicator size="large" color={Colors.primary} />
            <Text style={styles.analyzingText}>AI가 이미지를 분석하고 있어요...</Text>
          </View>
        ) : null}
      </View>

      {analyzeError && scanState === 'preview' ? (
        <View style={styles.errorBanner}>
          <Text style={styles.errorText}>{analyzeError}</Text>
          <TouchableOpacity style={styles.errorRetryButton} onPress={analyzeScan} accessibilityLabel="스캔 분석 다시 시도">
            <Text style={styles.errorRetryText}>다시 시도</Text>
          </TouchableOpacity>
        </View>
      ) : null}

      {scanState === 'result' && scanResult ? (
        <View style={styles.resultContainer}>
          <Text style={styles.resultTitle}>감지된 항목 ({scanResult.items.length})</Text>

          <View style={styles.bulkPanel}>
            <Text style={styles.bulkTitle}>일괄 수정</Text>
            <View style={styles.bulkCategoryRow}>
              {STORAGE_CATEGORIES.map(category => (
                <TouchableOpacity
                  key={`bulk-${category}`}
                  style={[styles.categoryChip, bulkCategory === category && styles.categoryChipActive]}
                  onPress={() => setBulkCategory(category)}
                  accessibilityLabel={`일괄 보관 분류 ${category} 선택`}
                >
                  <Text style={[styles.categoryChipText, bulkCategory === category && styles.categoryChipTextActive]}>{category}</Text>
                </TouchableOpacity>
              ))}
            </View>
            <View style={styles.bulkInputRow}>
              <TextInput
                value={bulkUnit}
                onChangeText={setBulkUnit}
                placeholder="단위"
                style={styles.bulkInput}
                placeholderTextColor={Colors.gray500}
              />
              <TextInput
                value={bulkMultiplier}
                onChangeText={setBulkMultiplier}
                placeholder="수량 배율"
                style={styles.bulkInput}
                keyboardType="decimal-pad"
                placeholderTextColor={Colors.gray500}
              />
              <TouchableOpacity style={styles.bulkApplyButton} onPress={applyBulkEdit} accessibilityLabel="일괄 수정 적용">
                <Text style={styles.bulkApplyText}>전체 적용</Text>
              </TouchableOpacity>
            </View>
          </View>

          {scanResult.receipt_store || scanResult.receipt_purchased_at ? (
            <View style={styles.receiptMetaBox}>
              <Text style={styles.receiptMetaTitle}>영수증 메타</Text>
              {scanResult.receipt_store ? <Text style={styles.receiptMetaText}>매장: {scanResult.receipt_store}</Text> : null}
              {scanResult.receipt_purchased_at ? <Text style={styles.receiptMetaText}>구매일: {scanResult.receipt_purchased_at}</Text> : null}
            </View>
          ) : null}

          <ScrollView style={styles.resultScroll} contentContainerStyle={styles.resultScrollContent}>
            {scanResult.items.map((item, index) => renderResultItem(item, index))}

            {scanResult.raw_text ? (
              <View style={styles.rawTextBox}>
                <Text style={styles.rawTextTitle}>영수증 텍스트</Text>
                <Text style={styles.rawText}>{scanResult.raw_text}</Text>
              </View>
            ) : null}
          </ScrollView>
        </View>
      ) : null}

      <View style={styles.actionContainer}>
        {scanState === 'preview' ? (
          <RoundButton title="분석하기" onPress={analyzeScan} size="large" />
        ) : null}
        {scanState === 'result' ? (
          <>
            <RoundButton title="인벤토리에 저장" onPress={addToInventory} size="large" loading={savingInventory} />
            <View style={styles.actionSpacer} />
            <RoundButton title="다시 스캔" onPress={resetScan} size="small" variant="outline" />
          </>
        ) : null}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F5F8F7' },
  permissionContainer: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: 24 },
  permissionTitle: { fontSize: 22, fontWeight: '700', color: '#132018', marginBottom: 8, textAlign: 'center' },
  permissionText: { color: Colors.gray600, textAlign: 'center', marginBottom: 16 },
  camera: { flex: 1, justifyContent: 'space-between' },
  cameraHeader: { paddingTop: 60, paddingHorizontal: 24 },
  cameraTitle: { color: Colors.white, fontSize: 28, fontWeight: '700' },
  cameraSubtitle: { color: 'rgba(255,255,255,0.9)', marginTop: 6 },
  scanTypeContainer: { flexDirection: 'row', marginHorizontal: 24, backgroundColor: 'rgba(0,0,0,0.3)', borderRadius: 12, padding: 4 },
  scanTypeButton: { flex: 1, alignItems: 'center', paddingVertical: 8, borderRadius: 10 },
  scanTypeButtonActive: { backgroundColor: Colors.white },
  scanTypeText: { color: Colors.white, fontWeight: '700' },
  scanTypeTextActive: { color: '#22352B' },
  barcodePanel: {
    marginHorizontal: 24,
    marginTop: 10,
    borderRadius: 12,
    backgroundColor: 'rgba(0,0,0,0.35)',
    padding: 10,
  },
  barcodeTitle: {
    color: Colors.white,
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
    borderColor: 'rgba(255,255,255,0.25)',
    backgroundColor: 'rgba(255,255,255,0.12)',
    color: Colors.white,
    paddingHorizontal: 10,
    paddingVertical: 8,
  },
  barcodeLookupButton: {
    borderRadius: 9,
    backgroundColor: Colors.white,
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  barcodeLookupButtonText: {
    color: '#22352B',
    fontWeight: '700',
    fontSize: 12,
  },
  barcodeResultBox: {
    marginTop: 8,
    borderRadius: 10,
    backgroundColor: 'rgba(255,255,255,0.16)',
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.22)',
    padding: 9,
  },
  barcodeResultName: {
    color: Colors.white,
    fontWeight: '700',
  },
  barcodeResultMeta: {
    color: 'rgba(255,255,255,0.9)',
    fontSize: 12,
    marginTop: 3,
  },
  barcodeAddButton: {
    marginTop: 8,
    borderRadius: 8,
    backgroundColor: Colors.primary,
    alignItems: 'center',
    paddingVertical: 8,
  },
  barcodeAddButtonText: {
    color: Colors.white,
    fontWeight: '700',
    fontSize: 12,
  },
  cameraControls: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: 28, paddingBottom: 36 },
  galleryButton: { width: 72, alignItems: 'center' },
  galleryText: { color: Colors.white, fontWeight: '600' },
  captureButton: { width: 74, height: 74, borderRadius: 37, borderWidth: 4, borderColor: Colors.white, alignItems: 'center', justifyContent: 'center' },
  captureButtonInner: { width: 56, height: 56, borderRadius: 28, backgroundColor: Colors.white },
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


