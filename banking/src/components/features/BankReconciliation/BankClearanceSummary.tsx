import { useAtomValue } from "jotai"
import { MissingFiltersBanner } from "./MissingFiltersBanner"
import { bankRecDateAtom, SelectedBank, selectedBankAccountAtom } from "./bankRecAtoms"
import { useCurrentCompany } from "@/hooks/useCurrentCompany"
import { Paragraph } from "@/components/ui/typography"
import type { ColumnDef } from "@tanstack/react-table"
import { useCallback, useMemo, useState } from "react"
import { useFrappeGetCall, useFrappePostCall, useSWRConfig } from "frappe-react-sdk"
import { QueryReportReturnType } from "@/types/custom/Reports"
import { formatDate } from "@/lib/date"
import { ListView, type ListViewColumnMeta } from "@/components/ui/list-view"
import { Table, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { formatCurrency } from "@/lib/numbers"
import { getCompanyCurrency } from "@/lib/company"
import { slug } from "@/lib/frappe"
import { CheckCircle2, ReceiptTextIcon, XCircle } from "lucide-react"
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
import { Empty, EmptyMedia, EmptyHeader, EmptyTitle, EmptyDescription } from "@/components/ui/empty"

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

    const onCopy = useCallback(
        (text: string) => {
            copyToClipboard(text).then(() => {
                toast.success(_("Copied to clipboard"))
            })
        },
        [copyToClipboard],
    )

    const accountCurrency = useMemo(
        () => bankAccount?.account_currency ?? getCompanyCurrency(companyID),
        [bankAccount?.account_currency, companyID],
    )

    const clearanceColumns = useMemo<ColumnDef<BankClearanceSummaryEntry, unknown>[]>(
        () => [
            {
                accessorKey: "payment_document_type",
                header: _("Document Type"),
                size: 140,
                cell: ({ row }) => _(row.original.payment_document_type),
            },
            {
                id: "payment_entry",
                header: _("Payment Document"),
                size: 160,
                meta: {
                    getTooltipText: (r) => {
                        const x = r as BankClearanceSummaryEntry
                        return [x.payment_document_type, x.payment_entry].filter(Boolean).join(" · ") || undefined
                    },
                } satisfies ListViewColumnMeta,
                cell: ({ row }) => (
                    <a
                        target="_blank"
                        rel="noreferrer"
                        className="text-ink-gray-8 block min-w-0 w-full underline underline-offset-4"
                        href={`/desk/${slug(row.original.payment_document_type)}/${row.original.payment_entry}`}
                    >
                        {row.original.payment_entry}
                    </a>
                ),
            },
            {
                accessorKey: "posting_date",
                header: _("Posting Date"),
                size: 118,
                meta: { tabularNums: true } satisfies ListViewColumnMeta,
                cell: ({ row }) => formatDate(row.original.posting_date),
            },
            {
                accessorKey: "cheque_no",
                header: _("Cheque/Reference Number"),
                size: 160,
                cell: ({ row }) => {
                    const ref = row.original.cheque_no ?? ""
                    return (
                        <Tooltip delayDuration={500}>
                            <TooltipTrigger asChild>
                                <button
                                    type="button"
                                    className="text-ink-gray-8 hover:underline min-w-0 w-full cursor-pointer truncate text-start underline-offset-4"
                                    onClick={() => onCopy(ref)}
                                >
                                    {ref}
                                </button>
                            </TooltipTrigger>
                            <TooltipContent>
                                {ref}
                            </TooltipContent>
                        </Tooltip>

                    )
                },
            },
            {
                accessorKey: "clearance_date",
                header: _("Clearance Date"),
                size: 118,
                meta: { tabularNums: true } satisfies ListViewColumnMeta,
                cell: ({ row }) => formatDate(row.original.clearance_date),
            },
            {
                accessorKey: "against",
                header: _("Against Account"),
                size: 250,
            },
            {
                accessorKey: "amount",
                header: _("Amount"),
                size: 150,
                meta: { align: "right" } satisfies ListViewColumnMeta,
                cell: ({ row }) => <span className="font-numeric">{formatCurrency(row.original.amount, accountCurrency)}</span>,
            },
            {
                id: "status",
                header: _("Status"),
                size: 200,
                meta: { truncate: false, truncateTooltip: false } satisfies ListViewColumnMeta,
                cell: ({ row }) => {
                    const r = row.original
                    return r.clearance_date ? (
                        <Badge theme="green">
                            <CheckCircle2 />
                            {_("Cleared")}
                        </Badge>
                    ) : (
                        <div className="flex min-w-0 flex-wrap items-center gap-2">
                            <Badge theme="red">
                                <XCircle />
                                {_("Not Cleared")}
                            </Badge>
                            <SetClearanceDateButton
                                voucher={r}
                                bankAccount={bankAccount}
                                companyID={companyID}
                                mutate={mutate}
                            />
                        </div>
                    )
                },
            },
        ],
        [accountCurrency, bankAccount, companyID, mutate, onCopy],
    )

    return <div className="space-y-4 py-2">

        <div>
            <Paragraph className="text-sm">
                <span dangerouslySetInnerHTML={{
                    __html: _("Below is a list of all accounting entries posted against the bank account {0} between {1} and {2}.", [`<strong>${bankAccount?.account}</strong>`, `<strong>${formattedFromDate}</strong>`, `<strong>${formattedToDate}</strong>`])
                }} />
            </Paragraph>
        </div>

        {error && <ErrorBanner error={error} />}

        {data && data.message.result.length > 0 ? (
            <ListView
                data={data.message.result}
                columns={clearanceColumns}
                getRowId={(row) => `${row.payment_entry}-${row.posting_date}`}
                maxHeight="calc(100vh - 200px)"
                scrollAreaClassName="min-h-[calc(100vh-200px)]"
                emptyState={_("No rows to display.")}
            />
        ) : null}

        {data && data.message.result.length == 0 &&
            <Empty>
                <EmptyMedia>
                    <ReceiptTextIcon />
                </EmptyMedia>
                <EmptyHeader>
                    <EmptyTitle>{_("No entries found")}</EmptyTitle>
                    <EmptyDescription>{_("There are no accounting entries in the system for the selected account and dates.")}</EmptyDescription>
                </EmptyHeader>
            </Empty>
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
                    <Button variant='link' size="sm" className="px-0" theme="red">{_("Force Clear")}</Button>
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

    const { call, loading, error } = useFrappePostCall('erpnext.accounts.doctype.bank_reconciliation_tool.bank_reconciliation_tool.update_clearance_date')

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
                                    href={`/desk/${slug(voucher.payment_document_type)}/${voucher.payment_entry}`}>{_(voucher.payment_document_type)} : {voucher.payment_entry}</a></TableCell>
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
                                <TableCell className="text-end">{formatCurrency(voucher.amount, bankAccount?.account_currency ?? getCompanyCurrency(companyID))}</TableCell>
                            </TableRow>
                            <TableRow>
                                <TableHead>{_("Against Account")}</TableHead>
                                <TableCell><a target="_blank" className="underline underline-offset-4" href={`/desk/account/${voucher.against}`}>{voucher.against}</a></TableCell>
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
                        <Button variant={'outline'} disabled={loading} size='md'>{_("Cancel")}</Button>
                    </DialogClose>
                    <Button type='submit' disabled={loading} size='md'>{_("Submit")}</Button>
                </DialogFooter>
            </div>
        </form>
    </Form>
}

export default BankClearanceSummary
