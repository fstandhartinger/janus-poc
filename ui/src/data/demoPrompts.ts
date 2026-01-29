export type DemoPromptCategory = 'simple' | 'agentic' | 'research' | 'multimodal';

export interface DemoPrompt {
  id: string;
  label: string;
  prompt: string;
  icon: string;
  category: DemoPromptCategory;
  estimatedTime?: string;
  description?: string;
}

export const DEMO_PROMPTS: DemoPrompt[] = [
  {
    id: 'simple-sky',
    label: 'Explain why the sky is blue',
    prompt: 'Explain why the sky is blue.',
    icon: '💡',
    category: 'simple',
  },
  {
    id: 'simple-compare',
    label: 'Compare Python and JavaScript',
    prompt: 'Compare Python and JavaScript for web development.',
    icon: '⚖️',
    category: 'simple',
  },
  {
    id: 'simple-translate',
    label: 'Translate a greeting',
    prompt: "Translate 'Hello, how are you?' to German, French, and Japanese.",
    icon: '🌍',
    category: 'simple',
  },
  {
    id: 'agentic-clone-summarize',
    label: 'Clone & summarize a repo',
    prompt: 'Clone the https://github.com/anthropics/anthropic-cookbook repository and summarize what it contains.',
    icon: '📦',
    category: 'agentic',
    estimatedTime: '1-2 min',
    description: 'Spawns the agent to clone and analyze a GitHub repository.',
  },
  {
    id: 'agentic-analyze-code',
    label: 'Analyze a codebase',
    prompt: 'Clone https://github.com/fastapi/fastapi and explain the project structure.',
    icon: '🔍',
    category: 'agentic',
    estimatedTime: '1-2 min',
  },
  {
    id: 'agentic-download-process',
    label: 'Download & summarize docs',
    prompt: 'Download the README from https://github.com/langchain-ai/langchain and create a summary document.',
    icon: '📄',
    category: 'agentic',
    estimatedTime: '30-60s',
  },
  {
    id: 'research-web-2026',
    label: 'Web research report',
    prompt: 'Search the web for the latest AI developments in 2026 and write a brief report with sources.',
    icon: '🔎',
    category: 'research',
    estimatedTime: '30-60s',
    description: 'Searches the web and synthesizes sources into a short report.',
  },
  {
    id: 'research-rust-go',
    label: 'Rust vs Go deep dive',
    prompt: 'Research the pros and cons of Rust vs Go for backend development and give me a detailed comparison.',
    icon: '📊',
    category: 'research',
    estimatedTime: '1-2 min',
  },
  {
    id: 'research-news-summary',
    label: 'Weekly tech news summary',
    prompt: 'Find the top tech news from this week and summarize the key stories.',
    icon: '📰',
    category: 'research',
    estimatedTime: '30-60s',
  },
  {
    id: 'multimodal-image-city',
    label: 'Generate a futuristic city image',
    prompt: 'Generate an image of a futuristic city with flying cars at sunset.',
    icon: '🎨',
    category: 'multimodal',
    estimatedTime: '10-20s',
    description: 'Creates an image with the multimodal model.',
  },
  {
    id: 'multimodal-cabin-art',
    label: 'Create snowy cabin art',
    prompt: 'Generate an image of a cozy cabin in a snowy forest at night with northern lights.',
    icon: '🖼️',
    category: 'multimodal',
    estimatedTime: '10-20s',
  },
  {
    id: 'multimodal-poem-tts',
    label: 'Write a poem and read it aloud',
    prompt: 'Write a short poem about the ocean and read it aloud.',
    icon: '🔊',
    category: 'multimodal',
    estimatedTime: '15-30s',
  },
];

export const DEMO_PROMPTS_BY_CATEGORY = {
  simple: DEMO_PROMPTS.filter((prompt) => prompt.category === 'simple'),
  agentic: DEMO_PROMPTS.filter((prompt) => prompt.category === 'agentic'),
  research: DEMO_PROMPTS.filter((prompt) => prompt.category === 'research'),
  multimodal: DEMO_PROMPTS.filter((prompt) => prompt.category === 'multimodal'),
};
