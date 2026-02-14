'use client';

/// <reference types="jest" />
import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import HomePage from './page';
import { ToastProvider } from '@/components/ToastContext';

function renderHome() {
  return render(
    <ToastProvider>
      <HomePage />
    </ToastProvider>
  );
}

describe('Home page accessibility', () => {
  it('has upload form with accessible submit button and shows error on submit without file', async () => {
    renderHome();

    const submitButton = screen.getByRole('button', { name: /upload/i });
    expect(submitButton).toBeInTheDocument();

    const form = document.getElementById('upload-form');
    expect(form).toBeInTheDocument();

    fireEvent.submit(form!);

    await waitFor(() => {
      const inlineError = document.getElementById('upload-error');
      expect(inlineError).toBeInTheDocument();
      expect(inlineError).toHaveAttribute('role', 'alert');
      expect(inlineError).toHaveTextContent(/please select.*zip/i);
    });
  });

  it('has accessible file input via label', () => {
    renderHome();

    const fileInput = screen.getByLabelText(/upload code/i);
    expect(fileInput).toBeInTheDocument();
    expect(fileInput).toHaveAttribute('type', 'file');
    expect(fileInput).toHaveAttribute('accept', '.zip');
  });
});
