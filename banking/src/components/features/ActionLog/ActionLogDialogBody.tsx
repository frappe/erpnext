import { Button } from '@/components/ui/button'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import _ from '@/lib/translate'
import { useAtomValue, useSetAtom } from 'jotai'
import { ArrowDownRight, ArrowRightLeftIcon, ArrowUpRight, CalendarIcon, CircleXIcon, GitCompareIcon, HistoryIcon, LandmarkIcon, Loader2Icon, ReceiptIcon, ReceiptTextIcon, UserIcon, WalletIcon } from 'lucide-react'
import { useMemo, useState } from 'react'
import { ActionLogItem, ActionLog as ActionLogType, bankRecActionLog, bankRecDateAtom, bankRecMatchFilters, SelectedBank, selectedBankAccountAtom } from '../BankReconciliation/bankRecAtoms'
import { useGetBankAccounts } from '../BankReconciliation/utils'
import { getCompanyCurrency } from '@/lib/company'
import { formatCurrency } from '@/lib/numbers'
import dayjs from 'dayjs'
import { cn } from '@/lib/utils'
import { formatDate } from '@/lib/date'
import { Separator } from '@/components/ui/separator'
import { slug } from '@/lib/frappe'
import { PaymentEntry } from '@/types/Accounts/PaymentEntry'
import { JournalEntry } from '@/types/Accounts/JournalEntry'
import { HoverCard, HoverCardContent, HoverCardTrigger } from '@/components/ui/hover-card'
import { Table, TableCell, TableBody, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { AlertDialog, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger } from '@/components/ui/alert-dialog'
import { useFrappePostCall, useSWRConfig } from 'frappe-react-sdk'
import { toast } from 'sonner'
import { getErrorMessage } from '@/lib/frappe'
import ErrorBanner from '@/components/ui/error-banner'
import SelectedTransactionDetails from '../BankReconciliation/SelectedTransactionDetails'
import { Empty, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from '@/components/ui/empty'
import BankLogo from '@/components/common/BankLogo'

const ActionLogDialogBody = () => {

    const actionLog = useAtomValue(bankRecActionLog)

    return <div className='flex flex-col gap-2'>
        {actionLog.map((action) => (
            <div key={action.timestamp} className='flex flex-col gap-1'>
                <ActionGroupHeader action={action} />
                <div>
                    <div className='ms-2 border-s border-s-outline-gray-2 py-1'>
                        <div className='ms-5'>
                            {action.items.map((item, index) => (
                                <Row
                                    item={item}
                                    key={item.bankTransaction.name}
                                    index={index}
                                    action={action}
                                    isLast={index === action.items.length - 1} />
                            ))}
                        </div>
                    </div>
                </div>
            </div>
        ))}

        {actionLog.length === 0 && <Empty>
            <EmptyMedia>
                <HistoryIcon />
            </EmptyMedia>
            <EmptyHeader>
                <EmptyTitle>{_("No reconciliation actions found")}</EmptyTitle>
                <EmptyDescription>{_("You have not performed any reconciliations in this session yet.")}</EmptyDescription>
            </EmptyHeader>
        </Empty>}
    </div>
}



const ActionGroupHeader = ({ action }: { action: ActionLogType }) => {

    const label = useMemo(() => {
        switch (action.type) {
            case 'match':
                return _("Matched")
            case 'payment':
                if (action.isBulk) {
                    return _("Bulk Payment")
                }
                return _("Payment")

            case 'transfer':
                if (action.isBulk) {
                    return _("Bulk Transfer")
                }
                return _("Transfer")

            case 'bank_entry':
                if (action.isBulk) {
                    return _("Bulk Bank Entry")
                }
                return _("Bank Entry")

            default:
                return _("Action")
        }
    }, [action])

    return <div className='flex items-center gap-2 text-ink-gray-5'>
        {action.type === 'match' && <GitCompareIcon className='w-4 h-4' />}
        {action.type === 'payment' && <ReceiptIcon className='w-4 h-4' />}
        {action.type === 'transfer' && <ArrowRightLeftIcon className='w-4 h-4' />}
        {action.type === 'bank_entry' && <LandmarkIcon className='w-4 h-4' />}
        <span className='flex items-center gap-2 text-sm'>
            {label} - {dayjs(action.timestamp).fromNow()}
        </span>
    </div>
}

const Row = ({ item, index, isLast, action }: { item: ActionLogItem, index: number, isLast: boolean, action: ActionLogType }) => {

    const isWithdrawal = item.bankTransaction.withdrawal && item.bankTransaction.withdrawal > 0

    const { banks } = useGetBankAccounts()

    const bank = useMemo(() => {
        if (item.bankTransaction.bank_account) {
            return banks?.find((bank) => bank.name === item.bankTransaction.bank_account)
        }
        return null
    }, [item.bankTransaction.bank_account, banks])

    const amount = item.bankTransaction.withdrawal ? item.bankTransaction.withdrawal : item.bankTransaction.deposit

    const currency = item.bankTransaction.currency || getCompanyCurrency(item.bankTransaction.company ?? '')

    return <div className='flex items-center gap-2 group'>
        <div className={cn('p-3.5 group-hover:bg-surface-gray-1 border-s border-e border-t w-full', isLast ? 'rounded-b border-b' : '', index === 0 ? 'rounded-t' : '')}>
            <div className='flex justify-between items-center'>
                <div className='flex flex-col gap-2'>
                    <p className='text-p-base'>{item.bankTransaction.description}</p>
                    <div className='flex items-center gap-3'>
                        <div className='flex gap-2 items-center'>
                            <BankLogo bank={bank} className='h-4 mb-0' iconSize='16px' />
                            <span className='text-sm text-ink-gray-5'>{item.bankTransaction.bank_account}</span>
                        </div>
                        <Separator orientation='vertical' />
                        <div className='flex items-center gap-2 text-ink-gray-5 text-sm' title={_("Transaction Date")}>
                            <CalendarIcon className='w-4 h-4' />
                            <span className='text-sm'>{formatDate(item.bankTransaction.date, 'Do MMM YYYY')}</span>
                        </div>
                        <Separator orientation='vertical' />
                        <div>
                            <div className='flex items-center gap-1' title={isWithdrawal ? _("Spent") : _("Received")}>
                                {isWithdrawal ? <ArrowUpRight className="w-5 h-5 text-ink-red-3" /> : <ArrowDownRight className="w-5 h-5 text-ink-green-3" />}
                                <span className='text-sm text-ink-gray-5'>{formatCurrency(amount, currency)}</span>
                            </div>
                        </div>
                    </div>
                </div>
                <div className='flex justify-end items-center gap-2'>
                    <div className='text-end flex flex-col gap-2'>
                        <a
                            href={`/desk/${slug(item.voucher.reference_doctype)}/${item.voucher.reference_name}`}
                            target='_blank'
                            className='underline underline-offset-4 text-base'>
                            {["Payment Entry", "Journal Entry"].includes(item.voucher.reference_doctype) ? "" : _("{} :", [item.voucher.reference_doctype])} {item.voucher.reference_name}
                        </a>
                        {item.voucher.reference_doctype === "Payment Entry" && item.voucher.doc && <PaymentEntryDetails item={item} />}
                        {item.voucher.reference_doctype === "Journal Entry" && <JournalEntryDetails item={item} bank={bank} />}
                    </div>
                </div>
            </div>
        </div>
        <div className='w-10 h-10 flex items-center justify-center'>
            <CancelActionLogItem item={item} type={action.type} timestamp={action.timestamp} bank={bank} />
        </div>
    </div>
}

const JournalEntryDetails = ({ item, bank }: { item: ActionLogItem, bank?: SelectedBank | null }) => {

    return <div className='flex items-center gap-2 text-ink-gray-5 justify-end'>
        <WalletIcon className='w-4 h-4' />
        <JournalEntryAccountsTable item={item} bank={bank} />
    </div>
}

const JournalEntryAccountsTable = ({ item, bank }: { item: ActionLogItem, bank?: SelectedBank | null }) => {

    const accounts = useMemo(() => {

        const allAccounts = (item.voucher.doc as JournalEntry).accounts

        return allAccounts.filter((acc) => bank ? acc.account !== bank.account : true)

    }, [item, bank])

    return <>
        {accounts.length === 1 ? <span className='text-sm'>{accounts[0].account}</span> :
            <HoverCard>
                <HoverCardTrigger>
                    <span className='text-sm cursor-pointer hover:underline underline-offset-4'>{_("Split across {} accounts", [accounts.length.toString()])}</span>
                </HoverCardTrigger>
                <HoverCardContent className='w-full p-2' align='end'>
                    <Table>
                        <TableHeader>
                            <TableRow>
                                <TableHead>{_("Account")}</TableHead>
                                <TableHead className='text-end'>{_("Debit")}</TableHead>
                                <TableHead className='text-end'>{_("Credit")}</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {accounts.map((account) => (
                                <TableRow key={account.account}>
                                    <TableCell>{account.account}</TableCell>
                                    <TableCell className='text-end font-numeric'>{formatCurrency(account.debit ?? 0, account.account_currency ?? '')}</TableCell>
                                    <TableCell className='text-end font-numeric'>{formatCurrency(account.credit ?? 0, account.account_currency ?? '')}</TableCell>
                                </TableRow>
                            ))}
                        </TableBody>
                    </Table>
                </HoverCardContent>
            </HoverCard>
        }</>
}

const PaymentEntryDetails = ({ item, className }: { item: ActionLogItem, className?: string }) => {
    if ((item.voucher.doc as PaymentEntry).payment_type === "Internal Transfer") {
        return <TransferDetails item={item} className={className} />
    }

    const invoices = (item.voucher.doc as PaymentEntry).references ?? []

    const currency = item.bankTransaction.withdrawal && item.bankTransaction.withdrawal > 0 ? (item.voucher.doc as PaymentEntry)?.paid_to_account_currency : (item.voucher.doc as PaymentEntry)?.paid_from_account_currency

    return <div className='flex items-center gap-3'>
        <div className={cn('flex items-center gap-2 text-ink-gray-5 text-sm', className)}>
            <UserIcon className='w-4 h-4' />
            <span className='text-sm'>{(item.voucher.doc as PaymentEntry).party_name}</span>
        </div>
        <Separator orientation='vertical' />
        <HoverCard>
            <HoverCardTrigger>
                <div className={cn('flex items-center gap-2 text-ink-gray-5 text-sm', className)}>
                    <ReceiptTextIcon className='w-4 h-4' />
                    <span className='text-sm cursor-pointer hover:underline underline-offset-4'>{invoices.length === 0 ? _("No invoice linked") : invoices.length === 1 ? _("1 invoice") : _("{} invoices", [invoices.length.toString()])}</span>
                </div>
            </HoverCardTrigger>
            <HoverCardContent className='w-full p-2' align='end'>
                <div className='flex flex-col gap-2'>
                    {invoices.map((invoice) => (
                        <Table>
                            <TableHeader>
                                <TableRow>
                                    <TableHead>{_("Document")}</TableHead>
                                    <TableHead>{_("Invoice No")}</TableHead>
                                    <TableHead>{_("Due Date")}</TableHead>
                                    <TableHead className='text-end'>{_("Grand Total")}</TableHead>
                                    <TableHead className='text-end'>{_("Allocated")}</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                <TableRow>
                                    <TableCell><a href={`/desk/${slug(invoice.reference_doctype)}/${invoice.reference_name}`} target='_blank' className='underline underline-offset-4'>{invoice.reference_doctype}: {invoice.reference_name}</a></TableCell>
                                    <TableCell>{invoice.bill_no ?? "-"}</TableCell>
                                    <TableCell>{formatDate(invoice.due_date)}</TableCell>
                                    <TableCell className='text-end font-numeric'>{formatCurrency(invoice.total_amount, currency ?? '')}</TableCell>
                                    <TableCell className='text-end font-numeric'>{formatCurrency(invoice.allocated_amount, currency ?? '')}</TableCell>
                                </TableRow>
                            </TableBody>
                        </Table>
                    ))}
                </div>
            </HoverCardContent>
        </HoverCard>

    </div>
}

const TransferDetails = ({ item, className }: { item: ActionLogItem, className?: string }) => {

    const { banks } = useGetBankAccounts()

    const bank = useMemo(() => {

        const isWithdrawal = item.bankTransaction.withdrawal && item.bankTransaction.withdrawal > 0

        let transferAccount = ""

        if (isWithdrawal) {
            transferAccount = (item.voucher.doc as PaymentEntry).paid_to
        } else {
            transferAccount = (item.voucher.doc as PaymentEntry).paid_from
        }

        const transferBankAccount = banks?.find((bank) => bank.account === transferAccount)

        return transferBankAccount

    }, [banks, item])

    return <div className={cn('flex items-center gap-2 text-ink-gray-5 text-sm', className)}>
        <BankLogo bank={bank} className='h-5 mb-0' iconSize='16px' imageClassName='max-h-5' />
        <span className='text-sm'>{bank?.account}</span>
    </div>
}

const ACTION_TYPE_MAP = {
    'bank_entry': _("Bank Entry"),
    'payment': _("Payment"),
    'transfer': _("Transfer"),
    'match': _("Match"),
}

const CancelActionLogItem = ({ item, type, timestamp, bank }: { item: ActionLogItem, type: ActionLogType['type'], timestamp: number, bank?: SelectedBank | null }) => {

    const [isOpen, setIsOpen] = useState(false)

    const { call, loading, error } = useFrappePostCall('erpnext.accounts.doctype.bank_transaction.bank_transaction.unreconcile_transaction_entry')
    const { mutate } = useSWRConfig()
    const actionLog = useSetAtom(bankRecActionLog)
    const dates = useAtomValue(bankRecDateAtom)
    const matchFilters = useAtomValue(bankRecMatchFilters)
    const selectedBank = useAtomValue(selectedBankAccountAtom)

    const onUndo = () => {
        call({
            bank_transaction_id: item.bankTransaction.name,
            voucher_type: item.voucher.reference_doctype,
            voucher_id: item.voucher.reference_name,
        }).then(() => {
            toast.success(type === 'match' ? _("Unmatched") : _("Cancelled"))

            if (selectedBank?.name === item.bankTransaction.bank_account) {
                mutate(`bank-reconciliation-unreconciled-transactions-${selectedBank?.name}-${dates.fromDate}-${dates.toDate}`)
                mutate(`bank-reconciliation-account-closing-balance-${selectedBank?.name}-${dates.toDate}`)
                // Update the matching vouchers for the selected transaction
                mutate(`bank-reconciliation-vouchers-${item.bankTransaction.name}-${dates.fromDate}-${dates.toDate}-${matchFilters.join(',')}`)
            }

            setTimeout(() => {
                actionLog((prev) => {
                    // Find the action and then remove the item from the action. If the action is empty, remove the action from the array
                    const action = prev.find((action) => action.timestamp === timestamp)

                    if (action) {
                        action.items = action.items.filter((i) => i.bankTransaction.name !== item.bankTransaction.name)
                    }
                    // If the action is empty, remove the action from the array
                    if (action && action.items.length === 0) {
                        return prev.filter((a) => a.timestamp !== timestamp)
                    } else {
                        return prev.map((a) => a.timestamp === timestamp ? { ...a, items: action?.items ?? [] } : a)
                    }
                })
            }, 100)

            setIsOpen(false)

        }).catch((error) => {
            toast.error(_("There was an error while performing the action."), {
                duration: 5000,
                description: getErrorMessage(error),
            })
        })
    }

    return <AlertDialog open={isOpen} onOpenChange={setIsOpen}>
        <Tooltip>
            <TooltipTrigger asChild>
                <AlertDialogTrigger asChild>
                    <Button
                        variant={'ghost'}
                        isIconButton
                        theme='red'
                        title={_("Cancel")}
                        className='hover:text-ink-red-3 hover:bg-destructive/5 text-ink-gray-5 hidden group-hover:inline-flex'>
                        <CircleXIcon className='w-8 h-8' />
                    </Button>
                </AlertDialogTrigger>
            </TooltipTrigger>
            <TooltipContent>
                {_("Cancel")}
            </TooltipContent>
        </Tooltip>
        <AlertDialogContent className='min-w-3xl'>
            <AlertDialogHeader>
                <AlertDialogTitle>{type === 'match' ? _("Unmatch Transaction?") : _("Undo {}?", [item.voucher.reference_doctype])}</AlertDialogTitle>
                <AlertDialogDescription>{type === 'match' ? _("Are you sure you want to unmatch the voucher from this transaction?") : _("Are you sure you want to cancel this {} {}?", [_(item.voucher.reference_doctype), item.voucher.reference_name])}</AlertDialogDescription>
            </AlertDialogHeader>
            {error && <ErrorBanner error={error} />}
            <div className='flex flex-col gap-2'>
                <SelectedTransactionDetails transaction={item.bankTransaction} />
                <Table>
                    <TableRow>
                        <TableHead>{_("Action Type")}</TableHead>
                        <TableCell>{ACTION_TYPE_MAP[type]}</TableCell>
                    </TableRow>
                    <TableRow>
                        <TableHead>{_("Voucher Type")}</TableHead>
                        <TableCell>{_(item.voucher.reference_doctype)}</TableCell>
                    </TableRow>
                    <TableRow>
                        <TableHead>{_("Voucher Name")}</TableHead>
                        <TableCell><a href={`/desk/${slug(item.voucher.reference_doctype)}/${item.voucher.reference_name}`} target='_blank' className='underline underline-offset-4'>{item.voucher.reference_name}</a></TableCell>
                    </TableRow>
                    <TableRow>
                        <TableHead>{_("Posting Date")}</TableHead>
                        <TableCell>{formatDate(item.voucher.posting_date, 'Do MMM YYYY')}</TableCell>
                    </TableRow>
                    {type === 'transfer' && item.voucher.doc && <TableRow>
                        <TableHead>{_("Transfer Account")}</TableHead>
                        <TableCell>
                            <TransferDetails item={item} className='text-ink-gray-8' />
                        </TableCell>
                    </TableRow>}
                    {type === 'payment' && item.voucher.doc && <TableRow>
                        <TableHead>{_("Payment Details")}</TableHead>
                        <TableCell>
                            <PaymentEntryDetails item={item} className='text-ink-gray-8' />
                        </TableCell>
                    </TableRow>}
                    {type === 'bank_entry' && item.voucher.doc && <TableRow>
                        <TableHead>{_("Account")}</TableHead>
                        <TableCell><JournalEntryAccountsTable item={item} bank={bank} /></TableCell>
                    </TableRow>}
                </Table>
            </div>
            <AlertDialogFooter>
                <AlertDialogCancel disabled={loading}>
                    {_("Close")}
                </AlertDialogCancel>
                <Button theme="red" size='md' disabled={loading} onClick={onUndo}>
                    {loading ? <Loader2Icon className='w-4 h-4 animate-spin' /> : _(("Undo"))}
                </Button>
            </AlertDialogFooter>
        </AlertDialogContent>
    </AlertDialog>
}

export default ActionLogDialogBody
