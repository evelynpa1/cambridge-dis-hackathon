'use client';

import { useState, useEffect } from 'react';
import VerdictDisplay from '@/components/VerdictDisplay';
import { VerdictPayload } from '@/types/verdict';

const sampleVerdict: VerdictPayload = {
  claim: "The successive analysis of the basic reproduction number for COVID-19 in January gave 5.7 as a result.",
  truth: "Initial estimates of the basic reproduction number (R0) for COVID-19 in January were between 1.4 and 2.5, but a subsequent analysis has concluded that it may be higher (between 3.8 and 8.9).",
  decision: "mutated",
  confidence: 0.85,
  summary: "The claim is a mutation of the truth. While the truth mentions that subsequent analysis suggested R0 could be between 3.8 and 8.9, the claim cherry-picks a specific value (5.7) that falls within this range but presents it as THE definitive result rather than part of a range. The original source clearly states these were estimates with significant uncertainty, not a single conclusive finding.",
  conversation: [
    {
      agent: "Fact-Checker",
      message: "Let me analyze the numerical claims. The external claim states R0 = 5.7. The source mentions initial estimates of 1.4-2.5, and subsequent analysis of 3.8-8.9. The value 5.7 falls within the subsequent range but is not explicitly stated.",
      timestamp: "10:23:01"
    },
    {
      agent: "Sceptic",
      message: "I'm concerned about the framing here. The claim presents 5.7 as 'the result' - singular and definitive. But the source clearly indicates this was a RANGE of estimates (3.8 to 8.9), not a single value. This is a classic case of false precision.",
      timestamp: "10:23:15"
    },
    {
      agent: "Advocate",
      message: "To be fair, 5.7 does fall within the stated range. Someone reading the original research might reasonably cite a midpoint or commonly-referenced value from within that range.",
      timestamp: "10:23:28"
    },
    {
      agent: "Sceptic",
      message: "But that's exactly the problem! The source emphasizes uncertainty with phrases like 'may be higher' and provides a wide range. Converting that to a single precise number fundamentally misrepresents the scientific finding.",
      timestamp: "10:23:42"
    },
    {
      agent: "Judge",
      message: "I've heard both sides. The key issue is whether the external claim faithfully represents the source. While the number 5.7 is technically plausible given the range, presenting it as 'the result' removes critical context about uncertainty. This constitutes a mutation through false precision and removal of qualifying language.",
      timestamp: "10:23:58"
    }
  ]
};

export default function Home() {
  const [verdict, setVerdict] = useState<VerdictPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [useSample, setUseSample] = useState(false);

  useEffect(() => {
    async function fetchVerdict() {
      try {
        const res = await fetch('/api/verdict');
        if (res.ok) {
          const data = await res.json();
          setVerdict(data);
        } else {
          setUseSample(true);
          setVerdict(sampleVerdict);
        }
      } catch {
        setUseSample(true);
        setVerdict(sampleVerdict);
      } finally {
        setLoading(false);
      }
    }

    fetchVerdict();
  }, []);

  const refreshVerdict = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch('/api/verdict');
      if (res.ok) {
        const data = await res.json();
        setVerdict(data);
        setUseSample(false);
      } else {
        setError('No verdict available from API');
      }
    } catch {
      setError('Failed to fetch verdict');
    } finally {
      setLoading(false);
    }
  };

  const loadSample = () => {
    setVerdict(sampleVerdict);
    setUseSample(true);
    setError(null);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading verdict...</p>
        </div>
      </div>
    );
  }

  return (
    <main className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-4xl mx-auto px-6 mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-800">FactTrace</h1>
            <p className="text-gray-500">AI Jury Verdict Display</p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={refreshVerdict}
              className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors text-sm"
            >
              Refresh
            </button>
            <button
              onClick={loadSample}
              className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors text-sm"
            >
              Load Sample
            </button>
          </div>
        </div>

        {useSample && (
          <div className="mt-4 p-3 bg-amber-50 border border-amber-200 rounded-lg text-amber-700 text-sm">
            Displaying sample data. Send a POST request to <code className="bg-amber-100 px-1 rounded">/api/verdict</code> to display real verdict data.
          </div>
        )}

        {error && (
          <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
            {error}
          </div>
        )}
      </div>

      {verdict && <VerdictDisplay verdict={verdict} />}
    </main>
  );
}
