<template>
  <view class="portal">
    <!-- 报头 -->
    <view class="masthead">
      <view class="masthead-top">
        <text class="date">{{ dateStr }}</text>
        <text class="issue">第 2026 期</text>
      </view>
      <view class="masthead-divider" />
      <view class="masthead-title">
        <text class="title-main">张雪峰 AI 咨询</text>
        <text class="title-sub">Data-Driven Truth</text>
      </view>
      <view class="masthead-divider" />
      <view class="masthead-slogan">
        <text class="slogan">选学校、选专业、选城市</text>
        <text class="slogan-accent">先看数据，再做决定</text>
      </view>
      <view class="masthead-divider-thin" />
    </view>

    <!-- 场景卡片 -->
    <view class="scenarios">
      <view
        v-for="item in scenarios"
        :key="item.id"
        class="scenario-card"
        @tap="onSelect(item.id)"
      >
        <view class="card-badge">
          <text class="badge-text">{{ item.section }}</text>
        </view>
        <text class="card-icon">{{ item.icon }}</text>
        <text class="card-title">{{ item.title }}</text>
        <text class="card-subtitle">{{ item.subtitle }}</text>
        <view class="card-divider" />
        <view class="card-action">
          <text class="action-text">开始咨询</text>
          <text class="action-arrow">→</text>
        </view>
      </view>
    </view>

    <!-- 数据快报 -->
    <view class="stats-bar">
      <view class="stats-header">
        <view class="stamp">数据快报</view>
        <view class="stats-line" />
      </view>
      <view class="stats-grid">
        <view class="stat-item">
          <text class="stat-number">3,700+</text>
          <text class="stat-label">覆盖全国院校</text>
        </view>
        <view class="stat-item">
          <text class="stat-number">580+</text>
          <text class="stat-label">本科专业</text>
        </view>
        <view class="stat-item">
          <text class="stat-number">85,000+</text>
          <text class="stat-label">录取分数线</text>
        </view>
      </view>
    </view>

    <!-- 历史会话 -->
    <view v-if="sessions.length > 0" class="history">
      <view class="history-header">
        <view class="stamp">历史会话</view>
        <view class="history-line" />
      </view>
      <view
        v-for="s in sessions"
        :key="s.session_id"
        class="history-item"
        @tap="onResume(s.session_id)"
      >
        <text class="history-id">{{ s.session_id.slice(0, 8) }}...</text>
        <text class="history-count">{{ s.message_count }} 条消息</text>
        <text class="history-date">{{ formatDate(s.created_at) }}</text>
      </view>
    </view>

    <!-- 底部 -->
    <view class="footer">
      <text class="footer-text">数据驱动 · 说真话 · 不画饼</text>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'

const scenarios = [
  { id: 'gaokao', title: '高考志愿填报', subtitle: '分数出来别慌，我帮你算明白', icon: '🎓', section: 'A 版' },
  { id: 'kaoyan', title: '考研规划', subtitle: '选对学校和专业，比努力更重要', icon: '📚', section: 'B 版' },
  { id: 'career', title: '职业规划', subtitle: '选专业之前，先看看就业真相', icon: '💼', section: 'C 版' },
]

interface SessionSummary {
  session_id: string
  created_at: string
  message_count: number
}

const sessions = ref<SessionSummary[]>([])
const today = new Date()
const dateStr = `${today.getFullYear()} 年 ${today.getMonth() + 1} 月 ${today.getDate()} 日`

onMounted(() => {
  uni.request({
    url: '/api/sessions?limit=10',
    success: (res) => {
      if (res.data) sessions.value = res.data as SessionSummary[]
    },
  })
})

function onSelect(id: string) {
  uni.navigateTo({ url: `/pages/form/index?scenario=${id}` })
}

function onResume(sid: string) {
  uni.navigateTo({ url: `/pages/chat/index?session_id=${sid}` })
}

function formatDate(iso: string) {
  const d = new Date(iso)
  return `${d.getMonth() + 1}/${d.getDate()}`
}
</script>

<style scoped>
.portal {
  min-height: 100vh;
  background: #f5f0e8;
  padding: 0 24rpx 40rpx;
}

