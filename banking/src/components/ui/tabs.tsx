import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { Tabs as TabsPrimitive } from "radix-ui"

import { cn } from "@/lib/utils"

function Tabs({
  className,
  orientation = "horizontal",
  ...props
}: React.ComponentProps<typeof TabsPrimitive.Root>) {
  return (
    <TabsPrimitive.Root
      data-slot="tabs"
      data-orientation={orientation}
      orientation={orientation}
      className={cn(
        "group/tabs flex gap-2 data-[orientation=horizontal]:flex-col",
        className
      )}
      {...props}
    />
  )
}

const tabsListVariants = cva(
  "group/tabs-list text-ink-gray-5 inline-flex w-full items-center justify-start group-data-[orientation=vertical]/tabs:flex-col",
  {
    variants: {
      variant: {
        subtle: "bg-surface-gray-2 p-px",
        outline: "p-px border border-outline-gray-1",
        underline: "border-b border-outline-gray-1 gap-6",
      },
      size: {
        sm: "group-data-[orientation=horizontal]/tabs:h-7",
        md: "group-data-[orientation=horizontal]/tabs:h-7.5"
      }
    },
    compoundVariants: [
      {
        variant: "subtle",
        size: "sm",
        className: "rounded gap-1"
      },
      {
        variant: "subtle",
        size: "md",
        className: "rounded-md gap-1.5 font-medium"
      },
      {
        variant: "outline",
        size: "sm",
        className: "rounded gap-1",
      },
      {
        variant: "outline",
        size: "md",
        className: "rounded-md gap-1.5 font-medium",
      },
      {
        variant: "underline",
        size: "sm",
        className: "",
      },
      {
        variant: "underline",
        size: "md",
        className: "",
      },
    ],
    defaultVariants: {
      variant: "underline",
      size: "md",
    },
  }
)

function TabsList({
  className,
  variant = "underline",
  size = "md",
  ...props
}: React.ComponentProps<typeof TabsPrimitive.List> &
  VariantProps<typeof tabsListVariants>) {
  return (
    <TabsPrimitive.List
      data-slot="tabs-list"
      data-variant={variant}
      data-size={size}
      className={cn(tabsListVariants({ variant, size }), className)}
      {...props}
    />
  )
}

function TabsTrigger({
  className,
  ...props
}: React.ComponentProps<typeof TabsPrimitive.Trigger>) {
  return (
    <TabsPrimitive.Trigger
      data-slot="tabs-trigger"
      className={cn(
        // Common
        "whitespace-nowrap transition-all disabled:pointer-events-none disabled:opacity-50",
        "text-ink-gray-5 text-base data-[state=active]:text-ink-gray-8 hover:text-ink-gray-8 relative gap-2",
        "flex items-center justify-center group-data-[orientation=vertical]/tabs:w-full group-data-[orientation=vertical]/tabs:justify-start",
        // Icon Sizes - 16px for sm, 18px for md
        "[&_svg]:pointer-events-none [&_svg]:shrink-0 group-data-[size=sm]/tabs-list:[&_svg:not([class*='size-'])]:size-4 group-data-[size=md]/tabs-list:[&_svg:not([class*='size-'])]:size-4.5",

        // Variant: subtle, size: sm
        "group-data-[variant=subtle]/tabs-list:group-data-[size=sm]/tabs-list:py-[5px] group-data-[variant=subtle]/tabs-list:group-data-[size=sm]/tabs-list:px-2 group-data-[variant=subtle]/tabs-list:group-data-[size=sm]/tabs-list:rounded-[7px]",
        // Variant: subtle, size: md
        "group-data-[variant=subtle]/tabs-list:group-data-[size=md]/tabs-list:py-1.5 group-data-[variant=subtle]/tabs-list:group-data-[size=md]/tabs-list:px-2.5 group-data-[variant=subtle]/tabs-list:group-data-[size=md]/tabs-list:rounded-[9px]",
        // Variant: subtle - active - background, text color and shadow applied
        "group-data-[variant=subtle]/tabs-list:data-[state=active]:bg-surface-selected group-data-[variant=subtle]/tabs-list:data-[state=active]:shadow-active-tab",


        // Variant: outline, size: sm
        "group-data-[variant=outline]/tabs-list:group-data-[size=sm]/tabs-list:py-[5px] group-data-[variant=outline]/tabs-list:group-data-[size=sm]/tabs-list:px-2 group-data-[variant=outline]/tabs-list:group-data-[size=sm]/tabs-list:rounded-[7px]",
        // Variant: outline, size: md
        "group-data-[variant=outline]/tabs-list:group-data-[size=md]/tabs-list:py-1.5 group-data-[variant=outline]/tabs-list:group-data-[size=md]/tabs-list:px-2.5 group-data-[variant=outline]/tabs-list:group-data-[size=md]/tabs-list:rounded-[9px]",
        // Variant: outline - active - background, text color and shadow applied
        "group-data-[variant=outline]/tabs-list:data-[state=active]:bg-surface-selected group-data-[variant=outline]/tabs-list:data-[state=active]:shadow-active-tab",

        // Variant: underline - no radius
        "group-data-[variant=underline]/tabs-list:rounded-none group-data-[variant=underline]/tabs-list:px-0 group-data-[variant=underline]/tabs-list:bottom-px",
        // Variant: underline, size: sm
        "group-data-[variant=underline]/tabs-list:group-data-[size=sm]/tabs-list:py-1.5",
        // Variant: underline, size: md
        "group-data-[variant=underline]/tabs-list:group-data-[size=md]/tabs-list:py-[7px] group-data-[variant=underline]/tabs-list:group-data-[size=md]/tabs-list:font-medium",
        // Variant: underline - active - border applied
        "group-data-[variant=underline]/tabs-list:border-b group-data-[variant=underline]/tabs-list:border-b-transparent group-data-[variant=underline]/tabs-list:data-[state=active]:border-b-ink-gray-8 ",


        // "focus-visible:border-ring focus-visible:ring-ring/50 focus-visible:outline-ring focus-visible:ring-[3px] focus-visible:outline-1 group-data-[variant=default]/tabs-list:data-[state=active]:shadow-sm group-data-[variant=line]/tabs-list:data-[state=active]:shadow-none",
        // "group-data-[variant=line]/tabs-list:bg-transparent group-data-[variant=line]/tabs-list:data-[state=active]:bg-transparent",
        // "data-[state=active]:bg-background data-[state=active]:text-foreground",
        // "after:bg-foreground after:absolute after:opacity-0 after:transition-opacity group-data-[orientation=horizontal]/tabs:after:inset-x-0 group-data-[orientation=horizontal]/tabs:after:bottom-[-5px] group-data-[orientation=horizontal]/tabs:after:h-0.5 group-data-[orientation=vertical]/tabs:after:inset-y-0 group-data-[orientation=vertical]/tabs:after:-right-1 group-data-[orientation=vertical]/tabs:after:w-0.5 group-data-[variant=line]/tabs-list:data-[state=active]:after:opacity-100",
        className
      )}
      {...props}
    />
  )
}

function TabsContent({
  className,
  ...props
}: React.ComponentProps<typeof TabsPrimitive.Content>) {
  return (
    <TabsPrimitive.Content
      data-slot="tabs-content"
      className={cn("flex-1 outline-none", className)}
      {...props}
    />
  )
}

export { Tabs, TabsList, TabsTrigger, TabsContent, tabsListVariants }
