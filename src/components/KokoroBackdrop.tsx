import kokoroArt from "@/assets/kokoro.png";
import { cn } from "@/lib/utils";

const KokoroBackdrop = ({ className }: { className?: string }) => (
  <div
    aria-hidden
    className={cn(
      "pointer-events-none fixed inset-0 z-0 overflow-hidden opacity-[0.16]",
      className,
    )}
  >
    <img
      src={kokoroArt}
      alt=""
      className="absolute left-1/2 top-1/2 h-[36rem] w-[36rem] max-w-none -translate-x-1/2 -translate-y-1/2 object-contain"
    />
  </div>
);

export default KokoroBackdrop;
