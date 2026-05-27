import { useState } from 'react'
import type { UserProfile } from '../types'

interface SoulQuestionFormProps {
  scenario: 'gaokao' | 'kaoyan' | 'career'
  onComplete: (profile: UserProfile) => void
  onBack: () => void
}

const SCENARIO_CONFIG = {
  gaokao: {
    title: '高考志愿填报',
    emoji: '🎓',
    section: 'A 版',
    steps: [
      { key: 'score', label: '高考分数', placeholder: '例如：580', type: 'number' },
      { key: 'province', label: '所在省份', placeholder: '例如：河南', type: 'select' },
      { key: 'subject', label: '科类', placeholder: '选择科类', type: 'select' },
      { key: 'familyBudget', label: '家庭经济情况', placeholder: '选择情况', type: 'select' },
    ],
  },
  kaoyan: {
    title: '考研规划',
    emoji: '📚',
    section: 'B 版',
    steps: [
      { key: 'currentSchool', label: '本科学校', placeholder: '例如：河南大学', type: 'text' },
      { key: 'major', label: '本科专业', placeholder: '例如：计算机科学', type: 'text' },
      { key: 'gpa', label: 'GPA / 绩点', placeholder: '例如：3.5', type: 'text' },
      { key: 'targetSchool', label: '目标院校', placeholder: '例如：北京大学', type: 'text' },
    ],
  },
  career: {
    title: '职业规划',
    emoji: '💼',
    section: 'C 版',
    steps: [
      { key: 'education', label: '当前学历', placeholder: '例如：本科', type: 'select' },
      { key: 'major', label: '专业方向', placeholder: '例如：金融学', type: 'text' },
      { key: 'interests', label: '兴趣方向', placeholder: '例如：互联网、金融', type: 'text' },
      { key: 'concerns', label: '最关心的问题', placeholder: '例如：薪资、稳定性', type: 'text' },
    ],
  },
}

const PROVINCES = [
  '北京', '天津', '河北', '山西', '内蒙古', '辽宁', '吉林', '黑龙江',
  '上海', '江苏', '浙江', '安徽', '福建', '江西', '山东', '河南',
  '湖北', '湖南', '广东', '广西', '海南', '重庆', '四川', '贵州',
  '云南', '西藏', '陕西', '甘肃', '青海', '宁夏', '新疆',
]

const SUBJECTS = ['理科', '文科', '物理类', '历史类', '综合改革']

const BUDGET_OPTIONS = [
  '一般（公办优先）',
  '中等（公私皆可）',
  '较好（中外合作可考虑）',
  '不限',
]

const EDUCATION_LEVELS = ['高中', '大专', '本科', '硕士', '博士']

const VERSION_LABELS = ['第一版', '第二版', '第三版', '第四版']

