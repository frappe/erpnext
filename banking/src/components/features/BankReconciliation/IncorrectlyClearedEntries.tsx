import { useAtomValue } from "jotai"
import { MissingFiltersBanner } from "./MissingFiltersBanner"
import { bankRecDateAtom, selectedBankAccountAtom } from "./bankRecAtoms"
import { useCurrentCompany } from "@/hooks/useCurrentCompany"
import { Paragraph } from "@/components/ui/typography"
import type { ColumnDef } from "@tanstack/react-table"
import { useCallback, useMemo } from "react"
import { useFrappeGetCall, useFrappePostCall } from "frappe-react-sdk"
import { QueryReportReturnType } from "@/types/custom/Reports"
import { formatDate } from "@/lib/date"
import { ListView, type ListViewColumnMeta } from "@/components/ui/list-view"
import { formatCurrency } from "@/lib/numbers"
import { getCompanyCurrency } from "@/lib/company"
import { getErrorMessage, slug } from "@/lib/frappe"
import { Button } from "@/components/ui/button"
import { toast } from "sonner"
import { PartyPopper } from "lucide-react"
import ErrorBanner from "@/components/ui/error-banner"
import _ from "@/lib/translate"
import { Empty, EmptyTitle, EmptyDescription, EmptyMedia, EmptyHeader } from "@/components/ui/empty"

const IncorrectlyClearedEntries = () => {
    const companyID = useCurrentCompany()
    const bankAccount = useAtomValue(selectedBankAccountAtom)
    const dates = useAtomValue(bankRecDateAtom)

    if (!companyID || !bankAccount || !dates) {
        const missingFields = []
        if (!companyID) {
            missingFields.push('Company')
        }
        if (!bankAccount) {
            missingFields.push('Bank Account')
        }
        if (!dates) {
            missingFields.push('Dates')
        }
        return <MissingFiltersBanner text={`Please select ${missingFields.join(', ')} to view the incorrectly cleared entries.`} />
    }

    return <IncorrectlyClearedEntriesView />
}

interface IncorrectlyClearedEntry {
    payment_document: string
    payment_entry: string
    debit: number
    credit: number
    posting_date: string,
    clearance_date: string,
}

