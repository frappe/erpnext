import * as React from "react"
import { CheckIcon } from "lucide-react"
import { Checkbox as CheckboxPrimitive } from "radix-ui"

import { cn } from "@/lib/utils"

function Checkbox({
  className,
  size = "md",
  ...props
}: React.ComponentProps<typeof CheckboxPrimitive.Root> & { size?: "sm" | "md" }) {
  return (
    <CheckboxPrimitive.Root
      data-slot="checkbox"
      className={cn(
        "peer border data-[state=checked]:text-ink-white shrink-0 transition-shadow outline-none align-middle",
        "rounded-[4px]",
        "border-ink-gray-4 data-[state=checked]:bg-ink-gray-8 data-[state=checked]:border-ink-gray-8",
        // Hover state
        "hover:border-ink-gray-5 hover:shadow-checkbox-hover hover:data-[state=checked]:bg-ink-gray-7 hover:data-[state=checked]:border-ink-gray-7",
        // Active state
        "active:border-ink-gray-6 active:data-[state=checked]:bg-ink-gray-6 active:data-[state=checked]:border-ink-gray-6",
        // Focus state
        "focus-visible:border-ink-gray-8 focus-visible:shadow-focus-gray focus-visible:data-[state=checked]:bg-ink-gray-8 focus-visible:data-[state=checked]:border-ink-gray-8",
        // Disabled state
        "disabled:border-ink-gray-3 disabled:bg-surface-gray-1 disabled:cursor-not-allowed disabled:data-[state=checked]:bg-surface-gray-3 disabled:data-[state=checked]:border-surface-gray-3 disabled:text-ink-gray-4",
        // Invalid state
        "aria-invalid:border-red-500",
        size === "sm" ? "size-3.5" : "size-4",
        className
      )}
      {...props}
    >
      <CheckboxPrimitive.Indicator
        data-slot="checkbox-indicator"
        className="grid place-content-center text-current transition-none"
      >
        <CheckIcon className={size === 'sm' ? "size-2.5" : "size-3"} />
      </CheckboxPrimitive.Indicator>
    </CheckboxPrimitive.Root>
  )
}

export { Checkbox }
