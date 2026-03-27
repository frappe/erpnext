import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { Slot } from "radix-ui"

import { cn } from "@/lib/utils"

const badgeVariants = cva(
  "inline-flex items-center justify-center select-none rounded-full whitespace-nowrap gap-1 w-fit shrink-0 [&>svg]:pointer-events-none transition-[color,box-shadow] overflow-hidden",
  {
    variants: {
      variant: {
        solid: "",
        subtle: "",
        outline: "bg-transparent border",
        ghost: "bg-transparent",
      },
      size: {
        sm: 'h-4 text-xs px-1.5 [&>svg]:size-2.5',
        md: 'h-5 text-xs px-1.5 [&>svg]:size-3',
        lg: 'h-6 text-sm px-2 [&>svg]:size-3',
      },
      theme: {
        gray: "",
        blue: "",
        green: "",
        red: "",
        orange: "",
        violet: "",
      }
    },
    compoundVariants: [
      // Solid badges
      {
        variant: "solid",
        theme: "gray",
        className: "text-ink-white bg-surface-gray-7 [a&]:hover:bg-surface-gray-8"
      },
      {
        variant: "solid",
        theme: "blue",
        className: "text-ink-blue-1 bg-surface-blue-5 [a&]:hover:bg-surface-blue-6"
      },
      {
        variant: "solid",
        theme: "green",
        className: "text-ink-green-1 bg-surface-green-5 [a&]:hover:bg-surface-green-6"
      },
      {
        variant: "solid",
        theme: "orange",
        className: "text-ink-amber-1 bg-surface-amber-5 [a&]:hover:bg-surface-amber-6"
      },
      {
        variant: "solid",
        theme: "red",
        className: "text-ink-red-1 bg-surface-red-5 [a&]:hover:bg-surface-red-6"
      },
      {
        variant: "solid",
        theme: "violet",
        className: "text-ink-violet-1 bg-surface-violet-5 [a&]:hover:bg-surface-violet-6"
      },
      // Subtle badge
      {
        variant: "subtle",
        theme: "gray",
        className: "text-ink-gray-6 bg-surface-gray-2 [a&]:hover:bg-surface-gray-3"
      },
      {
        variant: "subtle",
        theme: "blue",
        className: "text-ink-blue-4 bg-surface-blue-2 [a&]:hover:bg-surface-blue-3"
      },
      {
        variant: "subtle",
        theme: "green",
        className: "text-ink-green-4 bg-surface-green-2 [a&]:hover:bg-surface-green-3"
      },
      {
        variant: "subtle",
        theme: "orange",
        className: "text-ink-amber-4 bg-surface-amber-2 [a&]:hover:bg-surface-amber-3"
      },
      {
        variant: "subtle",
        theme: "red",
        className: "text-ink-red-4 bg-surface-red-2 [a&]:hover:bg-surface-red-3"
      },
      {
        variant: "subtle",
        theme: "violet",
        className: "text-ink-violet-4 bg-surface-violet-2 [a&]:hover:bg-surface-violet-3"
      },
      // Outline badge
      {
        variant: "outline",
        theme: "gray",
        className: "text-ink-gray-6 border-outline-gray-2 [a&]:hover:bg-surface-gray-2"
      },
      {
        variant: "outline",
        theme: "blue",
        className: "text-ink-blue-4 border-outline-blue-2 [a&]:hover:bg-surface-blue-2"
      },
      {
        variant: "outline",
        theme: "green",
        className: "text-ink-green-4 border-outline-green-2 [a&]:hover:bg-surface-green-2"
      },
      {
        variant: "outline",
        theme: "orange",
        className: "text-ink-amber-4 border-outline-amber-2 [a&]:hover:bg-surface-amber-2"
      },
      {
        variant: "outline",
        theme: "red",
        className: "text-ink-red-4 border-outline-red-2 [a&]:hover:bg-surface-red-2"
      },
      {
        variant: "outline",
        theme: "violet",
        className: "text-ink-violet-4 border-outline-violet-2 [a&]:hover:bg-surface-violet-2"
      },
      // Ghost badge
      {
        variant: "ghost",
        theme: "gray",
        className: "text-ink-gray-6"
      },
      {
        variant: "ghost",
        theme: "blue",
        className: "text-ink-blue-4"
      },
      {
        variant: "ghost",
        theme: "green",
        className: "text-ink-green-4"
      },
      {
        variant: "ghost",
        theme: "orange",
        className: "text-ink-amber-4"
      },
      {
        variant: "ghost",
        theme: "red",
        className: "text-ink-red-4"
      },
      {
        variant: "ghost",
        theme: "violet",
        className: "text-ink-violet-4"
      }
    ],
    defaultVariants: {
      variant: "subtle",
      size: "md",
      theme: "gray",
    },
  }
)

function Badge({
  className,
  variant = "subtle",
  size = "md",
  theme = "gray",
  asChild = false,
  ...props
}: React.ComponentProps<"span"> &
  VariantProps<typeof badgeVariants> & { asChild?: boolean }) {
  const Comp = asChild ? Slot.Root : "span"

  return (
    <Comp
      data-slot="badge"
      data-variant={variant}
      data-size={size}
      data-theme={theme}
      className={cn(badgeVariants({ variant, size, theme }), className)}
      {...props}
    />
  )
}

export { Badge, badgeVariants }
