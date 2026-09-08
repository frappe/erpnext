import { useAtomValue, useSetAtom } from "jotai"
import { bankRecClosingBalanceAtom, bankRecDateAtom, SelectedBank, selectedBankAccountAtom } from "./bankRecAtoms"
import { FrappeConfig, FrappeContext, useFrappeGetDocCount, useFrappeGetDocList, useFrappePostCall, useSWRConfig } from "frappe-react-sdk"
import { BankTransaction } from "@/types/Accounts/BankTransaction"
import { Progress } from "@/components/ui/progress"
import { useGetAccountClosingBalance, useGetAccountClosingBalanceAsPerStatement, useGetAccountOpeningBalance, useGetUnreconciledTransactions } from "./utils"
import { flt, formatCurrency } from "@/lib/numbers"
import { Skeleton } from "@/components/ui/skeleton"
import { Edit, Info, Trash2 } from "lucide-react"
import { H4, Paragraph } from "@/components/ui/typography"
import { HoverCard, HoverCardContent, HoverCardTrigger } from "@/components/ui/hover-card"
import { getCompanyCurrency } from "@/lib/company"
import _ from "@/lib/translate"
import { cn } from "@/lib/utils"
import { Dialog, DialogClose, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import { formatDate } from "@/lib/date"
import { Form } from "@/components/ui/form"
import { CurrencyFormField } from "@/components/ui/form-elements"
import { useForm } from "react-hook-form"
import { Button } from "@/components/ui/button"
import { useContext, useState } from "react"
import { Separator } from "@/components/ui/separator"
import { BankAccountBalance } from "@/types/Accounts/BankAccountBalance"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { toast } from "sonner"
import ErrorBanner from "@/components/ui/error-banner"

const useBankCurrency = () => {
    const bankAccount = useAtomValue(selectedBankAccountAtom)
    return bankAccount?.account_currency ?? getCompanyCurrency(bankAccount?.company ?? '')
}

/**
 * One line of the balance summary - label on the left, figure right-aligned.
 *
 * `items-baseline` keeps the figure on the label's FIRST line, so a row carrying a `subLabel`
 * (the statement row's "As of <date>" note) doesn't centre its value against both lines.
 */
const BalanceRow = ({ label, info, subLabel, emphasis, children }: {
    label: React.ReactNode
    info?: React.ReactNode
    subLabel?: React.ReactNode
    emphasis?: boolean
    children: React.ReactNode
}) => (
    <div className="flex items-baseline justify-between gap-3">
        <span className="flex min-w-0 flex-col gap-1.5">
            <span className={cn("flex items-center gap-1 whitespace-nowrap text-xs text-ink-gray-6",
                emphasis && "font-medium text-ink-gray-7")}>
                {label}
                {info}
            </span>
            {subLabel}
        </span>
        <div className="flex flex-col items-end">{children}</div>
    </div>
)

/**
 * Type styles for a figure. Shared so an interactive figure can put them on the <button>
 * ITSELF rather than on a nested span: Tailwind's preflight sets `font: inherit` on buttons,
 * which resets line-height too, so a button wrapping a `text-sm` span gets a taller strut than
 * the span and the row grows - visible as extra space above a baseline-aligned row.
 */
const BALANCE_VALUE_CLASSES = "font-numeric text-sm tabular-nums text-ink-gray-8"

const BalanceValue = ({ children, emphasis, tone, className }: { children: React.ReactNode, emphasis?: boolean, tone?: 'red', className?: string }) => (
    <span className={cn(BALANCE_VALUE_CLASSES,
        emphasis && "font-semibold",
        tone === 'red' && "text-ink-red-3",
        className)}>
        {children}
    </span>
)

const BalanceSkeleton = () => <Skeleton className="h-4 w-24 rounded-sm" />

/**
 * Balances and progress for the selected bank account, laid out like the totals block of an
 * invoice. This sits beside the bank picker rather than in a row of its own (saves vertical
 * space) and outside the picker's horizontal scroll area, so the figures being reconciled
 * against can never scroll out of view.
 */
const BankAccountBalancePanel = () => {

    const bankAccount = useAtomValue(selectedBankAccountAtom)

    if (!bankAccount) {
        return null
    }

    return (
        <div className="flex w-72 shrink-0 flex-col justify-center gap-2.5 border-s border-outline-gray-2 ps-4">
            {/* Names the account these figures belong to - the picker scrolls, so the
                highlighted card can't be relied on as the referent. */}
            <span
                className="truncate text-xs font-medium text-ink-gray-7"
                title={bankAccount.account_name}>
                {bankAccount.account_name}
            </span>
            <OpeningBalanceRow />
            <SystemClosingBalanceRow />
            <StatementClosingBalanceRow />
            <Separator />
            <DifferenceRow />
            <ReconciledRow />
        </div>
    )
}

const OpeningBalanceRow = () => {
    const currency = useBankCurrency()
    const { data, isLoading } = useGetAccountOpeningBalance()

    return <BalanceRow label={_("Opening Balance")}>
        {isLoading ? <BalanceSkeleton /> : <BalanceValue>{formatCurrency(flt(data?.message, 2), currency)}</BalanceValue>}
    </BalanceRow>
}

const SystemClosingBalanceRow = () => {
    const currency = useBankCurrency()
    const { data, isLoading } = useGetAccountClosingBalance()

    return (
        <BalanceRow
            label={_("Closing (system)")}
            info={
                <HoverCard openDelay={100}>
                    <HoverCardTrigger>
                        <Info className="size-3.5 text-ink-gray-6" />
                    </HoverCardTrigger>
                    <HoverCardContent className="w-96" align="start" side="right">
                        <H4 className="text-base">{_("Closing balance as per system")}</H4>
                        <Paragraph className="mt-2 text-p-sm">
                            {_("This is what the system expects the closing balance to be in your bank statement.")}
                            <br />
                            {_("It takes into account all the transactions that have been posted and subtracts the transactions that have not cleared yet.")}
                            <br />
                            {_("If your bank statement shows a different closing balance, it is because all transactions have not reconciled yet.")}
                            <br /><br />
                            For more information, click on the <strong>Bank Reconciliation Statement</strong> tab below.
                        </Paragraph>
                    </HoverCardContent>
                </HoverCard>
            }
        >
            {isLoading ? <BalanceSkeleton /> : <BalanceValue>{formatCurrency(flt(data?.message, 2), currency)}</BalanceValue>}
        </BalanceRow>
    )
}

const StatementClosingBalanceRow = () => {

    const bankAccount = useAtomValue(selectedBankAccountAtom)
    const currency = useBankCurrency()
    const dates = useAtomValue(bankRecDateAtom)
    const setValue = useSetAtom(bankRecClosingBalanceAtom(bankAccount?.name ?? ''))

    const { data, isLoading } = useGetAccountClosingBalanceAsPerStatement({
        onSuccess: (data) => {
            if (data?.message && data?.message?.balance) {
                setValue({
                    value: data?.message?.balance,
                    stringValue: data?.message?.balance.toString()
                })
            }
        }
    })

    const isDateSame = data?.message?.date === dates.toDate

    // The server uses the returned date to distinguish an unset balance from a saved zero.
    const hasBalance = Boolean(data?.message?.date)

    const [isOpen, setIsOpen] = useState(false)

    const tooltip = hasBalance
        ? _("Click to change the closing balance as per statement")
        : _("Click to set the closing balance as per statement")

    return (
        <BalanceRow
            label={_("Closing (statement)")}
            // The pencil sits beside the label, mirroring the info icon on the row above, so
            // the figure stays a plain right-aligned number in line with every other row.
            info={
                <Tooltip>
                    <TooltipTrigger asChild>
                        {/* `p-0`: Tailwind's preflight gives buttons `appearance: button` but
                            doesn't reset padding, so a bare button picks up the UA's ~1px 6px
                            and knocks this row out of step with its neighbours. */}
                        <button
                            type='button'
                            aria-label={tooltip}
                            onClick={() => setIsOpen(true)}
                            className="cursor-pointer p-0 text-ink-gray-5 transition-colors hover:text-ink-gray-7">
                            <Edit className="size-3.5" />
                        </button>
                    </TooltipTrigger>
                    <TooltipContent>{tooltip}</TooltipContent>
                </Tooltip>
            }
            subLabel={!isDateSame && data?.message.date
                ? <span className="whitespace-nowrap text-2xs font-medium text-ink-red-3">
                    {_("As of {0}", [formatDate(data?.message?.date ?? '', 'Do MMM YYYY')])}
                </span>
                : undefined}
        >
            {/* Deliberately NOT a flex container: a flex box's baseline doesn't resolve to its
                text, so the row's `items-baseline` couldn't line this up with the label. As a
                plain inline button its baseline is the figure's own, like every other row.
                "Set" gets the same treatment as a figure - it stands in for one. */}
            {isLoading
                ? <BalanceSkeleton />
                : <Tooltip>
                    <TooltipTrigger asChild>
                        {/* The figure styles live on the button itself - see
                            BALANCE_VALUE_CLASSES. `p-0` because preflight leaves the UA's
                            button padding in place. */}
                        <button
                            type='button'
                            aria-label={tooltip}
                            onClick={() => setIsOpen(true)}
                            className={cn(BALANCE_VALUE_CLASSES,
                                "cursor-pointer p-0 underline decoration-outline-gray-5 decoration-dashed underline-offset-4",
                                "transition-colors hover:decoration-ink-gray-8")}>
                            {hasBalance ? formatCurrency(flt(data?.message?.balance, 2), currency) : _("Set")}
                        </button>
                    </TooltipTrigger>
                    <TooltipContent>{tooltip}</TooltipContent>
                </Tooltip>}

            <Dialog open={isOpen} onOpenChange={setIsOpen}>
                <DialogContent className="min-w-xl">
                    <ClosingBalanceForm
                        defaultBalance={data?.message?.balance ?? 0}
                        date={dates.toDate}
                        bankAccount={bankAccount}
                        onClose={() => setIsOpen(false)}
                    />
                </DialogContent>
            </Dialog>
        </BalanceRow>
    )
}

const DifferenceRow = () => {
    const bankAccount = useAtomValue(selectedBankAccountAtom)
    const currency = useBankCurrency()

    const { data, isLoading } = useGetAccountClosingBalance()

    const value = useAtomValue(bankRecClosingBalanceAtom(bankAccount?.name ?? ''))

    const difference = flt(value.value - (data?.message ?? 0))

    const isError = difference !== 0

    return <BalanceRow label={_("Difference")} emphasis>
        {isLoading
            ? <BalanceSkeleton />
            : <BalanceValue emphasis tone={isError ? 'red' : undefined}>{formatCurrency(difference, currency)}</BalanceValue>}
    </BalanceRow>
}

/** Reconciliation progress through the selected date range: a count plus a slim bar. */
const ReconciledRow = () => {

    const bankAccount = useAtomValue(selectedBankAccountAtom)

    const dates = useAtomValue(bankRecDateAtom)

    const { data: totalCount } = useFrappeGetDocCount<BankTransaction>('Bank Transaction', [
        ["bank_account", "=", bankAccount?.name ?? ''],
        ['docstatus', '=', 1],
        ['date', '<=', dates?.toDate],
        ['date', '>=', dates?.fromDate]
    ], false, undefined, {
        revalidateOnFocus: false
    })

    const { data: unreconciledTransactions, } = useGetUnreconciledTransactions()

    const reconciledCount = (totalCount ?? 0) - (unreconciledTransactions?.message?.length ?? 0)

    const progress = (totalCount ? reconciledCount / totalCount : 0) * 100

    return <div className="flex flex-col gap-1.5">
        <BalanceRow label={_("Reconciled")}>
            <BalanceValue>{reconciledCount} / {totalCount ?? 0}</BalanceValue>
        </BalanceRow>
        <Progress value={progress} max={100} size="sm" />
    </div>
}

const ClosingBalanceForm = ({ defaultBalance, date, bankAccount, onClose }: { defaultBalance: number, date: string, bankAccount: SelectedBank | null, onClose: VoidFunction }) => {

    const { mutate } = useSWRConfig()

    const form = useForm<{ balance: number }>({
        defaultValues: {
            balance: defaultBalance
        }
    })

    const setValue = useSetAtom(bankRecClosingBalanceAtom(bankAccount?.name ?? ''))

    const { call, loading, error } = useFrappePostCall("erpnext.accounts.doctype.bank_account.bank_account.set_closing_balance_as_per_statement")

    const onSubmit = (data: { balance: number }) => {
        if (data.balance) {
            call({
                bank_account: bankAccount?.name ?? '',
                date: date,
                balance: data.balance
            })
                .then(() => {
                    // Mutate the closing balance as per statement
                    mutate(`bank-reconciliation-account-closing-balance-as-per-statement-${bankAccount?.name}-${date}`)
                    setValue({
                        value: data.balance,
                        stringValue: data.balance.toString()
                    })
                    toast.success(_("Closing balance set."))
                    onClose()


                })
        } else {
            toast.error(_("Closing balance is required."))
        }
    }

    const currency = bankAccount?.account_currency ?? getCompanyCurrency(bankAccount?.company ?? '')


    return <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)}>
            <DialogHeader>
                <DialogTitle>{_("Set closing balance as per bank statement")}</DialogTitle>
                <DialogDescription>
                    {_("Enter the closing balance you see in your bank statement for {0} as of the {1}", [bankAccount?.account_name ?? bankAccount?.name ?? '', formatDate(date, 'Do MMM YYYY')])}
                </DialogDescription>
            </DialogHeader>
            {error && <div className="py-2"><ErrorBanner error={error} /></div>}
            <div className="py-4">
                <CurrencyFormField
                    name="balance"
                    label={_("Closing balance on bank statement as of {0}", [formatDate(date, 'Do MMM YYYY')])}
                    isRequired
                    currency={currency}
                />
            </div>

            <DialogFooter>
                <DialogClose asChild>
                    <Button variant={'outline'} size='md' disabled={loading}>{_("Cancel")}</Button>
                </DialogClose>
                <Button type='submit' size='md' disabled={loading}>{_("Save")}</Button>
            </DialogFooter>

            <ClosingBalancesList bankAccount={bankAccount} date={date} />
        </form>
    </Form>
}

