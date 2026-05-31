import { useState } from 'react'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, PieChart, Pie, Cell, Legend,
} from 'recharts'

/* ---------- Types ---------- */

export interface ScoreTrend {
  year: number
  min_score: number
  avg_score: number
  max_score: number
}

export interface EmploymentData {
  employment_rate: number
  avg_salary: number
  postgraduate_rate: number
  overseas_rate: number
}

interface DataVisualizationProps {
  schoolName: string
  majorName?: string
  scoreTrends: ScoreTrend[]
  employmentData: EmploymentData
}

/* ---------- Constants ---------- */

// 使用 CSS 变量，支持暗色模式
function getCSSVar(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim()
}

function getColors() {
  return {
    ink: getCSSVar('--ink') || '#1a1a2e',
    inkLight: getCSSVar('--ink-light') || '#4a4a6a',
    gold: getCSSVar('--gold') || '#c9a84c',
    goldLight: getCSSVar('--gold-light') || '#f0e6c8',
    paper: getCSSVar('--paper') || '#faf8f4',
    paperDark: getCSSVar('--paper-dark') || '#f0ede6',
    red: getCSSVar('--red') || '#c23c2e',
    rule: getCSSVar('--rule') || '#e0ddd6',
  }
}

// 组件内部使用的颜色引用
const COLORS = getColors()

const PIE_COLORS = [COLORS.gold, COLORS.red, COLORS.ink, COLORS.inkLight]

/* ---------- Sub-components ---------- */

function SectionHeader({ title }: { title: string }) {
  return (
    <div className="mb-4">
      <h3
        className="font-serif text-lg font-bold tracking-wide"
        style={{ color: COLORS.ink }}
      >
        {title}
      </h3>
      <div
        className="mt-1 h-px w-full"
        style={{ backgroundColor: COLORS.rule }}
      />
    </div>
  )
}

function ChartCard({ children }: { children: React.ReactNode }) {
  return (
    <div
      className="rounded-lg border p-5"
      style={{
        backgroundColor: COLORS.paper,
        borderColor: COLORS.rule,
        boxShadow: '0 2px 8px rgba(26,26,46,0.08)',
      }}
    >
      {children}
    </div>
  )
}

/* ---------- Score Trend Chart ---------- */

