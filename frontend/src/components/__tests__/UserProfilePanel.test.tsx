import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import UserProfilePanel from '../UserProfilePanel'

describe('UserProfilePanel', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    vi.spyOn(globalThis, 'fetch').mockImplementation((url) => {
      if (typeof url === 'string' && url.includes('/api/profile/')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            profile: {
              score: 650,
              province: '河南',
              subject: '物理+化学',
              family_background: '工薪阶层',
              target_city: '北京',
              family_budget: '10000-20000/年',
              rank: 12000,
            },
          }),
        } as Response)
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve({}) } as Response)
    })
  })

  it('renders enhanced profile fields from backend data', async () => {
    render(<UserProfilePanel sessionId="session-001" />)

    expect(await screen.findByDisplayValue('650')).toBeInTheDocument()
    expect(screen.getByDisplayValue('北京')).toBeInTheDocument()
    expect(screen.getByDisplayValue('10000-20000/年')).toBeInTheDocument()
    expect(screen.getByDisplayValue('12000')).toBeInTheDocument()
    expect(screen.getByText('省份批次')).toBeInTheDocument()
    expect(screen.getByText('选科限制')).toBeInTheDocument()
    expect(screen.getByText('职业偏好权重')).toBeInTheDocument()
  })

  it('saves target city and family budget as separate backend fields', async () => {
    const user = userEvent.setup()
    render(<UserProfilePanel sessionId="session-001" />)

    await screen.findByDisplayValue('650')
    await user.clear(screen.getByPlaceholderText('如：北京、上海、成都'))
    await user.type(screen.getByPlaceholderText('如：北京、上海、成都'), '上海')

    const budget = screen.getByDisplayValue('10000-20000/年')
    await user.selectOptions(budget, '20000以上/年')
    await user.click(screen.getByRole('button', { name: '保存设置' }))

    await waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalledWith(
        '/api/profile/session-001',
        expect.objectContaining({
          method: 'PUT',
          body: JSON.stringify({ field: 'target_city', value: '上海' }),
        }),
      )
      expect(globalThis.fetch).toHaveBeenCalledWith(
        '/api/profile/session-001',
        expect.objectContaining({
          method: 'PUT',
          body: JSON.stringify({ field: 'family_budget', value: '20000以上/年' }),
        }),
      )
    })
  })
})
