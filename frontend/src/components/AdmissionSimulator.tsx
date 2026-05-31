import { useState, useCallback } from 'react'

/* ── 类型定义 ────────────────────────────────────────────── */

interface SchoolRecommendation {
  id: string
  name: string
  location: string
  tier: string           // 985 / 211 / 双一流 / 一本 / 二本
  major: string
  admissionProb: number  // 0-100 录取概率
  matchScore: number     // 0-100 匹配度
  lastYearScore: number  // 去年最低录取分
  note?: string          // 备注
}

interface SimulationResult {
  reach: SchoolRecommendation[]
  match: SchoolRecommendation[]
  safety: SchoolRecommendation[]
}

interface AdmissionSimulatorProps {
  /** 模拟结果数据；缺省时使用内置演示数据 */
  data?: SimulationResult
  /** 用户分数（用于标题展示） */
  userScore?: number
}

/* ── 演示数据 ────────────────────────────────────────────── */

const DEMO_DATA: SimulationResult = {
  reach: [
    {
      id: 'r1',
      name: '武汉大学',
      location: '湖北·武汉',
      tier: '985',
      major: '计算机科学与技术',
      admissionProb: 25,
      matchScore: 68,
      lastYearScore: 621,
      note: '竞争激烈，需要冲',
    },
    {
      id: 'r2',
      name: '华中科技大学',
      location: '湖北·武汉',
      tier: '985',
      major: '软件工程',
      admissionProb: 30,
      matchScore: 72,
      lastYearScore: 618,
    },
    {
      id: 'r3',
      name: '中山大学',
      location: '广东·广州',
      tier: '985',
      major: '数据科学与大数据技术',
      admissionProb: 20,
      matchScore: 65,
      lastYearScore: 625,
      note: '近年分数线上涨明显',
    },
  ],
  match: [
    {
      id: 'm1',
      name: '湖南大学',
      location: '湖南·长沙',
      tier: '985',
      major: '计算机科学与技术',
      admissionProb: 55,
      matchScore: 85,
      lastYearScore: 602,
    },
    {
      id: 'm2',
      name: '重庆大学',
      location: '重庆',
      tier: '985',
      major: '软件工程',
      admissionProb: 60,
      matchScore: 88,
      lastYearScore: 598,
    },
    {
      id: 'm3',
      name: '南京航空航天大学',
      location: '江苏·南京',
      tier: '211',
      major: '人工智能',
      admissionProb: 65,
      matchScore: 90,
      lastYearScore: 595,
      note: '性价比极高',
    },
    {
      id: 'm4',
      name: '华东理工大学',
      location: '上海',
      tier: '211',
      major: '计算机科学与技术',
      admissionProb: 50,
      matchScore: 82,
      lastYearScore: 605,
    },
  ],
  safety: [
    {
      id: 's1',
      name: '郑州大学',
      location: '河南·郑州',
      tier: '211',
      major: '软件工程',
      admissionProb: 85,
      matchScore: 78,
      lastYearScore: 578,
    },
    {
      id: 's2',
      name: '武汉理工大学',
      location: '湖北·武汉',
      tier: '211',
      major: '计算机科学与技术',
      admissionProb: 90,
      matchScore: 80,
      lastYearScore: 572,
    },
    {
      id: 's3',
      name: '南昌大学',
      location: '江西·南昌',
      tier: '211',
      major: '软件工程',
      admissionProb: 92,
      matchScore: 75,
      lastYearScore: 565,
      note: '稳妥之选',
    },
  ],
}

/* ── 区域配置 ────────────────────────────────────────────── */

type ZoneKey = 'reach' | 'match' | 'safety'

const ZONE_CONFIG: Record<
  ZoneKey,
  { label: string; tag: string; color: string; borderColor: string; bgColor: string; desc: string }
> = {
  reach: {
    label: '冲一冲',
    tag: 'REACH',
    color: 'text-red',
    borderColor: 'border-red',
    bgColor: 'bg-red/5',
    desc: '有一定风险，但值得一试',
  },
  match: {
    label: '稳一稳',
    tag: 'MATCH',
    color: 'text-gold',
    borderColor: 'border-gold',
    bgColor: 'bg-gold-light/30',
    desc: '录取概率较高，重点考虑',
  },
  safety: {
    label: '保一保',
    tag: 'SAFETY',
    color: 'text-ink',
    borderColor: 'border-ink',
    bgColor: 'bg-paper-dark/50',
    desc: '基本确保录取，兜底志愿',
  },
}

/* ── 概率条颜色 ──────────────────────────────────────────── */

