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

      <view id="msg-bottom" />
    </scroll-view>

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

interface Message {
  role: 'user' | 'assistant'
  content: string
}

const messages = ref<Message[]>([])
const input = ref('')
const isLoading = ref(false)
const scrollTarget = ref('msg-bottom')
const sessionId = ref('')

// 页面加载
onLoad((options) => {
  sessionId.value = options?.session_id || generateId()
  if (options?.session_id) {
    loadHistory()
  }
})

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
        stream: false,
      },
    })

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

function scrollToBottom() {
  nextTick(() => {
    scrollTarget.value = ''
    setTimeout(() => {
      scrollTarget.value = 'msg-bottom'
    }, 50)
  })
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
