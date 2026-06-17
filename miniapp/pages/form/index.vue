<template>
  <view class="form-page">
    <!-- 进度条 -->
    <view class="progress">
      <view class="progress-bar">
        <view class="progress-fill" :style="{ width: `${(step / totalSteps) * 100}%` }" />
      </view>
      <text class="progress-text">{{ step }} / {{ totalSteps }}</text>
    </view>

    <!-- 步骤内容 -->
    <view class="step-content">
      <!-- Step 1: 分数 -->
      <view v-if="step === 1" class="step">
        <view class="step-header">
          <view class="stamp">STEP 1</view>
          <text class="step-title">考了多少分？</text>
        </view>
        <text class="step-hint">先把这个告诉我，我才能给你分析。</text>
        <input
          v-model="profile.score"
          class="input-field"
          type="number"
          placeholder="输入高考分数（100-750）"
          @input="validateScore"
        />
        <text v-if="scoreError" class="error-text">{{ scoreError }}</text>
      </view>

      <!-- Step 2: 省份 -->
      <view v-if="step === 2" class="step">
        <view class="step-header">
          <view class="stamp">STEP 2</view>
          <text class="step-title">哪个省的？</text>
        </view>
        <text class="step-hint">不同省差别太大了，这个很重要。</text>
        <scroll-view scroll-y class="province-list">
          <view
            v-for="p in provinces"
            :key="p"
            :class="['province-item', { active: profile.province === p }]"
            @tap="profile.province = p"
          >
            <text class="province-text">{{ p }}</text>
          </view>
        </scroll-view>
      </view>

      <!-- Step 3: 科类 -->
      <view v-if="step === 3" class="step">
        <view class="step-header">
          <view class="stamp">STEP 3</view>
          <text class="step-title">文科还是理科？</text>
        </view>
        <text class="step-hint">新高考的话告诉我选科组合。</text>
        <view class="radio-group">
          <view
            :class="['radio-item', { active: profile.subject === '综合' }]"
            @tap="profile.subject = '综合'"
          >
            <text class="radio-text">综合</text>
          </view>
          <view
            :class="['radio-item', { active: profile.subject === '理科' }]"
            @tap="profile.subject = '理科'"
          >
            <text class="radio-text">理科</text>
          </view>
          <view
            :class="['radio-item', { active: profile.subject === '文科' }]"
            @tap="profile.subject = '文科'"
          >
            <text class="radio-text">文科</text>
          </view>
        </view>
      </view>

      <!-- Step 4: 家庭条件与预算 -->
      <view v-if="step === 4" class="step">
        <view class="step-header">
          <view class="stamp">STEP 4</view>
          <text class="step-title">家庭条件和预算？</text>
        </view>
        <text class="step-hint">这个决定了完全不同的策略。</text>
        <view class="radio-group">
          <view
            v-for="opt in familyOptions"
            :key="opt"
            :class="['radio-item', { active: profile.familyCondition === opt }]"
            @tap="profile.familyCondition = opt"
          >
            <text class="radio-text">{{ opt }}</text>
          </view>
        </view>
        <view class="field-block">
          <text class="field-label">家庭预算</text>
          <view class="radio-group compact">
            <view
              v-for="opt in budgetOptions"
              :key="opt"
              :class="['radio-item', { active: profile.budget === opt }]"
              @tap="profile.budget = opt"
            >
              <text class="radio-text">{{ opt }}</text>
            </view>
          </view>
        </view>
      </view>

      <!-- Step 5: 批次与位次 -->
      <view v-if="step === 5" class="step">
        <view class="step-header">
          <view class="stamp">STEP 5</view>
          <text class="step-title">批次和位次？</text>
        </view>
        <text class="step-hint">位次比分数更能说明竞争位置，可以先填大概。</text>
        <view class="field-block">
          <text class="field-label">省份批次</text>
          <input
            v-model="profile.admissionBatch"
            class="input-field"
            placeholder="如：本科一批 / 本科批"
          />
        </view>
        <view class="field-block">
          <text class="field-label">省内位次</text>
          <input
            v-model="profile.rank"
            class="input-field"
            type="number"
            placeholder="如：12000"
          />
        </view>
        <view class="field-block">
          <text class="field-label">选科限制</text>
          <input
            v-model="profile.subjectRequirements"
            class="input-field"
            placeholder="如：物理+化学 / 不限"
          />
        </view>
      </view>

      <!-- Step 6: 地域偏好 -->
      <view v-if="step === 6" class="step">
        <view class="step-header">
          <view class="stamp">STEP 6</view>
          <text class="step-title">想去哪里？</text>
        </view>
        <text class="step-hint">城市和地域会影响实习、就业和生活成本。</text>
        <view class="field-block">
          <text class="field-label">目标城市</text>
          <input
            v-model="profile.targetCity"
            class="input-field"
            placeholder="如：北京、上海、成都"
          />
        </view>
        <view class="field-block">
          <text class="field-label">地域偏好</text>
          <input
            v-model="profile.regionPreference"
            class="input-field"
            placeholder="如：华北、长三角、珠三角"
          />
        </view>
        <view class="field-block">
          <text class="field-label">城市层级</text>
          <view class="radio-group compact">
            <view
              v-for="opt in cityTierOptions"
              :key="opt"
              :class="['radio-item', { active: profile.cityTier === opt }]"
              @tap="profile.cityTier = opt"
            >
              <text class="radio-text">{{ opt }}</text>
            </view>
          </view>
        </view>
      </view>

      <!-- Step 7: 职业偏好 -->
      <view v-if="step === 7" class="step">
        <view class="step-header">
          <view class="stamp">STEP 7</view>
          <text class="step-title">以后想干什么？</text>
        </view>
        <text class="step-hint">职业方向越明确，专业建议越不容易跑偏。</text>
        <view class="field-block">
          <text class="field-label">职业方向</text>
          <input
            v-model="profile.careerGoal"
            class="input-field"
            placeholder="如：计算机、金融、医学"
          />
        </view>
        <view class="field-block">
          <text class="field-label">风险偏好</text>
          <view class="radio-group compact">
            <view
              v-for="opt in riskOptions"
              :key="opt"
              :class="['radio-item', { active: profile.riskTolerance === opt }]"
              @tap="profile.riskTolerance = opt"
            >
              <text class="radio-text">{{ opt }}</text>
            </view>
          </view>
        </view>
        <view class="field-block">
          <text class="field-label">职业偏好权重（1-10）</text>
          <input
            v-model="profile.careerPreferenceWeight"
            class="input-field"
            type="number"
            placeholder="越看重就业就填得越高"
          />
        </view>
      </view>
    </view>

    <!-- 按钮 -->
    <view class="actions">
      <view v-if="step > 1" class="btn-secondary" @tap="step--">
        <text class="btn-text">上一步</text>
      </view>
      <view class="spacer" />
      <view v-if="step > 4 && step < totalSteps" class="btn-skip" @tap="onSkip">
        <text class="btn-text">跳过</text>
      </view>
      <view
        :class="['btn-primary', { disabled: !canProceed }]"
        @tap="onNext"
      >
        <text class="btn-text">{{ step === totalSteps ? '开始咨询' : '下一步' }}</text>
      </view>
    </view>

    <!-- 编者按 -->
    <view class="editor-note">
      <text class="note-text">编者按：信息越完整，建议越精准。所有信息仅用于咨询服务。</text>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { updateUserProfile } from '../../utils/profile'

