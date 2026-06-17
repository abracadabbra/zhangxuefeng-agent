import type { UserProfile } from '../types'
import { API_BASE } from '../config'

export interface BackendUserProfile {
  score?: number | string | null
  province?: string | null
  subject?: string | null
  family_background?: string | null
  target_city?: string | null
  risk_tolerance?: string | null
  career_goal?: string | null
  admission_batch?: string | null
  subject_requirements?: string | null
  rank?: number | string | null
  family_budget?: string | null
  region_preference?: string | null
  city_tier?: string | null
  career_preference_weight?: number | string | null
}

export interface ProfileResponse {
  session_id: string
  profile: BackendUserProfile
  is_complete: boolean
  missing_fields: string[]
}

export type ChatUserContext = {
  分数?: number
  省份?: string
  科类?: string
  家庭条件?: string
  目标城市?: string
  风险偏好?: string
  职业方向?: string
  省份批次?: string
  选科限制?: string
  位次?: number
  家庭预算?: string
  地域偏好?: string
  城市层级?: string
  职业偏好权重?: number
}

const hasValue = (value: unknown): value is string | number =>
  value !== undefined && value !== null && value !== ''

const toNumber = (value: BackendUserProfile['score']): number | undefined => {
  if (!hasValue(value)) return undefined
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : undefined
}

export function backendProfileToUserProfile(profile: BackendUserProfile | null | undefined): UserProfile {
  if (!profile) return {}

  return {
    score: toNumber(profile.score),
    province: profile.province ?? undefined,
    subject: profile.subject ?? undefined,
    familyCondition: profile.family_background ?? undefined,
    targetCity: profile.target_city ?? undefined,
    riskTolerance: profile.risk_tolerance ?? undefined,
    careerGoal: profile.career_goal ?? undefined,
    admissionBatch: profile.admission_batch ?? undefined,
    subjectRequirements: profile.subject_requirements ?? undefined,
    rank: toNumber(profile.rank),
    budget: profile.family_budget ?? undefined,
    regionPreference: profile.region_preference ?? undefined,
    cityTier: profile.city_tier ?? undefined,
    careerPreferenceWeight: toNumber(profile.career_preference_weight),
  }
}

export function userProfileToBackendFields(profile: UserProfile): Record<string, string> {
  const fields: Record<string, string> = {}
  if (profile.score != null) fields.score = String(profile.score)
  if (profile.province) fields.province = profile.province
  if (profile.subject) fields.subject = profile.subject
  if (profile.familyCondition) fields.family_background = profile.familyCondition
  if (profile.targetCity) fields.target_city = profile.targetCity
  if (profile.riskTolerance) fields.risk_tolerance = profile.riskTolerance
  if (profile.careerGoal) fields.career_goal = profile.careerGoal
  if (profile.admissionBatch) fields.admission_batch = profile.admissionBatch
  if (profile.subjectRequirements) fields.subject_requirements = profile.subjectRequirements
  if (profile.rank != null) fields.rank = String(profile.rank)
  if (profile.budget) fields.family_budget = profile.budget
  if (profile.regionPreference) fields.region_preference = profile.regionPreference
  if (profile.cityTier) fields.city_tier = profile.cityTier
  if (profile.careerPreferenceWeight != null) {
    fields.career_preference_weight = String(profile.careerPreferenceWeight)
  }
  return fields
}

export function userProfileToChatContext(profile: UserProfile | null | undefined): ChatUserContext | null {
  if (!profile) return null

  const context: ChatUserContext = {
    分数: profile.score,
    省份: profile.province,
    科类: profile.subject,
    家庭条件: profile.familyCondition,
    目标城市: profile.targetCity,
    风险偏好: profile.riskTolerance,
    职业方向: profile.careerGoal,
    省份批次: profile.admissionBatch,
    选科限制: profile.subjectRequirements,
    位次: profile.rank,
    家庭预算: profile.budget,
    地域偏好: profile.regionPreference,
    城市层级: profile.cityTier,
    职业偏好权重: profile.careerPreferenceWeight,
  }

  return Object.values(context).some(hasValue) ? context : null
}

export function profileSummary(profile: UserProfile): string {
  return [
    profile.score ? `${profile.score}分` : '',
    profile.province,
    profile.subject,
    profile.familyCondition,
    profile.targetCity ? `目标${profile.targetCity}` : '',
    profile.riskTolerance ? `风险${profile.riskTolerance}` : '',
    profile.careerGoal ? `方向${profile.careerGoal}` : '',
    profile.admissionBatch,
    profile.subjectRequirements ? `选科${profile.subjectRequirements}` : '',
    profile.rank ? `位次${profile.rank}` : '',
    profile.budget ? `预算${profile.budget}` : '',
    profile.regionPreference,
    profile.cityTier,
    profile.careerPreferenceWeight ? `职业权重${profile.careerPreferenceWeight}` : '',
  ].filter(Boolean).join('，')
}

export async function fetchUserProfile(sessionId: string): Promise<UserProfile | null> {
  const response = await fetch(`${API_BASE}/api/profile/${sessionId}`)
  if (!response.ok) return null
  const data = await response.json() as Partial<ProfileResponse>
  return backendProfileToUserProfile(data.profile)
}

export async function updateUserProfile(sessionId: string, profile: UserProfile): Promise<void> {
  const fields = userProfileToBackendFields(profile)

  await Promise.all(
    Object.entries(fields).map(([field, value]) =>
      fetch(`${API_BASE}/api/profile/${sessionId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ field, value }),
      })
    )
  )
}
