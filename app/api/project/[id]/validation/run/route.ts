import { NextResponse } from 'next/server';
import path from 'path';
import fs from 'fs';
import { spawn } from 'child_process';
import { getWorkspaceDir } from '@/lib/workspace';

const STATUS_FILE = 'validation_status.json';

interface ValidationStatus {
  status: 'idle' | 'running' | 'done' | 'error';
  message?: string;
  startedAt?: string;
  finishedAt?: string;
}

function writeStatus(workspaceDir: string, data: ValidationStatus) {
  const p = path.join(workspaceDir, STATUS_FILE);
  fs.writeFileSync(p, JSON.stringify(data, null, 2), 'utf-8');
}

/**
 * POST /api/project/[id]/validation/run
 * Starts codeval in the background. Returns immediately.
 * Writes validation_status.json and validation_report.json into the workspace.
 */
export async function POST(
  _req: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id: projectId } = await params;
    const workspaceDir = getWorkspaceDir(projectId);
    const projectRoot = process.cwd();
    const backendDir = path.join(projectRoot, 'Backend');
    const reportPath = path.join(workspaceDir, 'validation_report.json');

    if (!fs.existsSync(backendDir)) {
      return NextResponse.json(
        { error: 'Backend/codeval not found. Ensure Backend directory exists.' },
        { status: 500 }
      );
    }

    const statusPath = path.join(workspaceDir, STATUS_FILE);
    const existingStatus: ValidationStatus | null = fs.existsSync(statusPath)
      ? JSON.parse(fs.readFileSync(statusPath, 'utf-8'))
      : null;
    if (existingStatus?.status === 'running') {
      return NextResponse.json({ started: false, message: 'Already running' });
    }

    writeStatus(workspaceDir, {
      status: 'running',
      startedAt: new Date().toISOString(),
    });

    const pythonCmd = process.platform === 'win32' ? 'python' : 'python3';
    const args = [
      '-m',
      'codeval.cli',
      'run',
      '--path',
      workspaceDir,
      '--out',
      reportPath,
      '--format',
      'json',
      '--llm',
      'auto',
    ];

    const proc = spawn(pythonCmd, args, {
      cwd: backendDir,
      shell: false,
      env: { ...process.env, PYTHONUNBUFFERED: '1' },
    });

    let stderr = '';
    proc.stderr?.on('data', (chunk: Buffer) => {
      stderr += chunk.toString();
    });

    proc.on('exit', (code, signal) => {
      const finishedAt = new Date().toISOString();
      if (code === 0) {
        writeStatus(workspaceDir, { status: 'done', finishedAt });
      } else {
        const msg =
          signal
            ? `Killed (${signal})`
            : stderr.slice(-500) || `Exit code ${code}`;
        writeStatus(workspaceDir, {
          status: 'error',
          message: msg,
          finishedAt,
        });
      }
    });

    proc.on('error', (err) => {
      writeStatus(workspaceDir, {
        status: 'error',
        message: err.message,
        finishedAt: new Date().toISOString(),
      });
    });

    return NextResponse.json({ started: true });
  } catch (e) {
    console.error('Validation run error:', e);
    return NextResponse.json(
      {
        error: e instanceof Error ? e.message : 'Failed to start validation',
      },
      { status: 500 }
    );
  }
}