/* 报头 */
.masthead {
  padding: 32rpx 0 24rpx;
  text-align: center;
}
.masthead-top {
  display: flex;
  justify-content: space-between;
  font-size: 20rpx;
  color: #888;
  font-family: monospace;
  margin-bottom: 16rpx;
}
.masthead-divider {
  height: 4rpx;
  background: #1a1a2e;
  margin: 12rpx 0;
}
.masthead-divider-thin {
  height: 2rpx;
  background: #1a1a2e;
  margin: 8rpx 0;
}
.masthead-title {
  margin: 16rpx 0;
}
.title-main {
  display: block;
  font-size: 52rpx;
  font-weight: 900;
  color: #1a1a2e;
  font-family: serif;
  letter-spacing: 4rpx;
}
.title-sub {
  display: block;
  font-size: 20rpx;
  color: #888;
  font-family: monospace;
  letter-spacing: 6rpx;
  text-transform: uppercase;
  margin-top: 8rpx;
}
.masthead-slogan {
  margin: 16rpx 0;
}
.slogan {
  display: block;
  font-size: 32rpx;
  font-weight: 700;
  color: #1a1a2e;
  font-family: serif;
}
.slogan-accent {
  display: block;
  font-size: 28rpx;
  font-weight: 700;
  color: #c4a35a;
  font-family: serif;
  margin-top: 8rpx;
}

/* 场景卡片 */
.scenarios {
  margin: 24rpx 0;
}
.scenario-card {
  position: relative;
  background: #fff;
  border: 3rpx solid #1a1a2e;
  padding: 32rpx;
  margin-bottom: 20rpx;
}
.card-badge {
  position: absolute;
  top: 0;
  left: 0;
  background: #1a1a2e;
  padding: 8rpx 20rpx;
}
.badge-text {
  font-size: 20rpx;
  color: #f5f0e8;
  font-family: monospace;
  font-weight: 700;
}
.card-icon {
  display: block;
  font-size: 56rpx;
  margin: 24rpx 0 16rpx;
}
.card-title {
  display: block;
  font-size: 36rpx;
  font-weight: 700;
  color: #1a1a2e;
  font-family: serif;
  letter-spacing: 2rpx;
}
.card-subtitle {
  display: block;
  font-size: 24rpx;
  color: #888;
  font-family: serif;
  font-style: italic;
  margin-top: 8rpx;
}
.card-divider {
  height: 2rpx;
  background: #ddd;
  margin: 20rpx 0;
}
.card-action {
  display: flex;
  align-items: center;
  gap: 8rpx;
}
.action-text {
  font-size: 28rpx;
  font-weight: 700;
  color: #c4a35a;
  font-family: serif;
}
.action-arrow {
  font-size: 28rpx;
  color: #c4a35a;
}

/* 数据快报 */
.stats-bar {
  border: 3rpx solid #1a1a2e;
  background: #e8e3d8;
  padding: 24rpx;
  margin: 24rpx 0;
}
.stats-header {
  display: flex;
  align-items: center;
  gap: 12rpx;
  margin-bottom: 20rpx;
}
.stamp {
  font-size: 20rpx;
  font-weight: 700;
  color: #1a1a2e;
  font-family: monospace;
  border: 2rpx solid #1a1a2e;
  padding: 4rpx 12rpx;
  text-transform: uppercase;
}
.stats-line {
  flex: 1;
  height: 2rpx;
  background: #1a1a2e;
}
.stats-grid {
  display: flex;
  justify-content: space-around;
}
.stat-item {
  text-align: center;
}
.stat-number {
  display: block;
  font-size: 40rpx;
  font-weight: 900;
  color: #1a1a2e;
  font-family: monospace;
}
.stat-label {
  display: block;
  font-size: 20rpx;
  color: #888;
  font-family: serif;
  margin-top: 8rpx;
}

/* 历史会话 */
.history {
  border: 3rpx solid #1a1a2e;
  background: #fff;
  padding: 24rpx;
  margin: 24rpx 0;
}
.history-header {
  display: flex;
  align-items: center;
  gap: 12rpx;
  margin-bottom: 16rpx;
}
.history-line {
  flex: 1;
  height: 2rpx;
  background: #1a1a2e;
}
.history-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16rpx 0;
  border-bottom: 1rpx solid #eee;
}
.history-item:last-child {
  border-bottom: none;
}
.history-id {
  font-size: 24rpx;
  font-family: monospace;
  color: #1a1a2e;
}
.history-count {
  font-size: 22rpx;
  color: #888;
}
.history-date {
  font-size: 22rpx;
  color: #888;
  font-family: monospace;
}

/* 底部 */
.footer {
  text-align: center;
  padding: 32rpx 0;
}
.footer-text {
  font-size: 20rpx;
  color: #888;
  font-family: monospace;
}
</style>
