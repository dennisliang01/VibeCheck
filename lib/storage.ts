import fs from 'fs';
import path from 'path';
import {
  ProjectMapSchema,
  LearnerModelSchema,
  SessionHistorySchema,
  type ProjectMap,
  type LearnerModel,
  type SessionHistory,
  type SessionEntry,
  type TopicMastery,
} from './schemas';
import { getWorkspaceDir, getDataDir } from './workspace';
import {
  isBlobStorageAvailable,
  blobGetProjectFileContent,
  blobPutProjectFile,
  blobGetDataFile,
  blobPutDataFile,
} from './blobStorage';

const DEMO_USER_ID = 'local-user';

export function getProjectMapPath(projectId: string): string {
  if (process.env.VERCEL && isBlobStorageAvailable()) return '';
  return path.join(getWorkspaceDir(projectId), 'project_map.json');
}

export async function loadProjectMapAsync(projectId: string): Promise<ProjectMap | null> {
  if (process.env.VERCEL && isBlobStorageAvailable()) {
    try {
      const raw = await blobGetProjectFileContent(projectId, 'project_map.json');
      const parsed = JSON.parse(raw);
      parsed.projectId = projectId;
      return ProjectMapSchema.parse(parsed);
    } catch {
      return null;
    }
  }
  const filePath = path.join(getWorkspaceDir(projectId), 'project_map.json');
  if (!fs.existsSync(filePath)) return null;
  const raw = fs.readFileSync(filePath, 'utf-8');
  const parsed = JSON.parse(raw);
  parsed.projectId = projectId;
  return ProjectMapSchema.parse(parsed);
}

export function loadProjectMap(projectId: string): ProjectMap | null {
  if (process.env.VERCEL && isBlobStorageAvailable()) {
    throw new Error('Use loadProjectMapAsync on Vercel');
  }
  const filePath = getProjectMapPath(projectId);
  if (!fs.existsSync(filePath)) return null;
  const raw = fs.readFileSync(filePath, 'utf-8');
  const parsed = JSON.parse(raw);
  parsed.projectId = projectId;
  return ProjectMapSchema.parse(parsed);
}

export async function saveProjectMapAsync(projectId: string, map: ProjectMap): Promise<void> {
  if (process.env.VERCEL && isBlobStorageAvailable()) {
    const toSave = { ...map, projectId };
    await blobPutProjectFile(projectId, 'project_map.json', JSON.stringify(toSave, null, 2));
    return;
  }
  const filePath = path.join(getWorkspaceDir(projectId), 'project_map.json');
  const toSave = { ...map, projectId };
  fs.writeFileSync(filePath, JSON.stringify(toSave, null, 2), 'utf-8');
}

export function saveProjectMap(projectId: string, map: ProjectMap): void {
  if (process.env.VERCEL && isBlobStorageAvailable()) {
    throw new Error('Use saveProjectMapAsync on Vercel');
  }
  const filePath = getProjectMapPath(projectId);
  const toSave = { ...map, projectId };
  fs.writeFileSync(filePath, JSON.stringify(toSave, null, 2), 'utf-8');
}

export function getLearnerModelPath(): string {
  return path.join(getDataDir(), 'learner_model.json');
}

export async function loadLearnerModelAsync(): Promise<LearnerModel> {
  if (process.env.VERCEL && isBlobStorageAvailable()) {
    const raw = await blobGetDataFile('learner_model.json');
    if (!raw) {
      const initial: LearnerModel = {
        userId: DEMO_USER_ID,
        topicMasteries: [],
        updatedAt: new Date().toISOString(),
      };
      await saveLearnerModelAsync(initial);
      return initial;
    }
    return LearnerModelSchema.parse(JSON.parse(raw));
  }
  const filePath = getLearnerModelPath();
  if (!fs.existsSync(filePath)) {
    const initial: LearnerModel = {
      userId: DEMO_USER_ID,
      topicMasteries: [],
      updatedAt: new Date().toISOString(),
    };
    saveLearnerModel(initial);
    return initial;
  }
  const raw = fs.readFileSync(filePath, 'utf-8');
  return LearnerModelSchema.parse(JSON.parse(raw));
}

export function loadLearnerModel(): LearnerModel {
  if (process.env.VERCEL && isBlobStorageAvailable()) {
    throw new Error('Use loadLearnerModelAsync on Vercel');
  }
  const filePath = getLearnerModelPath();
  if (!fs.existsSync(filePath)) {
    const initial: LearnerModel = {
      userId: DEMO_USER_ID,
      topicMasteries: [],
      updatedAt: new Date().toISOString(),
    };
    saveLearnerModel(initial);
    return initial;
  }
  const raw = fs.readFileSync(filePath, 'utf-8');
  return LearnerModelSchema.parse(JSON.parse(raw));
}

