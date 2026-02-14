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

const DEMO_USER_ID = 'local-user';

export function getProjectMapPath(projectId: string): string {
  return path.join(getWorkspaceDir(projectId), 'project_map.json');
}

export function loadProjectMap(projectId: string): ProjectMap | null {
  const filePath = getProjectMapPath(projectId);
  if (!fs.existsSync(filePath)) return null;
  const raw = fs.readFileSync(filePath, 'utf-8');
  const parsed = JSON.parse(raw);
  parsed.projectId = projectId;
  return ProjectMapSchema.parse(parsed);
}

export function saveProjectMap(projectId: string, map: ProjectMap): void {
  const filePath = getProjectMapPath(projectId);
  const toSave = { ...map, projectId };
  fs.writeFileSync(filePath, JSON.stringify(toSave, null, 2), 'utf-8');
}

export function getLearnerModelPath(): string {
  return path.join(getDataDir(), 'learner_model.json');
}

export function loadLearnerModel(): LearnerModel {
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

export function saveLearnerModel(model: LearnerModel): void {
  const filePath = getLearnerModelPath();
  fs.writeFileSync(filePath, JSON.stringify(model, null, 2), 'utf-8');
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

export function loadSessionHistory(projectId: string): SessionHistory {
  const filePath = getSessionHistoryPath(projectId);
  if (!fs.existsSync(filePath)) {
    return { projectId, entries: [] };
  }
  const raw = fs.readFileSync(filePath, 'utf-8');
  return SessionHistorySchema.parse(JSON.parse(raw));
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
