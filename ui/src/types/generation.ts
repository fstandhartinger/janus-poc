export type GenerationTag =
  | 'generate_image'
  | 'generate_video'
  | 'generate_audio'
  | 'deep_research'
  | 'web_search';

export interface GenerationFlags {
  generate_image?: boolean;
  generate_video?: boolean;
  generate_audio?: boolean;
  deep_research?: boolean;
  web_search?: boolean;
}

export const GENERATION_TAG_LABELS: Record<GenerationTag, string> = {
  generate_image: '🎨 Image',
  generate_video: '🎬 Video',
  generate_audio: '🔊 Audio',
  deep_research: '🔍 Research',
  web_search: '🌐 Search',
};
