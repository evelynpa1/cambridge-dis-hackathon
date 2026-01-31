import { NextRequest, NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

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
}

// In-memory store (optional fallback)
let latestVerdict: VerdictPayload | null = null;

// Path to result.json in the parent directory (project root)
const RESULT_FILE_PATH = path.resolve(process.cwd(), '../result.json');

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

    // Optionally save to file (mirroring the script action)
    try {
      fs.writeFileSync(RESULT_FILE_PATH, JSON.stringify(body, null, 2));
    } catch (err) {
      console.error("Failed to write result.json", err);
    }

    return NextResponse.json({ success: true, message: 'Verdict received' });
  } catch (error) {
    return NextResponse.json(
      { error: 'Invalid JSON payload' },
      { status: 400 }
    );
  }
}

export async function GET() {
  // Try reading from file first
  try {
    if (fs.existsSync(RESULT_FILE_PATH)) {
      const fileContent = fs.readFileSync(RESULT_FILE_PATH, 'utf-8');
      const data = JSON.parse(fileContent);
      return NextResponse.json(data);
    }
  } catch (error) {
    console.error("Error reading result.json", error);
  }

  // Fallback to memory
  if (latestVerdict) {
    return NextResponse.json(latestVerdict);
  }

  return NextResponse.json(
    { error: 'No verdict available' },
    { status: 404 }
  );
}
