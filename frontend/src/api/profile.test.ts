import { describe, expect, it } from 'vitest'
import {
  backendProfileToUserProfile,
  profileSummary,
  userProfileToBackendFields,
  userProfileToChatContext,
} from './profile'

describe('profile api mapping', () => {
  it('maps backend profile fields to frontend profile fields', () => {
    const profile = backendProfileToUserProfile({
      score: '650',
      province: '河南',
      subject: '物理+化学',
      family_background: '工薪阶层',
      target_city: '北京',
      risk_tolerance: '稳健',
      career_goal: '计算机',
      admission_batch: '本科一批',
      subject_requirements: '物理+化学',
      rank: '12000',
      family_budget: '20000以内/年',
      region_preference: '华北',
      city_tier: '一线城市',
      career_preference_weight: '8',
    })

    expect(profile).toMatchObject({
      score: 650,
      province: '河南',
      subject: '物理+化学',
      familyCondition: '工薪阶层',
      targetCity: '北京',
      riskTolerance: '稳健',
      careerGoal: '计算机',
      admissionBatch: '本科一批',
      subjectRequirements: '物理+化学',
      rank: 12000,
      budget: '20000以内/年',
      regionPreference: '华北',
      cityTier: '一线城市',
      careerPreferenceWeight: 8,
    })
  })

  it('maps frontend profile fields to backend update fields', () => {
    const fields = userProfileToBackendFields({
      score: 650,
      province: '河南',
      subject: '物理+化学',
      familyCondition: '工薪阶层',
      targetCity: '北京',
      riskTolerance: '稳健',
      careerGoal: '计算机',
      admissionBatch: '本科一批',
      subjectRequirements: '物理+化学',
      rank: 12000,
      budget: '20000以内/年',
      regionPreference: '华北',
      cityTier: '一线城市',
      careerPreferenceWeight: 8,
    })

    expect(fields).toMatchObject({
      score: '650',
      province: '河南',
      subject: '物理+化学',
      family_background: '工薪阶层',
      target_city: '北京',
      risk_tolerance: '稳健',
      career_goal: '计算机',
      admission_batch: '本科一批',
      subject_requirements: '物理+化学',
      rank: '12000',
      family_budget: '20000以内/年',
      region_preference: '华北',
      city_tier: '一线城市',
      career_preference_weight: '8',
    })
    expect(fields.target_city).not.toBe(fields.family_budget)
  })

  it('maps frontend profile fields to chat context', () => {
    const context = userProfileToChatContext({
      score: 650,
      province: '河南',
      subject: '物理+化学',
      familyCondition: '工薪阶层',
      targetCity: '北京',
      budget: '20000以内/年',
      rank: 12000,
      careerPreferenceWeight: 8,
    })

    expect(context).toMatchObject({
      分数: 650,
      省份: '河南',
      科类: '物理+化学',
      家庭条件: '工薪阶层',
      目标城市: '北京',
      家庭预算: '20000以内/年',
      位次: 12000,
      职业偏好权重: 8,
    })
  })

  it('summarizes rank and budget when available', () => {
    const summary = profileSummary({
      score: 650,
      province: '河南',
      targetCity: '北京',
      admissionBatch: '本科一批',
      subjectRequirements: '物理+化学',
      rank: 12000,
      budget: '2万内',
      careerPreferenceWeight: 8,
    })

    expect(summary).toContain('目标北京')
    expect(summary).toContain('本科一批')
    expect(summary).toContain('选科物理+化学')
    expect(summary).toContain('位次12000')
    expect(summary).toContain('职业权重8')
  })
})
