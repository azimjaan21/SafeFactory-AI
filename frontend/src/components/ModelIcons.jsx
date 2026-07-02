function IconBase({ children, viewBox = "0 0 24 24" }) {
  return (
    <svg viewBox={viewBox} fill="none" aria-hidden="true">
      {children}
    </svg>
  );
}

export function HelmetIcon() {
  return (
    <IconBase>
      <path
        d="M6 13a6 6 0 0 1 12 0v1H6v-1Z"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M9 10.5V9a3 3 0 0 1 6 0v1.5"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
      />
      <path
        d="M5 14h14v2a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1v-2Z"
        fill="currentColor"
        fillOpacity="0.18"
        stroke="currentColor"
        strokeWidth="1.5"
      />
    </IconBase>
  );
}

export function WorkerGroupIcon() {
  return (
    <IconBase>
      <circle cx="9" cy="9" r="2.2" stroke="currentColor" strokeWidth="1.7" />
      <circle cx="15.5" cy="8.5" r="1.8" stroke="currentColor" strokeWidth="1.7" />
      <path
        d="M5.8 16.7c.6-2.2 2.1-3.4 4.2-3.4s3.6 1.2 4.2 3.4"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinecap="round"
      />
      <path
        d="M13.2 16.4c.5-1.6 1.6-2.5 3.2-2.5 1.1 0 2 .4 2.8 1.3"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinecap="round"
      />
    </IconBase>
  );
}

export function FireIcon() {
  return (
    <IconBase>
      <path
        d="M12.3 4.5c1.8 2.1 2.4 3.6 2.1 5-.1.6-.4 1.2-.8 1.7 1.8-.4 3.4 1.2 3.4 3.3 0 2.7-2.2 4.8-5 4.8s-5-2.1-5-4.8c0-1.9 1-3.2 2.5-4.3.8-.6 1.6-1.5 1.8-2.4.2-.9.2-1.8 1-3.3Z"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinejoin="round"
      />
      <path
        d="M11.4 12.4c1 .9 1.4 1.6 1.4 2.3 0 .9-.7 1.6-1.6 1.6-.8 0-1.5-.6-1.5-1.4 0-.9.6-1.5 1.7-2.5Z"
        fill="currentColor"
        fillOpacity="0.25"
        stroke="currentColor"
        strokeWidth="1.2"
      />
    </IconBase>
  );
}

export function ForkliftIcon() {
  return (
    <IconBase>
      <circle cx="8" cy="17" r="1.8" stroke="currentColor" strokeWidth="1.7" />
      <circle cx="17" cy="17" r="1.8" stroke="currentColor" strokeWidth="1.7" />
      <path
        d="M5 16V9h5l2 4h3.5a1.5 1.5 0 0 1 1.5 1.5V16"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M10 9V6h2.8l1.6 3"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinecap="round"
      />
      <path d="M19 8v8" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
      <path d="M19 8h2" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
    </IconBase>
  );
}

export function DangerZoneIcon() {
  return (
    <IconBase>
      <path
        d="M12 5 19 18H5L12 5Z"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinejoin="round"
      />
      <path d="M12 9.5v4.2" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
      <circle cx="12" cy="15.8" r="1" fill="currentColor" />
    </IconBase>
  );
}

export function WorkZoneIcon() {
  return (
    <IconBase>
      <path
        d="M8 5H5v3M16 5h3v3M19 16v3h-3M8 19H5v-3"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M5 8v8M19 8v8M8 5h8M8 19h8"
        stroke="currentColor"
        strokeWidth="1.2"
        strokeDasharray="2.5 2.5"
        strokeLinecap="round"
      />
    </IconBase>
  );
}

export function FallDetectionIcon() {
  return (
    <IconBase>
      <circle cx="15" cy="4.5" r="1.8" stroke="currentColor" strokeWidth="1.7" />
      <path d="M15 6.3L10.5 12" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
      <path
        d="M10.5 12L8 17M10.5 12L13.5 16.5"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M13.5 8.5L17 11M13.5 8.5L10 9.5"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinecap="round"
      />
      <path d="M5 20h7" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
      <path
        d="M4.5 17.5L6 20M7 17.5L7.5 20"
        stroke="currentColor"
        strokeWidth="1.3"
        strokeLinecap="round"
      />
    </IconBase>
  );
}

export function RunningDetectionIcon() {
  return (
    <IconBase>
      <circle cx="15.5" cy="4.5" r="1.8" stroke="currentColor" strokeWidth="1.7" />
      <path d="M15.5 6.3L14 11" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
      <path
        d="M14 11L16.5 16M14 11L11 15.5"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M14.5 8.5L17.5 10M14.5 8.5L12 9.5"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinecap="round"
      />
      <path
        d="M3.5 9h5M3.5 11.5h4M3.5 14h3"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeDasharray="2 1.5"
      />
    </IconBase>
  );
}

export function InactivityDetectionIcon() {
  return (
    <IconBase>
      <circle cx="7" cy="5.5" r="1.8" stroke="currentColor" strokeWidth="1.7" />
      <path d="M7 7.3V12" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
      <path
        d="M7 12L5 16M7 12L9 16"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M7 9.5L5 11.5M7 9.5L9 11.5"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinecap="round"
      />
      <path
        d="M13 7h3.5l-3.5 3.5h3.5"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M15 13h2.5L15 15.5h2.5"
        stroke="currentColor"
        strokeWidth="1.3"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </IconBase>
  );
}

export function PoseIcon() {
  return (
    <IconBase>
      {/* head */}
      <circle cx="12" cy="4.5" r="1.8" stroke="currentColor" strokeWidth="1.6" />
      {/* spine */}
      <line x1="12" y1="6.3" x2="12" y2="13" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
      {/* shoulders */}
      <line x1="7" y1="9" x2="17" y2="9" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
      {/* left arm */}
      <line x1="7" y1="9" x2="5" y2="14" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
      {/* right arm */}
      <line x1="17" y1="9" x2="19" y2="14" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
      {/* hips */}
      <line x1="9" y1="13" x2="15" y2="13" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
      {/* left leg */}
      <line x1="9" y1="13" x2="8" y2="19" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
      {/* right leg */}
      <line x1="15" y1="13" x2="16" y2="19" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
      {/* keypoint dots */}
      <circle cx="7" cy="9" r="1.2" fill="currentColor" />
      <circle cx="17" cy="9" r="1.2" fill="currentColor" />
      <circle cx="12" cy="13" r="1.2" fill="currentColor" />
    </IconBase>
  );
}
