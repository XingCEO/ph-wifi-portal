export default function SectionDivider({ flip = false }: { flip?: boolean }) {
  return (
    <div className={`w-full overflow-hidden ${flip ? "rotate-180" : ""}`}>
      <svg
        viewBox="0 0 1200 40"
        fill="none"
        preserveAspectRatio="none"
        className="w-full h-6 sm:h-10 text-[var(--color-brand-green)]"
      >
        <path
          d="M0 40 L0 20 Q300 0 600 20 Q900 40 1200 20 L1200 40 Z"
          fill="currentColor"
          fillOpacity="0.03"
        />
        <path
          d="M0 20 Q300 0 600 20 Q900 40 1200 20"
          stroke="currentColor"
          strokeWidth="0.8"
          strokeOpacity="0.08"
          fill="none"
        />
      </svg>
    </div>
  );
}
