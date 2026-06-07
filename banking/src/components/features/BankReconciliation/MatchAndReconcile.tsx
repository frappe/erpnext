import { useAtom, useAtomValue, useSetAtom } from "jotai"
import { bankRecAmountFilter, bankRecDateAtom, bankRecRecordJournalEntryModalAtom, bankRecRecordPaymentModalAtom, bankRecSelectedTransactionAtom, bankRecTransactionTypeFilter, bankRecTransferModalAtom, selectedBankAccountAtom } from "./bankRecAtoms"
import { H4 } from "@/components/ui/typography"
import { useMemo, useRef } from "react"
import { getCompanyCurrency } from "@/lib/company"
import ErrorBanner from "@/components/ui/error-banner"
import { Separator } from "@/components/ui/separator"
import Fuse from 'fuse.js'
import { getSearchResults, LinkedPayment, UnreconciledTransaction, useGetRuleForTransaction, useGetUnreconciledTransactions, useGetVouchersForTransaction, useIsTransactionWithdrawal, useReconcileTransaction, useTransactionSearch } from "./utils"
import { Input } from "@/components/ui/input"
import { AlertCircleIcon, ArrowDownRight, ArrowRightIcon, ArrowRightLeft, ArrowUpRight, BadgeCheck, ChevronDown, DollarSign, Landmark, LandmarkIcon, ListIcon, Loader2, Receipt, ReceiptIcon, Search, User, XCircle, ZapIcon } from "lucide-react"
import { cn } from "@/lib/utils"
import { DropdownMenu, DropdownMenuTrigger, DropdownMenuContent, DropdownMenuItem } from "@/components/ui/dropdown-menu"
import { Button } from "@/components/ui/button"
import CurrencyInput from 'react-currency-input-field'
import { getCurrencySymbol } from "@/lib/currency"
import { useVirtualizer } from '@tanstack/react-virtual'
import { formatDate } from "@/lib/date"
import { Badge } from "@/components/ui/badge"
import { formatCurrency, getCurrencyFormatInfo } from "@/lib/numbers"
import { Tooltip, TooltipTrigger, TooltipContent, TooltipProvider } from "@/components/ui/tooltip"
import { Skeleton } from "@/components/ui/skeleton"
import { slug } from "@/lib/frappe"
import _ from "@/lib/translate"
import { Card, CardAction, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import TransferModal from "./TransferModal"
import BankEntryModal from "./BankEntryModal"
import RecordPaymentModal from "./RecordPaymentModal"
import SelectedTransactionsTable from "./SelectedTransactionsTable"
import MatchFilters from "./MatchFilters"
import { useHotkeys } from "react-hotkeys-hook"
import { KeyboardMetaKeyIcon } from "@/components/ui/keyboard-keys"
import { Kbd, KbdGroup } from "@/components/ui/kbd"
import { useFrappeGetCall } from "frappe-react-sdk"
import { Empty, EmptyContent, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from "@/components/ui/empty"
import { Link } from "react-router"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { InputGroup, InputGroupAddon, InputGroupText } from "@/components/ui/input-group"

const MatchAndReconcile = ({ contentHeight }: { contentHeight: number }) => {
    const selectedBank = useAtomValue(selectedBankAccountAtom)

    if (!selectedBank) {
        return <Empty>
            <EmptyMedia>
                <LandmarkIcon />
            </EmptyMedia>
            <EmptyHeader>
                <EmptyTitle>{_("Select a bank account to reconcile")}</EmptyTitle>
            </EmptyHeader>
        </Empty>
    }

    return <>
        <div className={`flex items-start space-x-2`} >
            <div className="flex-1">
                <H4 className="text-sm font-medium">{_("Unreconciled Transactions")}</H4>
                <UnreconciledTransactions contentHeight={contentHeight} />
            </div>
            <Separator orientation="vertical" style={{ minHeight: `${contentHeight}px` }} />
            <div className="flex-1 px-1">
                <H4 className="text-sm font-medium">{_("Match or Create")}</H4>
                <VouchersSection contentHeight={contentHeight} />
            </div>
        </div>
        <TransferModal />
        <BankEntryModal />
        <RecordPaymentModal />
    </>
}

/** TanStack requires `estimateSize` for initial scroll range; `measureElement` on each row sets the real height. */
function VirtualizedListBody<T>({
    items,
    height,
    getItemKey,
    children,
    estimateSize = 74,
}: {
    items: T[]
    height: number
    getItemKey: (item: T, index: number) => string | number
    children: (item: T, index: number) => React.ReactNode
    estimateSize?: number
}) {
    const scrollRef = useRef<HTMLDivElement>(null)

    const rowVirtualizer = useVirtualizer({
        count: items.length,
        getScrollElement: () => scrollRef.current,
        estimateSize: () => estimateSize,
        overscan: 8,
        getItemKey: (index) => String(getItemKey(items[index], index)),
    })

    if (items.length === 0) {
        return null
    }

    return (
        <div
            ref={scrollRef}
            className="overflow-auto contain-strict"
            style={{ height }}
        >
            <div
                className="relative w-full"
                style={{ height: rowVirtualizer.getTotalSize() }}
            >
                {rowVirtualizer.getVirtualItems().map((virtualRow) => (
                    <div
                        key={virtualRow.key}
                        data-index={virtualRow.index}
                        ref={rowVirtualizer.measureElement}
                        className="absolute top-0 left-0 w-full"
                        style={{ transform: `translateY(${virtualRow.start}px)` }}
                    >
                        {children(items[virtualRow.index], virtualRow.index)}
                    </div>
                ))}
            </div>
        </div>
    )
}

const UnreconciledTransactions = ({ contentHeight }: { contentHeight: number }) => {
    const bankAccount = useAtomValue(selectedBankAccountAtom)

    const currency = bankAccount?.account_currency ?? getCompanyCurrency(bankAccount?.company ?? '')
    const currencySymbol = getCurrencySymbol(currency)
    const formatInfo = getCurrencyFormatInfo(currency)
    const groupSeparator = formatInfo.group_sep || ","
    const decimalSeparator = formatInfo.decimal_str || "."

    const inputRef = useRef<HTMLInputElement>(null)

    const { data: unreconciledTransactions, isLoading, error } = useGetUnreconciledTransactions()

    const [typeFilter, setTypeFilter] = useAtom(bankRecTransactionTypeFilter)
    const [amountFilter, setAmountFilter] = useAtom(bankRecAmountFilter)

    const [search, setSearch] = useTransactionSearch()

    const searchIndex = useMemo(() => {

        if (!unreconciledTransactions) {
            return null
        }

        return new Fuse(unreconciledTransactions.message, {
            keys: ['description', 'reference_number'],
            threshold: 0.5,
            includeScore: true
        })
    }, [unreconciledTransactions])

    const results = useMemo(() => {

        return getSearchResults(searchIndex, search, typeFilter, amountFilter.value, unreconciledTransactions?.message)

    }, [searchIndex, search, typeFilter, amountFilter.value, unreconciledTransactions?.message])

    const setSelectedTransaction = useSetAtom(bankRecSelectedTransactionAtom(bankAccount?.name || ''))

    const onFilterChange = () => {
        setSelectedTransaction([])
    }

    const onSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        setSearch(e.target.value)
        onFilterChange()
    }

    const onTypeFilterChange = (type: string) => {
        setTypeFilter(type)
        onFilterChange()
    }

    const onClearFilters = () => {
        setSearch('')
        if (inputRef.current) {
            inputRef.current.value = ''
        }
        setTypeFilter('All')
        setAmountFilter({ value: 0, stringValue: '' })
        onFilterChange()
    }

    const hasFilters = search !== '' || typeFilter !== 'All' || amountFilter.value !== 0
    const listHeight = contentHeight - 72

    if (isLoading) {
        return <UnreconciledTransactionsLoadingState />
    }

    return <div className="space-y-1">
        <div className="flex py-2 w-full gap-2">

            <InputGroup variant='outline'>
                <label className="sr-only">{_("Search transactions")}</label>
                <InputGroupAddon>
                    <Search className="w-4 h-4 text-ink-gray-5" />
                </InputGroupAddon>
                <Input
                    placeholder={_("Search")}
                    // type='search'
                    variant='outline'
                    onChange={onSearchChange}
                    defaultValue={search}
                    ref={inputRef}
                />
                <InputGroupAddon align='inline-end'>
                    <InputGroupText>{results?.length} {_(results?.length === 1 ? "result" : "results")}</InputGroupText>
                </InputGroupAddon>
            </InputGroup>
            <div>
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
                        const nextAmountFilter = {
                            value: Number(newValue),
                            stringValue: newValue
                        }
                        const hasAmountFilterChanged = amountFilter.value !== nextAmountFilter.value || amountFilter.stringValue !== nextAmountFilter.stringValue

                        setAmountFilter(nextAmountFilter)

                        // `onValueChange` also fires on blur; avoid clearing selected transaction unless filter value actually changed.
                        if (hasAmountFilterChanged) {
                            onFilterChange()
                        }
                    }}
                    // @ts-expect-error - CurrencyInputProps doesn't have a variant prop but Input does
                    variant={"outline"}
                    customInput={Input}
                />
            </div>
            <div>
                <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                        <Button variant="outline" size='md' className="min-w-32 text-start">
                            {typeFilter === 'All' ? <DollarSign className="text-ink-gray-5" /> : typeFilter === 'Debits' ? <ArrowUpRight className="text-ink-red-3" /> : <ArrowDownRight className="text-ink-green-3" />}
                            {_(typeFilter)}
                            <ChevronDown className="text-ink-gray-5" />
                        </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent>
                        <DropdownMenuItem onClick={() => onTypeFilterChange('All')}><DollarSign /> {_("All")}</DropdownMenuItem>
                        <DropdownMenuItem onClick={() => onTypeFilterChange('Debits')}><ArrowUpRight className="text-ink-red-3" /> {_("Debits")}</DropdownMenuItem>
                        <DropdownMenuItem onClick={() => onTypeFilterChange('Credits')}><ArrowDownRight className="text-ink-green-3" /> {_("Credits")}</DropdownMenuItem>
                    </DropdownMenuContent>
                </DropdownMenu>
            </div>
        </div>

        {error && <ErrorBanner error={error} />}

        <OlderUnreconciledTransactionsBanner />

        {results.length === 0 && <NoTransactionsFoundBanner
            onClearFilters={hasFilters ? onClearFilters : undefined}
            text={hasFilters ? _("No transactions found for the given filters.") : _("No unreconciled transactions found")}
            description={hasFilters ? _("Try adjusting your search or filter criteria.") : _("Import your bank statement to get started.")} />}

        <VirtualizedListBody
            items={results}
            height={listHeight}
            estimateSize={74}
            getItemKey={(transaction) => transaction.name}
        >
            {(transaction) => <UnreconciledTransactionItem transaction={transaction} />}
        </VirtualizedListBody>

    </div>
}

