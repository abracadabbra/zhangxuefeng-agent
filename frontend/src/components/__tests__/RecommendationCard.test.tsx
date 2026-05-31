import { describe, it, expect } from 'vitest'
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
      expect(screen.getByText('适中')).toBeInTheDocument()
    })

    it('shows "稳妥" label for probability >= 0.8', () => {
      const safeData = { ...schoolData, admission_probability: 0.85 }
      render(<RecommendationCard type="school" data={safeData} />)
      expect(screen.getByText('稳妥')).toBeInTheDocument()
    })

    it('shows "冲刺" label for probability >= 0.3', () => {
      const rushData = { ...schoolData, admission_probability: 0.4 }
      render(<RecommendationCard type="school" data={rushData} />)
      expect(screen.getByText('冲刺')).toBeInTheDocument()
    })

    it('shows "搏一搏" label for probability < 0.3', () => {
      const riskyData = { ...schoolData, admission_probability: 0.2 }
      render(<RecommendationCard type="school" data={riskyData} />)
      expect(screen.getByText('搏一搏')).toBeInTheDocument()
    })

    it('shows "展开详情" by default', () => {
      render(<RecommendationCard type="school" data={schoolData} />)
      expect(screen.getByText('展开详情')).toBeInTheDocument()
    })

    it('expands to show reason when clicked', async () => {
      const user = userEvent.setup()
      render(<RecommendationCard type="school" data={schoolData} />)

      const card = screen.getByRole('button')
      await user.click(card)

      expect(screen.getByText('推荐理由')).toBeInTheDocument()
      expect(screen.getByText('学校实力雄厚，专业匹配度高')).toBeInTheDocument()
      expect(screen.getByText('收起')).toBeInTheDocument()
    })

    it('collapses when clicked again', async () => {
      const user = userEvent.setup()
      render(<RecommendationCard type="school" data={schoolData} />)

      const card = screen.getByRole('button')

      // Expand
      await user.click(card)
      expect(screen.getByText('收起')).toBeInTheDocument()

      // Collapse
      await user.click(card)
      expect(screen.getByText('展开详情')).toBeInTheDocument()
    })

    it('toggles on Enter key', async () => {
      const user = userEvent.setup()
      render(<RecommendationCard type="school" data={schoolData} />)

      const card = screen.getByRole('button')
      card.focus()
      await user.keyboard('{Enter}')

      expect(screen.getByText('推荐理由')).toBeInTheDocument()
    })

    it('toggles on Space key', async () => {
      const user = userEvent.setup()
      render(<RecommendationCard type="school" data={schoolData} />)

      const card = screen.getByRole('button')
      card.focus()
      await user.keyboard(' ')

      expect(screen.getByText('推荐理由')).toBeInTheDocument()
    })
  })

  describe('Major Card', () => {
    const majorData = {
      major_name: '计算机科学与技术',
      category: '工学',
      reason: '就业前景广阔，薪资水平高',
      employment_rate: 0.95,
      avg_salary: 15000,
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

      const card = screen.getByRole('button')
      await user.click(card)

      expect(screen.getByText('推荐理由')).toBeInTheDocument()
      expect(screen.getByText('就业前景广阔，薪资水平高')).toBeInTheDocument()
    })

    it('collapses when clicked again', async () => {
      const user = userEvent.setup()
      render(<RecommendationCard type="major" data={majorData} />)

      const card = screen.getByRole('button')

      await user.click(card)
      expect(screen.getByText('收起')).toBeInTheDocument()

      await user.click(card)
      expect(screen.getByText('展开详情')).toBeInTheDocument()
    })

    it('toggles on keyboard interaction', async () => {
      const user = userEvent.setup()
      render(<RecommendationCard type="major" data={majorData} />)

      const card = screen.getByRole('button')
      card.focus()
      await user.keyboard('{Enter}')

      expect(screen.getByText('推荐理由')).toBeInTheDocument()
    })
  })
})
