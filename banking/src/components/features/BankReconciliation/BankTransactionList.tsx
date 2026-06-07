import { useAtomValue, useSetAtom } from "jotai"
import { MissingFiltersBanner } from "./MissingFiltersBanner"
import { bankRecDateAtom, bankRecUnreconcileModalAtom, selectedBankAccountAtom } from "./bankRecAtoms"
import { Paragraph } from "@/components/ui/typography"
import { formatDate } from "@/lib/date"
import { ListView, type ListViewColumnMeta } from "@/components/ui/list-view"
import { formatCurrency, getCurrencyFormatInfo } from "@/lib/numbers"
import { getCompanyCurrency } from "@/lib/company"
import { ArrowDownRight, ArrowUpRight, CheckCircle2, ChevronDown, DollarSign, ExternalLink, ImportIcon, ListIcon, Search, Undo2, XCircle } from "lucide-react"
import ErrorBanner from "@/components/ui/error-banner"
import { Badge } from "@/components/ui/badge"
import { useGetBankTransactions } from "./utils"
import { BankTransaction } from "@/types/Accounts/BankTransaction"
import { Button } from "@/components/ui/button"
import _ from "@/lib/translate"
import { Input } from "@/components/ui/input"
import CurrencyInput from "react-currency-input-field"
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu"
import { getCurrencySymbol } from "@/lib/currency"
import { useDebounceValue } from "usehooks-ts"
import type { ColumnDef } from "@tanstack/react-table"
import { useCallback, useMemo, useState } from "react"
import { Link } from "react-router"
import { Empty, EmptyTitle, EmptyHeader, EmptyMedia, EmptyDescription, EmptyContent } from "@/components/ui/empty"
import { InputGroup, InputGroupAddon } from "@/components/ui/input-group"

const BankTransactions = () => {
    const selectedBank = useAtomValue(selectedBankAccountAtom)
    const dates = useAtomValue(bankRecDateAtom)

    if (!selectedBank || !dates) {
        return <MissingFiltersBanner text={_("Please select a bank and set the date range")} />
    }

    return <>
        <BankTransactionListView />
    </>
}

