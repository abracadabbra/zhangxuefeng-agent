import React, { useEffect, useState } from 'react';
import { API_BASE } from '../config';

interface FeedbackStats {
  total_count: number;
  average_rating: number;
  rating_distribution: Record<number, number>;
  category_distribution: Record<string, number>;
  recent_trend: Array<{ date: string; count: number }>;
}

export const FeedbackDashboard: React.FC = () => {
  const [stats, setStats] = useState<FeedbackStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/v1/feedback/stats');
      if (response.ok) {
        const data = await response.json();
        setStats(data);
      }
    } catch (error) {
      console.error('Failed to fetch feedback stats:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500" />
      </div>
    );
  }

  if (!stats) {
    return (
      <div className="text-center p-8 text-gray-500">暂无反馈数据</div>
    );
  }

  const maxRatingCount = Math.max(...Object.values(stats.rating_distribution), 1);
  const maxCategoryCount = Math.max(...Object.values(stats.category_distribution), 1);
  const maxTrendCount = Math.max(...stats.recent_trend.map((t) => t.count), 1);

  return (
    <div className="space-y-6 p-6">
      <h2 className="text-2xl font-bold text-gray-900">反馈分析看板</h2>

      {/* 概览卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white rounded-lg shadow p-6">
          <div className="text-sm text-gray-500">总反馈数</div>
          <div className="text-3xl font-bold text-gray-900">{stats.total_count}</div>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <div className="text-sm text-gray-500">平均评分</div>
          <div className="text-3xl font-bold text-yellow-500">
            {stats.average_rating.toFixed(1)}
            <span className="text-lg text-gray-400">/5</span>
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <div className="text-sm text-gray-500">好评率 (4-5分)</div>
          <div className="text-3xl font-bold text-green-500">
            {stats.total_count > 0
              ? (
                  (((stats.rating_distribution[4] || 0) +
                    (stats.rating_distribution[5] || 0)) /
                    stats.total_count) *
                  100
                ).toFixed(1)
              : 0}
            %
          </div>
        </div>
      </div>

      {/* 评分分布 */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">评分分布</h3>
        <div className="space-y-3">
          {[5, 4, 3, 2, 1].map((star) => {
            const count = stats.rating_distribution[star] || 0;
            const percentage = stats.total_count > 0 ? (count / stats.total_count) * 100 : 0;
            return (
              <div key={star} className="flex items-center gap-3">
                <div className="w-16 text-sm text-gray-600 text-right">{star} 星</div>
                <div className="flex-1 bg-gray-100 rounded-full h-6 overflow-hidden">
                  <div
                    className="bg-yellow-400 h-full rounded-full transition-all duration-500"
                    style={{ width: `${(count / maxRatingCount) * 100}%` }}
                  />
                </div>
                <div className="w-20 text-sm text-gray-500">
                  {count} ({percentage.toFixed(1)}%)
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* 问题分类 */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">问题分类统计</h3>
        <div className="space-y-3">
          {Object.entries(stats.category_distribution)
            .sort(([, a], [, b]) => b - a)
            .map(([category, count]) => (
              <div key={category} className="flex items-center gap-3">
                <div className="w-24 text-sm text-gray-600 text-right">{category}</div>
                <div className="flex-1 bg-gray-100 rounded-full h-6 overflow-hidden">
                  <div
                    className="bg-blue-500 h-full rounded-full transition-all duration-500"
                    style={{ width: `${(count / maxCategoryCount) * 100}%` }}
                  />
                </div>
                <div className="w-16 text-sm text-gray-500">{count}</div>
              </div>
            ))}
        </div>
      </div>

      {/* 最近趋势 */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">最近 7 天趋势</h3>
        <div className="flex items-end gap-2 h-40">
          {stats.recent_trend.map((day) => (
            <div key={day.date} className="flex-1 flex flex-col items-center gap-1">
              <div className="text-xs text-gray-500">{day.count}</div>
              <div
                className="w-full bg-blue-500 rounded-t transition-all duration-500"
                style={{
                  height: `${(day.count / maxTrendCount) * 100}%`,
                  minHeight: day.count > 0 ? '8px' : '2px',
                }}
              />
              <div className="text-xs text-gray-400">{day.date.slice(5)}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
