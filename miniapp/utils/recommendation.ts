export interface MiniappRecommendationItem {
  school_name?: string
  school?: string
  major_name?: string
  major?: string
  name?: string
  reason?: string
}

interface RecommendationFavoritesResponse {
  favorite_keys?: string[]
}

export function recommendationName(item: MiniappRecommendationItem) {
  return (
    item.school_name ||
    item.school ||
    item.major_name ||
    item.major ||
    item.name ||
    '推荐项'
  )
}

export function recommendationKey(item: MiniappRecommendationItem) {
  if (item.school_name || item.school) return `school:${recommendationName(item)}`
  if (item.major_name || item.major) return `major:${recommendationName(item)}`
  return `recommendation:${recommendationName(item)}`
}

export function favoriteStorageKey(sessionId: string) {
  return `recommendation-favorites:${sessionId}`
}

export function parseFavoriteKeys(value: unknown): string[] {
  if (!Array.isArray(value)) return []
  return value.filter((item): item is string => typeof item === 'string')
}

export function readFavoriteKeysFromStorage(sessionId: string) {
  try {
    return parseFavoriteKeys(uni.getStorageSync(favoriteStorageKey(sessionId)))
  } catch {
    return []
  }
}

export function writeFavoriteKeysToStorage(sessionId: string, favoriteKeys: string[]) {
  try {
    uni.setStorageSync(favoriteStorageKey(sessionId), favoriteKeys)
  } catch {
    // 本地收藏不可用时不影响推荐主流程。
  }
}

export async function fetchFavoriteKeys(sessionId: string): Promise<string[] | null> {
  try {
    const res = await uni.request({
      url: `/api/session/${sessionId}/favorites`,
      method: 'GET',
    })
    if (res.statusCode >= 400) return null
    const data = res.data as RecommendationFavoritesResponse | undefined
    return parseFavoriteKeys(data?.favorite_keys)
  } catch {
    return null
  }
}

export async function saveFavoriteKeys(sessionId: string, favoriteKeys: string[]) {
  const res = await uni.request({
    url: `/api/session/${sessionId}/favorites`,
    method: 'PUT',
    data: { favorite_keys: favoriteKeys },
  })
  if (res.statusCode >= 400) {
    throw new Error(`Favorite sync failed: ${res.statusCode}`)
  }
}

export function markdownReportUrl(sessionId: string) {
  return `/api/session/${sessionId}/export`
}

export function pdfReportUrl(sessionId: string) {
  return `/api/session/${sessionId}/export/pdf`
}

export async function copyMarkdownReportToClipboard(sessionId: string) {
  const res = await uni.request({
    url: markdownReportUrl(sessionId),
    method: 'GET',
  })
  if (res.statusCode >= 400 || typeof res.data !== 'string') {
    throw new Error(`Export failed: ${res.statusCode}`)
  }
  await uni.setClipboardData({ data: res.data })
}

export async function copyPdfReportLinkToClipboard(sessionId: string) {
  await uni.setClipboardData({
    data: pdfReportUrl(sessionId),
  })
}
