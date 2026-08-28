import kokoroArt from "@/assets/kokoro.png";
import { cn } from "@/lib/utils";

const KokoroBackdrop = ({ className }: { className?: string }) => (
  <img
    src={kokoroArt}
    alt=""
    aria-hidden
    className={cn(
      "pointer-events-none select-none fixed inset-0 z-0 h-full w-full object-cover opacity-[0.14]",
      className,
    )}
  />
);

export default KokoroBackdrop;
