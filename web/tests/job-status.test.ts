import assert from 'node:assert/strict'
import test from 'node:test'
import { render } from '@lit-labs/ssr'
import { ApbJobStatus } from '../src/job-status.ts'

test('submission has progress before the server assigns a job', () => {
  const progress = new ApbJobStatus()
  progress.submitting = true
  const markup = Array.from(render(progress.render())).join('')
  assert.match(markup, /Submitting conversion/)
  assert.doesNotMatch(markup, /Job log/)
})

test('a rejected submission keeps its error visible without a job', () => {
  const progress = new ApbJobStatus()
  progress.error = 'upload refused: Result file is empty'
  const markup = Array.from(render(progress.render())).join('')
  assert.match(markup, /upload refused: Result file is empty/)
  assert.doesNotMatch(markup, /Submitting conversion|Job log/)
})
