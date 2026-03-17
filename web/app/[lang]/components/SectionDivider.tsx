export default function SectionDivider({ flip = false }: { flip?: boolean }) {
  return (
    <div className={`w-full flex justify-center py-2 ${flip ? "rotate-180" : ""}`}>
      <div className="w-16 h-[2px] rounded-full bg-[var(--color-brand-green)]/10" />
    </div>
  );
}
