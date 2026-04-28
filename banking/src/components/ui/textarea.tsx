import * as React from "react"

import { cn } from "@/lib/utils"
import { cva, VariantProps } from "class-variance-authority"


const textareaVariants = cva(cn("flex field-sizing-content w-full transition-all focus-visible:bg-surface-white focus-visible:border-outline-gray-4 focus-visible:shadow-focus-gray active:bg-surface-white active:shadow-textarea-active active:border-outline-gray-4 outline-none border border-transparent placeholder:text-ink-gray-4 text-ink-gray-7 disabled:bg-surface-gray-1 disabled:placeholder:text-ink-gray-3 disabled:text-ink-gray-3 disabled:cursor-not-allowed aria-readonly:bg-surface-gray-1 aria-readonly:text-ink-gray-6 aria-readonly:pointer-events-none aria-invalid:shadow-focus-red aria-invalid:border-outline-red-3",
  "in-data-[slot=input-group]:border-transparent! in-data-[slot=input-group]:focus-visible:shadow-none! in-data-[slot=input-group]:bg-transparent!"),
  {
    variants: {
      inputSize: {
        sm: "text-p-base rounded py-1.5 px-2 min-h-15",
        md: "text-p-base rounded-md py-2.5 px-3 min-h-20.5",
        lg: "text-p-lg rounded-md py-3 px-3.5 min-h-25.5",
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

function Textarea({ inputSize = "md", variant = "subtle", className, ...props }: React.ComponentProps<"textarea"> & VariantProps<typeof textareaVariants>) {
  return (
    <textarea
      data-slot="textarea"
      data-input-size={inputSize}
      data-variant={variant}
      className={cn(
        textareaVariants({ inputSize, variant }),
        className
      )}
      {...props}
    />
  )
}

export { Textarea }
