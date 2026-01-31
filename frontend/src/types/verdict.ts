export interface AgentMessage {
  agent: string;
  message: string;
  timestamp?: string;
}

export interface VerdictPayload {
  claim: string;
  truth: string;
  conversation: AgentMessage[];
  summary: string;
  decision: 'faithful' | 'mutated' | 'uncertain';
  confidence?: number;
  disclaimers?: string[];
  analysis?: {
    claim_analysis: string;
    truth_analysis: string;
  };
}
