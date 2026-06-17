export interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: Date
  toolCalls?: ToolCall[]
}

export interface ToolCall {
  id: string
  name: string
  arguments: Record<string, unknown>
  result?: string
}

export interface UserProfile {
  score?: number
  province?: string
  subject?: string
  familyCondition?: string
  targetCity?: string
  riskTolerance?: string
  careerGoal?: string
  admissionBatch?: string
  subjectRequirements?: string
  rank?: number
  budget?: string
  regionPreference?: string
  cityTier?: string
  careerPreferenceWeight?: number
  notes?: string
}

export interface SearchResult {
  title: string
  url: string
  snippet: string
  sourceType: 'government' | 'university' | 'media' | 'education' | 'forum' | 'other'
  credibilityScore: number
  freshnessLevel: 'normal' | 'attention' | 'warning'
  freshnessReason: string
  publishedDate?: string
}

export interface SearchResponse {
  query: string
  results: SearchResult[]
  totalResults: number
  searchTimeMs: number
  source: string
}
