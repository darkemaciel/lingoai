// Typed shapes mirrored from specs/001-placement-learning-loop/contracts/rest-api.md.
// Keep in sync with the backend contract — this is the single source of truth for
// the frontend's view of the API.

export interface ApiError {
  error: { code: string; message: string };
}

export interface RegisterRequest {
  email: string;
  password: string;
}

export interface RegisterResponse {
  user_id: string;
  email: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  expires_in: number;
}

export interface AccessTokenResponse {
  access_token: string;
  expires_in: number;
}

export type SessionStatus = 'in_progress' | 'completed' | 'abandoned';
export type Modality = 'text_only' | 'text_and_audio';

export interface StartPlacementSessionResponse {
  placement_session_id: string;
  status: SessionStatus;
  modality: Modality;
}

export interface SubmitAnswerRequest {
  client_submission_id: string;
  content_text: string;
  audio_ref?: string;
}

export interface Prompt {
  content_text: string;
  audio_ref?: string;
}

export interface SubmitAnswerResponse {
  next_prompt: Prompt | null;
  session_status: SessionStatus;
}

export type CEFRLevel = 'A1' | 'A2' | 'B1' | 'B2' | 'C1' | 'C2';

export interface PlacementResult {
  reading_level: CEFRLevel | null;
  writing_level: CEFRLevel | null;
  speaking_level: CEFRLevel | null;
  listening_level: CEFRLevel | null;
  strengths_summary: string;
  weaknesses_summary: string;
}

export interface GamificationDelta {
  xp_awarded: number;
  xp_total: number;
  streak_current: number;
  badges_unlocked: string[];
}

export interface ProgressionSkill {
  skill: string;
  cefr_level: CEFRLevel;
  mastery_score: number;
}

export interface ProgressionProfileResponse {
  skills: ProgressionSkill[];
}

export interface GamificationBadge {
  code: string;
  name: string;
  description: string;
  awarded_at: string;
}

export interface GamificationProfileResponse {
  xp_total: number;
  streak_current: number;
  badges: GamificationBadge[];
}

export interface StartConversationResponse {
  conversation_session_id: string;
}

export interface SendMessageRequest {
  client_submission_id: string;
  content_text: string;
  audio_ref?: string;
}

export interface AgentMessage {
  content_text: string;
  audio_ref?: string | null;
}

export interface SendMessageResponse {
  agent_message: AgentMessage;
  gamification_delta?: GamificationDelta | null;
}

export type ActivityType = 'writing_exercise' | 'speaking_exercise' | 'listening_exercise';

export interface NextActivityResponse {
  activity_id: string;
  type: ActivityType;
  skill: string;
  prompt_content: Record<string, unknown>;
}

export interface SubmitActivityAnswerRequest {
  client_submission_id: string;
  response: Record<string, unknown>;
}

export interface ActivityAnswerResponse {
  correct: boolean;
  feedback_text: string;
  performance_score: number;
  gamification_delta: GamificationDelta;
  level_advanced: boolean;
}
