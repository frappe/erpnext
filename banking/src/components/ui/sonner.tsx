"use client"

import { useTheme } from "next-themes"
import { Toaster as Sonner, type ToasterProps } from "sonner"
import { CircleCheckIcon, InfoIcon, TriangleAlertIcon, OctagonXIcon, Loader2Icon } from "lucide-react"

const Toaster = ({ ...props }: ToasterProps) => {
    const { theme = "system" } = useTheme()

    return (
        <Sonner
            theme={theme as ToasterProps["theme"]}
            className="toaster group"
            icons={{
                success: (
                    <CircleCheckIcon className="size-4" />
                ),
                info: (
                    <InfoIcon className="size-4" />
                ),
                warning: (
                    <TriangleAlertIcon className="size-4" />
                ),
                error: (
                    <OctagonXIcon className="size-4" />
                ),
                loading: (
                    <Loader2Icon className="size-4 animate-spin" />
                ),
            }}
            style={
                {
                    "--normal-bg": "var(--surface-gray-1)",
                    "--normal-text": "var(--text-ink-gray-8)",
                    "--normal-border": "var(--outline-gray-1)",
                    "--border-radius": "var(--radius)",
                } as React.CSSProperties
            }
            toastOptions={{
                classNames: {
                    toast: "cn-toast",
                },
            }}
            {...props}
        />
    )
}

export { Toaster }