const ClosingBalancesList = ({ bankAccount, date }: { bankAccount: SelectedBank | null, date: string }) => {

    const { data, mutate } = useFrappeGetDocList<BankAccountBalance>("Bank Account Balance", {
        filters: [["bank_account", "=", bankAccount?.name ?? ''], ["date", "<=", date]],
        orderBy: {
            field: "date",
            order: "desc"
        },
        fields: ["date", "balance", "name"],
        limit: 10
    })

    const { db } = useContext(FrappeContext) as FrappeConfig

    const onDelete = (name: string) => {
        toast.promise(db.deleteDoc("Bank Account Balance", name).then(() => {
            mutate()
        }), {
            loading: _("Deleting closing balance..."),
            success: _("Closing balance deleted."),
            error: _("Failed to delete closing balance.")
        })
    }

    if (data?.length === 0) {
        return null
    }

    return <div>
        <Separator className="my-8" />
        <p className="text-p-sm text-center pb-2">{_("Balances as per bank statement before {0}", [formatDate(date, 'Do MMM YYYY')])}</p>
        <Table>
            <TableHeader>
                <TableRow>
                    <TableHead>{_("Date")}</TableHead>
                    <TableHead className="text-end">{_("Balance")}</TableHead>
                    <TableHead></TableHead>
                </TableRow>
            </TableHeader>
            <TableBody>
                {data?.map((item) => (
                    <TableRow key={item.name}>
                        <TableCell>{formatDate(item.date, 'Do MMM YYYY')}</TableCell>
                        <TableCell className="text-end">{formatCurrency(flt(item.balance, 2), bankAccount?.account_currency ?? getCompanyCurrency(bankAccount?.company ?? ''))}</TableCell>
                        <TableCell className="text-end">
                            <Button
                                title={_("Delete")}
                                type='button' isIconButton variant='ghost' onClick={() => onDelete(item.name)}>
                                <Trash2 />
                            </Button>
                        </TableCell>
                    </TableRow>
                ))}
            </TableBody>
        </Table>
    </div>

}

export default BankAccountBalancePanel
