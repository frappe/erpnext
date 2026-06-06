import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"

const inputGroupVariants = cva(cn("group/input-group relative flex w-full items-center outline-none min-w-0 border border-transparent transition-all",

  // Variants based on alignment.
  "has-[>[data-align=inline-start]]:[&>input]:ps-2",
  "has-[>[data-align=inline-end]]:[&>input]:pe-2",
  "has-[>[data-align=block-start]]:h-auto has-[>[data-align=block-start]]:flex-col has-[>[data-align=block-start]]:[&>input]:pb-3",
  "has-[>[data-align=block-end]]:h-auto has-[>[data-align=block-end]]:flex-col has-[>[data-align=block-end]]:[&>input]:pt-3",


  // Focus state.
  "has-[[data-slot=input]:focus-visible]:bg-surface-white has-[[data-slot=input]:focus-visible]:border-outline-gray-4 has-[[data-slot=input]:focus-visible]:shadow-focus-gray",

  // Disabled state
  "has-[>[data-slot=input]:disabled]:bg-surface-gray-1 has-[>[data-slot=input]:disabled]:text-ink-gray-3 has-[>[data-slot=input]:disabled]:cursor-not-allowed has-[>[data-slot=input]:disabled]:pointer-events-none",

  // Error state.
  "has-[[data-slot][aria-invalid=true]]:shadow-focus-red has-[[data-slot][aria-invalid=true]]:border-outline-red-3",

  // Read only state
  "has-[[data-slot][aria-readonly=true]]:bg-surface-gray-1 has-[[data-slot][aria-readonly=true]]:text-ink-gray-6 has-[[data-slot][aria-readonly=true]]:pointer-events-none",

),
  {
    variants: {
      variant: {
        subtle: "bg-surface-gray-2",
        outline: "bg-surface-white border-outline-gray-2"
      },
      size: {
        sm: "h-7 has-[>textarea]:h-auto rounded text-base",
        md: "h-8 has-[>textarea]:h-auto rounded text-base",
        lg: "h-10 has-[>textarea]:h-auto rounded-md text-lg"
      }
    },
    defaultVariants: {
      variant: "subtle",
      size: "md"
    }
  }
)

function InputGroup({ className, variant = "subtle", size = "md", ...props }: React.ComponentProps<"div"> & VariantProps<typeof inputGroupVariants>) {
  return (
    <div
      data-slot="input-group"
      data-variant={variant}
      data-size={size}
      role="group"
      className={cn(
        inputGroupVariants({ variant, size }),
        className
      )}
      {...props}
    />
  )
}

const inputGroupAddonVariants = cva(
  "text-ink-gray-5 flex h-auto cursor-text items-center justify-center gap-2 py-1.5 text-sm font-medium select-none [&>svg:not([class*='size-'])]:size-4 [&>kbd]:rounded-[calc(var(--radius)-5px)] group-data-[disabled=true]/input-group:opacity-50",
  {
    variants: {
      align: {
        "inline-start":
          "order-first ps-3 has-[>button]:ms-[-0.45rem] has-[>kbd]:ms-[-0.35rem]",
        "inline-end":
          "order-last pe-3 has-[>button]:me-[-0.45rem] has-[>kbd]:me-[-0.35rem]",
        "block-start":
          "order-first w-full justify-start px-3 pt-3 [.border-b]:pb-3 group-has-[>input]/input-group:pt-2.5",
        "block-end":
          "order-last w-full justify-start px-3 pb-3 [.border-t]:pt-3 group-has-[>input]/input-group:pb-2.5",
      },
    },
    defaultVariants: {
      align: "inline-start",
    },
  }
)

function InputGroupAddon({
  className,
  align = "inline-start",
  ...props
}: React.ComponentProps<"div"> & VariantProps<typeof inputGroupAddonVariants>) {
  return (
    <div
      role="group"
      data-slot="input-group-addon"
      data-align={align}
      className={cn(inputGroupAddonVariants({ align }), className)}
      onClick={(e) => {
        if ((e.target as HTMLElement).closest("button")) {
          return
        }
        e.currentTarget.parentElement?.querySelector("input")?.focus()
      }}
      {...props}
    />
  )
}

const inputGroupButtonVariants = cva(
  "text-sm shadow-none flex gap-2 items-center",
  {
    variants: {
      size: {
        xs: "h-6 gap-1 px-2 rounded-[calc(var(--radius)-5px)] [&>svg:not([class*='size-'])]:size-3.5 has-[>svg]:px-2",
        sm: "h-8 px-2.5 gap-1.5 rounded-md has-[>svg]:px-2.5",
        "icon-xs":
          "size-6 rounded-[calc(var(--radius)-5px)] p-0 has-[>svg]:p-0",
        "icon-sm": "size-8 p-0 has-[>svg]:p-0",
      },
    },
    defaultVariants: {
      size: "xs",
    },
  }
)

function InputGroupButton({
  className,
  type = "button",
  variant = "ghost",
  size = "xs",
  ...props
}: Omit<React.ComponentProps<typeof Button>, "size"> &
  VariantProps<typeof inputGroupButtonVariants>) {
  return (
    <Button
      type={type}
      data-size={size}
      variant={variant}
      className={cn(inputGroupButtonVariants({ size }), className)}
      {...props}
    />
  )
}

function InputGroupText({ className, ...props }: React.ComponentProps<"span">) {
  return (
    <span
      className={cn(
        "text-ink-gray-5 flex items-center gap-2 text-sm whitespace-nowrap [&_svg]:pointer-events-none [&_svg:not([class*='size-'])]:size-4",
        className
      )}
      {...props}
    />
  )
}

export {
  InputGroup,
  InputGroupAddon,
  InputGroupButton,
  InputGroupText,
}
