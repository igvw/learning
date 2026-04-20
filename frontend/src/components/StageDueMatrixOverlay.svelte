<script lang="ts">
  import type { StageDueMatrixGraph } from '../lib/stats-page';

  export let open = false;
  export let graph: StageDueMatrixGraph;
  export let onClose: () => void = () => {};

  function handleWindowKeydown(event: KeyboardEvent): void {
    if (open && event.key === 'Escape') {
      onClose();
    }
  }

</script>

<svelte:window on:keydown={handleWindowKeydown} />

{#if open}
  <div class="modal-backdrop stage-detail-backdrop" role="presentation" on:click={onClose}>
    <div class="modal-shell stage-detail-shell" role="presentation" on:click|stopPropagation>
      <div class="panel modal-panel stage-detail-panel" role="dialog" aria-modal="true" aria-labelledby="stage-detail-title">
        <div class="panel-header sticky stage-detail-header">
          <div>
            <h2 id="stage-detail-title">Spaced repetition stage details</h2>
          </div>
          <button type="button" class="ghost-button" on:click={onClose}>Close</button>
        </div>

        <div class="subsection-header">
          <div><h3>Due-day heatmap</h3></div>
        </div>

        {#if graph.rows.length === 0}
          <p class="muted-copy">No fixed-stage questions are currently scheduled.</p>
        {:else}
          <div class="stage-detail-chart-shell">
            <svg
              class="session-graph stage-detail-chart"
              viewBox={`0 0 ${graph.chartWidth} ${graph.chartHeight}`}
              role="img"
              aria-label="Spaced repetition stage due-day heatmap"
            >
              {#each graph.columns as column}
                <text x={column.labelX} y="32" text-anchor="middle" class="graph-range-label stage-detail-column-label">
                  {column.label}
                </text>
              {/each}

              {#each graph.rows as row}
                <text x={graph.plotLeft - 10} y={row.labelY} text-anchor="end" class="graph-range-label stage-detail-row-label">
                  {row.label}
                </text>
              {/each}

              {#each graph.cells as cell}
                <g class="stage-detail-cell">
                  <title>{cell.title}</title>
                  <rect
                    x={cell.x}
                    y={cell.y}
                    width={cell.width}
                    height={cell.height}
                    rx="4"
                    ry="4"
                    fill={cell.fillColor}
                  />
                  {#if cell.count > 0}
                    <text
                      x={cell.labelX}
                      y={cell.labelY}
                      text-anchor="middle"
                      class="stage-detail-cell-count"
                      fill={cell.textColor}
                    >
                      {cell.count}
                    </text>
                  {/if}
                </g>
              {/each}
            </svg>
          </div>
        {/if}
      </div>
    </div>
  </div>
{/if}
