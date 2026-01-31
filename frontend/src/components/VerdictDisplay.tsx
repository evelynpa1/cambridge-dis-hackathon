'use client';

import { useState, useEffect, useRef } from 'react';
import { VerdictPayload, AgentMessage } from '@/types/verdict';
import ReactMarkdown from 'react-markdown';

interface VerdictDisplayProps {
  verdict: VerdictPayload;
  isStreaming?: boolean;
}

const agentColors: Record<string, string> = {
  'Sceptic': 'bg-red-50 border-red-200 text-gray-900',  // Softer background for readibility
  'Skeptic': 'bg-red-50 border-red-200 text-gray-900', // Handle spelling variant
  'Fact-Checker': 'bg-blue-50 border-blue-200 text-gray-900',
  'Judge': 'bg-purple-50 border-purple-200 text-gray-900',
  'Advocate': 'bg-green-50 border-green-200 text-gray-900',
  'Moderator': 'bg-gray-50 border-gray-200 text-gray-900',
  'Evidence Scout': 'bg-yellow-50 border-yellow-200 text-gray-900',
  'Context Analyst': 'bg-indigo-50 border-indigo-200 text-gray-900',
};

function getAgentColor(agent: string): string {
  return agentColors[agent] || 'bg-slate-50 border-slate-200 text-gray-900';
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
    </div>
  );
}

function ConversationMessage({ message }: { message: AgentMessage }) {
  return (
    <div className={`p-4 rounded-lg border-l-4 ${getAgentColor(message.agent)}`}>
      <div className="flex items-center justify-between mb-2">
        <span className="font-semibold text-sm uppercase tracking-wider opacity-80">{message.agent}</span>
        {message.timestamp && (
          <span className="text-xs opacity-60 font-mono">{message.timestamp}</span>
        )}
      </div>
      <div className="prose prose-sm max-w-none text-gray-800">
        <ReactMarkdown>{message.message}</ReactMarkdown>
      </div>
    </div>
  );
}

export default function VerdictDisplay({ verdict, isStreaming = false }: VerdictDisplayProps) {
  const [isExpanded, setIsExpanded] = useState(true); // Default open for better visibility
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when conversation updates
  useEffect(() => {
    if (bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [verdict.conversation.length, isExpanded]);

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      {/* Claim Card - Always Visible */}
      <div className="bg-white rounded-xl shadow-lg p-6 border-l-4 border-blue-500">
        <h2 className="text-sm font-semibold text-blue-600 uppercase tracking-wide mb-2">
          External Claim
        </h2>
        <p className="text-xl text-gray-900 font-medium">{verdict.claim}</p>
      </div>

      {/* Truth Card - Always Visible */}
      <div className="bg-white rounded-xl shadow-lg p-6 border-l-4 border-emerald-500">
        <h2 className="text-sm font-semibold text-emerald-600 uppercase tracking-wide mb-2">
          Source Truth / Evidence Context
        </h2>
        <div className="prose prose-sm max-w-none text-gray-800">
          <ReactMarkdown>{verdict.truth}</ReactMarkdown>
        </div>
      </div>

      {/* Decision Card - Show placeholder while streaming */}
      <div className="bg-white rounded-xl shadow-lg p-6">
        <h2 className="text-sm font-semibold text-gray-600 uppercase tracking-wide mb-4">
          Final Decision
        </h2>
        {isStreaming ? (
          <div className="flex items-center gap-3">
            <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-purple-500"></div>
            <span className="text-gray-500">Awaiting verdict...</span>
          </div>
        ) : (
          <DecisionBadge decision={verdict.decision} confidence={verdict.confidence} />
        )}
      </div>

      {/* Summary Card - Show placeholder while streaming */}
      <div className="bg-white rounded-xl shadow-lg p-6 border-l-4 border-amber-500">
        <h2 className="text-sm font-semibold text-amber-600 uppercase tracking-wide mb-2">
          Summary
        </h2>
        {isStreaming && !verdict.summary ? (
          <div className="flex items-center gap-2 text-gray-500">
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-amber-500"></div>
            <span>Generating summary...</span>
          </div>
        ) : (
          <div className="prose max-w-none text-gray-800">
            <ReactMarkdown>{verdict.summary}</ReactMarkdown>
          </div>
        )}
      </div>

      {/* Disclaimers Card - Conditional */}
      {verdict.disclaimers && verdict.disclaimers.length > 0 && (
        <div className="bg-white rounded-xl shadow-lg p-6 border-l-4 border-orange-400">
          <h2 className="text-sm font-semibold text-orange-600 uppercase tracking-wide mb-2">
            Disclaimers & Caveats
          </h2>
          <ul className="list-disc list-inside space-y-1 text-gray-700">
            {verdict.disclaimers.map((item, i) => (
              <li key={i}>{item}</li>
            ))}
          </ul>
        </div>
      )}

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
            {isStreaming && (
              <span className="flex items-center gap-1.5 text-xs bg-red-100 text-red-600 px-2 py-1 rounded-full">
                <span className="w-2 h-2 bg-red-500 rounded-full animate-pulse"></span>
                LIVE
              </span>
            )}
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
            {isStreaming && (
              <div className="flex items-center gap-3 p-4 bg-gray-50 rounded-lg border border-gray-200 animate-pulse">
                <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-500"></div>
                <span className="text-gray-600">Agent is thinking...</span>
              </div>
            )}
            <div ref={bottomRef} />
          </div>
        )}
      </div>
    </div>
  );
}
