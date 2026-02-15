/** General 2-word question categories. Used to map project topics to broader labels. */
export const GENERAL_CATEGORIES = [
  'App Setup',
  'UI',
  'Data Flow',
  'Security',
  'Performance',
  'Utilities',
] as const;

export type GeneralCategory = (typeof GENERAL_CATEGORIES)[number];

export function isGeneralCategory(s: string): s is GeneralCategory {
  return GENERAL_CATEGORIES.includes(s as GeneralCategory);
}

/** Map a topic (title, description) to general categories via keyword matching. */
export function topicToGeneralCategories(
  title: string,
  description: string,
  topicId: string
): GeneralCategory[] {
  const text = `${title} ${description} ${topicId}`.toLowerCase();
  const matches: GeneralCategory[] = [];
  if (/\b(entry|setup|boot|start|route|main|index)\b/.test(text)) matches.push('App Setup');
  if (/\b(ui|component|layout|view|render|style|css|frontend)\b/.test(text)) matches.push('UI');
  if (/\b(data|state|api|database|schema|model|store|fetch)\b/.test(text)) matches.push('Data Flow');
  if (/\b(auth|security|login|permission|token|session)\b/.test(text)) matches.push('Security');
  if (/\b(performance|optim|cache|speed|memory)\b/.test(text)) matches.push('Performance');
  if (/\b(util|helper|lib|shared|common)\b/.test(text)) matches.push('Utilities');
  if (matches.length === 0) matches.push('Utilities');
  return matches;
}
