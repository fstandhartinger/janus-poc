import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface SettingsState {
  ttsVoice: string;
  ttsSpeed: number;
  ttsAutoPlay: boolean;
  arenaMode: boolean;
  debugMode: boolean;
  setTTSVoice: (voice: string) => void;
  setTTSSpeed: (speed: number) => void;
  setTTSAutoPlay: (autoPlay: boolean) => void;
  setArenaMode: (enabled: boolean) => void;
  setDebugMode: (enabled: boolean) => void;
}

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set) => ({
      ttsVoice: 'af_sky',
      ttsSpeed: 1.0,
      ttsAutoPlay: false,
      arenaMode: false,
      debugMode: false,
      setTTSVoice: (voice) => set({ ttsVoice: voice }),
      setTTSSpeed: (speed) => set({ ttsSpeed: speed }),
      setTTSAutoPlay: (autoPlay) => set({ ttsAutoPlay: autoPlay }),
      setArenaMode: (enabled) => set({ arenaMode: enabled }),
      setDebugMode: (enabled) => set({ debugMode: enabled }),
    }),
    {
      name: 'janus-settings',
    }
  )
);
