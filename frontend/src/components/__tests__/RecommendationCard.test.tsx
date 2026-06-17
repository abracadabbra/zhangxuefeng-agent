import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import RecommendationCard from '../RecommendationCard'

describe('RecommendationCard', () => {
  describe('School Card', () => {
    const schoolData = {
      school_name: '清华大学',
      reason: '学校实力雄厚，专业匹配度高',
      admission_probability: 0.75,
      match_score: 0.92,
      strategy: '稳' as const,
      risk_points: ['热门专业分数波动大'],
      alternatives: ['北京邮电大学'],
    }

    it('renders school name', () => {
      render(<RecommendationCard type="school" data={schoolData} />)
      expect(screen.getByText('清华大学')).toBeInTheDocument()
    })

    it('renders match score percentage', () => {
      render(<RecommendationCard type="school" data={schoolData} />)
      expect(screen.getByText('92%')).toBeInTheDocument()
    })

    it('renders admission probability percentage', () => {
      render(<RecommendationCard type="school" data={schoolData} />)
      expect(screen.getByText('75%')).toBeInTheDocument()
    })

    it('shows correct probability label for high probability', () => {
      render(<RecommendationCard type="school" data={schoolData} />)
      expect(screen.getByText('稳 · 适中')).toBeInTheDocument()
    })

    it('shows "稳妥" label for probability >= 0.8', () => {
      const safeData = { ...schoolData, admission_probability: 0.85 }
      render(<RecommendationCard type="school" data={safeData} />)
      expect(screen.getByText('稳 · 稳妥')).toBeInTheDocument()
    })

    it('shows "冲刺" label for probability >= 0.3', () => {
      const rushData = { ...schoolData, admission_probability: 0.4 }
      render(<RecommendationCard type="school" data={rushData} />)
      expect(screen.getByText('稳 · 冲刺')).toBeInTheDocument()
    })

    it('shows "搏一搏" label for probability < 0.3', () => {
      const riskyData = { ...schoolData, admission_probability: 0.2 }
      render(<RecommendationCard type="school" data={riskyData} />)
      expect(screen.getByText('稳 · 搏一搏')).toBeInTheDocument()
    })

    it('shows "展开详情" by default', () => {
      render(<RecommendationCard type="school" data={schoolData} />)
      expect(screen.getByText('展开详情')).toBeInTheDocument()
    })

    it('expands to show reason when clicked', async () => {
      const user = userEvent.setup()
      render(<RecommendationCard type="school" data={schoolData} />)

      const toggle = screen.getByRole('button', { name: /展开详情/i })
      await user.click(toggle)

      expect(screen.getByText('推荐理由')).toBeInTheDocument()
      expect(screen.getByText('学校实力雄厚，专业匹配度高')).toBeInTheDocument()
      expect(screen.getByText('风险点')).toBeInTheDocument()
      expect(screen.getByText('热门专业分数波动大')).toBeInTheDocument()
      expect(screen.getByText('替代方案')).toBeInTheDocument()
      expect(screen.getByText('北京邮电大学')).toBeInTheDocument()
      expect(screen.getByText('收起')).toBeInTheDocument()
    })

    it('collapses when clicked again', async () => {
      const user = userEvent.setup()
      render(<RecommendationCard type="school" data={schoolData} />)

      const toggle = screen.getByRole('button', { name: /展开详情/i })

      // Expand
      await user.click(toggle)
      expect(screen.getByText('收起')).toBeInTheDocument()

      // Collapse
      await user.click(screen.getByRole('button', { name: /收起/i }))
      expect(screen.getByText('展开详情')).toBeInTheDocument()
    })

    it('toggles on Enter key', async () => {
      const user = userEvent.setup()
      render(<RecommendationCard type="school" data={schoolData} />)

      const toggle = screen.getByRole('button', { name: /展开详情/i })
      toggle.focus()
      await user.keyboard('{Enter}')

      expect(screen.getByText('推荐理由')).toBeInTheDocument()
    })

    it('toggles on Space key', async () => {
      const user = userEvent.setup()
      render(<RecommendationCard type="school" data={schoolData} />)

      const toggle = screen.getByRole('button', { name: /展开详情/i })
      toggle.focus()
      await user.keyboard(' ')

      expect(screen.getByText('推荐理由')).toBeInTheDocument()
    })

    it('calls favorite toggle without expanding the card', async () => {
      const user = userEvent.setup()
      const onFavoriteToggle = vi.fn()
      render(
        <RecommendationCard
          type="school"
          data={schoolData}
          isFavorite={false}
          onFavoriteToggle={onFavoriteToggle}
        />,
      )

      await user.click(screen.getByRole('button', { name: '收藏 清华大学' }))

      expect(onFavoriteToggle).toHaveBeenCalledTimes(1)
      expect(screen.getByText('展开详情')).toBeInTheDocument()
    })

    it('renders favorite state', () => {
      render(
        <RecommendationCard
          type="school"
          data={schoolData}
          isFavorite
          onFavoriteToggle={() => {}}
        />,
      )

      const favoriteButton = screen.getByRole('button', { name: '取消收藏 清华大学' })
      expect(favoriteButton).toHaveAttribute('aria-pressed', 'true')
      expect(favoriteButton).toHaveTextContent('已收藏')
    })
  })

  describe('Major Card', () => {
    const majorData = {
      major_name: '计算机科学与技术',
      category: '工学',
      reason: '就业前景广阔，薪资水平高',
      employment_rate: 0.95,
      avg_salary: 15000,
      strategy: '冲' as const,
      risk_points: ['行业变化快，需要持续学习'],
      alternatives: ['软件工程'],
    }

    it('renders major name', () => {
      render(<RecommendationCard type="major" data={majorData} />)
      expect(screen.getByText('计算机科学与技术')).toBeInTheDocument()
    })

    it('renders category', () => {
      render(<RecommendationCard type="major" data={majorData} />)
      const categories = screen.getAllByText('工学')
      expect(categories.length).toBeGreaterThan(0)
    })

    it('renders employment rate', () => {
      render(<RecommendationCard type="major" data={majorData} />)
      expect(screen.getByText('95')).toBeInTheDocument()
    })

    it('renders average salary', () => {
      render(<RecommendationCard type="major" data={majorData} />)
      expect(screen.getByText('15000')).toBeInTheDocument()
    })

    it('expands to show reason when clicked', async () => {
      const user = userEvent.setup()
      render(<RecommendationCard type="major" data={majorData} />)

      const toggle = screen.getByRole('button', { name: /展开详情/i })
      await user.click(toggle)

      expect(screen.getByText('推荐理由')).toBeInTheDocument()
      expect(screen.getByText('就业前景广阔，薪资水平高')).toBeInTheDocument()
      expect(screen.getByText('风险点')).toBeInTheDocument()
      expect(screen.getByText('行业变化快，需要持续学习')).toBeInTheDocument()
      expect(screen.getByText('替代方案')).toBeInTheDocument()
      expect(screen.getByText('软件工程')).toBeInTheDocument()
    })

    it('collapses when clicked again', async () => {
      const user = userEvent.setup()
      render(<RecommendationCard type="major" data={majorData} />)

      const toggle = screen.getByRole('button', { name: /展开详情/i })

      await user.click(toggle)
      expect(screen.getByText('收起')).toBeInTheDocument()

      await user.click(screen.getByRole('button', { name: /收起/i }))
      expect(screen.getByText('展开详情')).toBeInTheDocument()
    })

    it('toggles on keyboard interaction', async () => {
      const user = userEvent.setup()
      render(<RecommendationCard type="major" data={majorData} />)

      const toggle = screen.getByRole('button', { name: /展开详情/i })
      toggle.focus()
      await user.keyboard('{Enter}')

      expect(screen.getByText('推荐理由')).toBeInTheDocument()
    })

    it('calls major favorite toggle', async () => {
      const user = userEvent.setup()
      const onFavoriteToggle = vi.fn()
      render(
        <RecommendationCard
          type="major"
          data={majorData}
          isFavorite={false}
          onFavoriteToggle={onFavoriteToggle}
        />,
      )

      await user.click(screen.getByRole('button', { name: '收藏 计算机科学与技术' }))

      expect(onFavoriteToggle).toHaveBeenCalledTimes(1)
    })
  })
})
