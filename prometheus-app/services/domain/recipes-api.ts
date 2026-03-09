import type { ApiRecipe, CookingHistoryItem, CookingHistoryResponse } from '../api.types';
import { offlineCache } from '../offline-cache';

import type { ApiTransport } from './types';

const RECOMMENDATIONS_TIMEOUT_MS = 45000;

export async function getRecommendationsDomain(
  transport: ApiTransport,
  limit = 5,
  forceRefresh = false
) {
  const fallback = () =>
    transport.request<{ recipes: ApiRecipe[]; total_count: number }>(
      `/recipes/recommendations?limit=${limit}&force_refresh=${forceRefresh ? 'true' : 'false'}`,
      {
        cacheTtlMs: forceRefresh ? 0 : 10000,
        timeoutMs: RECOMMENDATIONS_TIMEOUT_MS,
      }
    );

  const createJob = await transport.request<{ job_id: string; status: string }>(
    `/recipes/recommendations/jobs?limit=${limit}&force_refresh=${forceRefresh ? 'true' : 'false'}`,
    {
      method: 'POST',
      timeoutMs: 10000,
      skipOfflineQueue: true,
    }
  );

  if (!createJob.data?.job_id) {
    return fallback();
  }

  const jobId = createJob.data.job_id;
  const maxPolls = 20;
  for (let attempt = 0; attempt < maxPolls; attempt += 1) {
    const statusResult = await transport.request<{
      job_id: string;
      status: 'pending' | 'processing' | 'completed' | 'failed';
      recipes?: ApiRecipe[];
      total_count?: number;
      error?: string;
    }>(`/recipes/recommendations/jobs/${jobId}`, {
      cacheTtlMs: 0,
      timeoutMs: 10000,
      skipOfflineQueue: true,
      skipRequestDedup: true,
    });

    if (!statusResult.data) {
      return { error: statusResult.error || 'Unable to check recommendation status.' };
    }

    if (statusResult.data.status === 'completed') {
      const recipes = statusResult.data.recipes || [];
      return {
        data: {
          recipes,
          total_count: statusResult.data.total_count ?? recipes.length,
        },
      };
    }

    if (statusResult.data.status === 'failed') {
      return { error: statusResult.data.error || 'Recommendation generation failed.' };
    }

    await new Promise(resolve => setTimeout(resolve, 500));
  }

  return { error: 'Recommendation generation is delayed. Please try again shortly.' };
}

export async function getRecipeDomain(transport: ApiTransport, recipeId: string) {
  return transport.request<ApiRecipe>(`/recipes/${recipeId}`, { cacheTtlMs: 15000 });
}

export async function getFavoriteRecipesDomain(transport: ApiTransport, limit = 30, offset = 0) {
  const result = await transport.request<{ recipes: ApiRecipe[]; total_count: number }>(
    `/recipes/favorites?limit=${limit}&offset=${offset}`,
    {
      cacheTtlMs: 6000,
    }
  );

  if (result.data?.recipes) {
    offlineCache.saveFavorites(result.data.recipes).catch(() => undefined);
  }
  return result;
}

export async function addFavoriteRecipeDomain(transport: ApiTransport, recipe: ApiRecipe) {
  const result = await transport.request<{ success: boolean; is_favorite: boolean; message: string }>(
    `/recipes/${recipe.id}/favorite`,
    {
      method: 'POST',
      body: JSON.stringify({ recipe }),
    }
  );
  if (result.data?.success) {
    transport.invalidateCache(['/recipes/recommendations', '/recipes/favorites', `/recipes/${recipe.id}`]);
  }
  return result;
}

export async function removeFavoriteRecipeDomain(transport: ApiTransport, recipeId: string) {
  const result = await transport.request<{ success: boolean; is_favorite: boolean; message: string }>(
    `/recipes/${recipeId}/favorite`,
    {
      method: 'DELETE',
    }
  );
  if (result.data?.success) {
    transport.invalidateCache(['/recipes/recommendations', '/recipes/favorites', `/recipes/${recipeId}`]);
  }
  return result;
}

export async function completeCookingDomain(transport: ApiTransport, recipeId: string, servings = 1) {
  const result = await transport.request<{
    success: boolean;
    message: string;
    deducted_items: Array<{
      name: string;
      deducted: number;
      remaining: number;
      deleted: boolean;
    }>;
  }>(`/recipes/${recipeId}/cook`, {
    method: 'POST',
    body: JSON.stringify({ servings }),
  });

  if (result.data?.success) {
    transport.invalidateCache(['/inventory', '/recipes/recommendations', `/recipes/${recipeId}`, '/recipes/history', '/notifications']);
  }
  return result;
}

export async function getCookingHistoryDomain(transport: ApiTransport, limit = 20, offset = 0) {
  return transport.request<CookingHistoryResponse>(`/recipes/history?limit=${limit}&offset=${offset}`, { cacheTtlMs: 5000 });
}

export async function getCookingHistoryDetailDomain(transport: ApiTransport, historyId: string) {
  return transport.request<CookingHistoryItem>(`/recipes/history/${historyId}`, { cacheTtlMs: 5000 });
}
