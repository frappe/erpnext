import { useAtomValue, useSetAtom } from "jotai"
import { bankRecClosingBalanceAtom, bankRecDateAtom, SelectedBank, selectedBankAccountAtom } from "./bankRecAtoms"
import { FrappeConfig, FrappeContext, useFrappeGetDocCount, useFrappeGetDocList, useFrappePostCall, useSWRConfig } from "frappe-react-sdk"
import { BankTransaction } from "@/types/Accounts/BankTransaction"
import { Progress } from "@/components/ui/progress"
import { useGetAccountClosingBalance, useGetAccountClosingBalanceAsPerStatement, useGetAccountOpeningBalance, useGetUnreconciledTransactions } from "./utils"
import { flt, formatCurrency } from "@/lib/numbers"
import { Skeleton } from "@/components/ui/skeleton"
import { StatContainer, StatLabel, StatValue } from "@/components/ui/stats"
import { Edit, Info, Trash2 } from "lucide-react"
import { H4, Paragraph } from "@/components/ui/typography"
import { HoverCard, HoverCardContent, HoverCardTrigger } from "@/components/ui/hover-card"
import { getCompanyCurrency } from "@/lib/company"
import _ from "@/lib/translate"
import { Dialog, DialogClose, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import { formatDate } from "@/lib/date"
import { Form } from "@/components/ui/form"
import { CurrencyFormField } from "@/components/ui/form-elements"
import { useForm } from "react-hook-form"
import { Button } from "@/components/ui/button"
import { useContext, useState } from "react"
import { Separator } from "@/components/ui/separator"
import { MintBankStatementBalance } from "@/types/Mint/MintBankStatementBalance"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { toast } from "sonner"
import ErrorBanner from "@/components/ui/error-banner"

const BankBalance = () => {

    const bankAccount = useAtomValue(selectedBankAccountAtom)

    if (!bankAccount) {
        return null
    }
    return (
        <div className="flex justify-between">
            <div className="w-[80%] flex justify-between gap-2 pr-8 border-r-border border-r">
                <OpeningBalance />
                <ClosingBalance />
                <ClosingBalanceAsPerStatement />
                <Difference />
            </div>

            <ReconcileProgress />
        </div>
    )
}

const OpeningBalance = () => {
    const bankAccount = useAtomValue(selectedBankAccountAtom)
    const { data, isLoading } = useGetAccountOpeningBalance()

    return <StatContainer className="min-w-48">
        <StatLabel>{_("Opening Balance")}</StatLabel>
        {isLoading ? <Skeleton className="w-[150px] h-9" /> : <StatValue className="font-mono">{formatCurrency(flt(data?.message, 2), bankAccount?.account_currency ?? getCompanyCurrency(bankAccount?.company ?? ''))}</StatValue>}
    </StatContainer>
}

const ClosingBalance = () => {
    const bankAccount = useAtomValue(selectedBankAccountAtom)
    const { data, isLoading } = useGetAccountClosingBalance()

    return (
        <StatContainer className="min-w-48">
            <div className="flex items-start gap-1">
                <StatLabel>
                    {_("Closing Balance as per system")}
                </StatLabel>
                <HoverCard openDelay={100}>
                    <HoverCardTrigger>
                        <Info size='14px' className="text-secondary-foreground/80" />
                    </HoverCardTrigger>
                    <HoverCardContent className="w-96" align="start" side="right">
                        <H4 className="text-base">{_("Closing balance as per system")}</H4>
                        <Paragraph className="mt-2 text-sm">
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

            </div>
            {isLoading ? <Skeleton className="w-[150px] h-9" /> : <StatValue className="font-mono">{formatCurrency(flt(data?.message, 2), bankAccount?.account_currency ?? getCompanyCurrency(bankAccount?.company ?? ''))}</StatValue>}
        </StatContainer>
    )
}

const Difference = () => {
    const bankAccount = useAtomValue(selectedBankAccountAtom)

    const { data, isLoading } = useGetAccountClosingBalance()

    const value = useAtomValue(bankRecClosingBalanceAtom(bankAccount?.name ?? ''))

    const difference = flt(value.value - (data?.message ?? 0))

    const isError = difference !== 0

    return <StatContainer className="w-fit text-right sm:min-w-56">
        <StatLabel className="text-right">{_("Difference")}</StatLabel>
        {isLoading ? <Skeleton className="w-[150px] h-9" /> : <StatValue className={isError ? 'text-destructive font-mono' : 'font-mono'}>
            {formatCurrency(difference,
                bankAccount?.account_currency ?? getCompanyCurrency(bankAccount?.company ?? ''))
            }</StatValue>}
    </StatContainer>
}

const ReconcileProgress = () => {

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

    return <div className="w-[18%] flex flex-col gap-1 items-end">
        <div>
            <span className="text-right font-medium text-sm">{_("Your Progress")}: {reconciledCount} / {totalCount} {_("reconciled")}</span>
        </div>
        <div className="w-full">
            <Progress value={progress} max={100} />
        </div>
    </div>
}

const ClosingBalanceAsPerStatement = () => {

    const bankAccount = useAtomValue(selectedBankAccountAtom)
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

    const [isOpen, setIsOpen] = useState(false)


    return <StatContainer className="min-w-48">
        <StatLabel>{_("Closing Balance as per statement")}</StatLabel>
        <div className="flex flex-col gap-2 items-start">
            <Dialog open={isOpen} onOpenChange={setIsOpen}>
                <DialogTrigger>
                    <Tooltip>
                        <TooltipTrigger asChild>
                            <div className="flex items-center gap-4 underline cursor-pointer underline-offset-6">
                                {isLoading ? <Skeleton className="w-[150px] h-9" /> : <StatValue className="font-mono">{formatCurrency(flt(data?.message?.balance, 2), bankAccount?.account_currency ?? getCompanyCurrency(bankAccount?.company ?? ''))}</StatValue>}
                                <Edit className="w-4 h-4" />
                            </div>
                        </TooltipTrigger>
                        <TooltipContent>
                            {_("Click to set the closing balance as per statement")}
                        </TooltipContent>
                    </Tooltip>
                </DialogTrigger>
                <DialogContent>
                    <ClosingBalanceForm
                        defaultBalance={data?.message?.balance ?? 0}
                        date={dates.toDate}
                        bankAccount={bankAccount}
                        onClose={() => setIsOpen(false)}
                    />


                </DialogContent>
            </Dialog>
            {!isDateSame && data?.message.date && <span className="text-xs font-medium text-destructive">{_("As of {0}", [formatDate(data?.message?.date ?? '', 'Do MMM YYYY')])}</span>}
        </div>
    </StatContainer>

}

const ClosingBalanceForm = ({ defaultBalance, date, bankAccount, onClose }: { defaultBalance: number, date: string, bankAccount: SelectedBank | null, onClose: VoidFunction }) => {

    const { mutate } = useSWRConfig()

    const form = useForm<{ balance: number }>({
        defaultValues: {
            balance: defaultBalance
        }
    })

    const setValue = useSetAtom(bankRecClosingBalanceAtom(bankAccount?.name ?? ''))

    const { call, loading, error } = useFrappePostCall("mint.apis.bank_account.set_closing_balance_as_per_statement")

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
            {error && <ErrorBanner error={error} />}
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
                    <Button variant={'outline'} disabled={loading}>{_("Cancel")}</Button>
                </DialogClose>
                <Button type='submit' disabled={loading}>{_("Save")}</Button>
            </DialogFooter>

            <ClosingBalancesList bankAccount={bankAccount} date={date} />
        </form>
    </Form>
}

const ClosingBalancesList = ({ bankAccount, date }: { bankAccount: SelectedBank | null, date: string }) => {

    const { data, mutate } = useFrappeGetDocList<MintBankStatementBalance>("Mint Bank Statement Balance", {
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
        toast.promise(db.deleteDoc("Mint Bank Statement Balance", name).then(() => {
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
        <p className="text-sm text-center">{_("Balances as per bank statement before {0}", [formatDate(date, 'Do MMM YYYY')])}</p>
        <Table>
            <TableHeader>
                <TableRow>
                    <TableHead>{_("Date")}</TableHead>
                    <TableHead className="text-right">{_("Balance")}</TableHead>
                    <TableHead></TableHead>
                </TableRow>
            </TableHeader>
            <TableBody>
                {data?.map((item) => (
                    <TableRow key={item.name}>
                        <TableCell>{formatDate(item.date, 'Do MMM YYYY')}</TableCell>
                        <TableCell className="text-right">{formatCurrency(flt(item.balance, 2), bankAccount?.account_currency ?? getCompanyCurrency(bankAccount?.company ?? ''))}</TableCell>
                        <TableCell className="text-right">
                            <Button
                                title={_("Delete")}
                                type='button' size='icon' className="h-fit w-fit p-0 hover:bg-transparent active:bg-transparent hover:text-destructive" variant='ghost' onClick={() => onDelete(item.name)}>
                                <Trash2 />
                            </Button>
                        </TableCell>
                    </TableRow>
                ))}
            </TableBody>
        </Table>
    </div>

}

export default BankBalance