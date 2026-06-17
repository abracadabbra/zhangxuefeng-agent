<template>
  <view class="result">
    <view class="header">
      <view class="stamp">推荐结果</view>
      <text class="title">志愿建议清单</text>
      <text v-if="updatedAt" class="updated">生成时间 {{ formatDate(updatedAt) }}</text>
      <text v-if="summary" class="summary">{{ summary }}</text>
    </view>

    <view v-if="recommendations.length > 0" class="stats">
      <view
        v-for="group in groups"
        :key="group.strategy"
        class="stat"
      >
        <text class="stat-number">{{ group.items.length }}</text>
        <text class="stat-label">{{ group.strategy }}</text>
      </view>
    </view>

    <view v-if="profileSummaryItems.length > 0" class="profile-panel">
      <view class="profile-head">
        <view class="stamp">用户画像</view>
        <text class="profile-hint">本次推荐依据</text>
      </view>
      <view class="profile-grid">
        <view
          v-for="item in profileSummaryItems"
          :key="item.label"
          class="profile-item"
        >
          <text class="profile-label">{{ item.label }}</text>
          <text class="profile-value">{{ item.value }}</text>
        </view>
      </view>
    </view>

    <view v-if="recommendations.length > 0" class="groups">
      <view
        v-for="group in groups"
        :key="group.strategy"
        class="group"
      >
        <view class="group-head">
          <text class="group-title">{{ group.strategy }}档</text>
          <text class="group-count">{{ group.items.length }} 项</text>
        </view>

        <view
          v-for="(item, idx) in group.items"
          :key="itemKey(item, idx)"
          class="card"
        >
          <view class="card-head">
            <text class="card-title">{{ item.school_name || item.major_name || '推荐项' }}</text>
            <view class="card-actions">
              <view
                :class="['favorite-btn', { active: isFavorite(item) }]"
                @tap.stop="toggleFavorite(item)"
              >
                <text class="favorite-text">{{ isFavorite(item) ? '已收藏' : '收藏' }}</text>
              </view>
              <text class="badge">{{ strategyLabel(item) }}</text>
            </view>
          </view>

          <text v-if="item.category" class="meta">{{ item.category }}</text>
          <text v-if="item.reason" class="reason">{{ item.reason }}</text>

          <view class="metrics">
            <text v-if="typeof item.match_score === 'number'" class="metric">
              匹配 {{ percent(item.match_score) }}
            </text>
            <text v-if="typeof item.admission_probability === 'number'" class="metric">
              录取 {{ percent(item.admission_probability) }}
            </text>
            <text v-if="typeof item.employment_rate === 'number'" class="metric">
              就业 {{ percent(item.employment_rate) }}
            </text>
          </view>

          <view v-if="item.risk_points?.length" class="detail">
            <text class="detail-title">风险点</text>
            <text
              v-for="risk in item.risk_points"
              :key="risk"
              class="detail-item"
            >
              {{ risk }}
            </text>
          </view>

          <view v-if="item.alternatives?.length" class="detail">
            <text class="detail-title">替代方案</text>
            <text
              v-for="alternative in item.alternatives"
              :key="alternative"
              class="detail-item"
            >
              {{ alternative }}
            </text>
          </view>
        </view>
      </view>
    </view>

    <view v-else class="empty">
      <text class="empty-title">暂无推荐结果</text>
      <text class="empty-sub">回到咨询页生成志愿推荐后，这里会展示完整清单。</text>
      <view class="primary-btn" @tap="goChat">
        <text class="primary-text">返回咨询</text>
      </view>
    </view>

    <view class="actions">
      <view class="action-btn" @tap="goChat">
        <text class="action-text">继续咨询</text>
      </view>
      <view class="action-btn" @tap="copyMarkdownReport">
        <text class="action-text">复制报告</text>
      </view>
      <view class="action-btn" @tap="copyPdfLink">
        <text class="action-text">复制 PDF 链接</text>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import {
  backendProfileToChatContext,
  chatContextToSummaryItems,
  type MiniappChatContext,
} from '../../utils/profile'
import {
  copyMarkdownReportToClipboard,
  copyPdfReportLinkToClipboard,
  fetchFavoriteKeys,
  readFavoriteKeysFromStorage,
  recommendationKey,
  saveFavoriteKeys,
  writeFavoriteKeysToStorage,
} from '../../utils/recommendation'

