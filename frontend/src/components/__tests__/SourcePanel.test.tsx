import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import SourcePanel from '../SourcePanel'
import type { ToolCall } from '../../types'

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, opts?: Record<string, unknown>) => {
      const overrides: Record<string, string> = {
        'sourcePanel.title': '参考文献',
        'sourcePanel.count': `${opts?.count ?? 0} 条`,
        'sourcePanel.noData': '暂无数据来源',
        'sourcePanel.waiting': '等待结果...',
        'sourcePanel.querySuccess': '查询成功，点击查看',
        'sourcePanel.status.success': '正常',
        'sourcePanel.status.pending': '等待中',
        'sourcePanel.detail.queryLabel': '查询：',
        'sourcePanel.detail.sourceLabel': '数据源：',
        'sourcePanel.detail.resultTitle': `查询结果 · ${opts?.count ?? 0} 条`,
        'sourcePanel.detail.moreResults': `... 还有 ${opts?.count ?? 0} 条结果`,
        'sourcePanel.detail.close': '关闭',
        'sourcePanel.toolNames.semantic_search_schools': '语义搜索院校',
      }
      return overrides[key] || key
    },
  }),
}))

const source: ToolCall = {
  id: 'tool-1',
  name: 'semantic_search_schools',
  arguments: { query: '计算机强的学校' },
  result: JSON.stringify({
    query: '计算机强的学校',
    source: 'school-vector-index',
    results: [
      {
        name: '北京邮电大学',
        confidence: 'high',
        source_type: 'vector_index',
        source: 'chroma:school:school_1',
      },
    ],
  }),
}

const databaseSource: ToolCall = {
  id: 'tool-2',
  name: 'search_admission',
  arguments: { school_name: '北京大学' },
  result: JSON.stringify({
    status: 'success',
    confidence: 'high',
    source_type: 'database',
    source: 'admission_scores',
    scores: [
      {
        school_name: '北京大学',
        min_score: 685,
        province: '北京',
      },
    ],
    total: 1,
  }),
}

describe('SourcePanel', () => {
  it('renders confidence and source type on source cards', () => {
    render(<SourcePanel sources={[source]} />)

    expect(screen.getByText('语义搜索院校')).toBeInTheDocument()
    expect(screen.getByText('高可信')).toBeInTheDocument()
    expect(screen.getByText('向量索引')).toBeInTheDocument()
  })

  it('renders confidence, source type and source id in detail modal', async () => {
    const user = userEvent.setup()
    render(<SourcePanel sources={[source]} />)

    await user.click(screen.getByRole('button', { name: /语义搜索院校/i }))

    expect(screen.getAllByText('高可信').length).toBeGreaterThan(1)
    expect(screen.getAllByText('向量索引').length).toBeGreaterThan(1)
    expect(screen.getAllByText('chroma:school:school_1').length).toBeGreaterThan(1)
    expect(screen.getByText('北京邮电大学')).toBeInTheDocument()
  })

  it('renders top-level database source metadata on source cards', () => {
    render(<SourcePanel sources={[databaseSource]} />)

    expect(screen.getByText('search_admission')).toBeInTheDocument()
    expect(screen.getByText('高可信')).toBeInTheDocument()
    expect(screen.getByText('结构化库')).toBeInTheDocument()
  })

  it('renders score results as structured rows in detail modal', async () => {
    const user = userEvent.setup()
    render(<SourcePanel sources={[databaseSource]} />)

    await user.click(screen.getByRole('button', { name: /search_admission/i }))

    expect(screen.getByText('查询结果 · 1 条')).toBeInTheDocument()
    expect(screen.getByText('school_name:')).toBeInTheDocument()
    expect(screen.getByText('北京大学')).toBeInTheDocument()
    expect(screen.getAllByText('admission_scores').length).toBeGreaterThan(1)
  })
})
