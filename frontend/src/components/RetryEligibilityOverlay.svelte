<script lang="ts">
  import type { RetryEligibilityHourlyGraph, RetryEligibilityLongRangeGraph } from '../lib/stats/retry-graphs';

  export let open = false;
  export let hourlyGraph: RetryEligibilityHourlyGraph;
  export let longRangeGraph: RetryEligibilityLongRangeGraph;
  export let onClose: () => void = () => {};

  function handleWindowKeydown(event: KeyboardEvent): void {
    if (open && event.key === 'Escape') {
      onClose();
    }
  }

  function handleShellClick(event: MouseEvent): void {
    if (event.target === event.currentTarget) {
      onClose();
    }
  }

  $: hourlyTotal = hourlyGraph.hours.reduce((total, hour) => total + hour.count, 0);
  $: longRangeTotal = longRangeGraph.weeks.reduce((total, week) => total + week.count, 0);
</script>

<svelte:window on:keydown={handleWindowKeydown} />

{#if open}
  <div class="modal-backdrop retry-detail-backdrop" role="presentation"></div>
  <div class="modal-shell retry-detail-shell" role="presentation" on:click={handleShellClick}>
    <div
      class="panel modal-panel retry-detail-panel"
      role="dialog"
      aria-modal="true"
      aria-labelledby="retry-detail-title"
      tabindex="-1"
    >
        <div class="panel-header sticky retry-detail-header">
          <div>
            <h2 id="retry-detail-title">Retry eligibility details</h2>
          </div>
          <button type="button" class="ghost-button" on:click={onClose}>Close</button>
        </div>

        <div class="retry-detail-stack">
          <section class="retry-detail-section">
            <div class="subsection-header">
              <div><h3>&lt;1 by hour</h3></div>
            </div>

            {#if hourlyTotal === 0}
              <p class="muted-copy">No fixed-bucket questions are currently due within the main graph&apos;s <code>&lt;1</code> group.</p>
            {:else}
              <div class="session-graph-shell">
                <svg
                  class="session-graph retry-detail-chart"
                  viewBox={`0 0 ${hourlyGraph.chartWidth} ${hourlyGraph.chartHeight}`}
                  role="img"
                  aria-label="Retry eligibility under one day by hour"
                >
                  <line
                    x1={hourlyGraph.plotLeft}
                    y1={hourlyGraph.axisY}
                    x2={hourlyGraph.plotRight}
                    y2={hourlyGraph.axisY}
                    class="graph-axis"
                  />
                  {#each hourlyGraph.hours as hour}
                    <g class="session-bar">
                      <title>{hour.fullLabel}: {hour.count} questions</title>
                      <rect
                        x={hour.x}
                        y={hour.y}
                        width={hour.width}
                        height={hour.height}
                        rx="6"
                        ry="6"
                        fill={hour.fillColor}
                      />
                      {#if hour.label}
                        <text x={hour.labelX} y={hourlyGraph.chartHeight - 18} text-anchor="middle" class="graph-range-label">
                          {hour.label}
                        </text>
                      {/if}
                    </g>
                  {/each}
                </svg>
              </div>
            {/if}
          </section>

          <section class="retry-detail-section">
            <div class="subsection-header">
              <div><h3>&gt;7 by week</h3></div>
            </div>

            {#if longRangeTotal === 0}
              <p class="muted-copy">No questions are currently beyond the main graph&apos;s 7-day window.</p>
            {:else}
              <div class="session-graph-shell">
                <svg
                  class="session-graph retry-detail-chart retry-detail-chart-wide"
                  viewBox={`0 0 ${longRangeGraph.chartWidth} ${longRangeGraph.chartHeight}`}
                  role="img"
                  aria-label="Retry eligibility beyond seven days by week"
                >
                  <line
                    x1={longRangeGraph.plotLeft}
                    y1={longRangeGraph.axisY}
                    x2={longRangeGraph.plotRight}
                    y2={longRangeGraph.axisY}
                    class="graph-axis"
                  />
                  {#each longRangeGraph.weeks as week}
                    <g class="session-bar">
                      <title>{week.fullLabel}: {week.count} questions</title>
                      <rect
                        x={week.x}
                        y={week.y}
                        width={week.width}
                        height={week.height}
                        rx="4"
                        ry="4"
                        fill={week.fillColor}
                      />
                      {#if week.label}
                        <text x={week.labelX} y={longRangeGraph.chartHeight - 18} text-anchor="middle" class="graph-range-label">
                          {week.label}
                        </text>
                      {/if}
                    </g>
                  {/each}
                </svg>
              </div>
            {/if}
          </section>
        </div>
      </div>
  </div>
{/if}