const NoTransactionsFoundBanner = ({ text, description, onClearFilters }: { text: string, description?: string, onClearFilters?: () => void }) => {

    return <Empty>
        <EmptyMedia>
            <ListIcon />
        </EmptyMedia>
        <EmptyHeader>
            <EmptyTitle>{text}</EmptyTitle>
            {description && <EmptyDescription>{description}</EmptyDescription>}
        </EmptyHeader>
        <EmptyContent>
            {onClearFilters ? <Button type='button' size='sm' variant='subtle' onClick={onClearFilters}>Clear Filters</Button> :
                <Button type='button' asChild size='sm' variant='subtle'>
                    <Link to="/statement-importer">
                        {_("Import Bank Statement")}
                    </Link>
                </Button>}
        </EmptyContent>
    </Empty>
}

const UnreconciledTransactionsLoadingState = () => {

    return <div className="flex flex-col gap-2 py-2">
        <div className="flex items-center gap-2 pb-2">
            <Skeleton className="h-9.5 w-full" />
            <Skeleton className="h-9.5 min-w-36" />
            <Skeleton className="h-9.5 min-w-32" />
        </div>
        {Array.from({ length: 6 }).map((_, index) => (
            <Skeleton key={index} className="h-16 w-full" />
        ))}
    </div>
}

