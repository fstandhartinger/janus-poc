declare module '@novnc/novnc/lib/rfb' {
  type RfbCredentials = { password?: string };
  type RfbOptions = { credentials?: RfbCredentials };

  export default class RFB {
    constructor(target: HTMLElement, url: string, options?: RfbOptions);

    addEventListener(type: 'connect' | 'disconnect', listener: (event: Event) => void): void;
    removeEventListener(type: 'connect' | 'disconnect', listener: (event: Event) => void): void;
    disconnect(): void;

    scaleViewport: boolean;
    resizeSession: boolean;
  }
}
