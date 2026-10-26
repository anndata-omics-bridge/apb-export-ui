import { LitElement, html, nothing } from './lit.ts'
import type { TemplateResult } from './lit.ts'
import { fileUrl, reportUrl } from './api.ts'
import type { Status } from './api.ts'
import { formatBytes } from './traces.ts'

export class ApbDownloads extends LitElement {
  static properties = {
    status: { attribute: false }
  }

  status: Status | null = null

  createRenderRoot (): this { return this }

  render (): TemplateResult | typeof nothing {
    const status = this.status
    if (!status || status.state !== 'done') return nothing
    return html`
      <section class="card">
        <h2>Downloads</h2>
        ${status.files.some(({ name }) => name === 'pmultiqc_report.html')
          ? html`<p><a href=${reportUrl(status.id)} target="_blank" rel="noopener">Open pMultiQC report</a></p>`
          : nothing}
        <ul class="files">
          ${status.files.map(({ name, bytes }) => html`
            <li><a href=${fileUrl(status.id, name)} download=${name}>${name}</a><span>${formatBytes(bytes)}</span></li>
          `)}
        </ul>
        <p class="note">Files are deleted from the server after a day.</p>
      </section>
    `
  }
}
