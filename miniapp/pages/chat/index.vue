<template>
  <view class="chat">
    <!-- 消息区域 -->
    <scroll-view
      class="messages"
      scroll-y
      :scroll-into-view="scrollTarget"
      scroll-with-animation
    >
      <!-- 欢迎消息 -->
      <view v-if="messages.length === 0" class="welcome">
        <view class="welcome-quote">"</view>
        <text class="welcome-title">你好！我是张雪峰 AI 助手</text>
        <text class="welcome-sub">高考志愿填报、考研择校、职业规划，有什么问题尽管问我！</text>
        <view class="welcome-divider" />
      </view>

      <!-- 消息列表 -->
      <view
        v-for="(msg, idx) in messages"
        :key="idx"
        :id="'msg-' + idx"
        :class="['message', msg.role]"
      >
        <view v-if="msg.role === 'assistant'" class="avatar">
          <text class="avatar-text">张</text>
        </view>
        <view class="bubble">
          <text class="bubble-text">{{ msg.content }}</text>
        </view>
      </view>

      <!-- 加载状态 -->
      <view v-if="isLoading" class="message assistant">
        <view class="avatar">
          <text class="avatar-text">张</text>
        </view>
        <view class="bubble loading-bubble">
          <view class="dot" />
          <view class="dot" />
          <view class="dot" />
        </view>
      </view>

      <!-- 推荐结果 -->
      <view v-if="recommendations.length > 0" class="recommend-panel">
        <view class="recommend-header">
          <view class="stamp">志愿推荐</view>
          <text v-if="recommendSummary" class="recommend-summary">{{ recommendSummary }}</text>
          <view class="result-link" @tap="onViewResult">
            <text class="result-link-text">查看完整结果</text>
          </view>
        </view>
        <view
          v-for="(item, idx) in recommendations"
          :key="itemKey(item, idx)"
          class="recommend-card"
        >
          <view class="recommend-card-head">
            <text class="recommend-title">{{ item.school_name || item.major_name || '推荐项' }}</text>
            <view class="recommend-actions">
              <view
                :class="['favorite-btn', { active: isFavorite(item) }]"
                @tap.stop="toggleFavorite(item)"
              >
                <text class="favorite-text">{{ isFavorite(item) ? '已收藏' : '收藏' }}</text>
              </view>
              <text class="recommend-badge">{{ strategyLabel(item) }}</text>
            </view>
          </view>
          <text v-if="item.category" class="recommend-meta">{{ item.category }}</text>
          <text v-if="item.reason" class="recommend-reason">{{ item.reason }}</text>
          <view class="metric-row">
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
          <view v-if="item.risk_points?.length" class="detail-list">
            <text class="detail-title">风险点</text>
            <text
              v-for="risk in item.risk_points"
              :key="risk"
              class="detail-item"
            >
              {{ risk }}
            </text>
          </view>
          <view v-if="item.alternatives?.length" class="detail-list">
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

      <view id="msg-bottom" />
    </scroll-view>

    <!-- 推荐入口 -->
    <view class="quick-actions">
      <view
        :class="['quick-btn', { disabled: isLoading || isRecommending }]"
        @tap="onRecommend"
      >
        <text class="quick-text">{{ isRecommending ? '推荐生成中' : '生成志愿推荐' }}</text>
      </view>
      <view
        :class="['quick-btn', { disabled: isExporting }]"
        @tap="onCopyMarkdownReport"
      >
        <text class="quick-text">{{ isExporting ? '报告生成中' : '复制报告' }}</text>
      </view>
      <view class="quick-btn" @tap="onCopyPdfLink">
        <text class="quick-text">复制 PDF 链接</text>
      </view>
    </view>

    <!-- 输入区域 -->
    <view class="input-bar">
      <input
        v-model="input"
        class="input-field"
        placeholder="输入你的问题..."
        :disabled="isLoading"
        @confirm="onSend"
        confirm-type="send"
      />
      <view
        :class="['send-btn', { disabled: !input.trim() || isLoading }]"
        @tap="onSend"
      >
        <text class="send-text">发送</text>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, nextTick } from 'vue'
