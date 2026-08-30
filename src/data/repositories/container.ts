import { isApiMode } from '@/config/runtime'
import { ApiCoreRepository } from '@/data/adapters/apiCoreRepository'
import { DemoCoreRepository } from '@/data/adapters/demoCoreRepository'
import type { CoreRepository } from '@/data/repositories/core'

const coreRepository: CoreRepository = isApiMode() ? new ApiCoreRepository() : new DemoCoreRepository()

export function getCoreRepository(): CoreRepository {
  return coreRepository
}
