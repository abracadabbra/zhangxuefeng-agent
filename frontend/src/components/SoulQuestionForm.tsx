import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import type { UserProfile } from '../types'

interface SoulQuestionFormProps {
  scenario: 'gaokao' | 'kaoyan' | 'career'
  onComplete: (profile: UserProfile) => void
  onBack: () => void
}

const PROVINCES = [
  '北京', '天津', '河北', '山西', '内蒙古', '辽宁', '吉林', '黑龙江',
  '上海', '江苏', '浙江', '安徽', '福建', '江西', '山东', '河南',
  '湖北', '湖南', '广东', '广西', '海南', '重庆', '四川', '贵州',
  '云南', '西藏', '陕西', '甘肃', '青海', '宁夏', '新疆',
]

const SUBJECT_KEYS = ['science', 'arts', 'physics', 'history', 'comprehensive'] as const
const BUDGET_KEYS = ['low', 'medium', 'high', 'unlimited'] as const
const EDUCATION_KEYS = ['highSchool', 'college', 'bachelor', 'master', 'phd'] as const

const STEP_KEYS = {
  gaokao: ['score', 'province', 'subject', 'familyBudget'],
  kaoyan: ['currentSchool', 'major', 'gpa', 'targetSchool'],
  career: ['education', 'major', 'interests', 'concerns'],
} as const

const STEP_TYPES: Record<string, string> = {
  score: 'number',
  province: 'select',
  subject: 'select',
  familyBudget: 'select',
  education: 'select',
}

const SCENARIO_META = {
  gaokao: { emoji: '🎓', sectionKey: 'scenarios.gaokao.section', titleKey: 'scenarios.gaokao.title' },
  kaoyan: { emoji: '📚', sectionKey: 'scenarios.kaoyan.section', titleKey: 'scenarios.kaoyan.title' },
  career: { emoji: '💼', sectionKey: 'scenarios.career.section', titleKey: 'scenarios.career.title' },
}

