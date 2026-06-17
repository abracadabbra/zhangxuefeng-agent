import { useState, useEffect, useCallback } from 'react'
import { fetchUserProfile, updateUserProfile } from '../api/profile'
import type { UserProfile } from '../types'

interface UserProfilePanelProps {
  sessionId: string
}

export default function UserProfilePanel({ sessionId }: UserProfilePanelProps) {
  const [profile, setProfile] = useState<UserProfile>({})
  const [isLoading, setIsLoading] = useState(false)
  const [isSaved, setIsSaved] = useState(false)

  const fetchProfile = useCallback(async () => {
    try {
      const nextProfile = await fetchUserProfile(sessionId)
      setProfile(nextProfile ?? {})
    } catch (error) {
      console.error('Failed to fetch profile:', error)
    }
  }, [sessionId])

  useEffect(() => {
    fetchProfile()
  }, [fetchProfile])

  const handleSave = async () => {
    setIsLoading(true)
    setIsSaved(false)

    try {
      await updateUserProfile(sessionId, profile)
      setIsSaved(true)
      setTimeout(() => setIsSaved(false), 2000)
    } catch (error) {
      console.error('Failed to save profile:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const handleChange = (field: string, value: string) => {
    setProfile(prev => ({ ...prev, [field]: value || undefined }))
  }

  const handleNumberChange = (field: string, value: string) => {
    const parsed = Number(value)
    setProfile(prev => ({
      ...prev,
      [field]: value && Number.isFinite(parsed) ? parsed : undefined,
    }))
  }

  return (
    <div className="max-w-3xl mx-auto bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <h2 className="text-lg font-semibold text-gray-900 mb-6">用户画像设置</h2>
      <p className="text-sm text-gray-500 mb-6">
        设置您的基本信息，以便 AI 助手提供更精准的建议。
      </p>

      <div className="space-y-4">
        <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide">基础信息</div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              考生分数
            </label>
            <input
              type="number"
              value={profile.score || ''}
              onChange={e => handleNumberChange('score', e.target.value)}
              placeholder="如：580"
              className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              所在省份
            </label>
            <select
              value={profile.province || ''}
              onChange={e => handleChange('province', e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            >
              <option value="">请选择省份</option>
              {[
                '北京', '天津', '上海', '重庆', '河北', '山西', '辽宁', '吉林',
                '黑龙江', '江苏', '浙江', '安徽', '福建', '江西', '山东', '河南',
                '湖北', '湖南', '广东', '海南', '四川', '贵州', '云南', '陕西',
                '甘肃', '青海', '内蒙古', '广西', '西藏', '宁夏', '新疆',
              ].map(p => (
                <option key={p} value={p}>{p}</option>
              ))}
            </select>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              科类
            </label>
            <select
              value={profile.subject || ''}
              onChange={e => handleChange('subject', e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            >
              <option value="">请选择科类</option>
              <option value="理科">理科</option>
              <option value="文科">文科</option>
              <option value="综合">综合</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              家庭条件
            </label>
            <select
              value={profile.familyCondition || ''}
              onChange={e => handleChange('familyCondition', e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            >
              <option value="">请选择</option>
              <option value="一般">一般</option>
              <option value="中等">中等</option>
              <option value="较好">较好</option>
              <option value="优越">优越</option>
            </select>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              省份批次
            </label>
            <input
              value={profile.admissionBatch || ''}
              onChange={e => handleChange('admissionBatch', e.target.value)}
              placeholder="如：本科一批 / 本科批"
              className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              位次
            </label>
            <input
              type="number"
              value={profile.rank || ''}
              onChange={e => handleNumberChange('rank', e.target.value)}
              placeholder="如：12000"
              className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            />
          </div>
        </div>

        <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide pt-2">偏好与约束</div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              目标城市
            </label>
            <input
              value={profile.targetCity || ''}
              onChange={e => handleChange('targetCity', e.target.value)}
              placeholder="如：北京、上海、成都"
              className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              地域偏好
            </label>
            <input
              value={profile.regionPreference || ''}
              onChange={e => handleChange('regionPreference', e.target.value)}
              placeholder="如：华北、长三角、珠三角"
              className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              城市层级
            </label>
            <select
              value={profile.cityTier || ''}
              onChange={e => handleChange('cityTier', e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            >
              <option value="">请选择城市层级</option>
              <option value="一线城市">一线城市</option>
              <option value="新一线城市">新一线城市</option>
              <option value="省会城市">省会城市</option>
              <option value="不限">不限</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              风险偏好
            </label>
            <select
              value={profile.riskTolerance || ''}
              onChange={e => handleChange('riskTolerance', e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            >
              <option value="">请选择风险偏好</option>
              <option value="保守">保守</option>
              <option value="稳健">稳健</option>
              <option value="激进">激进</option>
            </select>
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            家庭预算
          </label>
          <select
            value={profile.budget || ''}
            onChange={e => handleChange('budget', e.target.value)}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
          >
            <option value="">请选择预算</option>
            <option value="不限">不限</option>
            <option value="5000以内/年">5000以内/年</option>
            <option value="5000-10000/年">5000-10000/年</option>
            <option value="10000-20000/年">10000-20000/年</option>
            <option value="20000以上/年">20000以上/年</option>
            <option value="中外合作办学">中外合作办学</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            选科限制
          </label>
          <input
            value={profile.subjectRequirements || ''}
            onChange={e => handleChange('subjectRequirements', e.target.value)}
            placeholder="如：物理+化学，或不限"
            className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              职业方向
            </label>
            <input
              value={profile.careerGoal || ''}
              onChange={e => handleChange('careerGoal', e.target.value)}
              placeholder="如：计算机、金融、医学"
              className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              职业偏好权重
            </label>
            <input
              type="number"
              min={1}
              max={10}
              value={profile.careerPreferenceWeight || ''}
              onChange={e => handleNumberChange('careerPreferenceWeight', e.target.value)}
              placeholder="1-10"
              className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            />
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            备注信息
          </label>
          <textarea
            value={profile.notes || ''}
            onChange={e => handleChange('notes', e.target.value)}
            placeholder="其他需要说明的情况..."
            rows={3}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
          />
        </div>
      </div>

      <div className="mt-6 flex items-center justify-between">
        <button
          onClick={handleSave}
          disabled={isLoading}
          className="px-6 py-2 bg-primary-600 text-white rounded-lg font-medium hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {isLoading ? '保存中...' : '保存设置'}
        </button>

        {isSaved && (
          <span className="text-sm text-green-600 font-medium">保存成功！</span>
        )}
      </div>
    </div>
  )
}
