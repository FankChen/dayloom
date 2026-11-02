import assert from 'node:assert/strict'
import { readFileSync, readdirSync } from 'node:fs'
import path from 'node:path'
import { test } from 'node:test'
import i18next from 'i18next'
import prettier from 'prettier'
import { chinese } from '../src/locales/zh-CN.ts'
import { guideStorageKey, readGuideProgress, saveGuideProgress } from '../src/guideProgress.ts'

test('all static translation calls have a Simplified Chinese entry', async () => {
  const keys = new Set()
  function collect(node) {
    if (node.type === 'StringLiteral') keys.add(node.value)
    if (node.type === 'ConditionalExpression') {
      collect(node.consequent)
      collect(node.alternate)
    }
  }
  function visit(node) {
    if (
      node.type === 'CallExpression' &&
      (node.callee.name === 't' || node.callee.property?.name === 't') &&
      node.arguments[0]
    )
      collect(node.arguments[0])
    for (const [key, value] of Object.entries(node)) {
      if (['loc', 'tokens', 'comments', 'extra'].includes(key)) continue
      if (Array.isArray(value))
        for (const child of value) {
          if (child?.type) visit(child)
        }
      else if (value?.type) visit(value)
    }
  }
  for (const entry of readdirSync(new URL('../src', import.meta.url), {
    recursive: true,
    withFileTypes: true,
  })) {
    if (!entry.isFile() || !/\.tsx?$/.test(entry.name)) continue
    const { ast } = await prettier.__debug.parse(
      readFileSync(path.join(entry.parentPath, entry.name), 'utf8'),
      { parser: 'babel-ts' },
    )
    visit(ast)
  }
  assert.ok(keys.size > 200)
  assert.deepEqual([...keys].filter((key) => !chinese[key]).sort(), [])
})

test('Chinese interpolation and English fallback preserve user content', async () => {
  const instance = i18next.createInstance()
  await instance.init({
    lng: 'zh-CN',
    fallbackLng: 'en',
    keySeparator: false,
    nsSeparator: false,
    resources: { en: { translation: {} }, 'zh-CN': { translation: chinese } },
    interpolation: { escapeValue: false },
  })
  assert.equal(instance.t('Language'), '语言')
  assert.equal(instance.t('Edit {{title}}', { title: 'My task 我的任务' }), '编辑 My task 我的任务')
  assert.equal(
    instance.t('Step {{current}} of {{total}}', { current: 2, total: 5 }),
    '第 2 步，共 5 步',
  )
  await instance.changeLanguage('en')
  assert.equal(instance.t('Language'), 'Language')
  assert.equal(instance.t('Edit {{title}}', { title: '我的任务' }), 'Edit 我的任务')
})

function withStorage(operation, inaccessible = false) {
  const descriptor = Object.getOwnPropertyDescriptor(globalThis, 'localStorage')
  const values = new Map()
  Object.defineProperty(globalThis, 'localStorage', {
    configurable: true,
    value: {
      getItem(key) {
        if (inaccessible) throw new Error('Storage blocked')
        return values.get(key) ?? null
      },
      setItem(key, value) {
        if (inaccessible) throw new Error('Storage blocked')
        values.set(key, value)
      },
    },
  })
  try {
    operation(values)
  } finally {
    if (descriptor) Object.defineProperty(globalThis, 'localStorage', descriptor)
    else delete globalThis.localStorage
  }
}

test('guide progress is workspace scoped and only persists step and completion', () =>
  withStorage((values) => {
    assert.equal(readGuideProgress('first'), null)
    assert.equal(
      saveGuideProgress('first', {
        step: 2,
        completed: false,
        api_key: 'synthetic-do-not-store',
        message: 'private draft',
      }),
      true,
    )
    assert.deepEqual(readGuideProgress('first'), { step: 2, completed: false })
    assert.equal(readGuideProgress('second'), null)
    assert.deepEqual(JSON.parse(values.get(guideStorageKey('first'))), {
      step: 2,
      completed: false,
    })
  }))

test('malformed or out-of-range guide progress recovers safely', () =>
  withStorage((values) => {
    values.set(guideStorageKey('first'), 'not-json')
    assert.equal(readGuideProgress('first'), null)
    values.set(guideStorageKey('first'), JSON.stringify({ step: 99, completed: 'yes' }))
    assert.deepEqual(readGuideProgress('first'), { step: 0, completed: false })
  }))

test('blocked browser storage does not prevent setup', () =>
  withStorage(() => {
    assert.equal(readGuideProgress('first'), null)
    assert.equal(saveGuideProgress('first', { step: 1, completed: false }), false)
  }, true))
