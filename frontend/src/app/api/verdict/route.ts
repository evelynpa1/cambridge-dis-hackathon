import { NextRequest, NextResponse } from 'next/server';

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
}

// In-memory store for the latest verdict (for demo purposes)
let latestVerdict: VerdictPayload | null = null;

export async function POST(request: NextRequest) {
  try {
    const body: VerdictPayload = await request.json();

    // Validate required fields
    if (!body.claim || !body.truth || !body.conversation || !body.summary || !body.decision) {
      return NextResponse.json(
        { error: 'Missing required fields: claim, truth, conversation, summary, decision' },
        { status: 400 }
      );
    }

    latestVerdict = body;

    return NextResponse.json({ success: true, message: 'Verdict received' });
  } catch (error) {
    return NextResponse.json(
      { error: 'Invalid JSON payload' },
      { status: 400 }
    );
  }
}

export async function GET() {
  if (!latestVerdict) {
    return NextResponse.json(
      { error: 'No verdict available' },
      { status: 404 }
    );
  }

  return NextResponse.json(latestVerdict);
}