const UnreconciledTransactionItem = ({ transaction }: { transaction: UnreconciledTransaction }) => {

    const selectedBank = useAtomValue(selectedBankAccountAtom)

    const [selectedTransaction, setSelectedTransaction] = useAtom(bankRecSelectedTransactionAtom(selectedBank?.name || ''))

    const { amount, isWithdrawal } = useIsTransactionWithdrawal(transaction)

    const isSelected = selectedTransaction?.some((t) => t.name === transaction.name)

    const currency = transaction.currency ?? selectedBank?.account_currency ?? getCompanyCurrency(selectedBank?.company ?? '')

    const handleSelectTransaction = (event: React.MouseEvent<HTMLDivElement>) => {
        // If the user is pressing the shift key, add/remove the transaction from the selected transactions
        if (event.shiftKey) {
            setSelectedTransaction(isSelected ? selectedTransaction.filter((t) => t.name !== transaction.name) : [...selectedTransaction, transaction])
        } else {
            setSelectedTransaction([transaction])
        }
    }

    return <div className="py-1">
        <div className={cn("border outline rounded-md p-2 mx-0.5 cursor-pointer transition-[color,box-shadow, bg] hover:bg-surface-gray-1",
            isSelected ? "bg-surface-gray-1 border-outline-gray-5 outline-outline-gray-5" : "border-outline-gray-2 outline-none"
        )}
            role='button'
            tabIndex={0}
            onClick={handleSelectTransaction}>
            <div className="flex justify-between items-start w-full">
                <div className="space-y-1 overflow-hidden whitespace-pre-wrap">
                    <div className="flex items-center gap-1">
                        <span className="font-medium text-sm">{formatDate(transaction.date)}</span>
                        {transaction.transaction_type &&
                            <Badge theme="blue">{transaction.transaction_type}</Badge>}
                        {transaction.reference_number && <Badge
                            title={transaction.reference_number}
                            className="max-w-[300px] text-ellipsis"
                        >
                            {_("Ref")}: {transaction.reference_number}</Badge>}

                        {transaction.matched_transaction_rule && <Badge
                            theme="violet"
                            title={_("Matched by rule")}>
                            <ZapIcon className="w-4 h-4" /> {transaction.matched_transaction_rule}</Badge>}
                    </div>
                    <span className="text-sm wrap-anywhere" title={transaction.description}>{transaction.description}</span>
                </div>
                <div className="gap-1 flex flex-col items-end min-w-36 h-full text-end">
                    {isWithdrawal ? <ArrowUpRight className="size-5 text-ink-red-3" /> : <ArrowDownRight className="size-5 text-ink-green-3" />}
                    {amount && amount > 0 && <span className="font-semibold font-numeric text-base">{formatCurrency(amount, currency)}</span>}
                    {amount !== transaction.unallocated_amount && <span className="text-xs leading-normal text-ink-gray-5">{formatCurrency(transaction.unallocated_amount, currency)} {_("Unallocated")}</span>}
                </div>
            </div>
        </div>
    </div>
}