const BankTransactionListView = () => {

    const { data, error } = useGetBankTransactions()

    const bankAccount = useAtomValue(selectedBankAccountAtom)
    const dates = useAtomValue(bankRecDateAtom)

    const formattedFromDate = formatDate(dates.fromDate)
    const formattedToDate = formatDate(dates.toDate)

    const setBankRecUnreconcileModalAtom = useSetAtom(bankRecUnreconcileModalAtom)

    const onUndo = useCallback(
        (transaction: BankTransaction) => {
            setBankRecUnreconcileModalAtom(transaction.name)
        },
        [setBankRecUnreconcileModalAtom],
    )

    const accountCurrency = useMemo(
        () => bankAccount?.account_currency ?? getCompanyCurrency(bankAccount?.company ?? ""),
        [bankAccount?.account_currency, bankAccount?.company],
    )

    const transactionColumns = useMemo<ColumnDef<BankTransaction, unknown>[]>(
        () => [
            {
                accessorKey: "date",
                header: _("Date"),
                size: 112,
                meta: { tabularNums: true } satisfies ListViewColumnMeta,
                cell: ({ row }) => formatDate(row.original.date),
            },
            {
                accessorKey: "description",
                header: _("Description"),
                size: 250,
                // meta: { gridWidth: "minmax(0,2fr)" } satisfies ListViewColumnMeta,
                cell: ({ row }) => row.original.description,
            },
            {
                accessorKey: "reference_number",
                header: _("Reference #"),
                size: 128,
                cell: ({ row }) => row.original.reference_number,
            },
            {
                accessorKey: "withdrawal",
                header: _("Withdrawal"),
                size: 120,
                meta: { align: "right" } satisfies ListViewColumnMeta,
                cell: ({ row }) => <span className="font-numeric">{formatCurrency(row.original.withdrawal, accountCurrency)}</span>,
            },
            {
                accessorKey: "deposit",
                header: _("Deposit"),
                size: 120,
                meta: { align: "right" } satisfies ListViewColumnMeta,
                cell: ({ row }) => <span className="font-numeric">{formatCurrency(row.original.deposit, accountCurrency)}</span>,
            },
            {
                accessorKey: "unallocated_amount",
                header: _("Unallocated"),
                size: 120,
                meta: { align: "right" } satisfies ListViewColumnMeta,
                cell: ({ row }) => <span className="font-numeric">{formatCurrency(row.original.unallocated_amount, accountCurrency)}</span>,
            },
            {
                accessorKey: "transaction_type",
                header: _("Type"),
                size: 112,
                cell: ({ row }) =>
                    row.original.transaction_type ? <Badge>{row.original.transaction_type}</Badge> : null,
            },
            {
                id: "status",
                header: _("Status"),
                size: 168,
                meta: { truncate: false, truncateTooltip: false } satisfies ListViewColumnMeta,
                cell: ({ row }) => {
                    const tx = row.original
                    if (!tx.allocated_amount || (tx.allocated_amount && tx.allocated_amount === 0)) {
                        return (
                            <Badge theme="red">
                                <XCircle />
                                {_("Not Reconciled")}
                            </Badge>
                        )
                    }
                    if (tx.allocated_amount && tx.allocated_amount > 0 && tx.unallocated_amount !== 0) {
                        return (
                            <Badge theme="orange">
                                <CheckCircle2 />
                                {_("Partially Reconciled")}
                            </Badge>
                        )
                    }
                    return (
                        <Badge theme="green">
                            <CheckCircle2 />
                            {_("Reconciled")}
                        </Badge>
                    )
                },
            },
            {
                id: "actions",
                header: _("Actions"),
                size: 200,
                enableResizing: false,
                meta: { truncate: false, truncateTooltip: false } satisfies ListViewColumnMeta,
                cell: ({ row }) => (
                    <div className="flex gap-2 ps-0.5 items-center">
                        <Button variant="ghost" asChild size='sm'>
                            <a
                                href={`/desk/bank-transaction/${row.original.name}`}
                                target="_blank"

                                rel="noreferrer"
                            // className="text-ink-gray-8 underline underline-offset-4 inline-flex gap-2"
                            >
                                {_("View")} <ExternalLink className="w-4 h-4" />
                            </a>
                        </Button>
                        {row.original.allocated_amount && row.original.allocated_amount > 0 ? (
                            <Button
                                variant="ghost"
                                onClick={() => onUndo(row.original)}
                                size="sm"
                                theme='red'
                            >
                                <Undo2 />
                                {_("Undo")}
                            </Button>
                        ) : null}
                    </div>
                ),
            },
        ],
        [accountCurrency, onUndo],
    )

    const [search, setSearch] = useDebounceValue('', 250)
    const [amountFilter, setAmountFilter] = useState<{ value: number, stringValue?: string | number }>({ value: 0, stringValue: '0.00' })
    const [typeFilter, setTypeFilter] = useState('All')
    const [status, setStatus] = useState<'Reconciled' | 'Unreconciled' | 'All' | 'Partially Reconciled'>('All')

    const onSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        setSearch(e.target.value)
    }

    const filteredResults = useMemo(() => {
        if (!data) {
            return []
        }

        return data.message.filter((transaction) => {

            if (search && !transaction.description?.toLowerCase().includes(search.toLowerCase())) {
                return false
            }

            if (typeFilter !== 'All') {
                if (typeFilter === 'Debits' && transaction.deposit && transaction.deposit > 0) {
                    return false
                }
                if (typeFilter === 'Credits' && transaction.withdrawal && transaction.withdrawal > 0) {
                    return false
                }
            }

            if (status !== 'All') {
                if (status === 'Reconciled' && transaction.status !== 'Reconciled') {
                    return false
                }
                if (status === 'Unreconciled') {
                    if (transaction.status === 'Reconciled') {
                        return false
                    }
                    // Filter out partially reconciled transactions
                    if (transaction.allocated_amount && transaction.allocated_amount > 0 && transaction.unallocated_amount !== 0) {
                        return false
                    }
                }
                if (status === 'Partially Reconciled') {

                    if (transaction.status === 'Reconciled') {
                        return false
                    }
                    if ((transaction.allocated_amount ?? 0) === 0) {
                        return false
                    }
                }

            }

            if (amountFilter.value > 0 && transaction.withdrawal !== amountFilter.value && transaction.deposit !== amountFilter.value) {
                return false
            }

            return true
        })


    }, [data, search, amountFilter, typeFilter, status])

    return <div className="space-y-2 py-2">

        <div className="flex gap-2 justify-between items-center">
            <Paragraph className="text-sm">
                <span dangerouslySetInnerHTML={{
                    __html: _("Below is a list of all bank transactions imported in the system for the bank account {0} between {1} and {2}.", [`<strong>${bankAccount?.account_name}</strong>`, `<strong>${formattedFromDate}</strong>`, `<strong>${formattedToDate}</strong>`])
                }} />
            </Paragraph>

            <Button size='md' variant='subtle' asChild>
                <Link to="/statement-importer">
                    <ImportIcon />
                    {_("Import Bank Statement")}
                </Link>
            </Button>
        </div>

        {error && <ErrorBanner error={error} />}

        <Filters
            onSearchChange={onSearchChange}
            search={search}
            results={filteredResults}
            setAmountFilter={setAmountFilter}
            amountFilter={amountFilter}
            onTypeFilterChange={setTypeFilter}
            typeFilter={typeFilter}
            status={status}
            setStatus={setStatus}
        />

        <ListView
            data={filteredResults}
            columns={transactionColumns}
            getRowId={(row) => row.name}
            maxHeight="calc(100vh - 200px)"
            scrollAreaClassName="min-h-[calc(100vh-200px)]"
            emptyState={<Empty>
                <EmptyMedia>
                    <ListIcon />
                </EmptyMedia>
                <EmptyHeader>
                    <EmptyTitle>{_("No bank transactions found")}</EmptyTitle>
                    <EmptyDescription>{_("There are no transactions in the system for the selected bank account and dates that match the filters.")}</EmptyDescription>
                </EmptyHeader>
                {data && data.message.length === 0 ? <EmptyContent>
                    <Button type='button' asChild variant='outline'>
                        <Link to="/statement-importer">
                            {_("Import Bank Statement")}
                        </Link>
                    </Button>
                </EmptyContent> : null}
            </Empty>}
        />
    </div>
}

