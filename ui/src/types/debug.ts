export type DebugEventType =
  // Request lifecycle
  | 'request_received'

  // Complexity analysis
  | 'complexity_check_start'
  | 'complexity_check_keyword'
  | 'complexity_check_llm'
  | 'complexity_check_complete'
  | 'routing_decision'

  // Fast path
  | 'fast_path_start'
  | 'fast_path_llm_call'
  | 'fast_path_stream'
  | 'fast_path_complete'

  // Agent path
  | 'agent_path_start'
  | 'agent_selection'
  | 'model_selection'

  // Sandy interaction
  | 'sandbox_init'
  | 'sandy_sandbox_create'
  | 'sandy_sandbox_created'
  | 'sandy_agent_api_request'
  | 'sandy_agent_api_sse_event'
  | 'sandy_agent_api_complete'
  | 'sandy_agent_api_error'
  | 'sandy_sandbox_terminate'

  // Prompt details
  | 'prompt_original'
  | 'prompt_enhanced'
  | 'prompt_system'

  // Agent execution
  | 'agent_thinking'
  | 'tool_call_start'
  | 'tool_call_result'
  | 'tool_call_complete'

  // File/artifact operations
  | 'file_created'
  | 'file_modified'
  | 'artifact_generated'
  | 'artifact_created'

  // Response
  | 'response_chunk'
  | 'response_complete'

  // Errors
  | 'error';

export interface DebugEvent {
  request_id: string;
  timestamp: string;
  type: DebugEventType;
  step: string;
  message: string;
  data?: Record<string, unknown>;
  correlation_id?: string;
}

export interface DebugState {
  currentStep: string;
  activeNodes: string[];
  events: DebugEvent[];
  files: string[];
  correlationId?: string;
}

export interface LogEntry {
  timestamp: string;
  level: 'debug' | 'info' | 'warn' | 'error';
  message: string;
  context: {
    correlationId?: string;
    requestId?: string;
    component?: string;
    [key: string]: unknown;
  };
  data?: Record<string, unknown>;
}
