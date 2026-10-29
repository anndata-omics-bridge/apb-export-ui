import { LitElement, html, nothing } from './lit.ts'
import type { TemplateResult } from './lit.ts'
import { fileUrl, reportUrl, viewerUrl } from './api.ts'
import type { Options, Status } from './api.ts'
import { formatBytes } from './traces.ts'

export class ApbDownloads extends LitElement {
  static properties = {
    status: { attribute: false },
    options: { attribute: false }
  }

  status: Status | null = null
  options: Options | null = null
  // The page's address, which the job file URLs a viewer receives are relative to.
  page: string = typeof location === 'undefined' ? '' : location.href

  // Each .h5ad an output with a viewer wrote, <base>_<target>.h5ad or one per level as
  // <base>_<target>_<level>.h5ad, with its level and app.
  private viewed (status: Status): Array<{ name: string, level: string | undefined, viewer: string, app: string }> {
    const viewers = this.options?.viewers ?? {}
    return (this.options?.outputs ?? []).flatMap(({ name, about }) => {
      const viewer = about.viewer
      if (viewer === undefined || viewers[viewer] === undefined) return []
      const pattern = new RegExp(`_${name}(?:_(\\w+))?\\.h5ad$`)
      return status.files.flatMap(file => {
        const match = pattern.exec(file.name)
        return match === null ? [] : [{ name: file.name, level: match[1], viewer, app: viewers[viewer] }]
      })
    })
  }

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
        ${this.viewed(status).map(({ name, level, viewer, app }) => html`
          <p><a href=${viewerUrl(app, status.id, name, this.page)} target="_blank" rel="noopener">Open ${level === undefined ? '' : `${level} `}in ${viewer}</a></p>
        `)}
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
