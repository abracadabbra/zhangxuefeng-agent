import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { FeedbackDashboard } from '../FeedbackDashboard'

const mockStats = {
  total_count: 100,
  average_rating: 4.2,
  rating_distribution: { 1: 5, 2: 10, 3: 15, 4: 30, 5: 40 },
  category_distribution: {
    '志愿填报': 30,
    '院校选择': 25,
    '专业选择': 20,
    '分数分析': 15,
    '地域选择': 10,
  },
  recent_trend: [
    { date: '2026-05-20', count: 12 },
    { date: '2026-05-21', count: 15 },
    { date: '2026-05-22', count: 8 },
    { date: '2026-05-23', count: 20 },
    { date: '2026-05-24', count: 18 },
    { date: '2026-05-25', count: 14 },
    { date: '2026-05-26', count: 13 },
  ],
}

describe('FeedbackDashboard', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('shows loading state initially', () => {
    vi.spyOn(globalThis, 'fetch').mockImplementationOnce(() => new Promise(() => {}))

    const { container } = render(<FeedbackDashboard />)
    const spinner = container.querySelector('.animate-spin')
    expect(spinner).toBeInTheDocument()
  })

  it('shows empty state when no data', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: false,
    } as Response)

    render(<FeedbackDashboard />)

    await waitFor(() => {
      expect(screen.getByText('暂无反馈数据')).toBeInTheDocument()
    })
  })

  it('renders overview cards with stats', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockStats),
    } as Response)

    render(<FeedbackDashboard />)

    await waitFor(() => {
      expect(screen.getByText('总反馈数')).toBeInTheDocument()
      expect(screen.getByText('100')).toBeInTheDocument()
      expect(screen.getByText('平均评分')).toBeInTheDocument()
      expect(screen.getByText('4.2')).toBeInTheDocument()
    })
  })

  it('renders rating distribution', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockStats),
    } as Response)

    render(<FeedbackDashboard />)

    await waitFor(() => {
      expect(screen.getByText('评分分布')).toBeInTheDocument()
      expect(screen.getByText('5 星')).toBeInTheDocument()
      expect(screen.getByText('4 星')).toBeInTheDocument()
      expect(screen.getByText('3 星')).toBeInTheDocument()
      expect(screen.getByText('2 星')).toBeInTheDocument()
      expect(screen.getByText('1 星')).toBeInTheDocument()
    })
  })

  it('renders category distribution', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockStats),
    } as Response)

    render(<FeedbackDashboard />)

    await waitFor(() => {
      expect(screen.getByText('问题分类统计')).toBeInTheDocument()
      expect(screen.getByText('志愿填报')).toBeInTheDocument()
      expect(screen.getByText('院校选择')).toBeInTheDocument()
      expect(screen.getByText('专业选择')).toBeInTheDocument()
    })
  })

  it('renders recent trend chart', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockStats),
    } as Response)

    render(<FeedbackDashboard />)

    await waitFor(() => {
      expect(screen.getByText('最近 7 天趋势')).toBeInTheDocument()
    })
  })

  it('calculates satisfaction rate correctly', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockStats),
    } as Response)

    render(<FeedbackDashboard />)

    await waitFor(() => {
      expect(screen.getByText('好评率 (4-5分)')).toBeInTheDocument()
      // 4+5 star = 30+40 = 70 out of 100 = 70%
      expect(screen.getByText('70.0%')).toBeInTheDocument()
    })
  })

  it('handles fetch error gracefully', async () => {
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
    vi.spyOn(globalThis, 'fetch').mockRejectedValueOnce(new Error('Network error'))

    render(<FeedbackDashboard />)

    await waitFor(() => {
      expect(consoleSpy).toHaveBeenCalledWith('Failed to fetch feedback stats:', expect.any(Error))
      expect(screen.getByText('暂无反馈数据')).toBeInTheDocument()
    })
  })

  it('handles zero total count', async () => {
    const zeroStats = { ...mockStats, total_count: 0, rating_distribution: { 1: 0, 2: 0, 3: 0, 4: 0, 5: 0 } }
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(zeroStats),
    } as Response)

    render(<FeedbackDashboard />)

    await waitFor(() => {
      expect(screen.getByText('0%')).toBeInTheDocument()
    })
  })
})
