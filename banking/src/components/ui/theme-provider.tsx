import { useFrappePostCall } from "frappe-react-sdk"
import { createContext, useContext, useEffect, useState } from "react"

type Theme = "Dark" | "Light" | "Automatic"

type ThemeProviderProps = {
    children: React.ReactNode
    defaultTheme?: Theme
}

type ThemeProviderState = {
    theme: Theme
    setTheme: (theme: Theme) => void
}

const initialState: ThemeProviderState = {
    theme: "Light",
    setTheme: () => null,
}

const ThemeProviderContext = createContext<ThemeProviderState>(initialState)

export function ThemeProvider({
    children,
    defaultTheme = "Light",
    ...props
}: ThemeProviderProps) {
    const [theme, setTheme] = useState<Theme>(defaultTheme)

    const { call: switchTheme } = useFrappePostCall('frappe.core.doctype.user.user.switch_theme')

    useEffect(() => {
        const root = window.document.documentElement

        root.classList.remove("light", "dark")

        if (theme === "Automatic") {
            const systemTheme = window.matchMedia("(prefers-color-scheme: dark)")
                .matches
                ? "dark"
                : "light"

            root.classList.add(systemTheme)
            return
        }

        root.classList.add(theme.toLowerCase())
    }, [theme])

    const value = {
        theme,
        setTheme: (theme: Theme) => {
            switchTheme({
                theme: theme,
            }).then(() => {
                setTheme(theme)
            })
            setTheme(theme)
        },
    }

    return (
        <ThemeProviderContext.Provider {...props} value={value}>
            {children}
        </ThemeProviderContext.Provider>
    )
}

export const useTheme = () => {
    const context = useContext(ThemeProviderContext)

    if (context === undefined)
        throw new Error("useTheme must be used within a ThemeProvider")

    return context
}