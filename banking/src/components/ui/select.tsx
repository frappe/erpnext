import * as React from "react"
import { CheckIcon, ChevronDownIcon, ChevronUpIcon } from "lucide-react"
import { Select as SelectPrimitive } from "radix-ui"

import { cn } from "@/lib/utils"
import { cva, VariantProps } from "class-variance-authority"

function Select({
  ...props
}: React.ComponentProps<typeof SelectPrimitive.Root>) {
  return <SelectPrimitive.Root data-slot="select" {...props} />
}

function SelectGroup({
  ...props
}: React.ComponentProps<typeof SelectPrimitive.Group>) {
  return <SelectPrimitive.Group data-slot="select-group" {...props} />
}

function SelectValue({
  ...props
}: React.ComponentProps<typeof SelectPrimitive.Value>) {
  return <SelectPrimitive.Value data-slot="select-value" {...props} />
}


const selectVariants = cva(cn("flex w-fit items-center justify-between gap-2 min-w-0 transition-all outline-none border border-transparent whitespace-nowrap",
  "focus-visible:bg-surface-white focus-visible:border-outline-gray-4 focus-visible:shadow-focus-gray",
  "active:bg-surface-white active:shadow-sm active:border-outline-gray-4 data-[state=open]:border-outline-gray-4",
  "placeholder:text-ink-gray-4 text-ink-gray-7",
  "disabled:bg-surface-gray-1 disabled:placeholder:text-ink-gray-3 disabled:text-ink-gray-3 disabled:cursor-not-allowed disabled:pointer-events-none",
  "aria-readonly:bg-surface-gray-1 aria-readonly:text-ink-gray-6 aria-readonly:pointer-events-none aria-invalid:shadow-focus-red aria-invalid:border-outline-red-3",
  // Disable most styles inside an input group
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

function SelectTrigger({
  className,
  inputSize = "md",
  variant = "subtle",
  children,
  ...props
}: React.ComponentProps<typeof SelectPrimitive.Trigger> & VariantProps<typeof selectVariants>) {
  return (
    <SelectPrimitive.Trigger
      data-slot="select-trigger"
      data-input-size={inputSize}
      className={cn(
        "data-placeholder:text-ink-gray-4 [&_svg:not([class*='text-'])]:text-ink-gray-7",
        "*:data-[slot=select-value]:line-clamp-1 *:data-[slot=select-value]:flex *:data-[slot=select-value]:items-center *:data-[slot=select-value]:gap-2 [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4",
        selectVariants({ inputSize, variant }),
        className
      )}
      {...props}
    >
      {children}
      <SelectPrimitive.Icon asChild>
        <ChevronDownIcon />
      </SelectPrimitive.Icon>
    </SelectPrimitive.Trigger>
  )
}

function SelectContent({
  className,
  children,
  position = "popper",
  align = "center",
  ...props
}: React.ComponentProps<typeof SelectPrimitive.Content>) {
  return (
    <SelectPrimitive.Portal>
      <SelectPrimitive.Content
        data-slot="select-content"
        className={cn(
          "bg-surface-modal rounded-lg min-w-32 border shadow-xl",
          "data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95 data-[side=bottom]:slide-in-from-top-2 data-[side=left]:slide-in-from-right-2 data-[side=right]:slide-in-from-left-2 data-[side=top]:slide-in-from-bottom-2 relative z-50 max-h-(--radix-select-content-available-height) origin-(--radix-select-content-transform-origin) overflow-x-hidden overflow-y-auto",
          position === "popper" &&
          "data-[side=bottom]:translate-y-1 data-[side=left]:-translate-x-1 data-[side=right]:translate-x-1 data-[side=top]:-translate-y-1",
          className
        )}
        position={position}
        align={align}
        {...props}
      >
        <SelectScrollUpButton />
        <SelectPrimitive.Viewport
          className={cn(
            "p-1",
            position === "popper" &&
            "h-[var(--radix-select-trigger-height)] w-full min-w-[var(--radix-select-trigger-width)] scroll-my-1"
          )}
        >
          {children}
        </SelectPrimitive.Viewport>
        <SelectScrollDownButton />
      </SelectPrimitive.Content>
    </SelectPrimitive.Portal>
  )
}

function SelectLabel({
  className,
  ...props
}: React.ComponentProps<typeof SelectPrimitive.Label>) {
  return (
    <SelectPrimitive.Label
      data-slot="select-label"
      className={cn("text-ink-gray-4 px-2 py-1.5 text-sm font-medium", className)}
      {...props}
    />
  )
}

function SelectItem({
  className,
  children,
  ...props
}: React.ComponentProps<typeof SelectPrimitive.Item>) {
  return (
    <SelectPrimitive.Item
      data-slot="select-item"
      className={cn(
        "outline-hidden select-none relative flex w-full cursor-default items-center gap-2 rounded py-1.5 pe-8 px-2",
        "focus:bg-surface-gray-2 text-ink-gray-6 [&_svg:not([class*='text-'])]:text-ink-gray-6 text-base [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4 *:[span]:last:flex *:[span]:last:items-center *:[span]:last:gap-2",
        "data-disabled:pointer-events-none data-disabled:text-ink-gray-3",
        className
      )}
      {...props}
    >
      <span
        data-slot="select-item-indicator"
        className="absolute ltr:right-2 rtl:left-2 flex size-3.5 items-center justify-center"
      >
        <SelectPrimitive.ItemIndicator>
          <CheckIcon className="size-4" />
        </SelectPrimitive.ItemIndicator>
      </span>
      <SelectPrimitive.ItemText>{children}</SelectPrimitive.ItemText>
    </SelectPrimitive.Item>
  )
}

function SelectSeparator({
  className,
  ...props
}: React.ComponentProps<typeof SelectPrimitive.Separator>) {
  return (
    <SelectPrimitive.Separator
      data-slot="select-separator"
      className={cn("bg-outline-gray-modals pointer-events-none mx-0.5 my-1 h-px", className)}
      {...props}
    />
  )
}

function SelectScrollUpButton({
  className,
  ...props
}: React.ComponentProps<typeof SelectPrimitive.ScrollUpButton>) {
  return (
    <SelectPrimitive.ScrollUpButton
      data-slot="select-scroll-up-button"
      className={cn(
        "flex cursor-default items-center justify-center py-1",
        className
      )}
      {...props}
    >
      <ChevronUpIcon className="size-4" />
    </SelectPrimitive.ScrollUpButton>
  )
}

function SelectScrollDownButton({
  className,
  ...props
}: React.ComponentProps<typeof SelectPrimitive.ScrollDownButton>) {
  return (
    <SelectPrimitive.ScrollDownButton
      data-slot="select-scroll-down-button"
      className={cn(
        "flex cursor-default items-center justify-center py-1",
        className
      )}
      {...props}
    >
      <ChevronDownIcon className="size-4" />
    </SelectPrimitive.ScrollDownButton>
  )
}

export {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectScrollDownButton,
  SelectScrollUpButton,
  SelectSeparator,
  SelectTrigger,
  SelectValue,
}
