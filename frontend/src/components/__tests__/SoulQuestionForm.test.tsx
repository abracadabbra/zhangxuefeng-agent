import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import SoulQuestionForm from '../SoulQuestionForm'

// Mock react-i18next — return translated Chinese text
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, opts?: Record<string, unknown>) => {
      const overrides: Record<string, string | string[]> = {
        'form.stepOf': `${opts?.current ?? 1} / ${opts?.total ?? 4}`,
        'form.gaokao.steps.score.label': '高考分数',
        'form.gaokao.steps.score.placeholder': '请输入分数',
        'form.gaokao.steps.score.hint': '请输入预估或实际分数',
        'form.gaokao.steps.score.note': '建议使用最近一次模考成绩',
        'form.gaokao.steps.province.label': '所在省份',
        'form.gaokao.steps.province.placeholder': '选择省份',
        'form.gaokao.steps.province.hint': '选择你的高考报名省份',
        'form.gaokao.steps.province.note': '不同省份录取分数线不同',
        'form.gaokao.steps.province.selectPlaceholder': '请选择省份',
        'form.gaokao.steps.subject.label': '科类',
        'form.gaokao.steps.subject.placeholder': '选择科类',
        'form.gaokao.steps.subject.hint': '选择你的高考科类',
        'form.gaokao.steps.subject.note': '新高考省份选物理/历史',
        'form.gaokao.steps.familyBudget.label': '家庭预算',
        'form.gaokao.steps.familyBudget.placeholder': '选择预算',
        'form.gaokao.steps.familyBudget.hint': '大致家庭经济情况',
        'form.gaokao.steps.familyBudget.note': '影响院校地域推荐',
        'scenarios.gaokao.section': '高考志愿',
        'scenarios.gaokao.title': '高考志愿填报',
        'form.subjects.science': '理科',
        'form.subjects.arts': '文科',
        'form.subjects.physics': '物理',
        'form.subjects.history': '历史',
        'form.subjects.comprehensive': '综合',
        'form.budget.low': '3万以下',
        'form.budget.medium': '3-8万',
        'form.budget.high': '8-15万',
        'form.budget.unlimited': '不限',
        'form.education.highSchool': '高中',
        'form.education.college': '大专',
        'form.education.bachelor': '本科',
        'form.education.master': '硕士',
        'form.education.phd': '博士',
        'form.versionLabels': ['壹', '贰', '叁', '肆'],
        'form.editorNote': '编者按：',
        'form.back': '返回',
        'form.prevStep': '上一步',
        'form.nextStep': '下一步',
        'form.startConsult': '开始咨询',
        'form.skipDirect': '跳过，直接进入咨询',
        'form.pageLabel': `第 ${opts?.page ?? 1} 页`,
        'a11y.soulForm': '信息收集表单',
        'a11y.formProgress': `步骤 ${opts?.current ?? 1}，共 ${opts?.total ?? 4} 步`,
      }
      if (overrides[key]) return overrides[key]
      if (opts?.defaultValue) return opts.defaultValue as string
      return key
    },
  }),
}))

