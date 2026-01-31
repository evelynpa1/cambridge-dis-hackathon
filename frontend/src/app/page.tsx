'use client';

import { useState, useEffect } from 'react';
import VerdictDisplay from '@/components/VerdictDisplay';
import { VerdictPayload } from '@/types/verdict';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface CaseItem {
  id: number;
  claim: string;
  truth: string;
}

export default function Home() {
  const [verdict, setVerdict] = useState<VerdictPayload | null>(null);
  const [loading, setLoading] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [cases, setCases] = useState<CaseItem[]>([]);
  const [selectedCase, setSelectedCase] = useState<number | null>(null);
  const [claim, setClaim] = useState('');
  const [truth, setTruth] = useState('');

  // Fetch cases on mount
  useEffect(() => {
    async function fetchCases() {
      try {
        const res = await fetch(`${API_URL}/api/cases`);
        if (res.ok) {
          const data = await res.json();
          setCases(data);
        }
      } catch (err) {
        console.error('Failed to fetch cases:', err);
      }
    }
    fetchCases();
  }, []);

  // Load existing verdict on mount
  useEffect(() => {
    async function fetchVerdict() {
      setLoading(true);
      try {
        const res = await fetch(`${API_URL}/api/verdict`);
        if (res.ok) {
          const data = await res.json();
          setVerdict(data);
        }
      } catch (err) {
        // No verdict available, that's fine
      } finally {
        setLoading(false);
      }
    }
    fetchVerdict();
  }, []);

  // When a case is selected, populate the form
  useEffect(() => {
    if (selectedCase !== null) {
      const selected = cases.find(c => c.id === selectedCase);
      if (selected) {
        setClaim(selected.claim);
        setTruth(selected.truth);
      }
    }
  }, [selectedCase, cases]);

  const runVerification = async () => {
    if (!claim.trim() || !truth.trim()) {
      setError('Please enter both a claim and a truth');
      return;
    }

    setVerifying(true);
    setError(null);
    // Reset verdict but keep claim/truth for partial display
    setVerdict({
      claim,
      truth,
      conversation: [],
      summary: '',
      decision: 'uncertain',
      confidence: 0,
      disclaimers: [],
    });

    try {
      const res = await fetch(`${API_URL}/api/verify/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ claim, truth, debate_rounds: 2 }),
      });

      if (!res.ok) {
        const err = await res.json();
        setError(err.detail || 'Verification failed');
        setVerifying(false);
        return;
      }

      const reader = res.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) {
        setError('Failed to read stream');
        setVerifying(false);
        return;
      }

      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const event = JSON.parse(line.slice(6));

              if (event.type === 'agent') {
                // Add new agent message to conversation
                setVerdict((prev) => {
                  if (!prev) return prev;
                  return {
                    ...prev,
                    conversation: [...prev.conversation, event.data],
                  };
                });
              } else if (event.type === 'analysis') {
                // Update analysis section immediately
                setVerdict((prev) => {
                  if (!prev) return null; // Should ideally be initialized
                  return {
                    ...prev,
                    analysis: event.data,
                  };
                });
              } else if (event.type === 'verdict') {
                // Final verdict with all data
                setVerdict(event.data);
              }
            } catch (e) {
              console.error('Failed to parse SSE event:', e);
            }
          }
        }
      }
    } catch (err) {
      setError('Failed to connect to backend. Is it running on port 8000?');
    } finally {
      setVerifying(false);
    }
  };

  return (
    <main className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-4xl mx-auto px-6">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-800">FactTrace</h1>
          <p className="text-gray-500">AI Jury for Claim Verification</p>
        </div>

        {/* Input Section */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-6">
          <h2 className="text-lg font-semibold text-gray-800 mb-4">Evaluate a Claim</h2>

          {/* Case Selector */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Select from dataset (Atlas.csv)
            </label>
            <select
              value={selectedCase ?? ''}
              onChange={(e) => setSelectedCase(e.target.value ? Number(e.target.value) : null)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-gray-900 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="">-- Choose a case or enter custom --</option>
              {cases.map((c) => (
                <option key={c.id} value={c.id}>
                  Case {c.id}: {c.claim.slice(0, 60)}...
                </option>
              ))}
            </select>
          </div>

          {/* Claim Input */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              External Claim
            </label>
            <textarea
              value={claim}
              onChange={(e) => setClaim(e.target.value)}
              placeholder="The claim to evaluate..."
              rows={3}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-gray-900 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          {/* Truth Input */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Source Truth
            </label>
            <textarea
              value={truth}
              onChange={(e) => setTruth(e.target.value)}
              placeholder="The original source/fact..."
              rows={3}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-gray-900 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          {/* Submit Button */}
          <button
            onClick={runVerification}
            disabled={verifying}
            className="w-full px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium disabled:bg-blue-300 disabled:cursor-not-allowed"
          >
            {verifying ? (
              <span className="flex items-center justify-center gap-2">
                <span className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></span>
                Running AI Jury...
              </span>
            ) : (
              'Run Verification'
            )}
          </button>

          {error && (
            <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
              {error}
            </div>
          )}
        </div>

        {/* Loading State */}
        {loading && (
          <div className="flex items-center justify-center py-12">
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto"></div>
              <p className="mt-4 text-gray-600">Loading...</p>
            </div>
          </div>
        )}

        {/* Verdict Display - show during streaming too */}
        {verdict && verdict.conversation.length > 0 && !loading && (
          <VerdictDisplay verdict={verdict} isStreaming={verifying} />
        )}
      </div>
    </main>
  );
}
