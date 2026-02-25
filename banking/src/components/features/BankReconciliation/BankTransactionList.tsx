import { useAtomValue, useSetAtom } from "jotai"
import { MissingFiltersBanner } from "./MissingFiltersBanner"
import { bankRecDateAtom, bankRecUnreconcileModalAtom, selectedBankAccountAtom } from "./bankRecAtoms"
import { Paragraph } from "@/components/ui/typography"
import { formatDate } from "@/lib/date"
import { Table, TableBody, TableCell, TableHead, TableRow } from "@/components/ui/table"
import { formatCurrency, getCurrencyFormatInfo } from "@/lib/numbers"
import { getCompanyCurrency } from "@/lib/company"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
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
import { cn } from "@/lib/utils"
import { useDebounceValue } from "usehooks-ts"
import { useMemo, useState } from "react"
import { Link } from "react-router"
import { TableVirtuoso } from "react-virtuoso"

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

    const onUndo = (transaction: BankTransaction) => {
        setBankRecUnreconcileModalAtom(transaction.name)
    }

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
                if (status === 'Unreconciled' && (!transaction.allocated_amount || (transaction.allocated_amount && transaction.allocated_amount === 0))) {
                    return false
                }
                if (status === 'Partially Reconciled' && transaction.allocated_amount && transaction.allocated_amount > 0 && transaction.unallocated_amount !== 0) {
                    return false
                }

            }

            if (amountFilter.value > 0 && transaction.withdrawal !== amountFilter.value && transaction.deposit !== amountFilter.value) {
                return false
            }

            return true
        })


    }, [data, search, amountFilter, typeFilter, status])

    return <div className="space-y-4 py-2">

        <div className="flex gap-2 justify-between items-center">
            <Paragraph className="text-sm">
                <span dangerouslySetInnerHTML={{
                    __html: _("Below is a list of all bank transactions imported in the system for the bank account {0} between {1} and {2}.", [`<strong>${bankAccount?.account_name}</strong>`, `<strong>${formattedFromDate}</strong>`, `<strong>${formattedToDate}</strong>`])
                }} />
            </Paragraph>

            <Button size='sm' variant='outline' asChild>
                <Link to="/statement-importer">
                    <ImportIcon />
                    {_("Import Bank Statement")}
                </Link>
            </Button>
        </div>

        {error && <ErrorBanner error={error} />}

        {data && data.message.length > 0 && <Filters
            onSearchChange={onSearchChange}
            search={search}
            results={filteredResults}
            setAmountFilter={setAmountFilter}
            amountFilter={amountFilter}
            onTypeFilterChange={setTypeFilter}
            typeFilter={typeFilter}
            status={status}
            setStatus={setStatus}
        />}

        <TableVirtuoso
            data={filteredResults}
            components={{
                Table: Table,
                TableBody: TableBody,
                TableRow: TableRow,
            }}
            fixedHeaderContent={() => (
                <TableRow>
                    <TableHead>{_("Date")}</TableHead>
                    <TableHead>{_("Description")}</TableHead>
                    <TableHead>{_("Reference #")}</TableHead>
                    <TableHead className="text-right">{_("Withdrawal")}</TableHead>
                    <TableHead className="text-right">{_("Deposit")}</TableHead>
                    <TableHead className="text-right">{_("Unallocated")}</TableHead>
                    <TableHead>{_("Type")}</TableHead>
                    <TableHead>{_("Status")}</TableHead>
                    <TableHead>{_("Actions")}</TableHead>
                </TableRow>
            )}
            itemContent={(_index, row) => (
                <>
                    <TableCell>{formatDate(row.date)}</TableCell>
                    <TableCell className="max-w-[300px] overflow-hidden text-ellipsis whitespace-nowrap"><span title={row.description}>{row.description}</span></TableCell>
                    <TableCell>{row.reference_number}</TableCell>
                    <TableCell className="text-right">{formatCurrency(row.withdrawal, bankAccount?.account_currency ?? getCompanyCurrency(bankAccount?.company ?? ''))}</TableCell>
                    <TableCell className="text-right">{formatCurrency(row.deposit, bankAccount?.account_currency ?? getCompanyCurrency(bankAccount?.company ?? ''))}</TableCell>
                    <TableCell className="text-right">{formatCurrency(row.unallocated_amount, bankAccount?.account_currency ?? getCompanyCurrency(bankAccount?.company ?? ''))}</TableCell>
                    <TableCell>{row.transaction_type ? <Badge variant={'outline'}>{row.transaction_type}</Badge> : null}</TableCell>
                    <TableCell>
                        {(!row.allocated_amount || (row.allocated_amount && row.allocated_amount === 0)) ?
                            <div className="bg-transparent border border-border flex items-center justify-center gap-1.5 px-2 py-1 text-xs w-fit rounded-md">
                                <XCircle className="-mt-px text-destructive" size={14} />
                                {_("Not Reconciled")}</div> :
                            (row.allocated_amount && row.allocated_amount > 0 && row.unallocated_amount !== 0) ?
                                <div className="bg-transparent border border-border flex items-center gap-1.5 px-2 py-1 text-xs w-fit rounded-md">
                                    <CheckCircle2 size={14} className="-mt-px text-yellow-500 dark:text-yellow-400" />
                                    {_("Partially Reconciled")}</div> :
                                <div className="bg-transparent border border-border flex items-center gap-1.5 px-2 py-1 text-xs w-fit rounded-md">
                                    <CheckCircle2 size={14} className="-mt-px text-green-600 dark:text-green-500" />
                                    {_("Reconciled")}</div>}
                    </TableCell>
                    <TableCell>
                        <div className="flex gap-2">
                            <div>
                                <Button variant='link' size='sm' asChild>
                                    <a
                                        href={`/app/bank-transaction/${row.name}`}
                                        target="_blank"
                                        className="underline underline-offset-4"
                                    >{_("View")} <ExternalLink />
                                    </a>
                                </Button>
                            </div>
                            {(row.allocated_amount && row.allocated_amount > 0) ? <Button
                                variant='link'
                                onClick={() => onUndo(row)}
                                size='sm'
                                className="text-destructive px-0">
                                <Undo2 />
                                {_("Undo")}
                            </Button> : null}
                        </div>
                    </TableCell>
                </>
            )}
            style={{ minHeight: 'calc(100vh - 200px)' }}
            totalCount={filteredResults?.length}
        />

        {filteredResults.length === 0 &&
            <Alert variant='default'>
                <DollarSign />
                <AlertTitle>{_("No transactions found")}</AlertTitle>
                <AlertDescription>
                    {_("There are no transactions in the system for the selected bank account and dates that match the filters.")}
                </AlertDescription>
            </Alert>
        }


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
        <label className="sr-only">{_("Search transactions")}</label>
        <div className={cn("flex items-center gap-2 w-full rounded-md dark:bg-input/30 border-input border bg-transparent px-2 text-base shadow-xs transition-[color,box-shadow] outline-none",
            "focus-within:border-ring focus-within:ring-ring/50 focus-within:ring-[3px]",
            "aria-invalid:ring-destructive/20 dark:aria-invalid:ring-destructive/40 aria-invalid:border-destructive"
        )}>
            <Search className="w-5 h-5 text-muted-foreground" />
            <Input placeholder={_("Search")} type='search' onChange={onSearchChange} defaultValue={search}
                className="border-none px-0 shadow-none focus-visible:ring-0 focus-visible:ring-offset-0" />
            <div>
                <span className="text-sm text-muted-foreground text-nowrap whitespace-nowrap">{results?.length} {_(results?.length === 1 ? "result" : "results")}</span>
            </div>
        </div>
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
                customInput={Input}
            />
        </div>
        <div className="w-[25%]">
            <DropdownMenu>
                <DropdownMenuTrigger asChild>
                    <Button variant="outline" className="min-w-32 w-full h-9 text-left justify-between">
                        <div className="flex gap-2 items-center">
                            {typeFilter === 'All' ? <DollarSign className="w-4 h-4 text-muted-foreground" /> : typeFilter === 'Debits' ? <ArrowUpRight className="w-4 h-4 text-destructive" /> : <ArrowDownRight className="w-4 h-4 text-green-600" />}
                            {_(typeFilter)}
                        </div>
                        <ChevronDown className="w-4 h-4" />
                    </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent>
                    <DropdownMenuItem onClick={() => onTypeFilterChange('All')}><DollarSign /> {_("All")}</DropdownMenuItem>
                    <DropdownMenuItem onClick={() => onTypeFilterChange('Debits')}><ArrowUpRight className="text-destructive" /> {_("Debits")}</DropdownMenuItem>
                    <DropdownMenuItem onClick={() => onTypeFilterChange('Credits')}><ArrowDownRight className="text-green-600" /> {_("Credits")}</DropdownMenuItem>
                </DropdownMenuContent>
            </DropdownMenu>
        </div>
        <div className="w-[25%]">
            <DropdownMenu>
                <DropdownMenuTrigger asChild>
                    <Button variant="outline" className="min-w-32 w-full h-9 text-left justify-between">
                        <div className="flex gap-2 items-center">
                            {status === 'All' ? <ListIcon className="w-4 h-4 text-muted-foreground" /> :
                                status === 'Reconciled' ? <CheckCircle2 className="w-4 h-4 text-green-600" /> :
                                    status === 'Unreconciled' ? <XCircle className="w-4 h-4 text-destructive" /> :
                                        <CheckCircle2 className="w-4 h-4 text-yellow-500" />}
                            {_(status)}
                        </div>

                        <ChevronDown className="w-4 h-4" />
                    </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent>
                    <DropdownMenuItem onClick={() => setStatus('All')}>{<ListIcon className="w-4 h-4 text-muted-foreground" />} {_("All")}</DropdownMenuItem>
                    <DropdownMenuItem onClick={() => setStatus('Reconciled')}>{<CheckCircle2 className="w-4 h-4 text-green-600" />} {_("Reconciled")}</DropdownMenuItem>
                    <DropdownMenuItem onClick={() => setStatus('Unreconciled')}>{<XCircle className="w-4 h-4 text-destructive" />} {_("Unreconciled")}</DropdownMenuItem>
                    <DropdownMenuItem onClick={() => setStatus('Partially Reconciled')}>{<CheckCircle2 className="w-4 h-4 text-yellow-500" />} {_("Partially Reconciled")}</DropdownMenuItem>
                </DropdownMenuContent>
            </DropdownMenu>
        </div>
    </div>
}

export default BankTransactions
