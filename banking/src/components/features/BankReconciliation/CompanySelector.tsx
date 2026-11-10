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
import { selectedBankAccountAtom } from "./bankRecAtoms"
import { useFrappeGetDocList } from "frappe-react-sdk"
import ErrorBanner from "@/components/ui/error-banner"

const CompanySelector = ({ onChange }: { onChange?: (company: string) => void }) => {
    const [open, setOpen] = useState(false)
    const [searchQuery, setSearchQuery] = useState("")

    const { data: companies, error } = useFrappeGetDocList("Company", {
        limit: 0,
        fields: ["name"],
    }, 'company_list', {
        revalidateOnFocus: false,
        revalidateOnReconnect: false,
    })

    const options = companies?.map((company: { name: string }) => company.name) || []

    const setSelectedCompany = useSetAtom(selectedCompanyAtom)
    const setSelectedBankAccount = useSetAtom(selectedBankAccountAtom)
    const selectedCompany = useCurrentCompany()

    const handleSelectCompany = (company: string) => {
        setSelectedCompany(company)
        setSearchQuery("")
        setOpen(false)
        // Only reset bank account if the company is changed
        if (selectedCompany !== company) {
            setSelectedBankAccount(null)
            onChange?.(company)
        }
    }

    if (error) {
        return <ErrorBanner error={error} />
    }

    return (<Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
            <Button
                variant="outline"
                type='button'
                role="combobox"
                size='md'
                aria-expanded={open}
                className="justify-between"
            >
                <div className="flex items-center gap-2">
                    <Building2 />
                    {selectedCompany}
                </div>
                <ChevronDown className="text-ink-gray-4" />
            </Button>
        </PopoverTrigger>
        <PopoverContent className="min-w-56 w-fit p-0">
            <Command value={selectedCompany}>
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
                                        "ms-auto",
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