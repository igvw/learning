<script lang="ts">
  import type { StudyBlock } from '../lib/types';

  export let open = false;
  export let studyBlocks: StudyBlock[] = [];
  export let onClose: () => void = () => {};

  const rateFormatter = new Intl.NumberFormat(undefined, {
    maximumFractionDigits: 1,
    minimumFractionDigits: 1
  });
  const durationFormatter = new Intl.NumberFormat(undefined, {
    maximumFractionDigits: 0
  });

  function formatDate(value: string): string {
    return new Date(value).toLocaleDateString(undefined, {
      weekday: 'short',
      month: 'short',
      day: 'numeric'
    });
  }

  function formatTime(value: string): string {
    return new Date(value).toLocaleTimeString(undefined, {
      hour: '2-digit',
      minute: '2-digit',
      hour12: false
    });
  }

  function formatRange(block: StudyBlock): string {
    const startDate = formatDate(block.started_at);
    const endDate = formatDate(block.ended_at);
    if (startDate === endDate) {
      return `${startDate}, ${formatTime(block.started_at)}-${formatTime(block.ended_at)}`;
    }
    return `${startDate}, ${formatTime(block.started_at)} - ${endDate}, ${formatTime(block.ended_at)}`;
  }

  function formatQuestionCount(count: number): string {
    return `${count} ${count === 1 ? 'question' : 'questions'}`;
  }

  function formatDuration(minutes: number): string {
    return `${durationFormatter.format(minutes)} min`;
  }

  function formatRate(value: number): string {
    return `${rateFormatter.format(value)}/min`;
  }

  function formatAccuracy(value: number): string {
    return `${Math.round(value * 100)}%`;
  }

  function metricWidth(value: number, maxValue: number): string {
    if (maxValue <= 0) {
      return '0%';
    }
    return `${Math.max(4, Math.min(100, (value / maxValue) * 100))}%`;
  }

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

  $: orderedBlocks = [...studyBlocks].sort((left, right) => right.ended_at.localeCompare(left.ended_at));
  $: maxAnswersPerMinute = Math.max(...orderedBlocks.map((block) => block.answers_per_minute), 0);
</script>

<svelte:window on:keydown={handleWindowKeydown} />

{#if open}
  <div class="modal-backdrop study-block-detail-backdrop" role="presentation"></div>
  <div class="modal-shell study-block-detail-shell" role="presentation" on:click={handleShellClick}>
    <div
      class="panel modal-panel study-block-detail-panel"
      role="dialog"
      aria-modal="true"
      aria-labelledby="study-block-detail-title"
      tabindex="-1"
    >
      <div class="panel-header sticky study-block-detail-header">
        <div>
          <h2 id="study-block-detail-title">Study block details</h2>
          <p class="muted-copy">Activity blocks are grouped from answers with less than 30 minutes between them.</p>
        </div>
        <button type="button" class="ghost-button" on:click={onClose}>Close</button>
      </div>

      {#if orderedBlocks.length === 0}
        <p class="muted-copy">No study blocks yet for this scope.</p>
      {:else}
        <div class="study-block-detail-list">
          {#each orderedBlocks as block (block.started_at + ':' + block.ended_at)}
            <article class="study-block-detail-row">
              <div class="study-block-detail-time">
                <strong>{formatRange(block)}</strong>
                <span>{formatDuration(block.duration_minutes)}</span>
              </div>
              <div class="study-block-detail-count">{formatQuestionCount(block.answered_count)}</div>
              <div class="study-block-metric">
                <div class="study-block-metric-label">
                  <span>Answers/min</span>
                  <strong>{formatRate(block.answers_per_minute)}</strong>
                </div>
                <div class="study-block-metric-track" aria-hidden="true">
                  <span
                    class="study-block-metric-fill speed"
                    style={`width: ${metricWidth(block.answers_per_minute, maxAnswersPerMinute)}`}
                  ></span>
                </div>
              </div>
              <div class="study-block-metric">
                <div class="study-block-metric-label">
                  <span>Correct</span>
                  <strong>{formatAccuracy(block.accuracy)}</strong>
                </div>
                <div class="study-block-metric-track" aria-hidden="true">
                  <span
                    class="study-block-metric-fill accuracy"
                    style={`width: ${metricWidth(block.accuracy, 1)}`}
                  ></span>
                </div>
              </div>
            </article>
          {/each}
        </div>
      {/if}
    </div>
  </div>
{/if}
