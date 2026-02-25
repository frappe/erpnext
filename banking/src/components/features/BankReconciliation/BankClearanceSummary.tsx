import { useAtomValue } from "jotai"
import { MissingFiltersBanner } from "./MissingFiltersBanner"
import { bankRecDateAtom, SelectedBank, selectedBankAccountAtom } from "./bankRecAtoms"
import { useCurrentCompany } from "@/hooks/useCurrentCompany"
import { Paragraph } from "@/components/ui/typography"
import { useMemo, useState } from "react"
import { useFrappeGetCall, useFrappePostCall, useSWRConfig } from "frappe-react-sdk"
import { QueryReportReturnType } from "@/types/custom/Reports"
import { formatDate } from "@/lib/date"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { formatCurrency } from "@/lib/numbers"
import { getCompanyCurrency } from "@/lib/company"
import { slug } from "@/lib/frappe"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { AlertCircle, CheckCircle2, XCircle } from "lucide-react"
import ErrorBanner from "@/components/ui/error-banner"
import { Badge } from "@/components/ui/badge"
import _ from "@/lib/translate"
import { useCopyToClipboard } from "usehooks-ts"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Dialog, DialogClose, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Form } from "@/components/ui/form"
import { useForm } from "react-hook-form"
import { DateField } from "@/components/ui/form-elements"
import { TableVirtuoso } from "react-virtuoso"

const BankClearanceSummary = () => {
    const bankAccount = useAtomValue(selectedBankAccountAtom)
    const dates = useAtomValue(bankRecDateAtom)

    if (!bankAccount) {
        return <MissingFiltersBanner text={_("Please select a bank account to view the bank clearance summary.")} />
    }

    if (!dates) {
        return <MissingFiltersBanner text={_("Please select dates to view the bank clearance summary.")} />
    }

    return <BankClearanceSummaryView />
}
interface BankClearanceSummaryEntry {
    payment_document_type: string
    payment_entry: string
    posting_date: string,
    cheque_no?: string,
    amount: number,
    against: string,
    clearance_date: string,
}

const BankClearanceSummaryView = () => {

    const companyID = useCurrentCompany()
    const bankAccount = useAtomValue(selectedBankAccountAtom)
    const dates = useAtomValue(bankRecDateAtom)

    const filters = useMemo(() => {
        return JSON.stringify({
            account: bankAccount?.account,
            from_date: dates.fromDate,
            to_date: dates.toDate
        })
    }, [bankAccount, dates])

    const { data, error, mutate } = useFrappeGetCall<{ message: QueryReportReturnType<BankClearanceSummaryEntry> }>('frappe.desk.query_report.run', {
        report_name: 'Bank Clearance Summary',
        filters,
        ignore_prepared_report: 1,
        are_default_filters: false,
    }, `Report-Bank Clearance Summary-${filters}`, { keepPreviousData: true, revalidateOnFocus: false }, 'POST')

    const formattedFromDate = formatDate(dates.fromDate)
    const formattedToDate = formatDate(dates.toDate)

    const [, copyToClipboard] = useCopyToClipboard()

    const onCopy = (text: string) => {
        copyToClipboard(text)
            .then(() => {
                toast.success(_("Copied to clipboard"))
            })
    }

    return <div className="space-y-4 py-2">

        <div>
            <Paragraph className="text-sm">
                <span dangerouslySetInnerHTML={{
                    __html: _("Below is a list of all accounting entries posted against the bank account {0} between {1} and {2}.", [`<strong>${bankAccount?.account}</strong>`, `<strong>${formattedFromDate}</strong>`, `<strong>${formattedToDate}</strong>`])
                }} />
            </Paragraph>
        </div>

        {error && <ErrorBanner error={error} />}

        <TableVirtuoso
            data={data?.message.result}
            style={{ minHeight: 'calc(100vh - 200px)' }}
            fixedHeaderContent={() => (
                <TableRow>
                    <TableHead>{_("Document Type")}</TableHead>
                    <TableHead>{_("Payment Document")}</TableHead>
                    <TableHead>{_("Posting Date")}</TableHead>
                    <TableHead>{_("Cheque/Reference Number")}</TableHead>
                    <TableHead>{_("Clearance Date")}</TableHead>
                    <TableHead>{_("Against Account")}</TableHead>
                    <TableHead className="text-right">{_("Amount")}</TableHead>
                    <TableHead>{_("Status")}</TableHead>
                </TableRow>
            )}
            components={{
                Table: Table,
                TableBody: TableBody,
                TableRow: TableRow,
            }}
            itemContent={(_index, row) => (
                <>
                    <TableCell>{_(row.payment_document_type)}</TableCell>
                    <TableCell><a target="_blank" className="underline underline-offset-4" href={`/app/${slug(row.payment_document_type)}/${row.payment_entry}`}>{row.payment_entry}</a></TableCell>
                    <TableCell>{formatDate(row.posting_date)}</TableCell>
                    <TableCell title={row.cheque_no}>
                        <Tooltip delayDuration={500}>
                            <TooltipTrigger onClick={() => onCopy(row.cheque_no ?? "")}>
                                {row.cheque_no?.slice(0, 40)}{row.cheque_no?.length && row.cheque_no?.length > 40 ? "..." : ""}
                            </TooltipTrigger>
                            <TooltipContent align='start'>
                                {_("Copy to clipboard")}
                            </TooltipContent>
                        </Tooltip>
                    </TableCell>
                    <TableCell>{formatDate(row.clearance_date)}</TableCell>
                    <TableCell className="max-w-[250px] overflow-hidden text-ellipsis whitespace-nowrap" title={row.against}>{row.against}</TableCell>
                    <TableCell className="text-right">{formatCurrency(row.amount, bankAccount?.account_currency ?? getCompanyCurrency(companyID))}</TableCell>
                    <TableCell>
                        {row.clearance_date ? <Badge variant="outline" className="text-foreground px-1.5">
                            <CheckCircle2 width={16} height={16} className="text-green-600 dark:text-green-500" />
                            {_("Cleared")}</Badge> : <div className="flex items-center gap-2"><Badge variant="destructive" className="bg-destructive/10 text-destructive">
                                <XCircle className="-mt-0.5 text-destructive" />
                                {_("Not Cleared")}</Badge>
                            <SetClearanceDateButton voucher={row} bankAccount={bankAccount} companyID={companyID} mutate={mutate} />
                        </div>}
                    </TableCell>
                </>
            )}
        />



        {data && data.message.result.length === 0 &&
            <Alert variant='default'>
                <AlertCircle />
                <AlertTitle>No entries found</AlertTitle>
                <AlertDescription>
                    There are no accounting entries in the system for the selected account and dates.
                </AlertDescription>
            </Alert>
        }


    </div>
}

