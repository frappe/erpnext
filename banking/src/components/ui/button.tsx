import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { Slot } from "radix-ui"

import { cn } from "@/lib/utils"

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap transition-all disabled:pointer-events-none [&_svg]:pointer-events-none [&_svg:not([class*='size-'])]:size-4 shrink-0 [&_svg]:shrink-0 outline-none focus-visible:ring aria-invalid:ring-red-500/20 dark:aria-invalid:ring-red-500/40 aria-invalid:border-red-500",
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
        gray: "focus-visible:ring-outline-gray-3",
        blue: "focus-visible:ring-blue-400",
        green: "focus-visible:ring-outline-green-2",
        red: "focus-visible:ring-outline-red-2"
      },
      isIconButton: {
        true: "",
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
        className: "bg-blue-500 hover:bg-surface-blue-3 active:bg-blue-700 disabled:bg-blue-300 disabled:text-ink-white"
      },
      {
        variant: "solid",
        theme: "green",
        className: "bg-surface-green-3 hover:bg-green-700 active:bg-green-800 disabled:bg-surface-green-2 disabled:text-ink-green-2"
      },
      {
        variant: "solid",
        theme: "red",
        className: "bg-surface-red-5 hover:bg-surface-red-6 active:bg-surface-red-7 disabled:bg-surface-red-2 disabled:text-ink-red-2"
      },
      // Subtle Buttons
      {
        variant: "subtle",
        theme: "gray",
        className: "text-ink-gray-8 bg-surface-gray-2 hover:bg-surface-gray-3 active:bg-surface-gray-4 disabled:bg-surface-gray-2 disabled:text-ink-gray-4"
      },
      {
        variant: "subtle",
        theme: "blue",
        className: "text-ink-blue-3 bg-surface-blue-2 hover:bg-blue-200 active:bg-blue-300 disabled:bg-surface-blue-2 disabled:text-ink-blue-link"
      },
      {
        variant: "subtle",
        theme: "green",
        className: "text-green-800 bg-surface-green-2 hover:bg-green-200 active:bg-green-300 disabled:bg-surface-green-2 disabled:text-ink-green-2"
      },
      {
        variant: "subtle",
        theme: "red",
        className: "text-red-700 bg-surface-red-2 hover:bg-surface-red-3 active:bg-surface-red-4 disabled:bg-surface-red-2 disabled:text-ink-red-2"
      },

      // Outline buttons
      {
        variant: "outline",
        theme: "gray",
        className:
          "text-ink-gray-8 border-outline-gray-2 hover:border-outline-gray-3 active:border-outline-gray-3 active:bg-surface-gray-4 disabled:bg-surface-gray-2 disabled:text-ink-gray-4 disabled:border-outline-gray-2"
      },
      {
        variant: "outline",
        theme: "blue",
        className:
          "text-ink-blue-3 border-outline-blue-1 hover:border-blue-400 active:border-blue-400 active:bg-blue-300 disabled:bg-surface-blue-2 disabled:text-ink-blue-link disabled:border-outline-blue-1"
      },
      {
        variant: "outline",
        theme: "green",
        className:
          "text-green-800 border-outline-green-2 hover:border-green-500 active:border-green-500 active:bg-green-300 disabled:bg-surface-green-2 disabled:text-ink-green-2  disabled:border-outline-green-2"
      },
      {
        variant: "outline",
        theme: "red",
        className:
          "text-red-700 border-outline-red-1 hover:border-outline-red-2 active:border-outline-red-2 active:bg-surface-red-3 disabled:bg-surface-red-2 disabled:text-ink-red-2 disabled:border-outline-red-1"
      },

      // Ghost buttons
      {
        variant: "ghost",
        theme: "gray",
        className:
          "text-ink-gray-8 hover:bg-surface-gray-3 active:bg-surface-gray-4 disabled:text-ink-gray-4"
      },
      {
        variant: "ghost",
        theme: "blue",
        className:
          "text-ink-blue-3 hover:bg-blue-200 active:bg-blue-300 disabled:text-ink-blue-link"
      },
      {
        variant: "ghost",
        theme: "green",
        className:
          "text-green-800 hover:bg-green-200 active:bg-green-300 disabled:text-ink-green-2"
      },
      {
        variant: "ghost",
        theme: "red",
        className:
          "text-red-700 hover:bg-surface-red-3 active:bg-surface-red-4 disabled:text-ink-red-2"
      },
      //Link buttons
      {
        variant: "link",
        theme: "gray",
        className: "text-ink-gray-8 hover:text-ink-gray-9 active:text-ink-gray-9 disabled:text-ink-gray-4"
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
      className={cn(buttonVariants({ variant, size, theme, className }))}
      {...props}
    />
  )
}

export { Button, buttonVariants }