export async function saveLearnerModelAsync(model: LearnerModel): Promise<void> {
  if (process.env.VERCEL && isBlobStorageAvailable()) {
    await blobPutDataFile('learner_model.json', JSON.stringify(model, null, 2));
    return;
  }
  const filePath = getLearnerModelPath();
  fs.writeFileSync(filePath, JSON.stringify(model, null, 2), 'utf-8');
}

export function saveLearnerModel(model: LearnerModel): void {
  if (process.env.VERCEL && isBlobStorageAvailable()) {
    throw new Error('Use saveLearnerModelAsync on Vercel');
  }
  const filePath = getLearnerModelPath();
  fs.writeFileSync(filePath, JSON.stringify(model, null, 2), 'utf-8');
}

export async function updateLearnerModelFromGradeAsync(
  topicId: string,
  score: number
): Promise<LearnerModel> {
  const model = await loadLearnerModelAsync();
  const existing = model.topicMasteries.find((m) => m.topicId === topicId);
  const now = new Date().toISOString();
  if (existing) {
    existing.attempts += 1;
    existing.score = Math.round((existing.score * (existing.attempts - 1) + score) / existing.attempts);
    existing.lastAttemptAt = now;
  } else {
    model.topicMasteries.push({
      topicId,
      score,
      attempts: 1,
      lastAttemptAt: now,
    });
  }
  model.updatedAt = now;
  await saveLearnerModelAsync(model);
  return model;
}

export function updateLearnerModelFromGrade(
  topicId: string,
  score: number
): LearnerModel {
  const model = loadLearnerModel();
  const existing = model.topicMasteries.find((m) => m.topicId === topicId);
  const now = new Date().toISOString();
  if (existing) {
    existing.attempts += 1;
    existing.score = Math.round((existing.score * (existing.attempts - 1) + score) / existing.attempts);
    existing.lastAttemptAt = now;
  } else {
    model.topicMasteries.push({
      topicId,
      score,
      attempts: 1,
      lastAttemptAt: now,
    });
  }
  model.updatedAt = now;
  saveLearnerModel(model);
  return model;
}

export function getSessionHistoryPath(projectId: string): string {
  return path.join(getDataDir(), `sessions_${projectId}.json`);
}

export async function loadSessionHistoryAsync(projectId: string): Promise<SessionHistory> {
  if (process.env.VERCEL && isBlobStorageAvailable()) {
    const raw = await blobGetDataFile(`sessions_${projectId}.json`);
    if (!raw) return { projectId, entries: [] };
    return SessionHistorySchema.parse(JSON.parse(raw));
  }
  const filePath = getSessionHistoryPath(projectId);
  if (!fs.existsSync(filePath)) return { projectId, entries: [] };
  const raw = fs.readFileSync(filePath, 'utf-8');
  return SessionHistorySchema.parse(JSON.parse(raw));
}

export function loadSessionHistory(projectId: string): SessionHistory {
  if (process.env.VERCEL && isBlobStorageAvailable()) {
    throw new Error('Use loadSessionHistoryAsync on Vercel');
  }
  const filePath = getSessionHistoryPath(projectId);
  if (!fs.existsSync(filePath)) return { projectId, entries: [] };
  const raw = fs.readFileSync(filePath, 'utf-8');
  return SessionHistorySchema.parse(JSON.parse(raw));
}

export async function appendSessionEntryAsync(
  projectId: string,
  entry: SessionEntry
): Promise<SessionHistory> {
  const history = await loadSessionHistoryAsync(projectId);
  history.entries.push(entry);
  if (process.env.VERCEL && isBlobStorageAvailable()) {
    await blobPutDataFile(`sessions_${projectId}.json`, JSON.stringify(history, null, 2));
    return history;
  }
  fs.writeFileSync(
    getSessionHistoryPath(projectId),
    JSON.stringify(history, null, 2),
    'utf-8'
  );
  return history;
}

export function appendSessionEntry(
  projectId: string,
  entry: SessionEntry
): SessionHistory {
  const history = loadSessionHistory(projectId);
  history.entries.push(entry);
  fs.writeFileSync(
    getSessionHistoryPath(projectId),
    JSON.stringify(history, null, 2),
    'utf-8'
  );
  return history;
}
