import { Toaster as Sonner, type ToasterProps } from "sonner"
import { CircleCheckIcon, InfoIcon, TriangleAlertIcon, OctagonXIcon, Loader2Icon } from "lucide-react"
import { useTheme } from "./theme-provider"

const themeMap = {
    "Automatic": "system",
    "Dark": "dark",
    "Light": "light",
}

const Toaster = ({ ...props }: ToasterProps) => {
    const { theme = "Automatic" } = useTheme()

    return (
        <Sonner
            theme={themeMap[theme as keyof typeof themeMap] as ToasterProps["theme"]}
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
