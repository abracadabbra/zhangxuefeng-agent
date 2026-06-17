interface MiniappUserProfile {
  score?: string
  province?: string
  subject?: string
  familyCondition?: string
  targetCity?: string
  riskTolerance?: string
  careerGoal?: string
  admissionBatch?: string
  subjectRequirements?: string
  rank?: string
  budget?: string
  regionPreference?: string
  cityTier?: string
  careerPreferenceWeight?: string
}

interface BackendUserProfile {
  score?: string | number | null
  province?: string | null
  subject?: string | null
  family_background?: string | null
  target_city?: string | null
  risk_tolerance?: string | null
  career_goal?: string | null
  admission_batch?: string | null
  subject_requirements?: string | null
  rank?: string | number | null
  family_budget?: string | null
  region_preference?: string | null
  city_tier?: string | null
  career_preference_weight?: string | number | null
}

export interface MiniappChatContext {
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

export interface MiniappProfileSummaryItem {
  label: string
  value: string
}

const hasValue = (value: unknown): value is string | number =>
  value !== undefined && value !== null && value !== ''

function toNumber(value: string | number | null | undefined): number | undefined {
  if (!hasValue(value)) return undefined
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : undefined
}

export function userProfileToBackendFields(profile: MiniappUserProfile): Record<string, string> {
  const fields: Record<string, string> = {}
  if (profile.score) fields.score = profile.score
  if (profile.province) fields.province = profile.province
  if (profile.subject) fields.subject = profile.subject
  if (profile.familyCondition) fields.family_background = profile.familyCondition
  if (profile.targetCity) fields.target_city = profile.targetCity
  if (profile.riskTolerance) fields.risk_tolerance = profile.riskTolerance
  if (profile.careerGoal) fields.career_goal = profile.careerGoal
  if (profile.admissionBatch) fields.admission_batch = profile.admissionBatch
  if (profile.subjectRequirements) fields.subject_requirements = profile.subjectRequirements
  if (profile.rank) fields.rank = profile.rank
  if (profile.budget) fields.family_budget = profile.budget
  if (profile.regionPreference) fields.region_preference = profile.regionPreference
  if (profile.cityTier) fields.city_tier = profile.cityTier
  if (profile.careerPreferenceWeight) {
    fields.career_preference_weight = profile.careerPreferenceWeight
  }
  return fields
}

export function backendProfileToChatContext(
  profile: BackendUserProfile | null | undefined
): MiniappChatContext | null {
  if (!profile) return null

  const context: MiniappChatContext = {
    分数: toNumber(profile.score),
    省份: profile.province ?? undefined,
    科类: profile.subject ?? undefined,
    家庭条件: profile.family_background ?? undefined,
    目标城市: profile.target_city ?? undefined,
    风险偏好: profile.risk_tolerance ?? undefined,
    职业方向: profile.career_goal ?? undefined,
    省份批次: profile.admission_batch ?? undefined,
    选科限制: profile.subject_requirements ?? undefined,
    位次: toNumber(profile.rank),
    家庭预算: profile.family_budget ?? undefined,
    地域偏好: profile.region_preference ?? undefined,
    城市层级: profile.city_tier ?? undefined,
    职业偏好权重: toNumber(profile.career_preference_weight),
  }

  return Object.values(context).some(hasValue) ? context : null
}

export function chatContextToSummaryItems(
  context: MiniappChatContext | null | undefined
): MiniappProfileSummaryItem[] {
  if (!context) return []

  return Object.entries(context)
    .filter((entry): entry is [string, string | number] => hasValue(entry[1]))
    .map(([label, value]) => ({
      label,
      value: String(value),
    }))
}

export function updateUserProfile(sessionId: string, profile: MiniappUserProfile) {
  return Promise.all(
    Object.entries(userProfileToBackendFields(profile)).map(async ([field, value]) => {
      const res = await uni.request({
        url: `/api/profile/${sessionId}`,
        method: 'PUT',
        data: { field, value },
      })
      if (res.statusCode >= 400) {
        throw new Error(`Profile update failed: ${res.statusCode}`)
      }
      return res
    })
  )
}
