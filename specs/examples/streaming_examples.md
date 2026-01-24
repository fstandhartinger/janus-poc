# Streaming Examples

## SSE stream with reasoning_content
```
data: {"id":"chatcmpl_01","object":"chat.completion.chunk","created":1769088000,"model":"janus-baseline-agent-cli","choices":[{"index":0,"delta":{"role":"assistant"}}]}

data: {"id":"chatcmpl_01","object":"chat.completion.chunk","created":1769088000,"model":"janus-baseline-agent-cli","choices":[{"index":0,"delta":{"reasoning_content":"Starting sandbox..."}}]}

: ping

data: {"id":"chatcmpl_01","object":"chat.completion.chunk","created":1769088001,"model":"janus-baseline-agent-cli","choices":[{"index":0,"delta":{"reasoning_content":"Running CLI agent step 1"}}]}

data: {"id":"chatcmpl_01","object":"chat.completion.chunk","created":1769088002,"model":"janus-baseline-agent-cli","choices":[{"index":0,"delta":{"content":"Here is the result: "}}]}

data: {"id":"chatcmpl_01","object":"chat.completion.chunk","created":1769088003,"model":"janus-baseline-agent-cli","choices":[{"index":0,"delta":{"content":"the code compiled successfully."}}]}

data: [DONE]
```

## SSE stream with structured Janus events
```
data: {"id":"chatcmpl_02","object":"chat.completion.chunk","created":1769088000,"model":"janus-baseline-agent-cli","choices":[{"index":0,"delta":{"reasoning_content":"Starting tool" ,"janus":{"event":"tool_start","payload":{"name":"web_search"}}}}]}

data: {"id":"chatcmpl_02","object":"chat.completion.chunk","created":1769088001,"model":"janus-baseline-agent-cli","choices":[{"index":0,"delta":{"reasoning_content":"Tool finished" ,"janus":{"event":"tool_end","payload":{"name":"web_search","status":"ok"}}}}]}

data: [DONE]
```