describe('SoulQuestionForm', () => {
  const defaultProps = {
    scenario: 'gaokao' as const,
    onComplete: vi.fn(),
    onBack: vi.fn(),
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders the form', () => {
    render(<SoulQuestionForm {...defaultProps} />)
    expect(screen.getByRole('form')).toBeInTheDocument()
  })

  it('shows the first step label for gaokao', () => {
    render(<SoulQuestionForm {...defaultProps} />)
    // "高考分数" appears in both the progress bar step label and the form label
    const matches = screen.getAllByText('高考分数')
    expect(matches.length).toBeGreaterThanOrEqual(1)
  })

  it('shows progress indicator', () => {
    render(<SoulQuestionForm {...defaultProps} />)
    const progressbar = screen.getByRole('progressbar')
    expect(progressbar).toBeInTheDocument()
  })

  it('renders input field for score step', () => {
    render(<SoulQuestionForm {...defaultProps} />)
    const input = screen.getByLabelText('高考分数')
    expect(input).toBeInTheDocument()
    expect(input).toHaveAttribute('type', 'number')
  })

  it('next button is disabled when input is empty', () => {
    render(<SoulQuestionForm {...defaultProps} />)
    const nextButton = screen.getByRole('button', { name: '下一步' })
    expect(nextButton).toBeDisabled()
  })

  it('enables next button when input has value', async () => {
    const user = userEvent.setup()
    render(<SoulQuestionForm {...defaultProps} />)

    const input = screen.getByLabelText('高考分数')
    await user.type(input, '600')

    const nextButton = screen.getByRole('button', { name: '下一步' })
    expect(nextButton).toBeEnabled()
  })

  it('navigates to next step on next click', async () => {
    const user = userEvent.setup()
    render(<SoulQuestionForm {...defaultProps} />)

    const input = screen.getByLabelText('高考分数')
    await user.type(input, '600')

    const nextButton = screen.getByRole('button', { name: '下一步' })
    await user.click(nextButton)

    await waitFor(() => {
      const matches = screen.getAllByText('所在省份')
      expect(matches.length).toBeGreaterThanOrEqual(1)
    })
  })

  it('navigates back to previous step', async () => {
    const user = userEvent.setup()
    render(<SoulQuestionForm {...defaultProps} />)

    // Go to step 2
    const input = screen.getByLabelText('高考分数')
    await user.type(input, '600')
    await user.click(screen.getByRole('button', { name: '下一步' }))

    await waitFor(() => {
      expect(screen.getByLabelText('所在省份')).toBeInTheDocument()
    })

    // Go back
    const prevButton = screen.getByRole('button', { name: '上一步' })
    await user.click(prevButton)

    await waitFor(() => {
      expect(screen.getByLabelText('高考分数')).toBeInTheDocument()
    })
  })

  it('calls onBack when on first step and back is clicked', async () => {
    const onBack = vi.fn()
    const user = userEvent.setup()
    render(<SoulQuestionForm {...defaultProps} onBack={onBack} />)

    const backButton = screen.getByRole('button', { name: '返回' })
    await user.click(backButton)

    expect(onBack).toHaveBeenCalledTimes(1)
  })

  it('renders province select on step 2', async () => {
    const user = userEvent.setup()
    render(<SoulQuestionForm {...defaultProps} />)

    const input = screen.getByLabelText('高考分数')
    await user.type(input, '600')
    await user.click(screen.getByRole('button', { name: '下一步' }))

    await waitFor(() => {
      const select = screen.getByLabelText('所在省份')
      expect(select.tagName).toBe('SELECT')
    })
  })

  it('renders subject radio group on step 3', async () => {
    const user = userEvent.setup()
    render(<SoulQuestionForm {...defaultProps} />)

    // Step 1: score
    await user.type(screen.getByLabelText('高考分数'), '600')
    await user.click(screen.getByRole('button', { name: '下一步' }))

    // Step 2: province
    await waitFor(() => {
      expect(screen.getByLabelText('所在省份')).toBeInTheDocument()
    })
    await user.selectOptions(screen.getByLabelText('所在省份'), '北京')
    await user.click(screen.getByRole('button', { name: '下一步' }))

    // Step 3: subject
    await waitFor(() => {
      expect(screen.getByRole('radiogroup', { name: /科类/i })).toBeInTheDocument()
    })
  })

  it('completes form and calls onComplete on last step', async () => {
    const onComplete = vi.fn()
    const user = userEvent.setup()
    render(<SoulQuestionForm {...defaultProps} onComplete={onComplete} />)

    // Step 1: score
    await user.type(screen.getByLabelText('高考分数'), '600')
    await user.click(screen.getByRole('button', { name: '下一步' }))

    // Step 2: province
    await waitFor(() => {
      expect(screen.getByLabelText('所在省份')).toBeInTheDocument()
    })
    await user.selectOptions(screen.getByLabelText('所在省份'), '北京')
    await user.click(screen.getByRole('button', { name: '下一步' }))

    // Step 3: subject
    await waitFor(() => {
      expect(screen.getByRole('radiogroup', { name: /科类/i })).toBeInTheDocument()
    })
    const subjectButtons = screen.getAllByRole('radio')
    await user.click(subjectButtons[0])
    await user.click(screen.getByRole('button', { name: '下一步' }))

    // Step 4: family budget
    await waitFor(() => {
      expect(screen.getByRole('radiogroup', { name: /家庭预算/i })).toBeInTheDocument()
    })
    const budgetButtons = screen.getAllByRole('radio')
    await user.click(budgetButtons[0])

    // Click "start consult"
    await user.click(screen.getByRole('button', { name: '开始咨询' }))

    await waitFor(() => {
      expect(onComplete).toHaveBeenCalledWith(
        expect.objectContaining({
          score: 600,
          province: '北京',
        }),
      )
    })
  })

  it('skip button calls onComplete with empty profile', async () => {
    const onComplete = vi.fn()
    const user = userEvent.setup()
    render(<SoulQuestionForm {...defaultProps} onComplete={onComplete} />)

    const skipButton = screen.getByRole('button', { name: '跳过，直接进入咨询' })
    await user.click(skipButton)

    expect(onComplete).toHaveBeenCalledWith({})
  })

  it('renders kaoyan scenario steps', () => {
    render(<SoulQuestionForm {...defaultProps} scenario="kaoyan" />)
    expect(screen.getByRole('form')).toBeInTheDocument()
  })

  it('renders career scenario steps', () => {
    render(<SoulQuestionForm {...defaultProps} scenario="career" />)
    expect(screen.getByRole('form')).toBeInTheDocument()
  })
})