const VouchersSection = ({ contentHeight }: { contentHeight: number }) => {

    const selectedBank = useAtomValue(selectedBankAccountAtom)
    const selectedTransactions = useAtomValue(bankRecSelectedTransactionAtom(selectedBank?.name || ''))


    if (selectedTransactions.length === 0) {
        return <Empty>
            <EmptyMedia>
                <ReceiptIcon />
            </EmptyMedia>
            <EmptyHeader>
                <EmptyTitle>{_("Select a transaction to match and reconcile with vouchers")}</EmptyTitle>
            </EmptyHeader>
        </Empty>
    }

    if (selectedTransactions.length > 1) {
        return <OptionsForMultipleTransactions transactions={selectedTransactions} />
    }

    return <div style={{ minHeight: contentHeight }} className="mt-2">
        <OptionsForSingleTransaction transaction={selectedTransactions[0]} contentHeight={contentHeight} />
    </div>
}

const useKeyboardShortcuts = () => {
    const setTransferModalOpen = useSetAtom(bankRecTransferModalAtom)
    const setRecordPaymentModalOpen = useSetAtom(bankRecRecordPaymentModalAtom)
    const setRecordJournalEntryModalOpen = useSetAtom(bankRecRecordJournalEntryModalAtom)

    useHotkeys('meta+p', () => {
        // 
        setRecordPaymentModalOpen(true)
    }, {
        enabled: true,
        enableOnFormTags: false,
        preventDefault: true
    })

    useHotkeys('meta+b', () => {
        // 
        setRecordJournalEntryModalOpen(true)
    }, {
        enabled: true,
        enableOnFormTags: false,
        preventDefault: true
    })

    useHotkeys('meta+i', () => {
        // 
        setTransferModalOpen(true)
    }, {
        enabled: true,
        enableOnFormTags: false,
        preventDefault: true
    })

    return {
        setTransferModalOpen,
        setRecordPaymentModalOpen,
        setRecordJournalEntryModalOpen
    }
}

const OptionsForMultipleTransactions = ({ transactions }: { transactions: UnreconciledTransaction[] }) => {

    const { setTransferModalOpen, setRecordPaymentModalOpen, setRecordJournalEntryModalOpen } = useKeyboardShortcuts()

    return <div className="flex flex-col py-4">
        <Card className="gap-2">
            <CardHeader>
                <CardTitle>
                    <div className="flex items-center justify-between">
                        <span className="text-md font-medium">{transactions.length} {_(transactions.length === 1 ? _("transaction selected") : _("transactions selected"))}</span>
                        <span className="text-md font-medium font-numeric">
                            {formatCurrency(transactions.reduce((acc, transaction) => acc + (transaction.unallocated_amount ?? 0), 0), transactions[0].currency ?? '')}
                        </span>
                    </div>
                </CardTitle>
            </CardHeader>
            <CardContent>
                <SelectedTransactionsTable />

                <CardAction className="mt-4 justify-self-center">
                    <div className="flex gap-3 justify-center">
                        <TooltipProvider>
                            <div className="flex gap-4 justify-center">
                                <Tooltip>
                                    <TooltipTrigger asChild>
                                        <Button
                                            size='md'
                                            aria-label={_("Record a bank journal entry for expenses, income or split transactions")}
                                            onClick={() => setRecordJournalEntryModalOpen(true)}>
                                            <Landmark /> {_("Bank Entry")}
                                        </Button>
                                    </TooltipTrigger>
                                    <TooltipContent>
                                        {_("Record a journal entry for expenses, income or split transactions")}
                                        <KbdGroup className="ms-2">
                                            <Kbd><KeyboardMetaKeyIcon /></Kbd>
                                            <Kbd>B</Kbd>
                                        </KbdGroup>
                                    </TooltipContent>
                                </Tooltip>
                                <Tooltip>
                                    <TooltipTrigger asChild>
                                        <Button
                                            variant='outline'
                                            size='md'
                                            aria-label={_("Record a payment entry against a customer or supplier")}
                                            onClick={() => setRecordPaymentModalOpen(true)}>
                                            <Receipt /> {_("Record Payment")}
                                        </Button>
                                    </TooltipTrigger>
                                    <TooltipContent>
                                        {_("Record a payment entry against a customer or supplier")}
                                        <KbdGroup className="ms-2">
                                            <Kbd><KeyboardMetaKeyIcon /></Kbd>
                                            <Kbd>P</Kbd>
                                        </KbdGroup>
                                    </TooltipContent>
                                </Tooltip>

                                <Tooltip>
                                    <TooltipTrigger asChild>
                                        <Button
                                            variant='outline'
                                            size='md'
                                            aria-label={_("Record an internal transfer to another bank/credit card/cash account")}
                                            onClick={() => setTransferModalOpen(true)}>
                                            <ArrowRightLeft /> {_("Transfer")}
                                        </Button>
                                    </TooltipTrigger>
                                    <TooltipContent>
                                        {_("Record an internal transfer to another bank/credit card/cash account")}
                                        <KbdGroup className="ms-2">
                                            <Kbd><KeyboardMetaKeyIcon /></Kbd>
                                            <Kbd>I</Kbd>
                                        </KbdGroup>
                                    </TooltipContent>
                                </Tooltip>

                            </div>
                        </TooltipProvider>
                    </div>
                </CardAction>
            </CardContent>
        </Card>

    </div>
}