function probColor(p: number): string {
  if (p >= 80) return 'bg-ink'
  if (p >= 50) return 'bg-gold'
  return 'bg-red'
}

/* ── 主组件 ──────────────────────────────────────────────── */

export default function AdmissionSimulator({
  data = DEMO_DATA,
  userScore,
}: AdmissionSimulatorProps) {
  // 各区域内排序状态（id 数组）
  const [order, setOrder] = useState<Record<ZoneKey, string[]>>({
    reach: data.reach.map(s => s.id),
    match: data.match.map(s => s.id),
    safety: data.safety.map(s => s.id),
  })

  // 合并所有学校，按 id 索引
  const schoolMap = new Map<string, SchoolRecommendation>()
  for (const s of [...data.reach, ...data.match, ...data.safety]) {
    schoolMap.set(s.id, s)
  }

  /** 上移 */
  const moveUp = useCallback((zone: ZoneKey, index: number) => {
    if (index <= 0) return
    setOrder(prev => {
      const next = { ...prev, [zone]: [...prev[zone]] }
      ;[next[zone][index - 1], next[zone][index]] = [next[zone][index], next[zone][index - 1]]
      return next
    })
  }, [])

  /** 下移 */
  const moveDown = useCallback((zone: ZoneKey, index: number) => {
    setOrder(prev => {
      if (index >= prev[zone].length - 1) return prev
      const next = { ...prev, [zone]: [...prev[zone]] }
      ;[next[zone][index], next[zone][index + 1]] = [next[zone][index + 1], next[zone][index]]
      return next
    })
  }, [])

  /* ── 渲染 ──────────────────────────────────────────────── */

  return (
    <div className="w-full max-w-4xl mx-auto">
      {/* 标题栏 */}
      <div className="border-2 border-ink bg-paper mb-6">
        <div className="bg-ink text-paper px-4 py-2 flex items-center justify-between">
          <span className="font-mono text-sm font-bold">D 版</span>
          <span className="font-mono text-xs">🎯 志愿填报模拟</span>
        </div>
        <div className="px-6 py-4 text-center">
          <h2 className="text-2xl font-black text-ink font-serif tracking-wide">
            冲·稳·保 志愿填报方案
          </h2>
          {userScore != null && (
            <p className="text-sm text-ink-light font-serif mt-1">
              基于 <span className="font-bold text-gold">{userScore}</span> 分生成的个性化推荐
            </p>
          )}
        </div>
      </div>

      {/* 说明条 */}
      <div className="border-2 border-ink bg-paper-dark/30 px-6 py-3 mb-6 flex flex-wrap gap-x-6 gap-y-1 text-xs font-mono text-ink-light">
        <span>
          <span className="font-bold text-ink">录取概率</span> — 基于历年数据估算
        </span>
        <span>
          <span className="font-bold text-ink">匹配度</span> — 综合分数、地域、专业契合度
        </span>
        <span>
          <span className="font-bold text-ink">操作</span> — 点击箭头调整志愿顺序
        </span>
      </div>

      {/* 三个区域 */}
      <div className="space-y-6">
        {(['reach', 'match', 'safety'] as ZoneKey[]).map(zone => {
          const config = ZONE_CONFIG[zone]
          const ids = order[zone]
          const schools = ids.map(id => schoolMap.get(id)!).filter(Boolean)

          return (
            <section key={zone} className={`border-2 ${config.borderColor} bg-paper`}>
              {/* 区域头 */}
              <div className={`px-5 py-3 flex items-center justify-between border-b-2 ${config.borderColor} ${config.bgColor}`}>
                <div className="flex items-center gap-3">
                  <span className={`stamp text-xs ${config.color}`}>{config.tag}</span>
                  <h3 className="text-xl font-bold font-serif text-ink tracking-wide">
                    {config.label}
                  </h3>
                  <span className="text-xs text-ink-light font-serif italic hidden sm:inline">
                    — {config.desc}
                  </span>
                </div>
                <span className="text-xs font-mono text-ink-light">
                  {schools.length} 所院校
                </span>
              </div>

              {/* 学校列表 */}
              {schools.length === 0 ? (
                <div className="px-6 py-8 text-center text-ink-light font-serif">
                  暂无推荐院校
                </div>
              ) : (
                <div className="divide-y divide-rule">
                  {schools.map((school, idx) => (
                    <div
                      key={school.id}
                      className="px-5 py-4 hover:bg-paper-dark/30 transition-colors"
                    >
                      <div className="flex items-start gap-4">
                        {/* 排序序号 + 箭头 */}
                        <div className="flex flex-col items-center gap-1 pt-1 shrink-0">
                          <span className="text-xs font-mono text-ink-light">
                            第{idx + 1}志愿
                          </span>
                          <div className="flex flex-col gap-0.5 mt-1">
                            <button
                              onClick={() => moveUp(zone, idx)}
                              disabled={idx === 0}
                              className="w-7 h-7 flex items-center justify-center border border-ink/30 hover:border-ink hover:bg-paper-dark disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                              aria-label="上移"
                            >
                              <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                                <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 15.75l7.5-7.5 7.5 7.5" />
                              </svg>
                            </button>
                            <button
                              onClick={() => moveDown(zone, idx)}
                              disabled={idx === schools.length - 1}
                              className="w-7 h-7 flex items-center justify-center border border-ink/30 hover:border-ink hover:bg-paper-dark disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                              aria-label="下移"
                            >
                              <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                                <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
                              </svg>
                            </button>
                          </div>
                        </div>

                        {/* 学校信息 */}
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 flex-wrap mb-1">
                            <h4 className="text-lg font-bold font-serif text-ink">
                              {school.name}
                            </h4>
                            <span className="text-[10px] font-mono font-bold px-1.5 py-0.5 border border-ink/40 text-ink-light">
                              {school.tier}
                            </span>
                            <span className="text-xs font-mono text-ink-light">
                              {school.location}
                            </span>
                          </div>

                          <div className="flex items-center gap-2 mb-2">
                            <span className="text-sm font-serif text-ink-light">
                              专业：
                            </span>
                            <span className="text-sm font-serif font-medium text-ink">
                              {school.major}
                            </span>
                            {school.note && (
                              <span className="text-xs font-serif italic text-gold ml-2">
                                {school.note}
                              </span>
                            )}
                          </div>

                          {/* 数据指标条 */}
                          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                            {/* 录取概率 */}
                            <div>
                              <div className="flex items-center justify-between mb-1">
                                <span className="text-xs font-mono text-ink-light">录取概率</span>
                                <span className="text-xs font-mono font-bold text-ink">
                                  {school.admissionProb}%
                                </span>
                              </div>
                              <div className="h-2 bg-rule overflow-hidden">
                                <div
                                  className={`h-full ${probColor(school.admissionProb)} transition-all duration-500`}
                                  style={{ width: `${school.admissionProb}%` }}
                                />
                              </div>
                            </div>

                            {/* 匹配度 */}
                            <div>
                              <div className="flex items-center justify-between mb-1">
                                <span className="text-xs font-mono text-ink-light">匹配度</span>
                                <span className="text-xs font-mono font-bold text-ink">
                                  {school.matchScore}
                                </span>
                              </div>
                              <div className="h-2 bg-rule overflow-hidden">
                                <div
                                  className="h-full bg-gold transition-all duration-500"
                                  style={{ width: `${school.matchScore}%` }}
                                />
                              </div>
                            </div>

                            {/* 去年最低分 */}
                            <div className="flex items-center gap-2">
                              <span className="text-xs font-mono text-ink-light whitespace-nowrap">
                                去年最低分
                              </span>
                              <span className="text-sm font-mono font-bold text-ink">
                                {school.lastYearScore}
                              </span>
                              {userScore != null && (
                                <span
                                  className={`text-[10px] font-mono font-bold px-1 py-0.5 ${
                                    userScore >= school.lastYearScore
                                      ? 'bg-ink text-paper'
                                      : 'bg-red/10 text-red'
                                  }`}
                                >
                                  {userScore >= school.lastYearScore ? '达线' : '差' + (school.lastYearScore - userScore) + '分'}
                                </span>
                              )}
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </section>
          )
        })}
      </div>

      {/* 底部提示 */}
      <div className="mt-6 border-2 border-ink bg-paper-dark/30 px-6 py-4">
        <div className="flex items-start gap-2">
          <span className="stamp text-xs shrink-0 mt-0.5">编者按</span>
          <p className="text-sm font-serif text-ink-light leading-relaxed">
            以上方案基于历年录取数据和位次法生成，仅供参考。实际填报时请结合当年招生计划、
            一分一段表、以及各校最新政策综合判断。冲一冲的学校不要超过总志愿数的 1/3，
            保一保的学校至少留 2 所。记住：<span className="font-bold text-ink">不滑档比上好学校更重要。</span>
          </p>
        </div>
      </div>

      {/* 页码 */}
      <div className="text-center mt-4">
        <span className="text-xs text-ink-light font-mono">— 志愿模拟 · 第 1 版 —</span>
      </div>
    </div>
  )
}
