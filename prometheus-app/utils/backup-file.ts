import { Platform } from 'react-native';

import * as nativeImpl from './backup-file.native';
import * as webImpl from './backup-file.web';

const impl = Platform.OS === 'web' ? webImpl : nativeImpl;

export const saveBackupJsonAsFile = impl.saveBackupJsonAsFile;
export const loadBackupJsonFromFile = impl.loadBackupJsonFromFile;
