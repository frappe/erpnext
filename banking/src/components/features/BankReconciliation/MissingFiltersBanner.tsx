import { Paragraph } from "@/components/ui/typography"
import { cn } from "@/lib/utils"
import { ReactNode } from "react"


export const MissingFiltersBanner = ({ text, className }: { text: ReactNode, className?: string }) => {
    return <div className={cn("min-h-[50vh] flex items-center justify-center", className)}>
        <Paragraph>{text}</Paragraph>
    </div>
}