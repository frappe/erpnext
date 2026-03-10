import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { Slot } from "radix-ui"

import { cn } from "@/lib/utils"

const badgeVariants = cva(
  "inline-flex items-center justify-center select-none rounded-full whitespace-nowrap gap-1 w-fit shrink-0 [&>svg]:pointer-events-none focus-visible:border-ring focus-visible:ring-ring/50 focus-visible:ring-[3px] aria-invalid:ring-destructive/20 dark:aria-invalid:ring-destructive/40 aria-invalid:border-destructive transition-[color,box-shadow] overflow-hidden",
  {
    variants: {
      variant: {
        solid: "",
        subtle: "",
        outline: "bg-transparent border [a&]:hover:bg-accent [a&]:hover:text-accent-foreground",
        ghost: "bg-transparent [a&]:hover:bg-accent [a&]:hover:text-accent-foreground",
      },
      size: {
        sm: 'h-4 text-xs px-1.5 [&>svg]:size-3',
        md: 'h-5 text-xs px-2 [&>svg]:size-3',
        lg: 'h-6 text-sm px-2 [&>svg]:size-4',
        xl: 'h-7 text-base px-2 [&>svg]:size-5',
      },
      theme: {
        gray: "",
        blue: "",
        green: "",
        red: "",
        orange: "",
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
        className: "text-ink-blue-1 bg-surface-blue-5 [a&]:hover:bg-surface-blue-3"
      },
      {
        variant: "solid",
        theme: "green",
        className: "text-ink-green-1 bg-surface-green-3 [a&]:hover:bg-surface-green-4"
      },
      {
        variant: "solid",
        theme: "orange",
        className: "text-ink-amber-1 bg-surface-amber-2 [a&]:hover:bg-surface-amber-3"
      },
      {
        variant: "solid",
        theme: "red",
        className: "text-ink-red-1 bg-surface-red-4 [a&]:hover:bg-surface-red-5"
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
        className: "text-ink-blue-2 bg-surface-blue-2 [a&]:hover:bg-surface-blue-3"
      },
      {
        variant: "subtle",
        theme: "green",
        className: "text-ink-green-3 bg-surface-green-2 [a&]:hover:bg-surface-green-3"
      },
      {
        variant: "subtle",
        theme: "orange",
        className: "text-ink-amber-3 bg-surface-amber-1 [a&]:hover:bg-surface-amber-2"
      },
      {
        variant: "subtle",
        theme: "red",
        className: "text-ink-red-4 bg-surface-red-2 [a&]:hover:bg-surface-red-3"
      },
      // Outline badge
      {
        variant: "outline",
        theme: "gray",
        className: "text-ink-gray-6 border-outline-gray-1 [a&]:hover:border-outline-gray-2"
      },
      {
        variant: "outline",
        theme: "blue",
        className: "text-ink-blue-2 border-outline-blue-1 [a&]:hover:border-outline-blue-2"
      },
      {
        variant: "outline",
        theme: "green",
        className: "text-ink-green-3 border-outline-green-2 [a&]:hover:border-outline-green-3"
      },
      {
        variant: "outline",
        theme: "orange",
        className: "text-ink-amber-3 border-outline-amber-2 [a&]:hover:border-outline-amber-3"
      },
      {
        variant: "outline",
        theme: "red",
        className: "text-ink-red-4 border-outline-red-2 [a&]:hover:border-outline-red-3"
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
        className: "text-ink-blue-2"
      },
      {
        variant: "ghost",
        theme: "green",
        className: "text-ink-green-3"
      },
      {
        variant: "ghost",
        theme: "orange",
        className: "text-ink-amber-3"
      },
      {
        variant: "ghost",
        theme: "red",
        className: "text-ink-red-4"
      },


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