import { backendProfileToChatContext, type MiniappChatContext } from '../../utils/profile'
import {
  copyMarkdownReportToClipboard,
  copyPdfReportLinkToClipboard,
  fetchFavoriteKeys,
  readFavoriteKeysFromStorage,
  recommendationKey,
  saveFavoriteKeys,
  writeFavoriteKeysToStorage,
} from '../../utils/recommendation'

interface Message {
  role: 'user' | 'assistant'
  content: string
}

interface ProfileResponse {
  profile?: Record<string, string | number | null>
}

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

interface RecommendResponse {
  recommendations?: RecommendationItem[]
  summary?: string
  gradient_summary?: Partial<Record<string, string[]>>
}

const messages = ref<Message[]>([])
const input = ref('')
const isLoading = ref(false)
const isRecommending = ref(false)
const isExporting = ref(false)
const scrollTarget = ref('msg-bottom')
const sessionId = ref('')
const recommendations = ref<RecommendationItem[]>([])
const recommendSummary = ref('')
const gradientSummary = ref<Partial<Record<string, string[]>>>({})
const favoriteKeys = ref<string[]>([])
const recommendationProfileContext = ref<MiniappChatContext | null>(null)

// 页面加载
onLoad((options) => {
  sessionId.value = options?.session_id || generateId()
  loadFavorites()
  if (options?.session_id) {
    loadHistory()
  }
})

onShareAppMessage(() => ({
  title: '我的志愿咨询报告',
  path: `/pages/chat/index?session_id=${sessionId.value}`,
}))

function generateId() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0
    const v = c === 'x' ? r : (r & 0x3) | 0x8
    return v.toString(16)
  })
}

async function loadHistory() {
  try {
    const res = await uni.request({
      url: `/api/session/${sessionId.value}`,
      method: 'GET',
    })
    if (res.statusCode >= 400) return
    if (res.data?.messages?.length) {
      messages.value = res.data.messages
        .filter((m: any) => m.role === 'user' || m.role === 'assistant')
        .map((m: any) => ({ role: m.role, content: m.content || '' }))
    }
  } catch (e) {
    // 忽略
  }
}

async function onSend() {
  if (!input.value.trim() || isLoading.value) return

  const userMsg = input.value.trim()
  input.value = ''

  messages.value.push({ role: 'user', content: userMsg })
  isLoading.value = true
  scrollToBottom()

  try {
    const res = await uni.request({
      url: '/api/chat',
      method: 'POST',
      data: {
        session_id: sessionId.value,
        message: userMsg,
        user_context: await loadProfileContext(),
        stream: false,
      },
    })
    if (res.statusCode >= 400) {
      throw new Error(`Chat failed: ${res.statusCode}`)
    }

    if (res.data?.reply) {
      messages.value.push({ role: 'assistant', content: res.data.reply })
    }
  } catch (e) {
    messages.value.push({ role: 'assistant', content: '抱歉，发生了错误，请重试。' })
  } finally {
    isLoading.value = false
    scrollToBottom()
  }
}

async function loadProfileContext(): Promise<MiniappChatContext | null> {
  try {
    const res = await uni.request({
      url: `/api/profile/${sessionId.value}`,
      method: 'GET',
    })
    if (res.statusCode >= 400) return null
    const data = res.data as ProfileResponse | undefined
    return backendProfileToChatContext(data?.profile)
  } catch {
    return null
  }
}

async function onRecommend() {
  if (isLoading.value || isRecommending.value) return

  isRecommending.value = true
  try {
    const userContext = await loadProfileContext()
    const res = await uni.request({
      url: '/api/recommend',
      method: 'POST',
      data: {
        session_id: sessionId.value,
        message: '请根据我的画像生成高考志愿推荐，按冲稳保给出学校或专业建议。',
        user_context: userContext,
      },
    })
    if (res.statusCode >= 400) {
      throw new Error(`Recommend failed: ${res.statusCode}`)
    }
    const data = res.data as RecommendResponse | undefined
    recommendations.value = data?.recommendations || []
    recommendSummary.value = data?.summary || ''
    gradientSummary.value = data?.gradient_summary || {}
    recommendationProfileContext.value = userContext
    saveRecommendationSnapshot(userContext)
    if (!recommendations.value.length && !recommendSummary.value) {
      messages.value.push({ role: 'assistant', content: '暂时没有生成推荐结果，可以先补充位次、批次和目标城市。' })
    }
  } catch {
    messages.value.push({ role: 'assistant', content: '推荐生成失败，请稍后再试。' })
  } finally {
    isRecommending.value = false
    scrollToBottom()
  }
}

