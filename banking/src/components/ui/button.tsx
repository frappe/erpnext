import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { Slot } from "radix-ui"

import { cn } from "@/lib/utils"

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap transition-all disabled:pointer-events-none [&_svg]:pointer-events-none [&_svg:not([class*='size-'])]:size-4 shrink-0 [&_svg]:shrink-0 outline-none aria-invalid:shadow-focus-red aria-invalid:border-outline-red-3",
  {
    variants: {
      variant: {
        solid: "text-ink-white",
        subtle: "",
        ghost: "bg-transparent",
        outline: "bg-surface-white border",
        link: "bg-transparent underline-offset-4 underline",
      },
      size: {
        sm: "h-7 text-base px-2 rounded [&_svg:not([class*='size-'])]:size-4",
        md: "h-8 text-base font-medium px-2.5 rounded [&_svg:not([class*='size-'])]:size-4.5",
        lg: "h-10 text-lg font-medium px-3 rounded-md [&_svg:not([class*='size-'])]:size-5",
        xl: "h-11.5 text-xl font-medium px-3.5 rounded-lg [&_svg:not([class*='size-'])]:size-6",
        "2xl": "h-13 text-2xl font-medium px-3.5 rounded-xl [&_svg:not([class*='size-'])]:size-6",
      },
      theme: {
        gray: "focus-visible:shadow-focus-gray",
        blue: "focus-visible:shadow-focus-blue",
        green: "focus-visible:shadow-focus-green",
        red: "focus-visible:shadow-focus-red",
        amber: "focus-visible:shadow-focus-amber",
        violet: "focus-visible:shadow-focus-violet",
      },
      isIconButton: {
        true: "px-0",
        false: ""
      }
    },
    compoundVariants: [
      // Icon only buttons - Sizes
      {
        isIconButton: true,
        size: "sm",
        className: "size-7"
      },
      {
        isIconButton: true,
        size: "md",
        className: "size-8"
      },
      {
        isIconButton: true,
        size: "lg",
        className: "size-10"
      },
      {
        isIconButton: true,
        size: "xl",
        className: "size-11.5"
      },
      {
        isIconButton: true,
        size: "2xl",
        className: "size-13"
      },
      // Solid buttons
      {
        variant: "solid",
        theme: "gray",
        className: "bg-surface-gray-7 hover:bg-surface-gray-6 active:bg-surface-gray-5 disabled:bg-surface-gray-2 disabled:text-ink-gray-4"
      },
      {
        variant: "solid",
        theme: "blue",
        className: "bg-surface-blue-5 text-ink-blue-1 hover:bg-surface-blue-6 active:bg-surface-blue-7 disabled:bg-surface-blue-2 disabled:text-ink-blue-2"
      },
      {
        variant: "solid",
        theme: "green",
        className: "bg-surface-green-5 text-ink-green-1 hover:bg-surface-green-6 active:bg-surface-green-7 disabled:bg-surface-green-2 disabled:text-ink-green-2"
      },
      {
        variant: "solid",
        theme: "red",
        className: "bg-surface-red-5 text-ink-red-1 hover:bg-surface-red-6 active:bg-surface-red-7 disabled:bg-surface-red-2 disabled:text-ink-red-2"
      },
      {
        variant: "solid",
        theme: "violet",
        className: "bg-surface-violet-5 text-ink-violet-1 hover:bg-surface-violet-6 active:bg-surface-violet-7 disabled:bg-surface-violet-2 disabled:text-ink-violet-2"
      },
      {
        variant: "solid",
        theme: "amber",
        className: "bg-surface-amber-5 text-ink-amber-1 hover:bg-surface-amber-6 active:bg-surface-amber-7 disabled:bg-surface-amber-2 disabled:text-ink-amber-2"
      },
      // Subtle Buttons
      {
        variant: "subtle",
        theme: "gray",
        className: "text-ink-gray-7 bg-surface-gray-2 hover:bg-surface-gray-3 active:bg-surface-gray-4 disabled:bg-surface-gray-2 disabled:text-ink-gray-4"
      },
      {
        variant: "subtle",
        theme: "blue",
        className: "text-ink-blue-4 bg-surface-blue-2 hover:bg-surface-blue-3 active:bg-surface-blue-4 disabled:bg-surface-blue-2 disabled:text-ink-blue-2"
      },
      {
        variant: "subtle",
        theme: "green",
        className: "text-ink-green-4 bg-surface-green-2 hover:bg-surface-green-3 active:bg-surface-green-4 disabled:bg-surface-green-2 disabled:text-ink-green-2"
      },
      {
        variant: "subtle",
        theme: "red",
        className: "text-ink-red-4 bg-surface-red-2 hover:bg-surface-red-3 active:bg-surface-red-4 disabled:bg-surface-red-2 disabled:text-ink-red-2"
      },
      {
        variant: "subtle",
        theme: "violet",
        className: "text-ink-violet-4 bg-surface-violet-2 hover:bg-surface-violet-3 active:bg-surface-violet-4 disabled:bg-surface-violet-2 disabled:text-ink-violet-2"
      },
      {
        variant: "subtle",
        theme: "amber",
        className: "text-ink-amber-4 bg-surface-amber-2 hover:bg-surface-amber-3 active:bg-surface-amber-4 disabled:bg-surface-amber-2 disabled:text-ink-amber-2"
      },
      // Outline buttons
      {
        variant: "outline",
        theme: "gray",
        className:
          "text-ink-gray-7 border-outline-gray-2 hover:border-outline-gray-3 active:border-outline-gray-4 active:bg-surface-gray-4 disabled:bg-surface-gray-2 disabled:text-ink-gray-4 disabled:border-outline-gray-2"
      },
      {
        variant: "outline",
        theme: "blue",
        className:
          "text-ink-blue-4 border-outline-blue-2 hover:border-outline-blue-3 active:border-outline-blue-4 active:bg-surface-blue-4 disabled:bg-surface-blue-2 disabled:text-ink-blue-2 disabled:border-outline-blue-2"
      },
      {
        variant: "outline",
        theme: "green",
        className:
          "text-ink-green-4 border-outline-green-2 hover:border-outline-green-3 active:border-outline-green-4 active:bg-surface-green-4 disabled:bg-surface-green-2 disabled:text-ink-green-2 disabled:border-outline-green-2"
      },
      {
        variant: "outline",
        theme: "red",
        className:
          "text-ink-red-4 border-outline-red-2 hover:border-outline-red-3 active:border-outline-red-4 active:bg-surface-red-4 disabled:bg-surface-red-2 disabled:text-ink-red-2 disabled:border-outline-red-2"
      },
      {
        variant: "outline",
        theme: "violet",
        className: "text-ink-violet-4 border-outline-violet-2 hover:border-outline-violet-3 active:border-outline-violet-4 active:bg-surface-violet-4 disabled:bg-surface-violet-2 disabled:text-ink-violet-2 disabled:border-outline-violet-2"
      },
      {
        variant: "outline",
        theme: "amber",
        className: "text-ink-amber-4 border-outline-amber-2 hover:border-outline-amber-3 active:border-outline-amber-4 active:bg-surface-amber-4 disabled:bg-surface-amber-2 disabled:text-ink-amber-2 disabled:border-outline-amber-2"
      },
      // Ghost buttons
      {
        variant: "ghost",
        theme: "gray",
        className:
          "text-ink-gray-7 hover:bg-surface-gray-3 active:bg-surface-gray-4 disabled:text-ink-gray-4"
      },
      {
        variant: "ghost",
        theme: "blue",
        className:
          "text-ink-blue-4 hover:bg-surface-blue-3 active:bg-surface-blue-4 disabled:text-ink-blue-2"
      },
      {
        variant: "ghost",
        theme: "green",
        className:
          "text-ink-green-4 hover:bg-surface-green-3 active:bg-surface-green-4 disabled:text-ink-green-2"
      },
      {
        variant: "ghost",
        theme: "red",
        className:
          "text-ink-red-4 hover:bg-surface-red-3 active:bg-surface-red-4 disabled:text-ink-red-2"
      },
      {
        variant: "ghost",
        theme: "violet",
        className: "text-ink-violet-4 hover:bg-surface-violet-3 active:bg-surface-violet-4 disabled:text-ink-violet-2"
      },
      {
        variant: "ghost",
        theme: "amber",
        className: "text-ink-amber-4 hover:bg-surface-amber-3 active:bg-surface-amber-4 disabled:text-ink-amber-2"
      },
      //Link buttons
      {
        variant: "link",
        theme: "gray",
        className: "text-ink-gray-8 hover:text-ink-gray-8 active:text-ink-gray-8 disabled:text-ink-gray-4"
      },
      {
        variant: "link",
        theme: "blue",
        className: "text-ink-blue-3 hover:text-ink-blue-4 active:text-ink-blue-4 disabled:text-ink-blue-link"
      },
      {
        variant: "link",
        theme: "green",
        className: "text-ink-green-3 hover:text-ink-green-4 active:text-ink-green-4 disabled:text-ink-green-2"
      },
      {
        variant: "link",
        theme: "red",
        className: "text-ink-red-3 hover:text-ink-red-4 active:text-red-4 disabled:text-ink-red-2"
      },
      {
        variant: "link",
        theme: "violet",
        className: "text-ink-violet-3 hover:text-ink-violet-4 active:text-ink-violet-4 disabled:text-ink-violet-2"
      },
      {
        variant: "link",
        theme: "amber",
        className: "text-ink-amber-3 hover:text-ink-amber-4 active:text-ink-amber-4 disabled:text-ink-amber-2"
      }
    ],
    defaultVariants: {
      variant: "solid",
      size: "sm",
      theme: "gray",
    },
  }
)

function Button({
  className,
  variant = "solid",
  size = "sm",
  theme = "gray",
  isIconButton = false,
  asChild = false,
  ...props
}: React.ComponentProps<"button"> &
  VariantProps<typeof buttonVariants> & {
    asChild?: boolean
  }) {
  const Comp = asChild ? Slot.Root : "button"

  return (
    <Comp
      data-slot="button"
      data-variant={variant}
      data-size={size}
      data-theme={theme}
      className={cn(buttonVariants({ variant, size, theme, className, isIconButton }))}
      {...props}
    />
  )
}

export { Button, buttonVariants }