interface FilterProps {
    onSearchChange: (e: React.ChangeEvent<HTMLInputElement>) => void
    search: string
    results: BankTransaction[]
    setAmountFilter: (value: { value: number, stringValue?: string | number }) => void
    amountFilter: { value: number, stringValue?: string | number }
    onTypeFilterChange: (type: string) => void
    typeFilter: string
    status: 'Reconciled' | 'Unreconciled' | 'All' | 'Partially Reconciled'
    setStatus: (status: 'Reconciled' | 'Unreconciled' | 'All' | 'Partially Reconciled') => void
}


const Filters = ({
    onSearchChange,
    search,
    results,
    setAmountFilter,
    amountFilter,
    onTypeFilterChange,
    typeFilter,
    status,
    setStatus,

}: FilterProps) => {
    const bankAccount = useAtomValue(selectedBankAccountAtom)

    const currency = bankAccount?.account_currency ?? getCompanyCurrency(bankAccount?.company ?? '')
    const currencySymbol = getCurrencySymbol(currency)
    const formatInfo = getCurrencyFormatInfo(currency)
    const groupSeparator = formatInfo.group_sep || ","
    const decimalSeparator = formatInfo.decimal_str || "."

    return <div className="flex py-2 w-full gap-2">
        <InputGroup variant='outline'>
            <label className="sr-only">{_("Search transactions")}</label>
            <InputGroupAddon>
                <Search className="w-4 h-4 text-ink-gray-5" />
            </InputGroupAddon>
            <Input
                placeholder={_("Search")} type='search' onChange={onSearchChange} variant='outline' defaultValue={search}
                className="border-none px-0 shadow-none focus-visible:ring-0 focus-visible:ring-offset-0" />
            <InputGroupAddon align='inline-end'>
                <span className="text-sm text-ink-gray-5 text-nowrap whitespace-nowrap">{results?.length} {_(results?.length === 1 ? "result" : "results")}</span>
            </InputGroupAddon>
        </InputGroup>

        <div className="w-[25%]">
            <label className="sr-only">{_("Filter by amount")}</label>
            <CurrencyInput
                groupSeparator={groupSeparator}
                decimalSeparator={decimalSeparator}
                placeholder={`${currencySymbol}0${decimalSeparator}00`}
                decimalsLimit={2}
                value={amountFilter.stringValue}
                maxLength={12}
                decimalScale={2}
                prefix={currencySymbol}
                onValueChange={(v, _n, values) => {
                    // If the input ends with a decimal or a decimal with trailing zeroes, store the string since we need the user to be able to type the decimals.
                    // When the user eventually types the decimals or blurs out, the value is formatted anyway.
                    // Otherwise store the float value
                    // Check if the value ends with a decimal or a decimal with trailing zeroes
                    const isDecimal = v?.endsWith(decimalSeparator) || v?.endsWith(decimalSeparator + '0')
                    const newValue = isDecimal ? v : values?.float ?? ''
                    setAmountFilter({
                        value: Number(newValue),
                        stringValue: newValue
                    })
                }}
                // @ts-expect-error - CurrencyInputProps doesn't have a variant prop but Input does
                variant={"outline"}
                customInput={Input}
            />
        </div>
        <div className="w-[25%]">
            <DropdownMenu>
                <DropdownMenuTrigger asChild>
                    <Button variant="outline" size='md' className="min-w-32 w-full text-start justify-between">
                        <div className="flex gap-2 items-center">
                            {typeFilter === 'All' ? <DollarSign className="w-4 h-4 text-ink-gray-5" /> : typeFilter === 'Debits' ? <ArrowUpRight className="w-4 h-4 text-ink-red-3" /> : <ArrowDownRight className="w-4 h-4 text-ink-green-3" />}
                            {_(typeFilter)}
                        </div>
                        <ChevronDown className="w-4 h-4" />
                    </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent>
                    <DropdownMenuItem onClick={() => onTypeFilterChange('All')}><DollarSign /> {_("All")}</DropdownMenuItem>
                    <DropdownMenuItem onClick={() => onTypeFilterChange('Debits')}><ArrowUpRight className="text-ink-red-3" /> {_("Debits")}</DropdownMenuItem>
                    <DropdownMenuItem onClick={() => onTypeFilterChange('Credits')}><ArrowDownRight className="text-ink-green-3" /> {_("Credits")}</DropdownMenuItem>
                </DropdownMenuContent>
            </DropdownMenu>
        </div>
        <div className="w-[25%]">
            <DropdownMenu>
                <DropdownMenuTrigger asChild>
                    <Button variant="outline" size='md' className="min-w-32 w-full text-start justify-between">
                        <div className="flex gap-2 items-center">
                            {status === 'All' ? <ListIcon className="w-4 h-4 text-ink-gray-5" /> :
                                status === 'Reconciled' ? <CheckCircle2 className="w-4 h-4 text-ink-green-3" /> :
                                    status === 'Unreconciled' ? <XCircle className="w-4 h-4 text-ink-red-3" /> :
                                        <CheckCircle2 className="w-4 h-4 text-yellow-500" />}
                            {_(status)}
                        </div>

                        <ChevronDown className="w-4 h-4" />
                    </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent>
                    <DropdownMenuItem onClick={() => setStatus('All')}>{<ListIcon className="w-4 h-4 text-ink-gray-5" />} {_("All")}</DropdownMenuItem>
                    <DropdownMenuItem onClick={() => setStatus('Reconciled')}>{<CheckCircle2 className="w-4 h-4 text-ink-green-3" />} {_("Reconciled")}</DropdownMenuItem>
                    <DropdownMenuItem onClick={() => setStatus('Unreconciled')}>{<XCircle className="w-4 h-4 text-ink-red-3" />} {_("Unreconciled")}</DropdownMenuItem>
                    <DropdownMenuItem onClick={() => setStatus('Partially Reconciled')}>{<CheckCircle2 className="w-4 h-4 text-yellow-500" />} {_("Partially Reconciled")}</DropdownMenuItem>
                </DropdownMenuContent>
            </DropdownMenu>
        </div>
    </div>
}

export default BankTransactions