export default function SoulQuestionForm({ scenario, onComplete, onBack }: SoulQuestionFormProps) {
  const { t } = useTranslation()
  const [currentStep, setCurrentStep] = useState(0)
  const [formData, setFormData] = useState<Record<string, string>>({})

  const meta = SCENARIO_META[scenario]
  const stepKeys = STEP_KEYS[scenario]
  const currentStepKey = stepKeys[currentStep]
  const stepLabel = t(`form.${scenario}.steps.${currentStepKey}.label`)
  const stepPlaceholder = t(`form.${scenario}.steps.${currentStepKey}.placeholder`)
  const stepHint = t(`form.${scenario}.steps.${currentStepKey}.hint`)
  const stepNote = t(`form.${scenario}.steps.${currentStepKey}.note`)
  const isLast = currentStep === stepKeys.length - 1

  const subjects = SUBJECT_KEYS.map(k => t(`form.subjects.${k}`))
  const budgetOptions = BUDGET_KEYS.map(k => t(`form.budget.${k}`))
  const educationLevels = EDUCATION_KEYS.map(k => t(`form.education.${k}`))
  const versionLabels = t('form.versionLabels', { returnObjects: true }) as string[]

  const handleNext = () => {
    if (isLast) {
      const profile: UserProfile = {
        score: parseInt(formData.score) || undefined,
        province: formData.province,
        subject: formData.subject,
        familyCondition: formData.familyBudget,
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

  const canProceed = formData[currentStepKey]?.trim()

  const renderInput = () => {
    const value = formData[currentStepKey] || ''

    if (currentStepKey === 'province') {
      return (
        <select
          value={value}
          onChange={(e) => setFormData(prev => ({ ...prev, [currentStepKey]: e.target.value }))}
          aria-label={stepLabel}
          aria-required="true"
          className="w-full px-4 py-3 border-2 border-ink bg-paper
                     font-serif text-lg text-ink
                     focus:border-gold focus:outline-none transition-colors"
        >
          <option value="">{t('form.gaokao.steps.province.selectPlaceholder')}</option>
          {PROVINCES.map(p => (
            <option key={p} value={p}>{p}</option>
          ))}
        </select>
      )
    }

    if (currentStepKey === 'subject') {
      return (
        <div role="radiogroup" aria-label={stepLabel} className="grid grid-cols-2 gap-3">
          {subjects.map(s => (
            <button
              key={s}
              type="button"
              role="radio"
              aria-checked={value === s}
              onClick={() => setFormData(prev => ({ ...prev, [currentStepKey]: s }))}
              className={`px-4 py-3 border-2 text-base font-serif font-medium transition-all
                ${value === s
                  ? 'border-gold bg-gold-light/20 text-ink shadow-warm'
                  : 'border-rule bg-paper text-ink-light hover:border-ink hover:bg-paper-dark'
                }`}
            >
              {s}
            </button>
          ))}
        </div>
      )
    }

    if (currentStepKey === 'familyBudget') {
      return (
        <div role="radiogroup" aria-label={stepLabel} className="space-y-3">
          {budgetOptions.map(b => (
            <button
              key={b}
              type="button"
              role="radio"
              aria-checked={value === b}
              onClick={() => setFormData(prev => ({ ...prev, [currentStepKey]: b }))}
              className={`w-full px-4 py-3 border-2 text-left text-base font-serif transition-all
                ${value === b
                  ? 'border-gold bg-gold-light/20 text-ink shadow-warm'
                  : 'border-rule bg-paper text-ink-light hover:border-ink hover:bg-paper-dark'
                }`}
            >
              {b}
            </button>
          ))}
        </div>
      )
    }

    if (currentStepKey === 'education') {
      return (
        <div role="radiogroup" aria-label={stepLabel} className="grid grid-cols-2 gap-3">
          {educationLevels.map(e => (
            <button
              key={e}
              type="button"
              role="radio"
              aria-checked={value === e}
              onClick={() => setFormData(prev => ({ ...prev, [currentStepKey]: e }))}
              className={`px-4 py-3 border-2 text-base font-serif font-medium transition-all
                ${value === e
                  ? 'border-gold bg-gold-light/20 text-ink shadow-warm'
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
        id={`step-${currentStepKey}`}
        type={STEP_TYPES[currentStepKey] === 'number' ? 'number' : 'text'}
        value={value}
        onChange={(e) => setFormData(prev => ({ ...prev, [currentStepKey]: e.target.value }))}
        placeholder={stepPlaceholder}
        aria-label={stepLabel}
        aria-required="true"
        aria-describedby={`hint-${currentStepKey}`}
        className="w-full px-4 py-3 border-2 border-ink bg-paper
                   font-serif text-lg text-ink
                   focus:border-gold focus:outline-none transition-colors
                   placeholder:text-ink-light/50"
        autoFocus
      />
    )
  }

  return (
    <div role="form" aria-label={t('a11y.soulForm', { defaultValue: '信息收集表单' })} className="min-h-[calc(100vh-80px)] flex items-center justify-center p-4">
      <div className="w-full max-w-lg">
        {/* Form header */}
        <div className="border-2 border-ink bg-paper mb-6">
          <div className="bg-ink text-paper px-4 py-2 flex items-center justify-between">
            <span className="font-mono text-sm font-bold">{t(meta.sectionKey)}</span>
            <span className="font-mono text-xs">{meta.emoji} {t(meta.titleKey)}</span>
          </div>
          <div className="px-6 py-4 text-center">
            <h2 className="text-2xl font-black text-ink font-serif tracking-wide">
              {t(meta.titleKey)}
            </h2>
            <p className="text-sm text-ink-light font-serif mt-1">
              {t('form.stepOf', { current: currentStep + 1, total: stepKeys.length })}
            </p>
          </div>
        </div>

        {/* Progress bar */}
        <div className="mb-6" role="progressbar" aria-valuenow={currentStep + 1} aria-valuemin={1} aria-valuemax={stepKeys.length} aria-label={t('a11y.formProgress', { defaultValue: `步骤 ${currentStep + 1}，共 ${stepKeys.length} 步` })}>
          <div className="flex justify-between">
            {stepKeys.map((key, i) => (
              <div
                key={key}
                className={`flex flex-col items-center gap-1 transition-colors
                  ${i < currentStep ? 'text-gold' : i === currentStep ? 'text-ink' : 'text-ink-light/50/50'}`}
                aria-current={i === currentStep ? 'step' : undefined}
              >
                <div className={`w-full h-1 ${i <= currentStep ? 'bg-ink' : 'bg-rule-border'}`} />
                <span className="text-xs font-mono mt-1">{versionLabels[i]}</span>
                <span className={`w-6 h-6 flex items-center justify-center text-xs font-mono font-bold border-2
                  ${i < currentStep
                    ? 'border-gold bg-gold text-paper'
                    : i === currentStep
                      ? 'border-ink bg-ink text-paper'
                      : 'border-rule bg-paper text-ink-light'
                  }`}>
                  {i < currentStep ? '✓' : i + 1}
                </span>
                <span className="text-xs font-serif hidden sm:block">{t(`form.${scenario}.steps.${key}.label`)}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Form card */}
        <div className="border-2 border-ink bg-paper">
          <div className="px-5 sm:px-6 py-5">
            <label htmlFor={`step-${currentStepKey}`} className="block text-lg font-bold font-serif text-ink mb-2">
              {stepLabel}
            </label>
            <div className="rule-single mb-4" />
            <p id={`hint-${currentStepKey}`} className="text-sm text-ink-light font-serif mb-4 italic">
              {stepHint}
            </p>

            {renderInput()}

            {/* Editor's note */}
            <div className="mt-4 pt-3 border-t border-rule">
              <p className="text-xs text-ink-light font-serif">
                <span className="font-bold">{t('form.editorNote')}</span>
                {stepNote}
              </p>
            </div>
          </div>

          {/* Action buttons */}
          <div className="border-t-2 border-ink px-5 sm:px-6 py-4 flex gap-3">
            <button
              onClick={handleBack}
              aria-label={currentStep === 0 ? t('form.back') : t('form.prevStep')}
              className="flex-1 px-4 py-3 border-2 border-ink text-ink
                         font-serif font-bold hover:bg-ink hover:text-paper transition-colors"
            >
              {currentStep === 0 ? t('form.back') : t('form.prevStep')}
            </button>
            <button
              onClick={handleNext}
              disabled={!canProceed}
              aria-label={isLast ? t('form.startConsult') : t('form.nextStep')}
              aria-disabled={!canProceed}
              className={`flex-[2] px-4 py-3 font-serif font-bold text-base transition-all
                ${canProceed
                  ? 'bg-ink text-paper hover:bg-ink-light shadow-warm-lg'
                  : 'bg-rule-border text-ink-light cursor-not-allowed'
                }`}
            >
              {isLast ? t('form.startConsult') : t('form.nextStep')}
            </button>
          </div>
        </div>

        {/* Quick entry */}
        <div className="text-center mt-6">
          <button
            onClick={() => {
              onComplete({} as UserProfile)
            }}
            aria-label={t('form.skipDirect')}
            className="text-sm text-ink-light hover:text-ink
                       font-serif underline underline-offset-4 transition-colors"
          >
            {t('form.skipDirect')}
          </button>
        </div>

        {/* Page number */}
        <div className="text-center mt-4">
          <span className="text-xs text-ink-light font-mono">{t('form.pageLabel', { page: currentStep + 1 })}</span>
        </div>
      </div>
    </div>
  )
}
