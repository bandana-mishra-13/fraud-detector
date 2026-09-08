export default function Logo({ size = 28 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 64 64"
      aria-hidden="true"
      className="shrink-0"
    >
      <rect width="64" height="64" rx="14" fill="#4F46E5" />
      <ellipse
        cx="32"
        cy="32"
        rx="19"
        ry="11.5"
        fill="none"
        stroke="#ffffff"
        strokeWidth="3.5"
      />
      <circle cx="32" cy="32" r="5.5" fill="#ffffff" />
    </svg>
  );
}
