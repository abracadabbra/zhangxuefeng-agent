import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { FeedbackRating } from '../FeedbackRating'

describe('FeedbackRating', () => {
  const defaultProps = {
    sessionId: 'test-session-123',
    messageIndex: 0,
  }

  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('renders the feedback prompt', () => {
    render(<FeedbackRating {...defaultProps} />)
    expect(screen.getByText('这个回答有帮助吗？')).toBeInTheDocument()
  })

  it('renders 5 star buttons', () => {
    render(<FeedbackRating {...defaultProps} />)
    const buttons = screen.getAllByRole('button')
    expect(buttons.length).toBeGreaterThanOrEqual(5)
  })

  it('selects a rating when star is clicked', async () => {
    const user = userEvent.setup()
    render(<FeedbackRating {...defaultProps} />)

    const buttons = screen.getAllByRole('button')
    await user.click(buttons[2]) // Click 3rd star

    expect(screen.getByPlaceholderText('可选：留下你的建议或意见...')).toBeInTheDocument()
  })

  it('shows comment textarea after selecting rating', async () => {
    const user = userEvent.setup()
    render(<FeedbackRating {...defaultProps} />)

    const buttons = screen.getAllByRole('button')
    await user.click(buttons[3]) // Click 4th star

    expect(screen.getByPlaceholderText('可选：留下你的建议或意见...')).toBeInTheDocument()
    expect(screen.getByText('提交反馈')).toBeInTheDocument()
  })

  it('allows typing a comment', async () => {
    const user = userEvent.setup()
    render(<FeedbackRating {...defaultProps} />)

    const buttons = screen.getAllByRole('button')
    await user.click(buttons[4]) // Click 5th star

    const textarea = screen.getByPlaceholderText('可选：留下你的建议或意见...')
    await user.type(textarea, '很好的建议')

    expect(textarea).toHaveValue('很好的建议')
  })

  it('submits feedback successfully', async () => {
    const onSubmit = vi.fn()
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({}),
    } as Response)

    const user = userEvent.setup()
    render(<FeedbackRating {...defaultProps} onSubmit={onSubmit} />)

    const buttons = screen.getAllByRole('button')
    await user.click(buttons[3]) // Click 4th star
    await user.click(screen.getByText('提交反馈'))

    await waitFor(() => {
      expect(globalThis.fetch).toHaveBeenCalledWith('/api/v1/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: 'test-session-123',
          message_index: 0,
          rating: 4,
          comment: null,
        }),
      })
    })

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith(4, '')
    })
  })

  it('shows success message after submission', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({}),
    } as Response)

    const user = userEvent.setup()
    render(<FeedbackRating {...defaultProps} />)

    const buttons = screen.getAllByRole('button')
    await user.click(buttons[3]) // Click 4th star
    await user.click(screen.getByText('提交反馈'))

    await waitFor(() => {
      expect(screen.getByText('感谢来信')).toBeInTheDocument()
    })
  })

  it('handles submission error gracefully', async () => {
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
    vi.spyOn(globalThis, 'fetch').mockRejectedValueOnce(new Error('Network error'))

    const user = userEvent.setup()
    render(<FeedbackRating {...defaultProps} />)

    const buttons = screen.getAllByRole('button')
    await user.click(buttons[2]) // Click 3rd star
    await user.click(screen.getByText('提交反馈'))

    await waitFor(() => {
      expect(consoleSpy).toHaveBeenCalledWith('Failed to submit feedback:', expect.any(Error))
    })
  })

  it('shows loading state during submission', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementationOnce(() => new Promise(() => {}))

    const user = userEvent.setup()
    render(<FeedbackRating {...defaultProps} />)

    const buttons = screen.getAllByRole('button')
    await user.click(buttons[4]) // Click 5th star
    await user.click(screen.getByText('提交反馈'))

    expect(screen.getByText('提交中...')).toBeInTheDocument()
  })
})
