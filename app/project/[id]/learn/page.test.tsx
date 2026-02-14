'use client';

/// <reference types="jest" />
import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import LearnPage from './page';
import { ToastProvider } from '@/components/ToastContext';

jest.mock('next/navigation', () => ({
  useParams: () => ({ id: 'test-project' }),
}));

const mockQuestion = {
  id: 'q1',
  topicId: 't1',
  question: 'What does this function do?',
  hint: 'Look at the return value.',
};

function renderLearn() {
  return render(
    <ToastProvider>
      <LearnPage />
    </ToastProvider>
  );
}

describe('Learn page accessibility', () => {
  beforeEach(() => {
    global.fetch = jest.fn((url: string) => {
      if (url.includes('/question')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockQuestion),
        } as Response);
      }
      if (url.includes('/tree')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(null) } as Response);
      }
      return Promise.reject(new Error('Unknown URL'));
    }) as jest.Mock;
  });

  it('has one h1 and exposes answer textarea with accessible name', async () => {
    renderLearn();

    await waitFor(() => {
      expect(screen.getByText(mockQuestion.question)).toBeInTheDocument();
    });

    const headings = screen.getAllByRole('heading', { level: 1 });
    expect(headings).toHaveLength(1);
    expect(headings[0]).toHaveTextContent(/question/i);

    const textarea = screen.getByRole('textbox', { name: /your answer/i });
    expect(textarea).toBeInTheDocument();
    expect(textarea).toHaveAttribute('id', 'answer-input');
  });

  it('has submit button and form for answer', async () => {
    renderLearn();

    await waitFor(() => {
      expect(screen.getByText(mockQuestion.question)).toBeInTheDocument();
    });

    const submitButton = screen.getByRole('button', { name: /submit/i });
    expect(submitButton).toBeInTheDocument();

    const form = submitButton.closest('form');
    expect(form).toBeInTheDocument();
  });
});
