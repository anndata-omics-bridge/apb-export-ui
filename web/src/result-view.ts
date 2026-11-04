import { LitElement, html, nothing } from './lit.ts'
import type { TemplateResult } from './lit.ts'
import type { Qc } from './api.ts'
import type { ResultStructure } from './representation.ts'

type View = 'qc' | 'structure'

// A finished job's views: quality control first, then the AnnData structure of each result.
// A view the result cannot give is left out: a table export such as MSstats' has no QC
// matrix, and a Parquet, DuckDB or table result has no AnnData sidecar.
export class ApbResultView extends LitElement {
  static properties = {
    qc: { attribute: false },
    structures: { attribute: false },
    view: { state: true }
  }

  qc: Qc | null = null
  structures: ResultStructure[] = []
  view: View = 'qc'

  createRenderRoot (): this { return this }

  // Forget the previous job, so the next one opens on quality control.
  clear (): void {
    this.qc = null
    this.structures = []
    this.view = 'qc'
  }

  private views (): Array<[View, string]> {
    const views: Array<[View, string]> = []
    if ((this.qc?.matrices.length ?? 0) > 0) views.push(['qc', 'Quality control'])
    if (this.structures.length > 0) views.push(['structure', 'AnnData structure'])
    return views
  }

  render (): TemplateResult | typeof nothing {
    const views = this.views()
    const shown = views.find(([view]) => view === this.view) ?? views[0]
    if (shown === undefined) return nothing
    const [view, label] = shown
    return html`
      <section class="card result-view" aria-label="Result">
        ${views.length > 1
          ? html`<nav class="tabs view-tabs" role="tablist" aria-label="Result views">
              ${views.map(([id, title]) => html`
                <button type="button" role="tab" aria-selected=${String(id === view)} @click=${() => { this.view = id }}>${title}</button>
              `)}
            </nav>`
          : html`<h2>${label}</h2>`}
        ${view === 'qc'
          ? html`<apb-qc-panel .qc=${this.qc}></apb-qc-panel>`
          : html`<apb-structure-panel .structures=${this.structures}></apb-structure-panel>`}
      </section>
    `
  }
}
