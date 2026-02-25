import { Button } from '@/components/ui/button'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import _ from '@/lib/translate'
import { Settings } from 'lucide-react'
import { bankRecMatchFilters } from './bankRecAtoms'
import { useAtom } from 'jotai'
import { Switch } from '@/components/ui/switch'
import { Label } from '@/components/ui/label'
import { Separator } from '@/components/ui/separator'

const MatchFilters = () => {
    return (
        <Popover>
            <Tooltip>
                <PopoverTrigger asChild>
                    <TooltipTrigger asChild>
                        <Button size='sm' variant='outline' aria-label={_("Configure match filters for vouchers")}>
                            <Settings />
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
                    <ToggleSwitch label={_("Payment Entry")} id="payment_entry" />
                    <ToggleSwitch label={_("Journal Entry")} id="journal_entry" />
                    <ToggleSwitch label={_("Purchase Invoice")} id="purchase_invoice" />
                    <ToggleSwitch label={_("Sales Invoice")} id="sales_invoice" />
                    <ToggleSwitch label={_("Expense Claim")} id="expense_claim" />
                    <ToggleSwitch label={_("Bank Transaction")} id="bank_transaction" />
                </div>
            </PopoverContent>
        </Popover>
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