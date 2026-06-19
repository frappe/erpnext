import * as React from "react"
import { Switch as SwitchPrimitive } from "radix-ui"

import { cn } from "@/lib/utils"

function Switch({
  className,
  size = "sm",
  ...props
}: React.ComponentProps<typeof SwitchPrimitive.Root> & {
  size?: "sm" | "md"
}) {
  return (
    <SwitchPrimitive.Root
      data-slot="switch"
      data-size={size}
      className={cn(
        "peer cursor-pointer group/switch inline-flex shrink-0 items-center rounded-full transition-all outline-none disabled:cursor-not-allowed",
        "data-[state=unchecked]:bg-ink-gray-2 data-[state=unchecked]:hover:bg-ink-gray-3 data-[state=unchecked]:active:bg-ink-gray-4 data-[state=unchecked]:disabled:bg-ink-gray-1",
        "data-[state=checked]:bg-ink-gray-8 data-[state=checked]:hover:bg-ink-gray-7 data-[state=checked]:active:bg-ink-gray-6 data-[state=checked]:disabled:bg-ink-gray-1",
        "data-[size=sm]:h-4 data-[size=sm]:w-6.5 data-[size=md]:h-5 data-[size=md]:w-8",
        className
      )}
      {...props}
    >
      <SwitchPrimitive.Thumb
        data-slot="switch-thumb"
        className={cn(
          "shadow-switch block pointer-events-none rounded-full ring-0 transition-transform bg-ink-white",
          "group-data-[size=sm]/switch:size-3 group-data-[size=md]/switch:size-3.5",
          // Unchecked: keep thumb near the start edge (mirrored by dir)
          "ltr:data-[state=unchecked]:group-data-[size=sm]/switch:translate-x-0.5",
          "ltr:data-[state=unchecked]:group-data-[size=md]/switch:translate-x-[3px]",
          "rtl:data-[state=unchecked]:group-data-[size=sm]/switch:-translate-x-0.5",
          "rtl:data-[state=unchecked]:group-data-[size=md]/switch:-translate-x-[3px]",
          // Checked: move to opposite edge (mirrored by dir)
          "ltr:data-[state=checked]:translate-x-[calc(100%-0px)]",
          "rtl:data-[state=checked]:-translate-x-[calc(100%-0px)]",
        )}
      />
    </SwitchPrimitive.Root>
  )
}

export { Switch }