function ScoreTrendChart({ data }: { data: ScoreTrend[] }) {
  const [hoveredLine, setHoveredLine] = useState<string | null>(null)

  if (data.length === 0) {
    return (
      <ChartCard>
        <SectionHeader title="分数线趋势" />
        <p className="py-8 text-center text-sm" style={{ color: COLORS.inkLight }}>
          暂无分数线数据
        </p>
      </ChartCard>
    )
  }

  return (
    <ChartCard>
      <SectionHeader title="分数线趋势" />
      <p className="mb-3 text-xs" style={{ color: COLORS.inkLight }}>
        近 {data.length} 年录取分数线变化（单位：分）
      </p>
      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={data} margin={{ top: 8, right: 16, bottom: 4, left: -8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={COLORS.rule} />
          <XAxis
            dataKey="year"
            tick={{ fontSize: 12, fill: COLORS.inkLight }}
            axisLine={{ stroke: COLORS.rule }}
            tickLine={false}
          />
          <YAxis
            tick={{ fontSize: 12, fill: COLORS.inkLight }}
            axisLine={{ stroke: COLORS.rule }}
            tickLine={false}
            domain={['auto', 'auto']}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: COLORS.paper,
              border: `1px solid ${COLORS.rule}`,
              borderRadius: 8,
              fontSize: 13,
              boxShadow: '0 2px 8px rgba(26,26,46,0.12)',
            }}
            labelFormatter={(v) => `${v} 年`}
          />
          <Legend
            wrapperStyle={{ fontSize: 12 }}
            onMouseEnter={(e) => setHoveredLine(String(e.dataKey ?? ''))}
            onMouseLeave={() => setHoveredLine(null)}
          />
          <Line
            type="monotone"
            dataKey="max_score"
            name="最高分"
            stroke={COLORS.red}
            strokeWidth={hoveredLine === 'max_score' ? 3 : 2}
            dot={{ r: 4, fill: COLORS.red }}
            activeDot={{ r: 6 }}
          />
          <Line
            type="monotone"
            dataKey="avg_score"
            name="平均分"
            stroke={COLORS.gold}
            strokeWidth={hoveredLine === 'avg_score' ? 3 : 2}
            dot={{ r: 4, fill: COLORS.gold }}
            activeDot={{ r: 6 }}
          />
          <Line
            type="monotone"
            dataKey="min_score"
            name="最低分"
            stroke={COLORS.ink}
            strokeWidth={hoveredLine === 'min_score' ? 3 : 2}
            dot={{ r: 4, fill: COLORS.ink }}
            activeDot={{ r: 6 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </ChartCard>
  )
}

/* ---------- Employment Pie Chart ---------- */

interface PieItem {
  name: string
  value: number
}

function EmploymentChart({ data }: { data: EmploymentData }) {
  const directRate = Math.max(
    0,
    data.employment_rate - data.postgraduate_rate - data.overseas_rate,
  )

  const pieData: PieItem[] = [
    { name: '直接就业', value: Number(directRate.toFixed(1)) },
    { name: '考研深造', value: data.postgraduate_rate },
    { name: '出国留学', value: data.overseas_rate },
    { name: '其他', value: Number((100 - data.employment_rate).toFixed(1)) },
  ]

  return (
    <ChartCard>
      <SectionHeader title="就业数据" />

      {/* Summary metrics */}
      <div className="mb-4 grid grid-cols-2 gap-3">
        <MetricBox label="就业率" value={`${data.employment_rate}%`} highlight />
        <MetricBox
          label="平均薪资"
          value={`${(data.avg_salary / 1000).toFixed(1)}k`}
          highlight
        />
      </div>

      {/* Pie chart */}
      <ResponsiveContainer width="100%" height={220}>
        <PieChart>
          <Pie
            data={pieData}
            cx="50%"
            cy="50%"
            innerRadius={50}
            outerRadius={80}
            paddingAngle={3}
            dataKey="value"
            stroke="none"
          >
            {pieData.map((_, idx) => (
              <Cell key={idx} fill={PIE_COLORS[idx % PIE_COLORS.length]} />
            ))}
          </Pie>
          <Tooltip
            formatter={(value) => `${value ?? 0}%`}
            contentStyle={{
              backgroundColor: COLORS.paper,
              border: `1px solid ${COLORS.rule}`,
              borderRadius: 8,
              fontSize: 13,
            }}
          />
          <Legend
            wrapperStyle={{ fontSize: 12 }}
            formatter={(value) => (
              <span style={{ color: COLORS.ink }}>{value}</span>
            )}
          />
        </PieChart>
      </ResponsiveContainer>
    </ChartCard>
  )
}

function MetricBox({
  label,
  value,
  highlight = false,
}: {
  label: string
  value: string
  highlight?: boolean
}) {
  return (
    <div
      className="rounded-md border px-3 py-2 text-center"
      style={{
        borderColor: COLORS.rule,
        backgroundColor: highlight ? COLORS.goldLight : COLORS.paper,
      }}
    >
      <p className="text-xs" style={{ color: COLORS.inkLight }}>
        {label}
      </p>
      <p
        className="font-serif text-lg font-bold"
        style={{ color: COLORS.ink }}
      >
        {value}
      </p>
    </div>
  )
}

/* ---------- Main Component ---------- */

export default function DataVisualization({
  schoolName,
  majorName,
  scoreTrends,
  employmentData,
}: DataVisualizationProps) {
  const title = majorName
    ? `${schoolName} - ${majorName}`
    : schoolName

  return (
    <section
      className="mx-auto w-full max-w-4xl rounded-xl border p-6"
      style={{
        backgroundColor: COLORS.paper,
        borderColor: COLORS.rule,
        boxShadow: '0 4px 16px rgba(26,26,46,0.12)',
      }}
    >
      {/* Page header — newspaper masthead feel */}
      <div className="mb-6 text-center">
        <p
          className="font-mono text-xs tracking-widest uppercase"
          style={{ color: COLORS.inkLight }}
        >
          Data Report
        </p>
        <h2
          className="font-serif text-2xl font-bold tracking-wide"
          style={{ color: COLORS.ink }}
        >
          {title}
        </h2>
        <div
          className="mx-auto mt-2 h-0.5 w-24"
          style={{ backgroundColor: COLORS.gold }}
        />
      </div>

      {/* Responsive grid: stacks on mobile, side-by-side on desktop */}
      <div className="grid gap-6 md:grid-cols-2">
        <ScoreTrendChart data={scoreTrends} />
        <EmploymentChart data={employmentData} />
      </div>
    </section>
  )
}