export default function SoulQuestionForm({ scenario, onComplete, onBack }: SoulQuestionFormProps) {
  const [currentStep, setCurrentStep] = useState(0)
  const [formData, setFormData] = useState<Record<string, string>>({})

  const config = SCENARIO_CONFIG[scenario]
  const step = config.steps[currentStep]
  const isLast = currentStep === config.steps.length - 1
  const progress = ((currentStep + 1) / config.steps.length) * 100

  const handleNext = () => {
    if (isLast) {
      // 构建用户画像并完成
      const profile: UserProfile = {
        score: parseInt(formData.score) || undefined,
        province: formData.province,
        subject: formData.subject as '理科' | '文科' | '物理类' | '历史类',
        family_budget: formData.familyBudget as UserProfile['family_budget'],
      }
      onComplete(profile)
    } else {
      setCurrentStep(prev => prev + 1)
    }
  }

  const handleBack = () => {
    if (currentStep === 0) {
      onBack()
    } else {
      setCurrentStep(prev => prev - 1)
    }
  }

  const canProceed = formData[step.key]?.trim()

  const renderInput = () => {
    const value = formData[step.key] || ''

    if (step.key === 'province') {
      return (
        <select
          value={value}
          onChange={(e) => setFormData(prev => ({ ...prev, [step.key]: e.target.value }))}
          className="w-full px-4 py-3 border-2 border-ink bg-paper font-serif text-lg text-ink
                     focus:border-gold focus:outline-none transition-colors"
        >
          <option value="">选择省份</option>
          {PROVINCES.map(p => (
            <option key={p} value={p}>{p}</option>
          ))}
        </select>
      )
    }

    if (step.key === 'subject') {
      return (
        <div className="grid grid-cols-2 gap-3">
          {SUBJECTS.map(s => (
            <button
              key={s}
              type="button"
              onClick={() => setFormData(prev => ({ ...prev, [step.key]: s }))}
              className={`px-4 py-3 border-2 text-base font-serif font-medium transition-all
                ${value === s
                  ? 'border-gold bg-gold-light text-ink shadow-warm'
                  : 'border-rule bg-paper text-ink-light hover:border-ink hover:bg-paper-dark'
                }`}
            >
              {s}
            </button>
          ))}
        </div>
      )
    }

    if (step.key === 'familyBudget') {
      return (
        <div className="space-y-3">
          {BUDGET_OPTIONS.map(b => (
            <button
              key={b}
              type="button"
              onClick={() => setFormData(prev => ({ ...prev, [step.key]: b }))}
              className={`w-full px-4 py-3 border-2 text-left text-base font-serif transition-all
                ${value === b
                  ? 'border-gold bg-gold-light text-ink shadow-warm'
                  : 'border-rule bg-paper text-ink-light hover:border-ink hover:bg-paper-dark'
                }`}
            >
              {b}
            </button>
          ))}
        </div>
      )
    }

    if (step.key === 'education') {
      return (
        <div className="grid grid-cols-2 gap-3">
          {EDUCATION_LEVELS.map(e => (
            <button
              key={e}
              type="button"
              onClick={() => setFormData(prev => ({ ...prev, [step.key]: e }))}
              className={`px-4 py-3 border-2 text-base font-serif font-medium transition-all
                ${value === e
                  ? 'border-gold bg-gold-light text-ink shadow-warm'
                  : 'border-rule bg-paper text-ink-light hover:border-ink hover:bg-paper-dark'
                }`}
            >
              {e}
            </button>
          ))}
        </div>
      )
    }

    return (
      <input
        type={step.type === 'number' ? 'number' : 'text'}
        value={value}
        onChange={(e) => setFormData(prev => ({ ...prev, [step.key]: e.target.value }))}
        placeholder={step.placeholder}
        className="w-full px-4 py-3 border-2 border-ink bg-paper font-serif text-lg text-ink
                   focus:border-gold focus:outline-none transition-colors
                   placeholder:text-ink-light/50"
        autoFocus
      />
    )
  }

  return (
    <div className="min-h-[calc(100vh-80px)] flex items-center justify-center p-4">
      <div className="w-full max-w-lg">
        {/* 报纸式表单头 */}
        <div className="border-2 border-ink bg-paper mb-6">
          <div className="bg-ink text-paper px-4 py-2 flex items-center justify-between">
            <span className="font-mono text-sm font-bold">{config.section}</span>
            <span className="font-mono text-xs">{config.emoji} {config.title}</span>
          </div>
          <div className="px-6 py-4 text-center">
            <h2 className="text-2xl font-black text-ink font-serif tracking-wide">
              {config.title}
            </h2>
            <p className="text-sm text-ink-light font-serif mt-1">
              第 {currentStep + 1} 步，共 {config.steps.length} 步
            </p>
          </div>
        </div>

        {/* 进度条 - 报纸版面标记 */}
        <div className="mb-6">
          <div className="flex justify-between">
            {config.steps.map((s, i) => (
              <div
                key={s.key}
                className={`flex flex-col items-center gap-1 transition-colors
                  ${i < currentStep ? 'text-gold' : i === currentStep ? 'text-ink' : 'text-ink-light/50'}`}
              >
                <div className={`w-full h-1 ${i <= currentStep ? 'bg-ink' : 'bg-rule'}`} />
                <span className="text-xs font-mono mt-1">{VERSION_LABELS[i]}</span>
                <span className={`w-6 h-6 flex items-center justify-center text-xs font-mono font-bold border-2
                  ${i < currentStep
                    ? 'border-gold bg-gold text-paper'
                    : i === currentStep
                      ? 'border-ink bg-ink text-paper'
                      : 'border-rule bg-paper text-ink-light'
                  }`}>
                  {i < currentStep ? '✓' : i + 1}
                </span>
                <span className="text-xs font-serif hidden sm:block">{s.label}</span>
              </div>
            ))}
          </div>
        </div>

        {/* 表单卡片 - 报纸问卷风格 */}
        <div className="border-2 border-ink bg-paper">
          <div className="px-6 py-5">
            <label className="block text-lg font-bold font-serif text-ink mb-2">
              {step.label}
            </label>
            <div className="rule-single mb-4" />
            <p className="text-sm text-ink-light font-serif mb-4 italic">
              {step.key === 'score' && '填写你的高考总分，我会根据分数推荐合适院校'}
              {step.key === 'province' && '不同省份分数线差异很大，这个信息很关键'}
              {step.key === 'subject' && '选科决定了可报考的专业范围'}
              {step.key === 'familyBudget' && '我会根据实际情况推荐性价比最高的方案'}
              {step.key === 'currentSchool' && '了解你的起点，才能规划路径'}
              {step.key === 'major' && '你的专业背景决定了考研方向'}
              {step.key === 'gpa' && '成绩是考研择校的重要参考'}
              {step.key === 'targetSchool' && '有了目标才能倒推备考策略'}
              {step.key === 'education' && '你的学历起点决定了职业发展路径'}
              {step.key === 'interests' && '兴趣是最好的老师，也是职业选择的指南针'}
              {step.key === 'concerns' && '说出你最纠结的问题，我来给你掰开了讲'}
            </p>

            {renderInput()}

            {/* 编者注 */}
            <div className="mt-4 pt-3 border-t border-rule">
              <p className="text-xs text-ink-light font-serif">
                <span className="font-bold">编者注：</span>
                {step.key === 'score' && '请如实填写，分数越准确，推荐越精准'}
                {step.key === 'province' && '请选择参加高考的省份，这将影响分数线参考'}
                {step.key === 'subject' && '请选择你的高考科类或选科组合'}
                {step.key === 'familyBudget' && '此信息仅用于推荐，不会泄露'}
                {step.key === 'currentSchool' && '本科学校层次会影响考研目标院校的选择'}
                {step.key === 'major' && '本科专业决定了考研的可选方向'}
                {step.key === 'gpa' && 'GPA 是考研择校的重要参考指标'}
                {step.key === 'targetSchool' && '目标院校决定了备考策略和难度'}
                {step.key === 'education' && '当前学历决定了职业发展的起点'}
                {step.key === 'interests' && '兴趣方向将影响专业和职业推荐'}
                {step.key === 'concerns' && '说出你的真实顾虑，我会给出务实建议'}
              </p>
            </div>
          </div>

          {/* 操作按钮 */}
          <div className="border-t-2 border-ink px-6 py-4 flex gap-3">
            <button
              onClick={handleBack}
              className="flex-1 px-4 py-3 border-2 border-ink text-ink font-serif font-bold hover:bg-ink hover:text-paper transition-colors"
            >
              {currentStep === 0 ? '返回' : '上一步'}
            </button>
            <button
              onClick={handleNext}
              disabled={!canProceed}
              className={`flex-[2] px-4 py-3 font-serif font-bold text-base transition-all
                ${canProceed
                  ? 'bg-ink text-paper hover:bg-ink-light shadow-warm-lg'
                  : 'bg-rule text-ink-light cursor-not-allowed'
                }`}
            >
              {isLast ? '开始咨询 →' : '下一步 →'}
            </button>
          </div>
        </div>

        {/* 快捷入口 */}
        <div className="text-center mt-6">
          <button
            onClick={() => {
              // 跳过表单，直接使用空画像进入聊天
              onComplete({} as UserProfile)
            }}
            className="text-sm text-ink-light hover:text-ink font-serif underline underline-offset-4 transition-colors"
          >
            跳过，直接提问 →
          </button>
        </div>

        {/* 页码 */}
        <div className="text-center mt-4">
          <span className="text-xs text-ink-light font-mono">— 第 {currentStep + 1} 版 —</span>
        </div>
      </div>
    </div>
  )
}
