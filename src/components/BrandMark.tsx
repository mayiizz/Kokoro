type BrandMarkProps = {
  size?: "sm" | "md" | "lg";
};

const sizes = {
  sm: { mark: "h-8 w-8 text-lg", title: "text-base" },
  md: { mark: "h-10 w-10 text-xl", title: "text-xl" },
  lg: { mark: "h-14 w-14 text-3xl", title: "text-2xl" },
};

const BrandMark = ({ size = "md" }: BrandMarkProps) => {
  const s = sizes[size];
  return (
    <div className="flex items-center gap-2.5">
      <div
        className={`${s.mark} rounded-xl bg-primary text-primary-foreground flex items-center justify-center leading-none shrink-0`}
        aria-hidden
      >
        心
      </div>
      <p className={`font-bold text-foreground leading-tight ${s.title}`}>Kokoro</p>
    </div>
  );
};

export default BrandMark;
