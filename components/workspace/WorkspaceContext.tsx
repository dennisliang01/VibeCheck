'use client';

import { createContext, useCallback, useContext, useState } from 'react';

interface WorkspaceContextValue {
  selectedFilePath: string | null;
  setSelectedFilePath: (path: string | null) => void;
  onOpenCode: (path: string) => void;
}

const WorkspaceContext = createContext<WorkspaceContextValue | null>(null);

export function WorkspaceProvider({
  children,
  initialFilePath = null,
}: {
  children: React.ReactNode;
  initialFilePath?: string | null;
}) {
  const [selectedFilePath, setSelectedFilePathState] = useState<string | null>(initialFilePath);

  const setSelectedFilePath = useCallback((path: string | null) => {
    setSelectedFilePathState(path);
  }, []);

  const onOpenCode = useCallback((path: string) => {
    setSelectedFilePathState(path);
  }, []);

  const value: WorkspaceContextValue = {
    selectedFilePath,
    setSelectedFilePath,
    onOpenCode,
  };

  return (
    <WorkspaceContext.Provider value={value}>
      {children}
    </WorkspaceContext.Provider>
  );
}

export function useWorkspace() {
  const ctx = useContext(WorkspaceContext);
  if (!ctx) throw new Error('useWorkspace must be used within WorkspaceProvider');
  return ctx;
}