interface RecommendationItem {
  school_name?: string
  major_name?: string
  category?: string
  reason?: string
  admission_probability?: number
  match_score?: number
  employment_rate?: number
  strategy?: string | null
  risk_points?: string[]
  alternatives?: string[]
}

interface RecommendationSnapshot {
  session_id?: string
  summary?: string
  recommendations?: RecommendationItem[]
  gradient_summary?: Partial<Record<string, string[]>>
  favorite_keys?: string[]
  profile_context?: MiniappChatContext | null
  updated_at?: string
}

interface ProfileResponse {
  profile?: Record<string, string | number | null>
}

const sessionId = ref('')
const summary = ref('')
const updatedAt = ref('')
const recommendations = ref<RecommendationItem[]>([])
const gradientSummary = ref<Partial<Record<string, string[]>>>({})
const favoriteKeys = ref<string[]>([])
const profileContext = ref<MiniappChatContext | null>(null)

onLoad((options) => {
  sessionId.value = options?.session_id || ''
  loadSnapshot()
  loadProfileSummary()
  loadFavorites()
})

onShareAppMessage(() => ({
  title: '我的志愿推荐结果',
  path: `/pages/result/index?session_id=${sessionId.value}`,
}))

const groups = computed(() => {
  const strategies = ['冲', '稳', '保']
  return strategies.map(strategy => ({
    strategy,
    items: recommendations.value.filter(item => strategyLabel(item) === strategy),
  })).filter(group => group.items.length > 0)
})

const profileSummaryItems = computed(() => chatContextToSummaryItems(profileContext.value))

function loadSnapshot() {
  if (!sessionId.value) return
  const raw = uni.getStorageSync(recommendationStorageKey()) as RecommendationSnapshot | ''
  if (!raw || typeof raw !== 'object') return

  summary.value = raw.summary || ''
  updatedAt.value = raw.updated_at || ''
  recommendations.value = raw.recommendations || []
  gradientSummary.value = raw.gradient_summary || {}
  favoriteKeys.value = raw.favorite_keys || readFavoriteKeysFromStorage(sessionId.value)
  profileContext.value = raw.profile_context || null
}

function recommendationStorageKey() {
  return `recommendation-result:${sessionId.value}`
}

function strategyLabel(item: RecommendationItem) {
  if (item.strategy === '冲' || item.strategy === '稳' || item.strategy === '保') return item.strategy
  if (typeof item.admission_probability !== 'number') return '稳'
  if (item.admission_probability >= 0.8) return '保'
  if (item.admission_probability >= 0.55) return '稳'
  return '冲'
}

function percent(value: number) {
  const normalized = value > 1 ? value / 10 : value
  return `${Math.round(Math.max(0, Math.min(1, normalized)) * 100)}%`
}

function itemKey(item: RecommendationItem, idx: number) {
  return `${idx}-${item.school_name || item.major_name || item.reason || 'recommendation'}`
}

function saveSnapshot() {
  if (!sessionId.value) return
  uni.setStorageSync(recommendationStorageKey(), {
    session_id: sessionId.value,
    summary: summary.value,
    recommendations: recommendations.value,
    gradient_summary: gradientSummary.value,
    favorite_keys: favoriteKeys.value,
    profile_context: profileContext.value,
    updated_at: updatedAt.value || new Date().toISOString(),
  })
}

async function loadProfileSummary() {
  if (!sessionId.value || profileSummaryItems.value.length > 0) return

  try {
    const res = await uni.request({
      url: `/api/profile/${sessionId.value}`,
      method: 'GET',
    })
    if (res.statusCode >= 400) return
    const data = res.data as ProfileResponse | undefined
    const context = backendProfileToChatContext(data?.profile)
    if (!context) return
    profileContext.value = context
    if (recommendations.value.length > 0 || summary.value) {
      saveSnapshot()
    }
  } catch {
    // 画像摘要不可用时不影响推荐结果展示。
  }
}

