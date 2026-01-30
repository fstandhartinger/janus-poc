/**
 * Chat-related types matching OpenAI API with Janus extensions.
 */

import type { GenerationFlags } from './generation';

export type MessageRole = 'system' | 'user' | 'assistant' | 'tool';

export interface TextContent {
  type: 'text';
  text: string;
}

export interface ImageUrlContent {
  type: 'image_url';
  image_url: {
    url: string;
    detail?: 'auto' | 'low' | 'high';
  };
}

export interface VideoContent {
  type: 'video';
  video: {
    url: string;
    mime_type?: string;
    poster?: string;
  };
}

export interface AudioContent {
  type: 'audio';
  audio: {
    url: string;
    mime_type?: string;
    duration?: number;
  };
}

export interface FileContent {
  type: 'file';
  file: {
    url?: string;
    name: string;
    mime_type: string;
    size: number;
    content?: string;
  };
}

export type MessageContent = string | (
  | TextContent
  | ImageUrlContent
  | VideoContent
  | AudioContent
  | FileContent
)[];

export interface Artifact {
  id: string;
  type: 'image' | 'file' | 'dataset' | 'binary';
  mime_type: string;
  display_name: string;
  size_bytes: number;
  sha256?: string;
  created_at: string;
  ttl_seconds: number;
  url: string;
}

export interface Message {
  id: string;
  role: MessageRole;
  content: MessageContent;
  reasoning_content?: string;
  artifacts?: Artifact[];
  arena?: ArenaComparison;
  metadata?: MessageMetadata;
  created_at: Date;
}

export interface MessageMetadata {
  requestId?: string;
  debugRequestId?: string;
  model?: string;
  durationMs?: number;
}

export type ArenaWinner = 'A' | 'B' | 'tie' | 'both_bad';

export interface ArenaResponse {
  content: string;
}

export interface ArenaComparison {
  promptId: string;
  responseA: ArenaResponse;
  responseB: ArenaResponse;
  voted?: boolean;
  winner?: ArenaWinner;
  modelA?: string;
  modelB?: string;
  error?: string;
}

export interface Session {
  id: string;
  title: string;
  messages: Message[];
  created_at: Date;
  updated_at: Date;
}

export interface ChatCompletionRequest {
  model: string;
  messages: {
    role: MessageRole;
    content: MessageContent;
  }[];
  stream?: boolean;
  stream_options?: {
    include_usage?: boolean;
  };
  temperature?: number;
  max_tokens?: number;
  user_id?: string;
  enable_memory?: boolean;
  chutes_access_token?: string;
  generation_flags?: GenerationFlags;
  debug?: boolean;
}

export interface ArenaCompletionResponse {
  prompt_id: string;
  response_a: ArenaResponse;
  response_b: ArenaResponse;
}

export interface ArenaVoteResponse {
  status: string;
  model_a: string;
  model_b: string;
}

export interface ChatCompletionChunk {
  id: string;
  object: 'chat.completion.chunk';
  created: number;
  model: string;
  choices: {
    index: number;
    delta: {
      role?: MessageRole;
      content?: string;
      reasoning_content?: string;
      janus?: {
        event: string;
        payload?: Record<string, unknown>;
      };
    };
    finish_reason?: 'stop' | 'length' | 'tool_calls' | 'content_filter';
  }[];
}

export interface ScreenshotData {
  url: string;
  title: string;
  image_base64: string;
  timestamp: number;
}

export interface ScreenshotStreamEvent {
  type: 'screenshot';
  data: ScreenshotData;
}

export type ChatStreamEvent = ChatCompletionChunk | ScreenshotStreamEvent;

export interface Model {
  id: string;
  object: string;
  created: number;
  owned_by: string;
}
