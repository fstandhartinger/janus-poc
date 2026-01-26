# Chutes LLM Endpoint

## Endpoint
POST https://llm.chutes.ai/v1/chat/completions

## Authentication
Header: Authorization: Bearer $CHUTES_API_KEY

## OpenAI-Compatible Request
{
  "model": "deepseek-ai/DeepSeek-V3-0324",
  "messages": [{"role": "user", "content": "Hello"}],
  "temperature": 0.7,
  "max_tokens": 4096,
  "stream": true
}

## Available Models
- deepseek-ai/DeepSeek-V3-0324 (latest)
- deepseek-ai/DeepSeek-V3.2-TEE (secure enclave)
- Various open models via Chutes marketplace