async function loadFavorites() {
  if (!sessionId.value) return
  const localKeys = readFavoriteKeysFromStorage(sessionId.value)
  if (localKeys.length > 0) {
    favoriteKeys.value = localKeys
  }

  const serverKeys = await fetchFavoriteKeys(sessionId.value)
  if (serverKeys) {
    favoriteKeys.value = serverKeys
    writeFavoriteKeysToStorage(sessionId.value, serverKeys)
    if (recommendations.value.length > 0 || summary.value) {
      saveSnapshot()
    }
  }
}

function isFavorite(item: RecommendationItem) {
  return favoriteKeys.value.includes(recommendationKey(item))
}

function toggleFavorite(item: RecommendationItem) {
  const key = recommendationKey(item)
  favoriteKeys.value = favoriteKeys.value.includes(key)
    ? favoriteKeys.value.filter(itemKey => itemKey !== key)
    : [...favoriteKeys.value, key]

  writeFavoriteKeysToStorage(sessionId.value, favoriteKeys.value)
  saveSnapshot()
  saveFavoriteKeys(sessionId.value, favoriteKeys.value).catch(() => {
    // 已写入本地缓存；后端同步失败不阻断用户操作。
  })
}

function formatDate(iso: string) {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return ''
  return `${date.getMonth() + 1}/${date.getDate()} ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
}

function goChat() {
  uni.navigateTo({ url: `/pages/chat/index?session_id=${sessionId.value}` })
}

async function copyMarkdownReport() {
  try {
    await saveFavoriteKeys(sessionId.value, favoriteKeys.value)
    await copyMarkdownReportToClipboard(sessionId.value)
    uni.showToast({ title: '报告已复制', icon: 'success' })
  } catch {
    uni.showToast({ title: '报告生成失败', icon: 'none' })
  }
}

async function copyPdfLink() {
  try {
    await copyPdfReportLinkToClipboard(sessionId.value)
    uni.showToast({ title: 'PDF 链接已复制', icon: 'success' })
  } catch {
    uni.showToast({ title: '复制失败', icon: 'none' })
  }
}
</script>

<style scoped>
.result {
  min-height: 100vh;
  background: #f5f0e8;
  padding: 24rpx;
  padding-bottom: calc(32rpx + env(safe-area-inset-bottom));
}
.header {
  border: 3rpx solid #1a1a2e;
  background: #fff;
  padding: 24rpx;
}
.stamp {
  display: inline-block;
  font-size: 20rpx;
  font-weight: 700;
  color: #1a1a2e;
  font-family: monospace;
  border: 2rpx solid #1a1a2e;
  padding: 4rpx 12rpx;
}
.title {
  display: block;
  margin-top: 18rpx;
  font-size: 40rpx;
  font-weight: 800;
  color: #1a1a2e;
  font-family: serif;
}
.updated,
.summary {
  display: block;
  margin-top: 12rpx;
  color: #1a1a2e;
  font-family: serif;
  line-height: 1.5;
}
.updated {
  font-size: 22rpx;
  color: #888;
  font-family: monospace;
}
.summary {
  font-size: 26rpx;
}
.stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12rpx;
  margin-top: 18rpx;
}
.stat {
  border: 2rpx solid #1a1a2e;
  background: #e8e3d8;
  padding: 18rpx;
  text-align: center;
}
.stat-number,
.stat-label {
  display: block;
  color: #1a1a2e;
}
.stat-number {
  font-size: 34rpx;
  font-weight: 800;
  font-family: monospace;
}
.stat-label {
  margin-top: 4rpx;
  font-size: 22rpx;
  font-family: serif;
}
.profile-panel {
  margin-top: 20rpx;
  border: 2rpx solid #1a1a2e;
  background: #fff;
  padding: 22rpx;
}
.profile-head {
  display: flex;
  align-items: center;
  gap: 12rpx;
  margin-bottom: 16rpx;
}
.profile-hint {
  font-size: 22rpx;
  color: #888;
  font-family: serif;
}
.profile-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12rpx;
}
.profile-item {
  min-width: 0;
  border: 1rpx solid #ddd;
  padding: 12rpx;
  background: #f5f0e8;
}
.profile-label,
.profile-value {
  display: block;
  font-family: serif;
  line-height: 1.4;
}
.profile-label {
  font-size: 20rpx;
  color: #888;
}
.profile-value {
  margin-top: 4rpx;
  font-size: 24rpx;
  font-weight: 700;
  color: #1a1a2e;
  word-break: break-all;
}
.groups {
  margin-top: 20rpx;
}
.group {
  margin-top: 24rpx;
}
.group-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 3rpx solid #1a1a2e;
  padding-bottom: 10rpx;
}
.group-title {
  font-size: 30rpx;
  font-weight: 800;
  color: #1a1a2e;
  font-family: serif;
}
.group-count {
  font-size: 22rpx;
  color: #888;
  font-family: monospace;
}
.card {
  margin-top: 16rpx;
  border: 2rpx solid #1a1a2e;
  background: #fff;
  padding: 22rpx;
}
.card-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16rpx;
}
.card-title {
  flex: 1;
  min-width: 0;
  font-size: 30rpx;
  font-weight: 800;
  color: #1a1a2e;
  font-family: serif;
  line-height: 1.35;
}
.card-actions {
  display: flex;
  align-items: center;
  gap: 8rpx;
  flex-shrink: 0;
}
.favorite-btn {
  min-width: 96rpx;
  height: 48rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2rpx solid #1a1a2e;
  background: #fff;
}
.favorite-btn.active {
  background: #1a1a2e;
}
.favorite-text {
  font-size: 20rpx;
  font-weight: 700;
  color: #1a1a2e;
  font-family: serif;
}
.favorite-btn.active .favorite-text {
  color: #c4a35a;
}
.badge {
  min-width: 48rpx;
  padding: 6rpx 12rpx;
  background: #1a1a2e;
  color: #c4a35a;
  font-size: 22rpx;
  font-weight: 700;
  text-align: center;
  font-family: serif;
}
.meta,
.reason {
  display: block;
  margin-top: 10rpx;
  font-size: 24rpx;
  color: #1a1a2e;
  font-family: serif;
  line-height: 1.5;
}
.meta {
  color: #888;
}
.metrics {
  display: flex;
  flex-wrap: wrap;
  gap: 10rpx;
  margin-top: 14rpx;
}
.metric {
  padding: 6rpx 12rpx;
  border: 1rpx solid #1a1a2e;
  font-size: 20rpx;
  color: #1a1a2e;
  font-family: monospace;
}
.detail {
  margin-top: 14rpx;
}
.detail-title,
.detail-item {
  display: block;
  font-family: serif;
}
.detail-title {
  font-size: 22rpx;
  font-weight: 700;
  color: #888;
  margin-bottom: 6rpx;
}
.detail-item {
  font-size: 24rpx;
  color: #1a1a2e;
  line-height: 1.5;
}
.empty {
  margin-top: 24rpx;
  border: 3rpx solid #1a1a2e;
  background: #fff;
  padding: 36rpx 24rpx;
  text-align: center;
}
.empty-title,
.empty-sub {
  display: block;
  font-family: serif;
}
.empty-title {
  font-size: 34rpx;
  font-weight: 800;
  color: #1a1a2e;
}
.empty-sub {
  margin-top: 12rpx;
  font-size: 24rpx;
  color: #888;
  line-height: 1.5;
}
.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12rpx;
  margin-top: 24rpx;
}
.action-btn,
.primary-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2rpx solid #1a1a2e;
  background: #fff;
  min-height: 72rpx;
  padding: 0 20rpx;
}
.action-btn {
  flex: 1 1 190rpx;
}
.primary-btn {
  margin: 24rpx auto 0;
  width: 220rpx;
  background: #1a1a2e;
}
.action-text,
.primary-text {
  font-size: 24rpx;
  font-weight: 700;
  font-family: serif;
}
.action-text {
  color: #1a1a2e;
}
.primary-text {
  color: #f5f0e8;
}
</style>