const OptionsForSingleTransaction = ({ transaction, contentHeight }: { transaction: UnreconciledTransaction, contentHeight: number }) => {

    const { setTransferModalOpen, setRecordPaymentModalOpen, setRecordJournalEntryModalOpen } = useKeyboardShortcuts()

    return <div className="flex flex-col gap-3">
        <TooltipProvider>
            <div className="flex items-center justify-between pt-2">
                <div className="flex gap-4 justify-center">
                    <Tooltip>
                        <TooltipTrigger asChild>
                            <Button
                                variant='outline'
                                size='md'
                                aria-label={_("Record a payment entry against a customer or supplier")}
                                onClick={() => setRecordPaymentModalOpen(true)}>
                                <Receipt /> {_("Record Payment")}
                            </Button>
                        </TooltipTrigger>
                        <TooltipContent>
                            {_("Record a payment entry against a customer or supplier")}
                            <KbdGroup className="ms-2">
                                <Kbd><KeyboardMetaKeyIcon /></Kbd>
                                <Kbd>P</Kbd>
                            </KbdGroup>
                        </TooltipContent>
                    </Tooltip>
                    <Tooltip>
                        <TooltipTrigger asChild>
                            <Button
                                variant='outline'
                                size='md'
                                aria-label={_("Record a bank journal entry for expenses, income or split transactions")}
                                onClick={() => setRecordJournalEntryModalOpen(true)}>
                                <Landmark /> {_("Bank Entry")}
                            </Button>
                        </TooltipTrigger>
                        <TooltipContent>
                            {_("Record a journal entry for expenses, income or split transactions")}
                            <KbdGroup className="ms-2">
                                <Kbd><KeyboardMetaKeyIcon /></Kbd>
                                <Kbd>B</Kbd>
                            </KbdGroup>
                        </TooltipContent>
                    </Tooltip>
                    <Tooltip >
                        <TooltipTrigger asChild>
                            <Button
                                variant='outline'
                                size='md'
                                aria-label={_("Record an internal transfer to another bank/credit card/cash account")}
                                onClick={() => setTransferModalOpen(true)}>
                                <ArrowRightLeft /> {_("Transfer")}
                            </Button>
                        </TooltipTrigger>
                        <TooltipContent>
                            {_("Record an internal transfer to another bank/credit card/cash account")}
                            <KbdGroup className="ms-2">
                                <Kbd><KeyboardMetaKeyIcon /></Kbd>
                                <Kbd>I</Kbd>
                            </KbdGroup>
                        </TooltipContent>
                    </Tooltip>
                </div>
                <MatchFilters />
            </div>
        </TooltipProvider>
        {transaction.matched_transaction_rule && <RuleAction transaction={transaction} />}
        <VouchersForTransaction transaction={transaction} contentHeight={contentHeight} />
    </div>
}

