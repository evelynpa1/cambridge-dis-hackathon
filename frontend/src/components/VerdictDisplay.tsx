'use client';

import { useState } from 'react';
import { VerdictPayload, AgentMessage } from '@/types/verdict';

interface VerdictDisplayProps {
  verdict: VerdictPayload;
}

const agentColors: Record<string, string> = {
  'Sceptic': 'bg-red-100 border-red-300 text-red-800',
  'Fact-Checker': 'bg-blue-100 border-blue-300 text-blue-800',
  'Judge': 'bg-purple-100 border-purple-300 text-purple-800',
  'Advocate': 'bg-green-100 border-green-300 text-green-800',
  'Moderator': 'bg-gray-100 border-gray-300 text-gray-800',
};

function getAgentColor(agent: string): string {
  return agentColors[agent] || 'bg-slate-100 border-slate-300 text-slate-800';
}

function DecisionBadge({ decision, confidence }: { decision: string; confidence?: number }) {
  const colorMap = {
    faithful: 'bg-green-500 text-white',
    mutated: 'bg-red-500 text-white',
    uncertain: 'bg-yellow-500 text-black',
  };

  const color = colorMap[decision as keyof typeof colorMap] || 'bg-gray-500 text-white';

  return (
    <div className="flex items-center gap-3">
      <span className={`px-4 py-2 rounded-full font-bold text-lg uppercase ${color}`}>
        {decision}
      </span>
      {confidence !== undefined && (
        <span className="text-sm text-gray-500">
          {Math.round(confidence * 100)}% confidence
        </span>
      )}
    </div>
  );
}

function ConversationMessage({ message }: { message: AgentMessage }) {
  return (
    <div className={`p-4 rounded-lg border-l-4 ${getAgentColor(message.agent)}`}>
      <div className="flex items-center justify-between mb-2">
        <span className="font-semibold">{message.agent}</span>
        {message.timestamp && (
          <span className="text-xs opacity-60">{message.timestamp}</span>
        )}
      </div>
      <p className="whitespace-pre-wrap">{message.message}</p>
    </div>
  );
}

export default function VerdictDisplay({ verdict }: VerdictDisplayProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      {/* Claim Card - Always Visible */}
      <div className="bg-white rounded-xl shadow-lg p-6 border-l-4 border-blue-500">
        <h2 className="text-sm font-semibold text-blue-600 uppercase tracking-wide mb-2">
          External Claim
        </h2>
        <p className="text-xl text-gray-800">{verdict.claim}</p>
      </div>

      {/* Truth Card - Always Visible */}
      <div className="bg-white rounded-xl shadow-lg p-6 border-l-4 border-emerald-500">
        <h2 className="text-sm font-semibold text-emerald-600 uppercase tracking-wide mb-2">
          Source Truth
        </h2>
        <p className="text-xl text-gray-800">{verdict.truth}</p>
      </div>

      {/* Decision Card - Always Visible */}
      <div className="bg-white rounded-xl shadow-lg p-6">
        <h2 className="text-sm font-semibold text-gray-600 uppercase tracking-wide mb-4">
          Final Decision
        </h2>
        <DecisionBadge decision={verdict.decision} confidence={verdict.confidence} />
      </div>

      {/* Summary Card - Always Visible */}
      <div className="bg-white rounded-xl shadow-lg p-6 border-l-4 border-amber-500">
        <h2 className="text-sm font-semibold text-amber-600 uppercase tracking-wide mb-2">
          Summary
        </h2>
        <p className="text-gray-700 leading-relaxed whitespace-pre-wrap">{verdict.summary}</p>
      </div>

      {/* Collapsible Agent Discussion */}
      <div className="bg-white rounded-xl shadow-lg overflow-hidden">
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="w-full p-6 flex items-center justify-between hover:bg-gray-50 transition-colors"
        >
          <div className="flex items-center gap-3">
            <h2 className="text-sm font-semibold text-gray-600 uppercase tracking-wide">
              Agent Discussion
            </h2>
            <span className="text-xs bg-gray-200 text-gray-600 px-2 py-1 rounded-full">
              {verdict.conversation.length} messages
            </span>
          </div>
          <svg
            className={`w-6 h-6 text-gray-400 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </button>

        {isExpanded && (
          <div className="px-6 pb-6 space-y-4 border-t border-gray-100 pt-4">
            {verdict.conversation.map((msg, index) => (
              <ConversationMessage key={index} message={msg} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
