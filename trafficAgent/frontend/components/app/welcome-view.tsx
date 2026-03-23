import { Button } from '@/components/livekit/button';

function TrafficIcon() {
  return (
    <svg
      width="64"
      height="64"
      viewBox="0 0 64 64"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className="text-fg0 mb-4 size-16"
    >
      {/* Traffic signal / alert icon */}
      <rect x="22" y="4" width="20" height="56" rx="4" fill="currentColor" opacity="0.15" />
      <rect x="22" y="4" width="20" height="56" rx="4" stroke="currentColor" strokeWidth="2" />
      <circle cx="32" cy="16" r="5" fill="currentColor" opacity="0.4" />
      <circle cx="32" cy="32" r="5" fill="currentColor" opacity="0.6" />
      <circle cx="32" cy="48" r="5" fill="currentColor" />
      {/* Signal arms */}
      <line x1="42" y1="20" x2="54" y2="20" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      <line x1="10" y1="20" x2="22" y2="20" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

interface WelcomeViewProps {
  startButtonText: string;
  onStartCall: () => void;
}

export const WelcomeView = ({
  startButtonText,
  onStartCall,
  ref,
}: React.ComponentProps<'div'> & WelcomeViewProps) => {
  return (
    <div ref={ref}>
      <section className="bg-background flex flex-col items-center justify-center text-center">
        <TrafficIcon />

        <p className="text-foreground max-w-prose pt-1 leading-6 font-medium">
          Traffic Incident Command — AI Co-Pilot
        </p>

        <p className="text-muted-foreground max-w-md pt-2 text-sm leading-5">
          Report an incident and receive real-time signal re-timing, diversion routes, public alerts, and priority dispatch recommendations.
        </p>

        <Button variant="primary" size="lg" onClick={onStartCall} className="mt-6 w-64 font-mono">
          {startButtonText}
        </Button>
      </section>

      <div className="fixed bottom-5 left-0 flex w-full items-center justify-center">
        <p className="text-muted-foreground max-w-prose pt-1 text-xs leading-5 font-normal text-pretty md:text-sm">
          Powered by AI — assists traffic control officers during major incidents with actionable intelligence.
        </p>
      </div>
    </div>
  );
};
