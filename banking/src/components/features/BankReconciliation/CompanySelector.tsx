import { Button } from "@/components/ui/button"
import { selectedCompanyAtom, useCurrentCompany } from "@/hooks/useCurrentCompany"
import { useSetAtom } from "jotai"
import { Building2, Check, ChevronDown } from "lucide-react"
import { useState } from "react"
import {
    Command,
    CommandEmpty,
    CommandGroup,
    CommandInput,
    CommandItem,
    CommandList,
} from "@/components/ui/command"
import {
    Popover,
    PopoverContent,
    PopoverTrigger,
} from "@/components/ui/popover"
import { cn } from "@/lib/utils"
import _ from "@/lib/translate"

const CompanySelector = ({ onChange }: { onChange?: (company: string) => void }) => {
    const [open, setOpen] = useState(false)
    const [searchQuery, setSearchQuery] = useState("")

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const options = window.frappe?.boot?.docs?.filter((doc: Record<string, any>) => doc.doctype === ":Company").map((company: Record<string, any>) => company.name) || []

    const setSelectedCompany = useSetAtom(selectedCompanyAtom)
    const selectedCompany = useCurrentCompany()

    const handleSelectCompany = (company: string) => {
        setSelectedCompany(company)
        setSearchQuery("")
        setOpen(false)
        onChange?.(company)
    }

    return (<Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
            <Button
                variant="outline"
                role="combobox"
                aria-expanded={open}
                className="justify-between"
            >
                <div className="flex items-center gap-2">
                    <Building2 />
                    {selectedCompany}
                </div>
                <ChevronDown className="opacity-50" />
            </Button>
        </PopoverTrigger>
        <PopoverContent className="min-w-56 w-fit p-0">
            <Command>
                {options.length > 5 && <CommandInput placeholder={_("Search company...")} className="h-9" />}
                <CommandList>
                    <CommandEmpty>{_("No company found.")}</CommandEmpty>
                    <CommandGroup>
                        {options.map((option: string) => (
                            <CommandItem
                                key={option}
                                value={option}
                                onSelect={(currentValue) => {
                                    handleSelectCompany(currentValue)
                                }}
                            >
                                {option}
                                <Check
                                    className={cn(
                                        "ml-auto",
                                        searchQuery === option ? "opacity-100" : "opacity-0"
                                    )}
                                />
                            </CommandItem>
                        ))}
                    </CommandGroup>
                </CommandList>
            </Command>
        </PopoverContent>
    </Popover>)
}

export default CompanySelector