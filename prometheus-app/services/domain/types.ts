import type { ApiResponse, RequestOptions } from '../http-client';

export type ApiTransport = {
  request<T>(endpoint: string, options?: RequestOptions): Promise<ApiResponse<T>>;
  invalidateCache(prefixes?: string[]): void;
};