const RuleAction = ({ transaction }: { transaction: UnreconciledTransaction }) => {

    const { data: rule } = useGetRuleForTransaction(transaction)
    const setTransferModalOpen = useSetAtom(bankRecTransferModalAtom)
    const setRecordPaymentModalOpen = useSetAtom(bankRecRecordPaymentModalAtom)
    const setRecordJournalEntryModalOpen = useSetAtom(bankRecRecordJournalEntryModalAtom)

    const getActionIcon = () => {
        if (!rule) return null
        switch (rule.classify_as) {
            case "Bank Entry":
                return <Landmark />
            case "Payment Entry":
                return <Receipt className="w-6 h-6" />
            case "Transfer":
                return <ArrowRightLeft />
            default:
                return <ZapIcon />
        }
    }

    const getActionStyles = () => {
        if (!rule) return {}
        switch (rule.classify_as) {
            case "Bank Entry":
                return {
                    border: "border-outline-blue-3",
                    bg: "bg-surface-blue-1/50",
                    text: "text-ink-blue-4",
                    theme: "blue",
                }
            case "Payment Entry":
                return {
                    border: "border-outline-green-3",
                    bg: "bg-surface-green-1/50",
                    text: "text-ink-green-4",
                    theme: "green",
                }
            case "Transfer":
                return {
                    border: "border-outline-violet-3",
                    bg: "bg-surface-violet-2/50",
                    text: "text-ink-violet-4",
                    theme: "violet",
                }
            default:
                return {
                    border: "border-outline-amber-3",
                    bg: "bg-surface-amber-1/50",
                    text: "text-ink-amber-4",
                    theme: "orange",
                }
        }
    }

    const handleActionClick = () => {
        if (!rule) return
        switch (rule.classify_as) {
            case "Bank Entry":
                setRecordJournalEntryModalOpen(true)
                break
            case "Payment Entry":
                setRecordPaymentModalOpen(true)
                break
            case "Transfer":
                setTransferModalOpen(true)
                break
        }
    }

    const getActionDescription = () => {
        if (!rule) return ""
        switch (rule.classify_as) {
            case "Bank Entry":
                return _("Create a journal entry for expenses, income or split transactions")
            case "Payment Entry":
                return _("Record a payment entry against a customer or supplier")
            case "Transfer":
                return _("Record an internal transfer to another bank/credit card/cash account")
            default:
                return _("Create a new entry based on the rule")
        }
    }

    useHotkeys('alt+r', () => {
        handleActionClick()
    }, {
        enabled: true,
        enableOnFormTags: false,
        preventDefault: true
    })

    const styles = getActionStyles()

    if (!rule) {
        return null
    }

    return (
        <Card className={`border ${styles.border} ${styles.bg} shadow-sm hover:shadow-md transition-all duration-200`}>
            <CardHeader className="pb-0">
                <CardTitle className="flex justify-between items-center gap-3">
                    <div className="flex items-center gap-3">
                        <div className={`px-2.5 rounded-lg ${styles.bg} ${styles.text}`}>
                            {getActionIcon()}
                        </div>
                        <div className="flex flex-col gap-0.5">
                            <span className="font-semibold text-lg">{rule.rule_name}</span>
                            <span className="text-sm text-ink-gray-5 font-normal">
                                {rule.rule_description || _("Rule matched based on transaction description and other criteria.")}
                            </span>
                        </div>
                    </div>
                    <div className="flex items-center gap-0.5">
                        <Badge size='lg'
                            theme={rule.classify_as === "Bank Entry" ? "blue" : rule.classify_as === "Payment Entry" ? "green" : rule.classify_as === "Transfer" ? "violet" : "orange"}>
                            {rule.classify_as}
                        </Badge>
                    </div>
                </CardTitle>
            </CardHeader>
            <CardContent className="pt-0 space-y-3">
                <div className="flex items-center justify-between p-2 bg-surface-white rounded-lg border border-outline-gray-1">
                    <div className="flex items-center gap-2">
                        <BadgeCheck className="w-4 h-4 text-ink-green-3" />
                        <span className="text-sm font-medium text-ink-gray-8">{_("Recommended Action")}</span>
                    </div>
                    <Badge variant="ghost" theme={styles.theme as "blue" | "green" | "violet" | "orange"}>
                        {_("Priority")} {rule.priority}
                    </Badge>
                </div>

                <div className="space-y-2">

                    {rule.account && (
                        <div className="flex items-center gap-2">
                            <span className="text-sm font-medium text-ink-gray-8">{_("Account")}:</span>
                            <span className="text-sm">{rule.account}</span>
                        </div>
                    )}

                    {rule.party_type && rule.party && (
                        <div className="flex items-center gap-2">
                            <span className="text-sm font-medium text-ink-gray-8">{_("Party")}:</span>
                            <span className="text-sm">{rule.party} ({_(rule.party_type)})</span>
                        </div>
                    )}
                </div>

                <div className="pt-1">
                    <Button
                        onClick={handleActionClick}
                        className={`w-full`}
                        theme={styles.theme as "blue" | "green" | "violet"}
                        size="md"
                    >
                        {getActionIcon()}
                        <span>{_("Create")} {rule.classify_as}</span>
                    </Button>
                    <p className="text-sm text-ink-gray-5 mt-2 text-center leading-relaxed">
                        {getActionDescription()}
                    </p>
                </div>
            </CardContent>
        </Card>
    )
}

