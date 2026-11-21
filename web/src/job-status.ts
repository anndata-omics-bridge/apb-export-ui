import { LitElement, html, nothing } from './lit.ts'
import type { PropertyValues, TemplateResult } from './lit.ts'
import { logUrl } from './api.ts'
import type { Status, Step } from './api.ts'

// "14 s", or "2 min 14 s" from a minute on.
function elapsed (seconds: number): string {
  const whole = Math.max(0, Math.floor(seconds))
  const minutes = Math.floor(whole / 60)
  return minutes > 0 ? `${minutes} min ${whole % 60} s` : `${whole} s`
}

export class ApbJobStatus extends LitElement {
  static properties = {
    status: { attribute: false },
    error: { type: String },
    submitting: { type: Boolean },
    now: { attribute: false }
  }

  status: Status | null = null
  error = ''
  submitting = false
  // Milliseconds since the epoch; ticks every second while a step runs.
  now = Date.now()
  private ticker = 0

  createRenderRoot (): this { return this }

  willUpdate (changed: PropertyValues<this>): void {
    if (changed.has('status')) this.now = Date.now()
  }

  updated (): void {
    const running = this.status?.steps.some(step => step.state === 'running') ?? false
    if (running && this.ticker === 0) {
      this.ticker = window.setInterval(() => { this.now = Date.now() }, 1000)
    } else if (!running && this.ticker !== 0) this.stop()
  }

  disconnectedCallback (): void {
    super.disconnectedCallback()
    this.stop()
  }

  private stop (): void {
    window.clearInterval(this.ticker)
    this.ticker = 0
  }

  private detail (step: Step): string {
    if (step.state === 'running' && step.started != null) {
      return `running · ${elapsed(this.now / 1000 - step.started)}`
    }
    return `${step.state}${step.seconds === null ? '' : ` · ${step.seconds} s`}`
  }

  render (): TemplateResult | typeof nothing {
    if (!this.status && !this.error && !this.submitting) return nothing
    const status = this.status
    return html`
      <section class="card">
        <h2>Progress</h2>
        ${this.submitting ? html`<p role="status">Submitting conversion…</p>` : nothing}
        ${status
          ? html`
            <p class="state state-${status.state}">${status.state}</p>
            <ol class="steps">
              ${status.steps.map(step => html`
                <li class="state-${step.state}">
                  ${step.name}<span>${this.detail(step)}</span>
                  ${step.state === 'running'
                    ? html`<progress aria-label="${step.name} running"></progress>`
                    : nothing}
                </li>
              `)}
            </ol>
            ${status.error ? html`<pre class="error">${status.error}</pre>` : nothing}
            <a href=${logUrl(status.id)} target="_blank" rel="noopener">Job log</a>
          `
          : nothing}
        ${this.error ? html`<pre class="error">${this.error}</pre>` : nothing}
      </section>
    `
  }
}
