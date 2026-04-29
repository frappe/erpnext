import { Button } from '@/components/ui/button'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import _ from '@/lib/translate'
import { FilterIcon } from 'lucide-react'
import { bankRecMatchFilters } from './bankRecAtoms'
import { useAtom } from 'jotai'
import { Switch } from '@/components/ui/switch'
import { Label } from '@/components/ui/label'
import { Separator } from '@/components/ui/separator'
import { useFrappeGetCall } from 'frappe-react-sdk'
import { scrub } from '@/lib/frappe'
import { useMemo } from 'react'

const MatchFilters = () => {
    return (
        <Popover>
            <Tooltip>
                <PopoverTrigger asChild>
                    <TooltipTrigger asChild>
                        <Button size='md' isIconButton variant='outline' aria-label={_("Configure match filters for vouchers")}>
                            <FilterIcon />
                        </Button>
                    </TooltipTrigger>
                </PopoverTrigger>
                <TooltipContent>
                    {_("Configure match filters for vouchers")}
                </TooltipContent>
            </Tooltip>
            <PopoverContent>
                <div className="flex flex-col gap-4">
                    <ToggleSwitch label={_("Show Only Exact Amount")} id="exact_match" />
                    <Separator />
                    <MatchFiltersContent />
                    <ToggleSwitch label={_("Bank Transaction")} id="bank_transaction" />
                </div>
            </PopoverContent>
        </Popover>
    )
}

const MatchFiltersContent = () => {

    const { data } = useFrappeGetCall<{ message: string[] }>("erpnext.accounts.doctype.bank_transaction.bank_transaction.get_doctypes_for_bank_reconciliation", undefined,
        "bank_rec_doctypes", {
        revalidateOnFocus: false,
        revalidateIfStale: false,
        revalidateOnReconnect: false,
    }
    )

    const doctypes = useMemo(() => {
        const STANDARD_DOCTYPES = ["Payment Entry", "Journal Entry", "Purchase Invoice", "Sales Invoice"]
        if (data) {
            return data.message.map(doctype => ({
                label: doctype,
                id: scrub(doctype),
            }))

        } else {
            return STANDARD_DOCTYPES.map(doctype => ({
                label: doctype,
                id: scrub(doctype),
            }))
        }
    }, [data])

    return (
        <div className="flex flex-col gap-4">
            {doctypes.map((doctype) => (
                <ToggleSwitch key={doctype.id} label={doctype.label} id={doctype.id} />
            ))}
        </div>
    )
}

const ToggleSwitch = ({ label, id }: { label: string, id: string }) => {

    const [matchFilters, setMatchFilters] = useAtom(bankRecMatchFilters)

    return <div className="flex items-center space-x-2">
        <Switch id={id} checked={matchFilters.includes(id)} onCheckedChange={(checked) => {
            if (checked) {
                setMatchFilters([...matchFilters, id])
            } else {
                setMatchFilters(matchFilters.filter(filter => filter !== id))
            }
        }} />
        <Label htmlFor={id}>{label}</Label>
    </div>
}

export default MatchFilters