const VouchersForTransaction = ({ transaction, contentHeight }: { transaction: UnreconciledTransaction, contentHeight: number }) => {

    const { data: vouchers, isLoading, error } = useGetVouchersForTransaction(transaction)

    const voucherList = vouchers?.message ?? []
    const listHeight = contentHeight - 120

    if (error) {
        return <ErrorBanner error={error} />
    }

    if (isLoading) {
        return <div className="flex flex-col gap-2">
            <div className="flex items-center gap-2 text-sm text-ink-gray-5">
                <Separator className="flex-1" />
                <span>or</span>
                <Separator className="flex-1" />
            </div>
            <Skeleton className="h-16 w-full" />
            <Skeleton className="h-16 w-full" />
            <Skeleton className="h-16 w-full" />
            <Skeleton className="h-16 w-full" />
            <Skeleton className="h-16 w-full" />
            <Skeleton className="h-16 w-full" />
        </div>
    }

    return <div className="relative space-y-2">
        <div className="flex items-center gap-2 text-sm text-ink-gray-5">
            <Separator className="flex-1" />
            <span>or</span>
            <Separator className="flex-1" />
        </div>
        {voucherList.length === 0 && <Empty className="my-4">
            <EmptyMedia>
                <ReceiptIcon />
            </EmptyMedia>
            <EmptyHeader>

                <EmptyTitle>{_("No vouchers found for this transaction")}</EmptyTitle>
            </EmptyHeader>
        </Empty>}
        <VirtualizedListBody
            items={voucherList}
            height={listHeight}
            estimateSize={121}
            getItemKey={(voucher) => voucher.name}
        >
            {(voucher, index) => <VoucherItem voucher={voucher} index={index} />}
        </VirtualizedListBody>
    </div >
}

const VoucherItem = ({ voucher, index }: { voucher: LinkedPayment, index: number }) => {

    const selectedBank = useAtomValue(selectedBankAccountAtom)
    const selectedTransaction = useAtomValue(bankRecSelectedTransactionAtom(selectedBank?.name || ''))

    const { amountMatches, postingDateMatches, referenceDateMatches, referenceMatchesFull, referenceMatchesPartial, isSuggested } = useMemo(() => {

        const transaction = selectedTransaction?.[0]

        // We need to check if the following details match:
        // Amount
        // Date
        // Reference/Description: Full or partial
        // Whether this is suggested or not - depends on the above scores

        const amountMatches = voucher.paid_amount === transaction?.unallocated_amount
        const postingDateMatches = voucher.posting_date === transaction?.date
        const referenceDateMatches = voucher.reference_date === transaction?.date
        const referenceMatchesFull = voucher.reference_no === transaction?.reference_number || voucher.reference_no === transaction?.description

        const referenceMatchesPartial = transaction?.reference_number?.includes(voucher.reference_no) || transaction?.description?.includes(voucher.reference_no)


        const isSuggested = amountMatches && (postingDateMatches || referenceDateMatches || referenceMatchesPartial) && index === 0

        return { isSelected: false, amountMatches, postingDateMatches, referenceDateMatches, referenceMatchesFull, referenceMatchesPartial, isSuggested: isSuggested }

    }, [voucher, selectedTransaction, index])

    const { reconcileTransaction, loading } = useReconcileTransaction()

    const onClick = () => {
        if (!selectedTransaction) {
            return
        }
        reconcileTransaction(selectedTransaction[0], voucher)
    }

    return <div className="py-1 px-1">
        <div
            className={cn("border outline overflow-hidden relative rounded-md p-2",
                isSuggested ? "border-outline-green-4 bg-surface-green-1/40 outline-outline-green-4" : "border-outline-gray-2 outline-transparent"
            )}
        >

            <div className="flex justify-between items-end gap-2">
                <div className="flex flex-col gap-2">
                    <div className="flex items-center gap-2">
                        <Badge size='md'>{_(voucher.doctype)}</Badge>
                        <a target="_blank"
                            href={`/desk/${slug(voucher.doctype)}/${voucher.name}`}
                            className="underline underline-offset-2 text-base"
                        >{voucher.name}</a>
                    </div>
                    {voucher.party && voucher.party_type && <div className="flex items-center gap-1.5 text-base">
                        <User size='18px' />
                        <span>{_(voucher.party_type)}</span>
                        <a target="_blank"
                            href={`/desk/${slug(voucher.party_type)}/${voucher.party}`}
                            className="underline underline-offset-2"
                        >{voucher.party}</a>
                    </div>}
                    <TooltipProvider>
                        <div className="flex items-start gap-8 py-0.5">
                            <div className="flex flex-col gap-1 min-w-24">
                                <div className="text-xs text-ink-gray-6">{_("Amount")}</div>
                                <div className="text-base font-medium flex items-center gap-1">{formatCurrency(voucher.paid_amount, voucher.currency)} {amountMatches ? <MatchBadge matchType="full" label={_("Amount matches the selected transaction")} /> : <MatchBadge matchType="none" label={_("Amount does not match the selected transaction")} />}</div>
                            </div>

                            <div className="flex flex-col gap-1 min-w-24">
                                <div className="text-xs text-ink-gray-6">{_("Posted On")}</div>
                                <div className="text-base font-medium flex items-center gap-1">{formatDate(voucher.posting_date)} {postingDateMatches ? <MatchBadge matchType="full" label={_("Posting date matches the selected transaction")} /> : <MatchBadge matchType="none" label={_("Posting date does not match the selected transaction")} />}</div>
                            </div>

                            {voucher.reference_date && <div className="flex flex-col gap-1 min-w-24">
                                <div className="text-xs text-ink-gray-6">{_("Reference Date")}</div>
                                <div className="text-base font-medium flex items-center gap-1">{formatDate(voucher.reference_date)} {referenceDateMatches ? <MatchBadge matchType="full" label={_("Reference date matches the selected transaction")} /> : <MatchBadge matchType="none" label={_("Reference date does not match the selected transaction")} />}</div>
                            </div>}

                        </div>
                        {voucher.reference_no && <div className="flex items-start gap-1">
                            <span className="text-p-base">
                                {voucher.reference_no}
                                &nbsp;&nbsp;
                                <Tooltip>
                                    <TooltipTrigger>
                                        <Badge theme={referenceMatchesFull ? "green" : referenceMatchesPartial ? "orange" : "red"} variant={referenceMatchesFull || referenceMatchesPartial ? "subtle" : "outline"}>
                                            {referenceMatchesFull ? `${_("Complete Match")}` : referenceMatchesPartial ? `${_("Partial Match")}` : `${_("No Match")}`}</Badge>
                                    </TooltipTrigger>
                                    <TooltipContent side="top">
                                        {referenceMatchesFull ? `${_("Reference matches the selected transaction")}` : referenceMatchesPartial ? `${_("Reference matches the selected transaction partially")}` : `${_("Reference does not match the selected transaction")}`}
                                    </TooltipContent>
                                </Tooltip>
                            </span>
                        </div>}
                    </TooltipProvider>
                </div>
                <div>
                    <Button
                        variant={isSuggested || amountMatches ? "solid" : "outline"}
                        theme={isSuggested || amountMatches ? "green" : "gray"}
                        onClick={onClick} disabled={loading}>{loading ? <><Loader2 className="w-4 h-4 animate-spin" /> {_("Reconciling")}...</> : `${_("Reconcile")}`}</Button>
                </div>
            </div>

            {isSuggested && <div className="absolute top-1.5 end-2 flex items-center gap-1 justify-center">
                <Badge theme="green" variant="subtle" size='md'>{_("Suggested")}</Badge>
            </div>}

        </div>
    </div>
}


