import * as React from "react"

import { cn } from "@/lib/utils"
import { cva, VariantProps } from "class-variance-authority"

const inputVariants = cva(cn("flex w-full min-w-0 transition-all outline-none border border-transparent",
  "focus-visible:bg-surface-white focus-visible:border-outline-gray-4 focus-visible:shadow-focus-gray",
  "active:bg-surface-white active:shadow-sm active:border-outline-gray-4",
  "placeholder:text-ink-gray-4 text-ink-gray-7",
  "disabled:bg-surface-gray-1 disabled:placeholder:text-ink-gray-3 disabled:text-ink-gray-3 disabled:cursor-not-allowed disabled:pointer-events-none",
  "aria-readonly:bg-surface-gray-1 aria-readonly:text-ink-gray-6 aria-readonly:pointer-events-none aria-invalid:shadow-focus-red aria-invalid:border-outline-red-3",
  "in-data-[slot=input-group]:border-transparent! in-data-[slot=input-group]:focus-visible:shadow-none! in-data-[slot=input-group]:bg-transparent!"),
  {
    variants: {
      inputSize: {
        sm: "text-base rounded py-1.5 px-2 h-7",
        md: "text-base rounded py-2 px-2.5 h-8",
        lg: "text-lg rounded-md py-[11px] px-3 h-10",
      },
      variant: {
        subtle: "bg-surface-gray-2 hover:bg-surface-gray-3 aria-invalid:bg-surface-red-1",
        outline: "bg-surface-white border-outline-gray-2 hover:border-outline-gray-3 active:border-outline-gray-4 disabled:border-outline-gray-2",
      }
    },
    defaultVariants: {
      inputSize: "md",
      variant: "subtle"
    }
  }
)

function Input({ className, type, inputSize = "md", variant = "subtle", ...props }: React.ComponentProps<"input"> & VariantProps<typeof inputVariants>) {
  return (
    <input
      type={type}
      data-slot="input"
      data-input-size={inputSize}
      data-variant={variant}
      className={cn(
        "file:text-ink-gray-8 file:inline-flex file:border-0 file:bg-transparent file:text-sm file:font-medium",
        inputVariants({ inputSize, variant }),
        className
      )}
      {...props}
    />
  )
}

export { Input }
