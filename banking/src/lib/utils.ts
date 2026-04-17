import { clsx, type ClassValue } from "clsx"
import { extendTailwindMerge } from "tailwind-merge"

const twMerge = extendTailwindMerge({
  extend: {
    classGroups: {
      "font-size": [
        { text: ["p-base", "p-2xs", "p-xs", "p-sm", "p-lg", "p-xl", "p-2xl", "p-3xl"] }
      ]
    }
  }
})



export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