const step = ref(1)
const totalSteps = 7
const profile = ref({
  score: '',
  province: '',
  subject: '',
  familyCondition: '',
  targetCity: '',
  riskTolerance: '',
  careerGoal: '',
  admissionBatch: '',
  subjectRequirements: '',
  rank: '',
  budget: '',
  regionPreference: '',
  cityTier: '',
  careerPreferenceWeight: '',
})
const scoreError = ref('')

const provinces = [
  '北京', '天津', '上海', '重庆', '河北', '山西', '辽宁', '吉林',
  '黑龙江', '江苏', '浙江', '安徽', '福建', '江西', '山东', '河南',
  '湖北', '湖南', '广东', '海南', '四川', '贵州', '云南', '陕西',
  '甘肃', '青海', '内蒙古', '广西', '西藏', '宁夏', '新疆',
]

const familyOptions = ['工薪阶层', '经商家庭', '体制内家庭', '其他']
const budgetOptions = ['不限', '5000以内/年', '5000-10000/年', '10000-20000/年', '20000以上/年', '中外合作办学']
const cityTierOptions = ['一线城市', '新一线城市', '省会城市', '不限']
const riskOptions = ['保守', '稳健', '激进']

const canProceed = computed(() => {
  if (step.value === 1) return profile.value.score && !scoreError.value
  if (step.value === 2) return !!profile.value.province
  if (step.value === 3) return !!profile.value.subject
  if (step.value === 4) return !!profile.value.familyCondition
  return true
})

function validateScore() {
  const s = Number(profile.value.score)
  if (s && (s < 100 || s > 750)) {
    scoreError.value = '分数应在 100-750 之间'
  } else {
    scoreError.value = ''
  }
}

function onNext() {
  if (!canProceed.value) return
  if (step.value < totalSteps) {
    step.value++
  } else {
    onSubmit()
  }
}

function onSkip() {
  if (step.value < totalSteps) step.value++
}

