import * as React from "react"
import { Progress as ProgressPrimitive } from "radix-ui"

import { cn } from "@/lib/utils"
import { cva, VariantProps } from "class-variance-authority"

const progressVariants = cva(
  "bg-surface-gray-2 relative w-full overflow-hidden rounded-full",
  {
    variants: {
      size: {
        sm: "h-0.5",
        md: "h-1",
        lg: "h-2.5",
        xl: "h-3"
      }
    }
  }
)

interface ProgressProps extends React.ComponentProps<typeof ProgressPrimitive.Root>, VariantProps<typeof progressVariants> {
  /** Optional text label displayed on the progress bar */
  label?: React.ReactNode,
  /** Whether to show a hint/tooltip for the progress value */
  hint?: boolean,
  /** Override the default hint text with custom progress value */
  hintText?: React.ReactNode
}

function Progress({
  className,
  value,
  size = "sm",
  label,
  hint,
  hintText,
  ...props
}: ProgressProps) {

  const progressValue = hintText ? hintText : `${value}%`

  return (
    <div className="flex flex-col gap-2.5">
      {label || hint ? <div className="flex items-center justify-between gap-1">
        {label && <span className="text-base font-medium text-ink-gray-7">{label}</span>}
        {hint && <span className="text-base font-medium text-ink-gray-5">{progressValue}</span>}
      </div> : null}
      <ProgressPrimitive.Root
        data-slot="progress"
        data-size={size}
        className={cn(
          progressVariants({ size }),
          className
        )}
        {...props}
      >
        <ProgressPrimitive.Indicator
          data-slot="progress-indicator"
          className="bg-surface-gray-7 rounded-xl h-full w-full flex-1 transition-all"
          style={{ transform: `translateX(-${100 - (value || 0)}%)` }}
        />
      </ProgressPrimitive.Root>
    </div>
  )
}

export { Progress }
