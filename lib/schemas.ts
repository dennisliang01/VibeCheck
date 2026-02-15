import { z } from 'zod';

// ----- Project Map (one-time build per project) -----
export const ProjectMapTopicSchema = z.object({
  id: z.string(),
  title: z.string(),
  description: z.string(),
  fileHints: z.array(z.string()).optional(), // relevant file paths
});

export const ProjectMapSchema = z.object({
  projectId: z.string(),
  name: z.string(),
  summary: z.string(),
  topics: z.array(ProjectMapTopicSchema),
  builtAt: z.string(),
});

export type ProjectMap = z.infer<typeof ProjectMapSchema>;
export type ProjectMapTopic = z.infer<typeof ProjectMapTopicSchema>;

// ----- Question (generated for Q/A loop) -----
export const QuestionObjSchema = z.object({
  id: z.string(),
  topicId: z.string(),
  question: z.string(),
  hint: z.string().optional(),
  expectedConcepts: z.array(z.string()).optional(),
});

export type QuestionObj = z.infer<typeof QuestionObjSchema>;

// ----- Grade (after user submits answer) -----
export const GradeObjSchema = z.object({
  score: z.number().min(0).max(100),
  feedback: z.string(),
  correctPoints: z.array(z.string()).optional(),
  missedPoints: z.array(z.string()).optional(),
  nextRecommendedTopicId: z.string().optional(),
});

export type GradeObj = z.infer<typeof GradeObjSchema>;

// ----- Learner model (per user) -----
export const TopicMasterySchema = z.object({
  topicId: z.string(),
  score: z.number(),
  attempts: z.number(),
  lastAttemptAt: z.string().optional(),
});

export const LearnerModelSchema = z.object({
  userId: z.string(),
  topicMasteries: z.array(TopicMasterySchema),
  updatedAt: z.string(),
});

export type LearnerModel = z.infer<typeof LearnerModelSchema>;
export type TopicMastery = z.infer<typeof TopicMasterySchema>;

// ----- Session history (questions/answers/scores per project) -----
export const SessionEntrySchema = z.object({
  questionId: z.string(),
  topicId: z.string(),
  question: z.string(),
  userAnswer: z.string(),
  score: z.number(),
  feedback: z.string(),
  answeredAt: z.string(),
});

export const SessionHistorySchema = z.object({
  projectId: z.string(),
  entries: z.array(SessionEntrySchema),
});

export type SessionHistory = z.infer<typeof SessionHistorySchema>;
export type SessionEntry = z.infer<typeof SessionEntrySchema>;

// ----- Validation (for Python backend integration) -----
export const ValidationScoresSchema = z.object({
  performance: z.number().min(0).max(100),
  security: z.number().min(0).max(100),
  codeQuality: z.number().min(0).max(100),
  architecture: z.number().min(0).max(100),
});

export const ValidationFeedbackItemSchema = z.object({
  id: z.string(),
  title: z.string(),
  severity: z.enum(['high', 'medium', 'low']),
  filePath: z.string().optional(),
  recommendation: z.string(),
});

/** A single finding within a section (file:line to pay attention to). */
export const ValidationSectionDetailSchema = z.object({
  file: z.string(),
  line: z.number().optional(),
  description: z.string(),
  severity: z.enum(['critical', 'high', 'medium', 'low']).optional(),
  suggestion: z.string().optional(),
});

/** One of 8 validation sections with score and expandable details. */
export const ValidationSectionSchema = z.object({
  id: z.string(),
  label: z.string(),
  score: z.number().min(0).max(100),
  details: z.array(ValidationSectionDetailSchema).default([]),
});

export const ValidationReportSchema = z.object({
  scores: ValidationScoresSchema.optional(),
  feedback: z.array(ValidationFeedbackItemSchema).optional(),
  /** 8 sections: functional, logic, architecture, technical_debt, performance, security, observability, resilience */
  sections: z.array(ValidationSectionSchema).optional(),
});

export type ValidationScores = z.infer<typeof ValidationScoresSchema>;
export type ValidationFeedbackItem = z.infer<typeof ValidationFeedbackItemSchema>;
export type ValidationSectionDetail = z.infer<typeof ValidationSectionDetailSchema>;
export type ValidationSection = z.infer<typeof ValidationSectionSchema>;
export type ValidationReport = z.infer<typeof ValidationReportSchema>;