async function onSubmit() {
  const sessionId = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0
    const v = c === 'x' ? r : (r & 0x3) | 0x8
    return v.toString(16)
  })

  try {
    uni.showLoading({ title: '保存中' })
    await updateUserProfile(sessionId, profile.value)
    uni.navigateTo({ url: `/pages/chat/index?session_id=${sessionId}` })
  } catch {
    uni.showToast({ title: '画像保存失败，请重试', icon: 'none' })
  } finally {
    uni.hideLoading()
  }
}
</script>

<style scoped>
.form-page {
  min-height: 100vh;
  background: #f5f0e8;
  padding: 0 32rpx 40rpx;
}

/* 进度条 */
.progress {
  padding: 24rpx 0;
}
.progress-bar {
  height: 8rpx;
  background: #ddd;
  border: 2rpx solid #1a1a2e;
}
.progress-fill {
  height: 100%;
  background: #c4a35a;
  transition: width 0.3s;
}
.progress-text {
  display: block;
  text-align: right;
  font-size: 22rpx;
  color: #888;
  font-family: monospace;
  margin-top: 8rpx;
}

/* 步骤 */
.step {
  margin: 24rpx 0;
}
.step-header {
  display: flex;
  align-items: center;
  gap: 16rpx;
  margin-bottom: 16rpx;
}
.stamp {
  font-size: 20rpx;
  font-weight: 700;
  color: #1a1a2e;
  font-family: monospace;
  border: 2rpx solid #1a1a2e;
  padding: 4rpx 12rpx;
}
.step-title {
  font-size: 40rpx;
  font-weight: 900;
  color: #1a1a2e;
  font-family: serif;
}
.step-hint {
  display: block;
  font-size: 26rpx;
  color: #888;
  font-family: serif;
  font-style: italic;
  margin-bottom: 32rpx;
}

/* 输入框 */
.input-field {
  box-sizing: border-box;
  width: 100%;
  height: 96rpx;
  padding: 0 24rpx;
  border: 3rpx solid #1a1a2e;
  background: #fff;
  font-size: 32rpx;
  font-family: serif;
}
.error-text {
  display: block;
  font-size: 24rpx;
  color: #c44;
  margin-top: 8rpx;
}

.field-block {
  margin-top: 28rpx;
}
.field-block:first-of-type {
  margin-top: 0;
}
.field-label {
  display: block;
  margin-bottom: 12rpx;
  font-size: 24rpx;
  font-weight: 700;
  color: #1a1a2e;
  font-family: serif;
}

/* 省份列表 */
.province-list {
  max-height: 600rpx;
}
.province-item {
  padding: 20rpx 24rpx;
  border-bottom: 1rpx solid #eee;
}
.province-item.active {
  background: #1a1a2e;
}
.province-item.active .province-text {
  color: #f5f0e8;
}
.province-text {
  font-size: 28rpx;
  color: #1a1a2e;
  font-family: serif;
}

/* 单选组 */
.radio-group {
  display: flex;
  flex-wrap: wrap;
  gap: 16rpx;
}
.radio-group.compact {
  gap: 12rpx;
}
.radio-item {
  padding: 20rpx 32rpx;
  border: 3rpx solid #1a1a2e;
  background: #fff;
  box-sizing: border-box;
}
.radio-group.compact .radio-item {
  padding: 16rpx 24rpx;
}
.radio-item.active {
  background: #1a1a2e;
}
.radio-item.active .radio-text {
  color: #f5f0e8;
}
.radio-text {
  font-size: 28rpx;
  color: #1a1a2e;
  font-family: serif;
}

/* 按钮 */
.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 16rpx;
  margin-top: 40rpx;
  align-items: center;
}
.spacer {
  flex: 1;
}
.btn-primary,
.btn-secondary,
.btn-skip {
  padding: 20rpx 40rpx;
  border: 3rpx solid #1a1a2e;
}
.btn-primary {
  background: #1a1a2e;
}
.btn-primary,
.btn-secondary,
.btn-skip {
  box-sizing: border-box;
  min-width: 148rpx;
  text-align: center;
}
.btn-primary .btn-text {
  color: #f5f0e8;
}
.btn-primary.disabled {
  opacity: 0.5;
}
.btn-secondary {
  background: #fff;
}
.btn-skip {
  background: transparent;
}
.btn-text {
  font-size: 28rpx;
  font-weight: 700;
  font-family: serif;
}

/* 编者按 */
.editor-note {
  margin-top: 40rpx;
  padding: 20rpx;
  border-top: 2rpx solid #1a1a2e;
}
.note-text {
  font-size: 22rpx;
  color: #888;
  font-family: serif;
  font-style: italic;
}
</style>
