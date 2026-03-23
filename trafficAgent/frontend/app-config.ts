export interface AppConfig {
  pageTitle: string;
  pageDescription: string;
  companyName: string;

  supportsChatInput: boolean;
  supportsVideoInput: boolean;
  supportsScreenShare: boolean;
  isPreConnectBufferEnabled: boolean;

  logo: string;
  startButtonText: string;
  accent?: string;
  logoDark?: string;
  accentDark?: string;

  // for LiveKit Cloud Sandbox
  sandboxId?: string;
  agentName?: string;
}

export const APP_CONFIG_DEFAULTS: AppConfig = {
  companyName: 'TrafficCommand',
  pageTitle: 'Traffic Incident Co-Pilot',
  pageDescription: 'AI-powered real-time traffic incident command assistant',

  supportsChatInput: true,
  supportsVideoInput: true,
  supportsScreenShare: true,
  isPreConnectBufferEnabled: true,

  logo: '/lk-logo.svg',
  accent: '#e67e22',
  logoDark: '/lk-logo-dark.svg',
  accentDark: '#f39c12',
  startButtonText: 'Start Incident Session',

  // for LiveKit Cloud Sandbox
  sandboxId: undefined,
  agentName: undefined,
};
