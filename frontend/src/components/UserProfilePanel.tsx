import { useState, useEffect } from 'react'
import type { UserProfile } from '../types'

interface UserProfilePanelProps {
  sessionId: string
}

export default function UserProfilePanel({ sessionId }: UserProfilePanelProps) {
  const [profile, setProfile] = useState<UserProfile>({})
  const [isLoading, setIsLoading] = useState(false)
  const [isSaved, setIsSaved] = useState(false)

  useEffect(() => {
    fetchProfile()
  }, [sessionId])

  const fetchProfile = async () => {
    try {
      const response = await fetch(`/api/profile/${sessionId}`)
      if (response.ok) {
        const data = await response.json()
        setProfile(data.profile)
      }
    } catch (error) {
      console.error('Failed to fetch profile:', error)
    }
  }

  const handleSave = async () => {
    setIsLoading(true)
    setIsSaved(false)

    try {
      // 逐个字段更新
      for (const [field, value] of Object.entries(profile)) {
        if (value) {
          await fetch(`/api/profile/${sessionId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ field, value }),
          })
        }
      }
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

  return (
    <div className="max-w-2xl mx-auto bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <h2 className="text-lg font-semibold text-gray-900 mb-6">用户画像设置</h2>
      <p className="text-sm text-gray-500 mb-6">
        设置您的基本信息，以便 AI 助手提供更精准的建议。
      </p>

      <div className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              考生分数
            </label>
            <input
              type="number"
              value={profile.score || ''}
              onChange={e => handleChange('score', e.target.value)}
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

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            预算范围
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
