import { describe, it, expect, vi, beforeEach } from 'vitest';
import fs from 'fs';
import path from 'path';

// Mock dependencies before importing
vi.mock('../board/board.js', () => ({
  recalcStats: vi.fn(),
  saveBoard: vi.fn(),
  loadBoard: vi.fn(),
  addTask: vi.fn(),
  moveTask: vi.fn(),
  findTaskFile: vi.fn(),
}));

vi.mock('../board/board-md.js', () => ({
  renderBoardMd: vi.fn(() => '# Mock Board'),
}));

vi.mock('../board/live.js', () => ({
  writeBoardLiveSnapshot: vi.fn(() => '/tmp/test-project/MPGA/board/live/snapshot.json'),
}));

vi.mock('../board/live-html.js', () => ({
  writeBoardLiveHtml: vi.fn(() => '/tmp/test-project/MPGA/board/live/index.html'),
}));

vi.mock('fs', async () => {
  const actual = await vi.importActual<typeof import('fs')>('fs');
  return {
    ...actual,
    default: {
      ...actual,
      writeFileSync: vi.fn(),
      mkdirSync: vi.fn(),
    },
    writeFileSync: vi.fn(),
    mkdirSync: vi.fn(),
  };
});

import { persistBoard } from './board.js';
import { recalcStats, saveBoard } from '../board/board.js';
import { renderBoardMd } from '../board/board-md.js';
import { writeBoardLiveSnapshot } from '../board/live.js';
import { writeBoardLiveHtml } from '../board/live-html.js';

describe('persistBoard', () => {
  const boardDir = '/tmp/test-project/MPGA/board';
  const tasksDir = '/tmp/test-project/MPGA/board/tasks';
  const mockBoard = { columns: {}, stats: {}, version: '1.0.0' } as any;

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('calls recalcStats with board and tasksDir', () => {
    persistBoard(mockBoard, boardDir, tasksDir);
    expect(recalcStats).toHaveBeenCalledWith(mockBoard, tasksDir);
  });

  it('calls saveBoard with boardDir and board', () => {
    persistBoard(mockBoard, boardDir, tasksDir);
    expect(saveBoard).toHaveBeenCalledWith(boardDir, mockBoard);
  });

  it('writes BOARD.md with rendered markdown', () => {
    persistBoard(mockBoard, boardDir, tasksDir);
    expect(renderBoardMd).toHaveBeenCalledWith(mockBoard, tasksDir);
    expect(fs.writeFileSync).toHaveBeenCalledWith(path.join(boardDir, 'BOARD.md'), '# Mock Board');
  });

  it('refreshes live board artifacts from the same persisted state', () => {
    persistBoard(mockBoard, boardDir, tasksDir);
    expect(writeBoardLiveSnapshot).toHaveBeenCalledWith(mockBoard, tasksDir, boardDir);
    expect(writeBoardLiveHtml).toHaveBeenCalledWith(boardDir);
  });

  it('calls functions in correct order: recalcStats → saveBoard → writeBoardMd → live artifacts', () => {
    const callOrder: string[] = [];
    vi.mocked(recalcStats).mockImplementation((() => {
      callOrder.push('recalcStats');
    }) as unknown as typeof recalcStats);
    vi.mocked(saveBoard).mockImplementation(() => {
      callOrder.push('saveBoard');
    });
    vi.mocked(renderBoardMd).mockImplementation(() => {
      callOrder.push('renderBoardMd');
      return '';
    });
    vi.mocked(fs.writeFileSync).mockImplementation(() => {
      callOrder.push('writeFileSync');
    });
    vi.mocked(writeBoardLiveSnapshot).mockImplementation(() => {
      callOrder.push('writeBoardLiveSnapshot');
      return '';
    });
    vi.mocked(writeBoardLiveHtml).mockImplementation(() => {
      callOrder.push('writeBoardLiveHtml');
      return '';
    });

    persistBoard(mockBoard, boardDir, tasksDir);
    expect(callOrder).toEqual([
      'recalcStats',
      'saveBoard',
      'renderBoardMd',
      'writeFileSync',
      'writeBoardLiveSnapshot',
      'writeBoardLiveHtml',
    ]);
  });
});
