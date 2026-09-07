import { readFile } from 'node:fs/promises'
import { describe, expect, it } from 'vitest'
import pagesConfig from '../../pages.json'

const pageSource = (relativePath: string) => readFile(new URL(relativePath, import.meta.url), 'utf8')

describe('T17 student information architecture', () => {
  it('uses concise native titles for the three primary destinations and legacy history', () => {
    const titles = Object.fromEntries(pagesConfig.pages.map((page) => [page.path, page.style.navigationBarTitleText]))
    expect(titles['pages/student/pbl/pbl']).toBe('研讨')
    expect(titles['pages/student/learning/index']).toBe('学习')
    expect(titles['pages/student/insights/index']).toBe('学情')
    expect(titles['pages/student/chat/chat']).toBe('历史答疑')
    expect(titles['pages/student/question/question']).toBe('病例与练习')
  })

  it('removes the known duplicate visible heroes while retaining accessible page names', async () => {
    const [pbl, insights, chat] = await Promise.all([
      pageSource('./pbl/pbl.vue'),
      pageSource('./insights/index.vue'),
      pageSource('./chat/chat.vue'),
    ])

    expect(pbl).not.toContain('我的 PBL 课堂')
    expect(pbl).not.toContain('PATHOLOGY · PBL')
    expect(insights).not.toContain('我的病理学习档案')
    expect(insights).not.toContain('LEARNING EVIDENCE')
    expect(chat).toContain('class="sr-only"')
    expect([pbl, insights, chat].every((source) => source.includes('aria-level="1"'))).toBe(true)
  })
})
