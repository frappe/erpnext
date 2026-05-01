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
        const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)")

        const applySystemTheme = () => {
            root.classList.remove("light", "dark")
            root.classList.add(mediaQuery.matches ? "dark" : "light")
        }

        if (theme !== "Automatic") {
            root.classList.remove("light", "dark")
            root.classList.add(theme.toLowerCase())
            return () => { }
        }

        applySystemTheme()
        mediaQuery.addEventListener("change", applySystemTheme)

        return () => {
            mediaQuery.removeEventListener("change", applySystemTheme)
        }
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