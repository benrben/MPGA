import { describe, it, expect } from 'vitest';
import { renderBoardLiveHtml } from './live-html.js';

describe('renderBoardLiveHtml', () => {
  it('renders a polling HTML shell with lane and lock sections', () => {
    const html = renderBoardLiveHtml();
    expect(html).toContain('Live Board');
    expect(html).toContain('setInterval(() => loadSnapshot().catch(console.error), 2500)');
    expect(html).toContain('data-section="lanes"');
    expect(html).toContain('data-section="locks"');
    expect(html).toContain('mpga-initial-snapshot');
    expect(html).toContain('function loadEmbeddedSnapshot');
  });

  it('embeds a safely escaped snapshot for direct-open fallback', () => {
    const html = renderBoardLiveHtml({
      generated_at: '2026-03-24T19:30:00.000Z',
      milestone: 'M001',
      stats: {
        total: 1,
        done: 0,
        in_flight: 1,
        blocked: 0,
        progress_pct: 0,
        evidence_produced: 0,
        evidence_expected: 0,
      },
      scheduler: {
        lock_mode: 'file',
        max_parallel_lanes: 3,
        split_strategy: 'file-groups',
      },
      ui: {
        refresh_interval_ms: 2500,
        theme: 'mpga-signal',
      },
      columns: {
        backlog: [],
        todo: [
          {
            id: 'T001',
            title: '</script><script>alert(1)</script>',
            column: 'todo',
            priority: 'high',
            assigned: 'codex',
            lane_id: null,
            run_status: 'queued',
            current_agent: null,
            file_locks: [],
            scope_locks: [],
          },
        ],
        'in-progress': [],
        testing: [],
        review: [],
        done: [],
      },
      active_lanes: [],
      active_runs: [],
      recent_events: [],
    });

    expect(html).not.toContain('</script><script>alert(1)</script>');
    expect(html).toContain(
      '\\u003c/script\\u003e\\u003cscript\\u003ealert(1)\\u003c/script\\u003e',
    );
    expect(html).toContain('textContent = value');
  });
});
