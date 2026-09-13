import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ReviewDetail from './review-detail.vue'
import ReviewList from './review-list.vue'

const mocks = vi.hoisted(() => ({
  route: { value: {} as Record<string, string> },
  getReviewQueue: vi.fn(),
  getReviewView: vi.fn(),
  submitMedicalReview: vi.fn(),
  goDetail: vi.fn(),
  backOrRoute: vi.fn(),
  handleBackPress: vi.fn(),
}))

vi.mock('@dcloudio/uni-app', () => ({
  onLoad: (hook: (query: Record<string, string>) => void) => hook(mocks.route.value),
  onShow: (hook: () => void) => hook(),
  onBackPress: vi.fn(),
}))
vi.mock('@/features/identity/public', () => ({ requireRole: () => true }))
vi.mock('@/features/content/public', () => ({
  getReviewQueue: mocks.getReviewQueue,
  getReviewView: mocks.getReviewView,
  submitMedicalReview: mocks.submitMedicalReview,
}))
vi.mock('@/platform/navigation', () => ({
  goDetail: mocks.goDetail,
  backOrRoute: mocks.backOrRoute,
  handleBackPress: mocks.handleBackPress,
  ROUTES: {
    teacherWorkspace: '/workspace',
    teacherReviewList: '/review-list',
    teacherReviewDetail: '/review-detail',
  },
}))

const reviewItem = {
  id: 'case-1',
  title: '肾小球病变病例',
  version: 2,
  specialty: '病理学',
  medicalReviewStatus: 'pending',
}

beforeEach(() => {
  mocks.route.value = {}
  mocks.getReviewQueue
    .mockReset()
    .mockImplementation(async (status: string) => (status === 'pending' ? [reviewItem] : []))
  mocks.getReviewView.mockReset().mockResolvedValue(undefined)
  mocks.submitMedicalReview.mockReset()
  mocks.goDetail.mockReset()
  mocks.backOrRoute.mockReset()
})

describe('medical review navigation context', () => {
  it('carries the content/resources origin through list and detail', async () => {
    mocks.route.value = { returnTab: 'problems', returnSection: 'resources' }
    const wrapper = mount(ReviewList)
    await flushPromises()
    await wrapper.get('.item').trigger('click')
    expect(mocks.goDetail).toHaveBeenCalledWith('/review-detail', {
      id: 'case-1',
      returnTab: 'problems',
      returnSection: 'resources',
    })
  })

  it('returns an empty direct-linked queue to its validated workspace origin', async () => {
    mocks.route.value = { returnTab: 'problems', returnSection: 'resources' }
    mocks.getReviewQueue.mockResolvedValue([])
    const wrapper = mount(ReviewList)
    await flushPromises()
    await wrapper.get('.med-state__secondary').trigger('click')
    expect(mocks.backOrRoute).toHaveBeenCalledWith('/workspace', {
      tab: 'problems',
      section: 'resources',
    })
  })

  it('returns a failed direct-linked detail to the queue with the same safe origin', async () => {
    mocks.route.value = {
      id: 'missing-case',
      returnTab: 'problems',
      returnSection: 'resources',
    }
    const wrapper = mount(ReviewDetail)
    await flushPromises()
    await wrapper.get('.med-state__secondary').trigger('click')
    expect(mocks.backOrRoute).toHaveBeenCalledWith('/review-list', {
      returnTab: 'problems',
      returnSection: 'resources',
    })
  })

  it('drops unrecognized return parameters instead of routing to an arbitrary tab', async () => {
    mocks.route.value = { returnTab: 'admin', returnSection: '../private' }
    mocks.getReviewQueue.mockResolvedValue([])
    const wrapper = mount(ReviewList)
    await flushPromises()
    await wrapper.get('.med-state__secondary').trigger('click')
    expect(mocks.backOrRoute).toHaveBeenCalledWith('/workspace', {
      tab: 'overview',
      section: undefined,
    })
  })
})