const IncorrectlyClearedEntriesView = () => {

    const companyID = useCurrentCompany()
    const bankAccount = useAtomValue(selectedBankAccountAtom)
    const dates = useAtomValue(bankRecDateAtom)

    const filters = useMemo(() => {
        return JSON.stringify({
            company: companyID,
            account: bankAccount?.account,
            report_date: dates.toDate
        })
    }, [companyID, bankAccount, dates])

    const { data, error, mutate } = useFrappeGetCall<{ message: QueryReportReturnType<IncorrectlyClearedEntry> }>('frappe.desk.query_report.run', {
        report_name: 'Cheques and Deposits Incorrectly cleared',
        filters,
        ignore_prepared_report: 1,
        are_default_filters: false,
    }, `Report-Cheques and Deposits Incorrectly cleared-${filters}`, { keepPreviousData: true, revalidateOnFocus: false }, 'POST')

    const formattedToDate = formatDate(dates.toDate)

    const { call: clearClearingDate } = useFrappePostCall('erpnext.accounts.doctype.bank_reconciliation_tool.bank_reconciliation_tool.clear_clearing_date')

    const onClearClick = useCallback(
        (voucher_type: string, voucher_name: string) => {
            clearClearingDate({ voucher_type, voucher_name })
                .then(() => {
                    toast.success(_("Cleared"), {
                        duration: 1000,
                    })
                    mutate()
                })
                .catch((e) => {
                    toast.error(_("There was an error while performing the action."), {
                        description: getErrorMessage(e),
                        duration: 5000,
                    })
                })
        },
        [clearClearingDate, mutate],
    )

    const accountCurrency = useMemo(
        () => bankAccount?.account_currency ?? getCompanyCurrency(companyID),
        [bankAccount?.account_currency, companyID],
    )

    const incorrectlyClearedColumns = useMemo<ColumnDef<IncorrectlyClearedEntry, unknown>[]>(
        () => [
            {
                accessorKey: "payment_document",
                header: _("Document Type"),
                size: 128,
                cell: ({ row }) => _(row.original.payment_document),
            },
            {
                id: "payment_entry",
                header: _("Payment Document"),
                size: 160,
                meta: {
                    getTooltipText: (r) => {
                        const x = r as IncorrectlyClearedEntry
                        return [x.payment_document, x.payment_entry].filter(Boolean).join(" · ") || undefined
                    },
                } satisfies ListViewColumnMeta,
                cell: ({ row }) => (
                    <a
                        target="_blank"
                        rel="noreferrer"
                        className="text-ink-gray-8 block min-w-0 w-full underline underline-offset-4"
                        href={`/desk/${slug(row.original.payment_document)}/${row.original.payment_entry}`}
                    >
                        {row.original.payment_entry}
                    </a>
                ),
            },
            {
                accessorKey: "debit",
                header: _("Debit"),
                size: 120,
                meta: { align: "right" } satisfies ListViewColumnMeta,
                cell: ({ row }) => formatCurrency(row.original.debit, accountCurrency),
            },
            {
                accessorKey: "credit",
                header: _("Credit"),
                size: 120,
                meta: { align: "right" } satisfies ListViewColumnMeta,
                cell: ({ row }) => formatCurrency(row.original.credit, accountCurrency),
            },
            {
                accessorKey: "posting_date",
                header: _("Posting Date"),
                size: 118,
                meta: { tabularNums: true } satisfies ListViewColumnMeta,
                cell: ({ row }) => formatDate(row.original.posting_date),
            },
            {
                accessorKey: "clearance_date",
                header: _("Clearance Date"),
                size: 118,
                meta: { tabularNums: true } satisfies ListViewColumnMeta,
                cell: ({ row }) => formatDate(row.original.clearance_date),
            },
            {
                id: "actions",
                header: _("Actions"),
                size: 180,
                enableResizing: false,
                meta: { truncate: false, truncateTooltip: false } satisfies ListViewColumnMeta,
                cell: ({ row }) => (
                    <Button
                        variant="link"
                        size="sm"
                        className="text-ink-red-3 px-0"
                        onClick={() => onClearClick(row.original.payment_document, row.original.payment_entry)}
                    >
                        {_("Reset Clearing Date")}
                    </Button>
                ),
            },
        ],
        [accountCurrency, onClearClick],
    )

    return <div className="space-y-4 py-2">

        <div>
            <Paragraph className="text-sm">
                <span dangerouslySetInnerHTML={{
                    __html: _("This report shows all entries in the system where the <strong>clearance date is before the posting date</strong> which is incorrect.")
                }} />
                <br />
                {data && data.message.result.length > 0 && <span>
                    <span dangerouslySetInnerHTML={{
                        __html: _("Entries below have a posting date after {0} but the clearance date is before {1}.", [`<strong>${formattedToDate}</strong>`, `<strong>${formattedToDate}</strong>`])
                    }} />
                    <br />
                    {_("You can reset the clearing dates of these entries here.")}
                </span>}
            </Paragraph>
        </div>

        {error && <ErrorBanner error={error} />}

        {data && data.message.result.length > 0 && (
            <div className="space-y-2">
                <p className="text-ink-gray-5 text-sm">{_("Incorrectly cleared entries as per the report.")}</p>
                <ListView
                    data={data.message.result}
                    columns={incorrectlyClearedColumns}
                    getRowId={(row) => `${row.payment_entry}-${row.posting_date}`}
                    maxHeight="min(70vh, 640px)"
                    emptyState={_("No rows to display.")}
                />
            </div>
        )}

        {data && data.message.result.length === 0 &&
            <Empty>
                <EmptyMedia>
                    <PartyPopper />
                </EmptyMedia>
                <EmptyHeader>
                    <EmptyTitle>{_("It's all good!")}</EmptyTitle>
                    <EmptyDescription>{_("There are no entries in the system where the clearance date is before the posting date.")}</EmptyDescription>
                </EmptyHeader>
            </Empty>
        }


    </div>
}

export default IncorrectlyClearedEntries