const SetClearanceDateButton = ({ voucher, bankAccount, companyID, mutate }: { voucher: BankClearanceSummaryEntry, bankAccount: SelectedBank | null, companyID: string, mutate: VoidFunction }) => {

    const [open, setOpen] = useState(false)

    const onClose = () => {
        setOpen(false)
        mutate()
    }

    return <Dialog open={open} onOpenChange={setOpen}>
        <DialogTrigger disabled={!bankAccount}>
            <Tooltip delayDuration={500}>
                <TooltipTrigger>
                    <Button variant='link' size="sm" className="px-0 text-destructive underline underline-offset-4">{_("Force Clear")}</Button>
                </TooltipTrigger>
                <TooltipContent align='start'>
                    {_("Set the clearance date for this voucher without reconciling with a bank transaction.")}
                </TooltipContent>
            </Tooltip>
        </DialogTrigger>
        <DialogContent className="min-w-2xl">
            {bankAccount && <ForceClearVoucherForm voucher={voucher} bankAccount={bankAccount} companyID={companyID} onClose={onClose} />}
        </DialogContent>
    </Dialog>
}

const ForceClearVoucherForm = ({ voucher, bankAccount, companyID, onClose }: { voucher: BankClearanceSummaryEntry, bankAccount: SelectedBank, companyID: string, onClose: () => void }) => {

    const { mutate } = useSWRConfig()

    const dates = useAtomValue(bankRecDateAtom)
    const form = useForm<{ clearance_date: string }>({
        defaultValues: {
            clearance_date: voucher.posting_date,
        }
    })

    const { call, loading, error } = useFrappePostCall('mint.apis.bank_clearance.update_clearance_date')

    const onSubmit = (data: { clearance_date: string }) => {
        call({
            payment_document: voucher.payment_document_type,
            payment_entry: voucher.payment_entry,
            account: bankAccount.account,
            clearance_date: data.clearance_date,
        })
            .then(() => {
                toast.success(_("Clearance date updated"))
                onClose()
                mutate(`bank-reconciliation-account-closing-balance-${bankAccount?.name}-${dates.toDate}`)
            })
    }

    return <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)}>

            <div className='flex flex-col gap-4'>

                <DialogHeader>
                    <DialogTitle>{_("Force Clear Voucher")}</DialogTitle>
                    <DialogDescription>
                        {_("Set the clearance date for this voucher without reconciling with a bank transaction.")}
                    </DialogDescription>
                </DialogHeader>
                {error && <ErrorBanner error={error} />}
                <div>
                    <Table>
                        <TableHeader>
                            <TableRow>
                                <TableHead>{_("Payment Document")}</TableHead>
                                <TableCell><a target="_blank" className="underline underline-offset-4"
                                    href={`/app/${slug(voucher.payment_document_type)}/${voucher.payment_entry}`}>{_(voucher.payment_document_type)} : {voucher.payment_entry}</a></TableCell>
                            </TableRow>
                            <TableRow>
                                <TableHead>{_("Posting Date")}</TableHead>
                                <TableCell>{formatDate(voucher.posting_date)}</TableCell>
                            </TableRow>
                            <TableRow>
                                <TableHead>{_("Cheque/Reference Number")}</TableHead>
                                <TableCell title={voucher.cheque_no}>{voucher.cheque_no?.slice(0, 40)}{voucher.cheque_no?.length && voucher.cheque_no?.length > 40 ? "..." : ""}</TableCell>
                            </TableRow>
                            <TableRow>
                                <TableHead>{_("Amount")}</TableHead>
                                <TableCell className="text-right">{formatCurrency(voucher.amount, bankAccount?.account_currency ?? getCompanyCurrency(companyID))}</TableCell>
                            </TableRow>
                            <TableRow>
                                <TableHead>{_("Against Account")}</TableHead>
                                <TableCell><a target="_blank" className="underline underline-offset-4" href={`/app/account/${voucher.against}`}>{voucher.against}</a></TableCell>
                            </TableRow>
                        </TableHeader>
                    </Table>
                </div>
                <DateField
                    name='clearance_date'
                    label={_("Clearance Date")}
                    isRequired
                    inputProps={{ autoFocus: true }}
                />

                <DialogFooter>
                    <DialogClose asChild>
                        <Button variant={'outline'} disabled={loading}>{_("Cancel")}</Button>
                    </DialogClose>
                    <Button type='submit' disabled={loading}>{_("Submit")}</Button>
                </DialogFooter>
            </div>
        </form>
    </Form>
}

export default BankClearanceSummary
