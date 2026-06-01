import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const alertVariants = cva(
  "relative w-full rounded-lg border px-4 py-3.5 text-base grid has-[>svg]:grid-cols-[calc(var(--spacing)*4)_1fr] grid-cols-[0_1fr] has-[>svg]:gap-x-3 gap-y-0.5 items-start [&>svg]:size-4 [&>svg]:translate-y-1 [&>svg]:text-current",
  {
    variants: {
      variant: {
        subtle: "bg-surface-white",
        outline: "border border-outline-gray-3",
      },
      theme: {
        gray: "text-ink-gray-8",
        blue: "text-ink-blue-3",
        green: "text-ink-green-3",
        red: "text-ink-red-3",
        amber: "text-ink-amber-3",
      }
    },
    compoundVariants: [
      // Subtle alerts
      {
        theme: "gray",
        variant: "subtle",
        className: "bg-surface-gray-2 border-outline-gray-1"
      },
      {
        theme: "blue",
        variant: "subtle",
        className: "bg-surface-blue-2 border-surface-blue-2"
      },
      {
        theme: "green",
        variant: "subtle",
        className: "bg-surface-green-2 border-surface-green-2"
      },
      {
        theme: "red",
        variant: "subtle",
        className: "bg-surface-red-2 border-surface-red-2"
      },
      {
        theme: "amber",
        variant: "subtle",
        className: "bg-surface-amber-2 border-surface-amber-2"
      }
    ],
    defaultVariants: {
      variant: "subtle",
      theme: "gray",
    },
  }
)

export type AlertProps = React.ComponentProps<"div"> & VariantProps<typeof alertVariants>

function Alert({
  className,
  variant,
  theme,
  ...props
}: AlertProps) {
  return (
    <div
      data-slot="alert"
      role="alert"
      className={cn(alertVariants({ variant, theme }), className)}
      {...props}
    />
  )
}

function AlertTitle({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="alert-title"
      className={cn(
        "col-start-2 min-h-4 text-ink-gray-8 font-medium text-p-base",
        className
      )}
      {...props}
    />
  )
}

function AlertDescription({
  className,
  ...props
}: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="alert-description"
      className={cn(
        "text-ink-gray-6 col-start-2 grid justify-items-start gap-1 text-p-base",
        className
      )}
      {...props}
    />
  )
}

export { Alert, AlertTitle, AlertDescription }
