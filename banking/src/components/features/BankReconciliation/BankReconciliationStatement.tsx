import { useAtomValue } from "jotai"
import { MissingFiltersBanner } from "./MissingFiltersBanner"
import { bankRecDateAtom, selectedBankAccountAtom } from "./bankRecAtoms"
import { useCurrentCompany } from "@/hooks/useCurrentCompany"
import { Paragraph } from "@/components/ui/typography"
import { useCallback, useMemo } from "react"
import type { ColumnDef } from "@tanstack/react-table"
import { useFrappeGetCall } from "frappe-react-sdk"
import { QueryReportReturnType } from "@/types/custom/Reports"
import { formatDate } from "@/lib/date"
import { ListView, type ListViewColumnMeta } from "@/components/ui/list-view"
import { formatCurrency } from "@/lib/numbers"
import { getCompanyCurrency } from "@/lib/company"
import { slug } from "@/lib/frappe"
import { ScrollTextIcon } from "lucide-react"
import ErrorBanner from "@/components/ui/error-banner"
import { StatContainer, StatLabel, StatValue } from "@/components/ui/stats"
import _ from "@/lib/translate"
import { toast } from "sonner"
import { useCopyToClipboard } from "usehooks-ts"
import { Empty, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from "@/components/ui/empty"

const BankReconciliationStatement = () => {
    const bankAccount = useAtomValue(selectedBankAccountAtom)
    const dates = useAtomValue(bankRecDateAtom)

    if (!bankAccount) {
        return <MissingFiltersBanner text={_("Please select a bank account to view the bank reconciliation statement.")} />
    }

    if (!dates) {
        return <MissingFiltersBanner text={_("Please select dates to view the bank reconciliation statement.")} />
    }

    return <BankReconciliationStatementView />
}
interface BankClearanceSummaryEntry {
    payment_document: string
    payment_entry: string
    posting_date: string,
    reference_no: string,
    credit: number,
    debit: number,
    against_account: string,
    ref_date: string,
    account_currency: string,
    clearance_date: string
}

const BankReconciliationStatementView = () => {

    const companyID = useCurrentCompany()
    const bankAccount = useAtomValue(selectedBankAccountAtom)
    const dates = useAtomValue(bankRecDateAtom)

    const filters = useMemo(() => {
        return JSON.stringify({
            account: bankAccount?.account,
            report_date: dates.toDate,
            company: companyID
        })
    }, [bankAccount, dates, companyID])

    const { data, error } = useFrappeGetCall<{ message: QueryReportReturnType }>('frappe.desk.query_report.run', {
        report_name: 'Bank Reconciliation Statement',
        filters,
        ignore_prepared_report: 1,
        are_default_filters: false,
    }, `Report-Bank Reconciliation Statement-${filters}`, { keepPreviousData: true, revalidateOnFocus: false }, 'POST')

    const [, copyToClipboard] = useCopyToClipboard()

    const onCopy = useCallback(
        (text: string) => {
            copyToClipboard(text).then(() => {
                toast.success(_("Copied to clipboard"))
            })
        },
        [copyToClipboard, _],
    )

    const statementColumns = useMemo<ColumnDef<BankClearanceSummaryEntry, unknown>[]>(
        () => [
            {
                accessorKey: "posting_date",
                header: _("Posting Date"),
                size: 118,
                meta: { tabularNums: true } satisfies ListViewColumnMeta,
                cell: ({ row }) => formatDate(row.original.posting_date),
            },
            {
                accessorKey: "payment_document",
                header: _("Document Type"),
                size: 140,
                cell: ({ row }) => _(row.original.payment_document),
            },
            {
                id: "payment_entry",
                header: _("Payment Document"),
                size: 300,
                meta: {
                    getTooltipText: (r) => {
                        const x = r as BankClearanceSummaryEntry
                        const parts = [x.payment_document, x.payment_entry].filter(Boolean)
                        return parts.length ? parts.join(" · ") : undefined
                    },
                } satisfies ListViewColumnMeta,
                cell: ({ row }) => {
                    const { payment_document, payment_entry } = row.original
                    return payment_document ? (
                        <a
                            target="_blank"
                            rel="noreferrer"
                            className="text-ink-gray-8 block min-w-0 w-full underline underline-offset-4"
                            href={`/desk/${slug(payment_document)}/${payment_entry}`}
                        >
                            {payment_entry}
                        </a>
                    ) : (
                        payment_entry
                    )
                },
            },
            {
                accessorKey: "debit",
                header: _("Debit"),
                size: 112,
                meta: { align: "right" } satisfies ListViewColumnMeta,
                cell: ({ row }) => <span className="font-numeric">{formatCurrency(row.original.debit, row.original.account_currency)}</span>,
            },
            {
                accessorKey: "credit",
                header: _("Credit"),
                size: 112,
                meta: { align: "right" } satisfies ListViewColumnMeta,
                cell: ({ row }) => <span className="font-numeric">{formatCurrency(row.original.credit, row.original.account_currency)}</span>,
            },
            {
                accessorKey: "against_account",
                header: _("Against Account"),
                meta: { gridWidth: "minmax(0,1.25fr)" } satisfies ListViewColumnMeta,
                cell: ({ row }) => (
                    <a
                        target="_blank"
                        rel="noreferrer"
                        className="text-ink-gray-8 block min-w-0 w-full underline underline-offset-4"
                        href={`/desk/account/${row.original.against_account}`}
                    >
                        {row.original.against_account}
                    </a>
                ),
            },
            {
                accessorKey: "reference_no",
                header: _("Reference #"),
                cell: ({ row }) => {
                    const ref = row.original.reference_no
                    return (
                        <button
                            type="button"
                            className="text-ink-gray-8 hover:underline min-w-0 w-full cursor-pointer truncate text-start underline-offset-4"
                            onClick={() => onCopy(ref)}
                        >
                            {ref}
                        </button>
                    )
                },
            },
            {
                accessorKey: "ref_date",
                header: _("Reference Date"),
                size: 118,
                meta: { tabularNums: true } satisfies ListViewColumnMeta,
                cell: ({ row }) => formatDate(row.original.ref_date),
            },
            {
                accessorKey: "clearance_date",
                header: _("Clearance Date"),
                size: 118,
                meta: { tabularNums: true } satisfies ListViewColumnMeta,
                cell: ({ row }) => formatDate(row.original.clearance_date),
            },
        ],
        [_, onCopy],
    )

    const statementRows = useMemo(() => {
        if (!data?.message.result) return []
        return data.message.result.filter((row: BankClearanceSummaryEntry) => Boolean(row.payment_entry))
    }, [data])

    return <div className="space-y-4 py-2">

        <div>
            <Paragraph className="text-sm">
                <span dangerouslySetInnerHTML={{
                    __html: _("Below is a list of all entries posted against the bank account {0} which have not been cleared till {1}.", [`<strong>${bankAccount?.account}</strong>`, `<strong>${formatDate(dates.toDate)}</strong>`])
                }} />
            </Paragraph>
        </div>

        {error && <ErrorBanner error={error} />}

        {data && <SummarySection data={data} />}

        {data && data.message.result.length > 0 && (
            <div className="space-y-2">
                <p className="text-ink-gray-5 text-sm">{_("Bank Reconciliation Statement")}</p>
                <ListView
                    data={statementRows}
                    columns={statementColumns}
                    getRowId={(row) => row.payment_entry}
                    maxHeight="min(70vh, 640px)"
                    emptyState={_("No entries with a payment document in this list.")}
                />
            </div>
        )}

        {data && data.message.result.length === 0 &&
            <Empty>
                <EmptyMedia>
                    <ScrollTextIcon />
                </EmptyMedia>
                <EmptyHeader>
                    <EmptyTitle>{_("No entries found")}</EmptyTitle>
                    <EmptyDescription>{_("There are no accounting entries in the system for the selected account and dates.")}</EmptyDescription>
                </EmptyHeader>
            </Empty>
        }


    </div>
}

const SummarySection = ({ data }: { data: { message: QueryReportReturnType } }) => {

    const company = useCurrentCompany()
    const bankAccount = useAtomValue(selectedBankAccountAtom)

    const { bankStatementBalanceAsPerGL, outstandingChecksDebit, outstandingChecksCredit, incorrectlyClearedEntriesDebit, incorrectlyClearedEntriesCredit, calculatedBankStatementBalance } = useMemo(() => {

        // Loop over the results and find the corresponding rows

        let bankStatementBalanceAsPerGL = 0

        let outstandingChecksDebit = 0
        let outstandingChecksCredit = 0

        let incorrectlyClearedEntriesDebit = 0
        let incorrectlyClearedEntriesCredit = 0

        let calculatedBankStatementBalance = 0

        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        data?.message.result.forEach((r: any) => {
            if (r.payment_entry === 'Bank Statement balance as per General Ledger') {
                bankStatementBalanceAsPerGL = r.debit - r.credit
            }

            if (r.payment_entry === 'Outstanding Checks and Deposits to clear') {
                outstandingChecksDebit = r.debit
                outstandingChecksCredit = r.credit
            }

            if (r.payment_entry === 'Checks and Deposits incorrectly cleared') {
                incorrectlyClearedEntriesDebit = r.debit
                incorrectlyClearedEntriesCredit = r.credit
            }

            if (r.payment_entry === 'Calculated Bank Statement balance') {
                calculatedBankStatementBalance = r.debit - r.credit
            }
        })

        return {
            bankStatementBalanceAsPerGL,
            outstandingChecksDebit,
            outstandingChecksCredit,
            incorrectlyClearedEntriesDebit,
            incorrectlyClearedEntriesCredit,
            calculatedBankStatementBalance
        }

    }, [data])

    const currency = bankAccount?.account_currency ?? getCompanyCurrency(company)

    return <div className="flex gap-4 items-start justify-between">
        <StatContainer>
            <StatLabel>{_("Bank Statement Balance as per General Ledger")}</StatLabel>
            <StatValue className="font-numeric">{formatCurrency(bankStatementBalanceAsPerGL, currency)}</StatValue>
        </StatContainer>

        <StatContainer>
            <StatLabel>{_("Outstanding Checks and Deposits to clear")}</StatLabel>
            <StatValue className="font-numeric">{formatCurrency(outstandingChecksDebit - outstandingChecksCredit, currency)}</StatValue>
        </StatContainer>

        {(incorrectlyClearedEntriesDebit > 0 || incorrectlyClearedEntriesCredit > 0) && <StatContainer>
            <StatLabel className="text-ink-red-3">{_("Checks and Deposits incorrectly cleared")}</StatLabel>
            <StatValue className="text-ink-red-3 font-numeric">{formatCurrency(incorrectlyClearedEntriesDebit - incorrectlyClearedEntriesCredit)}</StatValue>
            {/* <div className="" divider={<StackDivider height='20px' />}>
                {incorrectlyClearedEntriesDebit !== 0 && <StatHelpText>Debit: {formatCurrency(incorrectlyClearedEntriesDebit)}</StatHelpText>}
                {incorrectlyClearedEntriesCredit !== 0 && <StatHelpText>Credit: {formatCurrency(incorrectlyClearedEntriesCredit)}</StatHelpText>}
            </div> */}
        </StatContainer>}
        <StatContainer>
            <StatLabel>{_("Calculated Bank Statement Balance")}</StatLabel>
            <StatValue className="font-numeric">{formatCurrency(calculatedBankStatementBalance)}</StatValue>
        </StatContainer>

    </div>
}

export default BankReconciliationStatement
