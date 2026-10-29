// Composition root: define the elements, load the options, submit, poll, show results.
// The job id lives in the URL hash, so a reload resumes the same job.

import './app.css'
import { loadExamples, loadOptions, loadQc, loadStatus, submitJob } from './api.ts'
import type { Status } from './api.ts'
import { ApbAbout } from './about.ts'
import { ApbDownloads } from './downloads.ts'
import { ApbFilePreview } from './file-preview.ts'
import { ApbJobStatus } from './job-status.ts'
import { ApbQcPanel } from './qc-panel.ts'
import { ApbUploadForm } from './upload-form.ts'

customElements.define('apb-upload-form', ApbUploadForm)
customElements.define('apb-job-status', ApbJobStatus)
customElements.define('apb-downloads', ApbDownloads)
customElements.define('apb-qc-panel', ApbQcPanel)
customElements.define('apb-file-preview', ApbFilePreview)
customElements.define('apb-about', ApbAbout)

const POLL_MS = 2000

function element<T extends HTMLElement> (selector: string): T {
  const found = document.querySelector<T>(selector)
  if (!found) throw new Error(`${selector} is missing from the page`)
  return found
}

const form = element<ApbUploadForm>('apb-upload-form')
const progress = element<ApbJobStatus>('apb-job-status')
const downloads = element<ApbDownloads>('apb-downloads')
const qc = element<ApbQcPanel>('apb-qc-panel')
const about = element<ApbAbout>('apb-about')
const setup = element<HTMLElement>('#setup')
const results = element<HTMLElement>('#results')
const summary = element<HTMLElement>('#run-summary')
const editSetup = element<HTMLButtonElement>('#edit-setup')
const viewResult = element<HTMLButtonElement>('#view-result')
const setupError = element<HTMLElement>('#setup-error')

let polling = 0
let pollRevision = 0
let activeJob: string | null = null

function showResults (description: string): void {
  summary.textContent = description
  setup.hidden = true
  results.hidden = false
  element<HTMLElement>('.run-summary h2').focus()
}

function showSetup (): void {
  setup.hidden = false
  results.hidden = true
  form.querySelector<HTMLSelectElement>('select')?.focus()
}

editSetup.addEventListener('click', () => {
  window.location.hash = ''
  showSetup()
})
viewResult.addEventListener('click', () => {
  if (activeJob) window.location.hash = `job=${activeJob}`
})

function show (status: Status | null): void {
  progress.status = status
  downloads.status = status
  form.busy = status !== null && (status.state === 'queued' || status.state === 'running')
}

async function follow (id: string): Promise<void> {
  const revision = ++pollRevision
  window.clearTimeout(polling)
  progress.error = ''
  qc.qc = null
  try {
    const status = await loadStatus(id)
    if (revision !== pollRevision) return
    show(status)
    if (status.state === 'done') {
      const report = await loadQc(id)
      if (revision === pollRevision) qc.qc = report
    } else if (status.state !== 'failed') polling = window.setTimeout(() => { void follow(id) }, POLL_MS)
  } catch (error) {
    if (revision !== pollRevision) return
    show(null)
    progress.error = String(error)
  }
}

form.addEventListener('submit-job', event => {
  const body = (event as CustomEvent<FormData>).detail
  const description = form.description
  window.clearTimeout(polling)
  pollRevision++
  activeJob = null
  viewResult.hidden = true
  form.busy = true
  progress.status = null
  progress.error = ''
  progress.submitting = true
  downloads.status = null
  qc.qc = null
  editSetup.disabled = true
  showResults(description)
  submitJob(body)
    .then(id => {
      sessionStorage.setItem(`apb-job-summary:${id}`, description)
      window.location.hash = `job=${id}`
    })
    .catch((error: unknown) => {
      form.busy = false
      progress.error = String(error)
    })
    .finally(() => {
      progress.submitting = false
      editSetup.disabled = false
    })
})

function fromHash (): void {
  const id = new URLSearchParams(window.location.hash.slice(1)).get('job')
  if (id) {
    activeJob = id
    viewResult.hidden = false
    showResults(sessionStorage.getItem(`apb-job-summary:${id}`) ?? `Job ${id}`)
    void follow(id)
  } else showSetup()
}

function showSetupError (error: unknown): void {
  setupError.textContent = String(error)
  setupError.hidden = false
}

window.addEventListener('hashchange', fromHash)
loadOptions()
  .then(options => { form.options = options; downloads.options = options; about.versions = options.versions })
  .catch(showSetupError)
loadExamples()
  .then(examples => { form.examples = examples })
  .catch(showSetupError)
fromHash()