function saveRecommendationSnapshot(profileContext = recommendationProfileContext.value) {
  uni.setStorageSync(recommendationStorageKey(), {
    session_id: sessionId.value,
    summary: recommendSummary.value,
    recommendations: recommendations.value,
    gradient_summary: gradientSummary.value,
    favorite_keys: favoriteKeys.value,
    profile_context: profileContext,
    updated_at: new Date().toISOString(),
  })
}

function recommendationStorageKey() {
  return `recommendation-result:${sessionId.value}`
}

function onViewResult() {
  if (!recommendations.value.length) return
  saveRecommendationSnapshot()
  uni.navigateTo({ url: `/pages/result/index?session_id=${sessionId.value}` })
}

async function loadFavorites() {
  favoriteKeys.value = readFavoriteKeysFromStorage(sessionId.value)
  const serverKeys = await fetchFavoriteKeys(sessionId.value)
  if (serverKeys) {
    favoriteKeys.value = serverKeys
    writeFavoriteKeysToStorage(sessionId.value, serverKeys)
    if (recommendations.value.length > 0 || recommendSummary.value) {
      saveRecommendationSnapshot()
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
  saveRecommendationSnapshot()
  saveFavoriteKeys(sessionId.value, favoriteKeys.value).catch(() => {
    // 已写入本地缓存；后端同步失败不阻断用户操作。
  })
}

async function onCopyMarkdownReport() {
  if (isExporting.value) return

  isExporting.value = true
  try {
    await copyMarkdownReportToClipboard(sessionId.value)
    uni.showToast({ title: '报告已复制', icon: 'success' })
  } catch {
    uni.showToast({ title: '报告生成失败，请稍后再试', icon: 'none' })
  } finally {
    isExporting.value = false
  }
}

async function onCopyPdfLink() {
  try {
    await copyPdfReportLinkToClipboard(sessionId.value)
    uni.showToast({ title: 'PDF 链接已复制', icon: 'success' })
  } catch {
    uni.showToast({ title: '复制失败，请重试', icon: 'none' })
  }
}

function scrollToBottom() {
  nextTick(() => {
    scrollTarget.value = ''
    setTimeout(() => {
      scrollTarget.value = 'msg-bottom'
    }, 50)
  })
}

function itemKey(item: RecommendationItem, idx: number) {
  return `${idx}-${item.school_name || item.major_name || item.reason || 'recommendation'}`
}

function percent(value: number) {
  const normalized = value > 1 ? value / 10 : value
  return `${Math.round(Math.max(0, Math.min(1, normalized)) * 100)}%`
}

function strategyLabel(item: RecommendationItem) {
  if (item.strategy) return item.strategy
  if (typeof item.admission_probability !== 'number') return '稳'
  if (item.admission_probability >= 0.8) return '保'
  if (item.admission_probability >= 0.55) return '稳'
  return '冲'
}
</script>

<style scoped>
.chat {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: #f5f0e8;
}

/* 消息区域 */
.messages {
  flex: 1;
  padding: 24rpx;
  overflow-y: auto;
}

/* 欢迎 */
.welcome {
  text-align: center;
  padding: 80rpx 40rpx;
}
.welcome-quote {
  font-size: 80rpx;
  color: #c4a35a;
  font-family: serif;
  line-height: 1;
}
.welcome-title {
  display: block;
  font-size: 36rpx;
  font-weight: 700;
  color: #1a1a2e;
  font-family: serif;
  margin: 16rpx 0;
}
.welcome-sub {
  display: block;
  font-size: 26rpx;
  color: #888;
  font-family: serif;
}
.welcome-divider {
  height: 2rpx;
  background: #1a1a2e;
  margin-top: 40rpx;
  max-width: 200rpx;
  margin-left: auto;
  margin-right: auto;
}

/* 消息 */
.message {
  display: flex;
  gap: 16rpx;
  margin-bottom: 24rpx;
}
.message.user {
  flex-direction: row-reverse;
}
.avatar {
  width: 64rpx;
  height: 64rpx;
  background: #1a1a2e;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.avatar-text {
  font-size: 28rpx;
  font-weight: 700;
  color: #c4a35a;
  font-family: serif;
}
.bubble {
  max-width: 70%;
  padding: 20rpx 24rpx;
  border: 2rpx solid #1a1a2e;
}
.message.assistant .bubble {
  background: #fff;
}
.message.user .bubble {
  background: #1a1a2e;
}
.message.user .bubble-text {
  color: #f5f0e8;
}
.bubble-text {
  font-size: 28rpx;
  color: #1a1a2e;
  font-family: serif;
  line-height: 1.6;
}

/* 加载动画 */
.loading-bubble {
  display: flex;
  gap: 8rpx;
  align-items: center;
  padding: 24rpx 32rpx;
}
.dot {
  width: 12rpx;
  height: 12rpx;
  background: #888;
  border-radius: 50%;
  animation: bounce 1.4s infinite;
}
.dot:nth-child(2) { animation-delay: 0.2s; }
.dot:nth-child(3) { animation-delay: 0.4s; }
@keyframes bounce {
  0%, 80%, 100% { transform: translateY(0); }
  40% { transform: translateY(-10rpx); }
}

/* 推荐结果 */
.recommend-panel {
  border: 3rpx solid #1a1a2e;
  background: #e8e3d8;
  padding: 20rpx;
  margin: 16rpx 0 28rpx;
}
.recommend-header {
  margin-bottom: 16rpx;
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
.recommend-summary {
  display: block;
  margin-top: 12rpx;
  font-size: 24rpx;
  color: #1a1a2e;
  font-family: serif;
  line-height: 1.5;
}
.result-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  margin-top: 16rpx;
  border: 2rpx solid #1a1a2e;
  background: #fff;
  padding: 8rpx 18rpx;
}
.result-link-text {
  font-size: 22rpx;
  font-weight: 700;
  color: #1a1a2e;
  font-family: serif;
}
.recommend-card {
  background: #fff;
  border: 2rpx solid #1a1a2e;
  padding: 20rpx;
  margin-top: 16rpx;
}
.recommend-card-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16rpx;
}
.recommend-title {
  flex: 1;
  min-width: 0;
  font-size: 30rpx;
  font-weight: 700;
  color: #1a1a2e;
  font-family: serif;
  line-height: 1.35;
}
.recommend-actions {
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
.recommend-badge {
  min-width: 48rpx;
  padding: 6rpx 12rpx;
  background: #1a1a2e;
  color: #c4a35a;
  font-size: 22rpx;
  font-weight: 700;
  text-align: center;
  font-family: serif;
}
.recommend-meta,
.recommend-reason {
  display: block;
  margin-top: 10rpx;
  font-size: 24rpx;
  color: #1a1a2e;
  font-family: serif;
  line-height: 1.5;
}
.recommend-meta {
  color: #888;
}
.metric-row {
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
.detail-list {
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

/* 快捷操作 */
.quick-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12rpx;
  padding: 16rpx 24rpx 0;
  background: #e8e3d8;
  border-top: 3rpx solid #1a1a2e;
}
.quick-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 1 1 180rpx;
  height: 68rpx;
  border: 2rpx solid #1a1a2e;
  background: #fff;
}
.quick-btn.disabled {
  opacity: 0.5;
}
.quick-text {
  font-size: 24rpx;
  font-weight: 700;
  color: #1a1a2e;
  font-family: serif;
}

/* 输入区域 */
.input-bar {
  display: flex;
  gap: 16rpx;
  padding: 20rpx 24rpx;
  background: #e8e3d8;
  border-top: 3rpx solid #1a1a2e;
  padding-bottom: calc(20rpx + env(safe-area-inset-bottom));
}
.input-field {
  flex: 1;
  height: 80rpx;
  padding: 0 24rpx;
  border: 3rpx solid #1a1a2e;
  background: #fff;
  font-size: 28rpx;
  font-family: serif;
}
.send-btn {
  width: 140rpx;
  height: 80rpx;
  background: #1a1a2e;
  display: flex;
  align-items: center;
  justify-content: center;
}
.send-btn.disabled {
  opacity: 0.5;
}
.send-text {
  font-size: 28rpx;
  font-weight: 700;
  color: #f5f0e8;
  font-family: serif;
}
</style>