const MatchBadge = ({ matchType, label }: { matchType: 'full' | 'partial' | 'none', label: string }) => {
    return <Tooltip>
        <TooltipTrigger>
            {matchType === 'full' ? <BadgeCheck className="text-ink-white fill-surface-green-5 size-4" /> : matchType === 'partial' ?
                <Badge theme="orange" variant="subtle">{_("Partial Match")}</Badge> :
                <XCircle className="text-ink-red-4 size-4" />}
        </TooltipTrigger>
        <TooltipContent>
            {label}
        </TooltipContent>
    </Tooltip>
}

const OlderUnreconciledTransactionsBanner = () => {

    // A banner to show when there are unreconciled transactions for the given bank account before the current selected date
    const [dates, setDates] = useAtom(bankRecDateAtom)
    const selectedBank = useAtomValue(selectedBankAccountAtom)

    const { data } = useFrappeGetCall<{
        message: {
            count: number,
            oldest_date: string
        }
    }>("erpnext.accounts.doctype.bank_reconciliation_tool.bank_reconciliation_tool.get_older_unreconciled_transactions", {
        bank_account: selectedBank?.name,
        from_date: dates.fromDate,
    }, undefined, {
        revalidateOnFocus: false,
    })

    if (data && data.message.count > 0) {

        return <Alert theme='gray' variant='subtle'>
            <AlertCircleIcon />
            <div className="flex justify-between items-center gap-1.5">
                <div>
                    <AlertTitle> {data.message.count > 1 ? (
                        <span>{_("There are {0} unreconciled transactions before {1}.", [data.message.count.toString(), formatDate(dates.fromDate)])}</span>
                    ) : (
                        <span>{_("There is one unreconciled transaction before {0}.", [formatDate(dates.fromDate)])}</span>
                    )}</AlertTitle>
                    <AlertDescription className="flex justify-between text-balance">
                        {_("The opening balance might not match your bank statement. Would you like to reconcile them?")}
                    </AlertDescription>
                </div>
                <div>
                    <Button
                        size='sm'
                        type='button'
                        theme='gray'
                        variant='outline'
                        onClick={() => setDates({ fromDate: data.message.oldest_date, toDate: dates.toDate })}>
                        <span>{data.message.count > 1 ? _("View older transactions") : _("View older transaction")}</span>
                        <ArrowRightIcon />
                    </Button>
                </div>
            </div>
        </Alert>
    }

    return null

}

export default MatchAndReconcile