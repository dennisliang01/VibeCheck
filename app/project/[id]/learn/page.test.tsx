'use client';

/// <reference types="jest" />
import React from 'react';
import { render, screen } from '@testing-library/react';
import LearnRedirectPage from './page';

const mockReplace = jest.fn();

jest.mock('next/navigation', () => ({
  useParams: () => ({ id: 'test-project' }),
  useRouter: () => ({ replace: mockReplace }),
}));

function renderLearn() {
  return render(<LearnRedirectPage />);
}

describe('Learn page redirect', () => {
  beforeEach(() => {
    mockReplace.mockClear();
  });

  it('redirects to workspace with understanding tab', () => {
    renderLearn();

    expect(mockReplace).toHaveBeenCalledWith('/project/test-project?tab=understanding');
  });

  it('shows redirecting message', () => {
    renderLearn();

    expect(screen.getByText(/redirecting/i)).toBeInTheDocument();
  });
});
