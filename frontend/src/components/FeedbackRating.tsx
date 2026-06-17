import React, { useState } from 'react';
import { API_BASE } from '../config';

interface FeedbackRatingProps {
  sessionId: string;
  messageIndex: number;
  onSubmit?: (rating: number, comment: string) => void;
}

export const FeedbackRating: React.FC<FeedbackRatingProps> = ({
  sessionId,
  messageIndex,
  onSubmit,
}) => {
  const [rating, setRating] = useState<number>(0);
  const [hoveredRating, setHoveredRating] = useState<number>(0);
  const [comment, setComment] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    if (rating === 0) return;

    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/v1/feedback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          message_index: messageIndex,
          rating,
          comment: comment || null,
        }),
      });

      if (response.ok) {
        setSubmitted(true);
        onSubmit?.(rating, comment);
      }
    } catch (error) {
      console.error('Failed to submit feedback:', error);
    } finally {
      setLoading(false);
    }
  };

  if (submitted) {
    return (
      <div className="border-2 border-ink bg-paper p-4 mt-2">
        <div className="flex items-center gap-3">
          <span className="stamp">感谢来信</span>
          <span className="text-sm font-serif text-ink">
            您的反馈已收到，我们将持续改进服务质量
          </span>
        </div>
      </div>
    );
  }

  return (
    <div className="border border-rule bg-paper-dark p-4 mt-2">
      <div className="flex items-center gap-3 mb-3">
        <span className="text-sm font-serif text-ink">这个回答有帮助吗？</span>
        <div className="flex gap-1">
          {[1, 2, 3, 4, 5].map((star) => (
            <button
              key={star}
              type="button"
              className={`w-8 h-8 border-2 font-mono font-bold text-sm transition-all ${
                star <= (hoveredRating || rating)
                  ? 'border-gold bg-gold text-paper'
                  : 'border-rule bg-paper text-ink-light hover:border-ink'
              }`}
              onClick={() => setRating(star)}
              onMouseEnter={() => setHoveredRating(star)}
              onMouseLeave={() => setHoveredRating(0)}
            >
              {star}
            </button>
          ))}
        </div>
      </div>

      {rating > 0 && (
        <>
          <div className="rule-single mb-3" />
          <textarea
            className="w-full px-3 py-2 text-sm border-2 border-ink bg-paper font-serif text-ink resize-none focus:outline-none focus:border-gold transition-colors"
            rows={2}
            placeholder="可选：留下你的建议或意见..."
            value={comment}
            onChange={(e) => setComment(e.target.value)}
          />
          <div className="flex justify-end mt-3">
            <button
              type="button"
              className="px-4 py-2 text-sm bg-ink text-paper font-serif font-bold hover:bg-ink-light disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              onClick={handleSubmit}
              disabled={loading}
            >
              {loading ? '提交中...' : '提交反馈'}
            </button>
          </div>
        </>
      )}
    </div>
  );
};
