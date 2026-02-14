import type { ProjectMap, GradeObj, QuestionObj } from '@/lib/schemas';
import type { LearnerModel } from '@/lib/schemas';
import type { SessionEntry } from '@/lib/schemas';

export interface FilesSummary {
  fileCount: number;
  fileList: string[];
  totalSizeBytes: number;
  extensions: Record<string, number>;
}

/** Context for building project map: summary + optional key file contents (from discovery). */
export interface ProjectContext extends FilesSummary {
  projectId?: string;
  name?: string;
  keyFiles?: Array<{ path: string; content: string }>;
}

export interface LLMClient {
  buildProjectMap(context: ProjectContext): Promise<ProjectMap>;
  generateQuestion(
    projectMap: ProjectMap,
    learnerModel: LearnerModel,
    history: SessionEntry[]
  ): Promise<QuestionObj>;
  gradeAnswer(
    questionObj: QuestionObj,
    userAnswer: string,
    projectMap: ProjectMap
  ): Promise<GradeObj>;
}
