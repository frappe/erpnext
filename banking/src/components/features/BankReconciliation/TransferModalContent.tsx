import { useAtomValue, useSetAtom } from 'jotai'
import { bankRecSelectedTransactionAtom, bankRecTransferModalAtom, bankRecUnreconcileModalAtom, SelectedBank, selectedBankAccountAtom } from './bankRecAtoms'
import { DialogFooter, DialogClose } from '@/components/ui/dialog'
import _ from '@/lib/translate'
import { UnreconciledTransaction, useGetBankAccounts, useGetRuleForTransaction, useRefreshUnreconciledTransactions, useUpdateActionLog } from './utils'
import { Button } from '@/components/ui/button'
import SelectedTransactionDetails from './SelectedTransactionDetails'
import { PaymentEntry } from '@/types/Accounts/PaymentEntry'
import { useForm, useFormContext, useWatch } from 'react-hook-form'
import { FrappeConfig, FrappeContext, useFrappeGetCall, useFrappePostCall } from 'frappe-react-sdk'
import { toast } from 'sonner'
import ErrorBanner from '@/components/ui/error-banner'
import { H4 } from '@/components/ui/typography'
import { cn } from '@/lib/utils'
import { ArrowRight, Banknote, BadgeCheck, Calendar, ArrowUpRight, ArrowDownRight, CheckIcon, CheckCircle, ArrowLeft } from 'lucide-react'
import { Separator } from '@/components/ui/separator'
import { Form } from '@/components/ui/form'
import { AccountFormField, DataField, DateField, SmallTextField } from '@/components/ui/form-elements'
import SelectedTransactionsTable from './SelectedTransactionsTable'
import { useCurrentCompany } from '@/hooks/useCurrentCompany'
import { useMultiFileUploadProgress } from '@/hooks/useMultiFileUploadProgress'
import { formatDate } from '@/lib/date'
import { useContext, useMemo, useState } from 'react'
import { formatCurrency } from '@/lib/numbers'
import { Label } from '@/components/ui/label'
import { FileDropzone } from '@/components/ui/file-dropzone'
import FileUploadBanner from '@/components/common/FileUploadBanner'
import { BankTransaction } from '@/types/Accounts/BankTransaction'
import { useHotkeys } from 'react-hotkeys-hook'
import { useDirection } from '@/components/ui/direction'
import BankLogo from '@/components/common/BankLogo'
const TransferModalContent = () => {

    const selectedBankAccount = useAtomValue(selectedBankAccountAtom)

    const selectedTransaction = useAtomValue(bankRecSelectedTransactionAtom(selectedBankAccount?.name ?? ''))

    if (!selectedTransaction || !selectedBankAccount || selectedTransaction.length === 0) {
        return <div className='p-4'>
            <span className='text-center'>{_("No transaction selected")}</span>
        </div>
    }

    if (selectedTransaction.length === 1) {
        return <InternalTransferForm
            selectedBankAccount={selectedBankAccount}
            selectedTransaction={selectedTransaction[0]} />
    }

    return <BulkInternalTransferForm transactions={selectedTransaction} />

}

const BulkInternalTransferForm = ({ transactions }: { transactions: UnreconciledTransaction[] }) => {

    const form = useForm<{
        bank_account: string
    }>()

    const setIsOpen = useSetAtom(bankRecTransferModalAtom)

    const { call: createPaymentEntry, loading, error } = useFrappePostCall<{ message: { transaction: BankTransaction, payment_entry: PaymentEntry }[] }>('erpnext.accounts.doctype.bank_reconciliation_tool.bank_reconciliation_tool.create_bulk_internal_transfer')

    const onReconcile = useRefreshUnreconciledTransactions()
    const addToActionLog = useUpdateActionLog()

    const onSubmit = (data: { bank_account: string }) => {

        createPaymentEntry({
            bank_transaction_names: transactions.map((transaction) => transaction.name),
            bank_account: data.bank_account
        }).then(({ message }) => {
            addToActionLog({
                type: 'transfer',
                timestamp: (new Date()).getTime(),
                isBulk: true,
                items: message.map((item) => ({
                    bankTransaction: item.transaction,
                    voucher: {
                        reference_doctype: "Payment Entry",
                        reference_name: item.payment_entry.name,
                        posting_date: item.payment_entry.posting_date,
                        doc: item.payment_entry,
                    }
                })),
                bulkCommonData: {
                    bank_account: data.bank_account,
                }
            })
            toast.success(_("Transfer Recorded"), {
                duration: 4000,
                closeButton: true,
            })
            onReconcile(transactions[transactions.length - 1])
            setIsOpen(false)
        })

    }

    const onAccountChange = (account: string) => {
        form.setValue('bank_account', account)
    }

    const selectedAccount = useWatch({ control: form.control, name: 'bank_account' })

    const currentCompany = useCurrentCompany()

    const company = transactions && transactions.length > 0 ? transactions[0].company : (currentCompany ?? '')

    return <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)}>
            <div className='flex flex-col gap-4'>

                {error && <ErrorBanner error={error} />}

                <SelectedTransactionsTable />

                <BankOrCashPicker company={company} bankAccount={transactions[0]?.bank_account ?? ''} onAccountChange={onAccountChange} selectedAccount={selectedAccount} />

                <DialogFooter>
                    <DialogClose asChild>
                        <Button size='md' variant={'outline'} disabled={loading}>{_("Cancel")}</Button>
                    </DialogClose>
                    <Button size='md' type='submit' disabled={loading}>{_("Transfer")}</Button>
                </DialogFooter>
            </div>
        </form>

    </Form>
}

interface InternalTransferFormFields extends PaymentEntry {
    mirror_transaction_name?: string
}

const InternalTransferForm = ({ selectedBankAccount, selectedTransaction }: { selectedBankAccount: SelectedBank, selectedTransaction: UnreconciledTransaction }) => {


    const setIsOpen = useSetAtom(bankRecTransferModalAtom)

    const onClose = () => {
        setIsOpen(false)
    }

    const { data: rule } = useGetRuleForTransaction(selectedTransaction)

    const isWithdrawal = (selectedTransaction.withdrawal && selectedTransaction.withdrawal > 0) ? true : false

    const form = useForm<InternalTransferFormFields>({
        defaultValues: {
            payment_type: 'Internal Transfer',
            company: selectedTransaction?.company,
            // If the transaction is a withdrawal, set the paid from to the selected bank account
            paid_from: isWithdrawal ? selectedBankAccount.account : (rule?.account ?? ''),
            // If the transaction is a deposit, set the paid to to the selected bank account
            paid_to: !isWithdrawal ? selectedBankAccount.account : (rule?.account ?? ''),
            // Set the amount to the amount of the selected transaction
            paid_amount: selectedTransaction.unallocated_amount,
            received_amount: selectedTransaction.unallocated_amount,
            reference_date: selectedTransaction.date,
            posting_date: selectedTransaction.date,
            reference_no: (selectedTransaction.reference_number || selectedTransaction.description || '').slice(0, 140),
        }
    })

    const onReconcile = useRefreshUnreconciledTransactions()

    const { call: createPaymentEntry, loading, error, isCompleted } = useFrappePostCall<{ message: { transaction: BankTransaction, payment_entry: PaymentEntry } }>('erpnext.accounts.doctype.bank_reconciliation_tool.bank_reconciliation_tool.create_internal_transfer')

    const setBankRecUnreconcileModalAtom = useSetAtom(bankRecUnreconcileModalAtom)
    const addToActionLog = useUpdateActionLog()

    const { file: frappeFile } = useContext(FrappeContext) as FrappeConfig

    const [isUploading, setIsUploading] = useState(false)
    const { uploadProgress, startTracking, updateFileProgress, resetProgress } = useMultiFileUploadProgress()

    const [files, setFiles] = useState<File[]>([])

    const onSubmit = (data: InternalTransferFormFields) => {

        createPaymentEntry({
            bank_transaction_name: selectedTransaction.name,
            ...data,
            custom_remarks: data.remarks ? true : false,
            // Pass this to reconcile both at the same time
            mirror_transaction_name: data.mirror_transaction_name
        }).then(async ({ message }) => {
            addToActionLog({
                type: 'transfer',
                timestamp: (new Date()).getTime(),
                isBulk: false,
                items: [
                    {
                        bankTransaction: message.transaction,
                        voucher: {
                            reference_doctype: "Payment Entry",
                            reference_name: message.payment_entry.name,
                            reference_no: message.payment_entry.reference_no,
                            reference_date: message.payment_entry.reference_date,
                            posting_date: message.payment_entry.posting_date,
                            doc: message.payment_entry,
                        }
                    }
                ]
            })
            toast.success(_("Transfer Recorded"), {
                duration: 4000,
                closeButton: true,
                action: {
                    label: _("Undo"),
                    onClick: () => setBankRecUnreconcileModalAtom(selectedTransaction.name)
                },
                actionButtonStyle: {
                    backgroundColor: "rgb(0, 138, 46)"
                }
            })

            if (files.length > 0) {
                setIsUploading(true)
                startTracking(files.length)

                const uploadPromises = files.map((f, fileIndex) => {
                    return frappeFile.uploadFile(f, {
                        isPrivate: true,
                        doctype: "Payment Entry",
                        docname: message.payment_entry.name,
                    }, (_bytesUploaded, _totalBytes, progress) => {
                        updateFileProgress(fileIndex, progress?.progress ?? 0)
                    })
                })

                return Promise.all(uploadPromises).then(() => {
                    resetProgress()
                    setIsUploading(false)
                })
            } else {
                return Promise.resolve()
            }
        }).then(() => {
            resetProgress()
            setIsUploading(false)
            onReconcile(selectedTransaction)
            onClose()
        })
    }


    useHotkeys('meta+s', () => {
        form.handleSubmit(onSubmit)()
    }, {
        enabled: true,
        preventDefault: true,
        enableOnFormTags: true
    })

    const onAccountChange = (account: string, is_mirror: boolean = false) => {
        //If the transaction is a withdrawal, set the paid to to the selected account - since this is the account where the money is deposited into
        if (selectedTransaction.withdrawal && selectedTransaction.withdrawal > 0) {
            form.setValue('paid_to', account)
        } else {
            form.setValue('paid_from', account)
        }

        if (!is_mirror) {
            // Reset the mirror transaction name
            form.setValue('mirror_transaction_name', '')
        }
    }

    const selectedAccount = useWatch({ control: form.control, name: (selectedTransaction.deposit && selectedTransaction.deposit > 0) ? 'paid_from' : 'paid_to' })

    const direction = useDirection()

    if (isUploading && isCompleted) {
        return <FileUploadBanner uploadProgress={uploadProgress} />
    }

    return <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)}>
            <div className='flex flex-col gap-4'>
                {error && <ErrorBanner error={error} />}
                <div className='grid grid-cols-2 gap-4'>
                    <SelectedTransactionDetails transaction={selectedTransaction} />

                    <div className='flex flex-col gap-4'>
                        <div className='grid grid-cols-2 gap-4'>
                            <DateField
                                name='posting_date'
                                label={_("Posting Date")}
                                isRequired
                                inputProps={{ autoFocus: false }}
                            />
                            <DateField
                                name='reference_date'
                                label={_("Reference Date")}
                                isRequired
                                inputProps={{ autoFocus: false }}
                            />
                        </div>
                        <DataField name='reference_no' label={_("Reference")} isRequired inputProps={{ autoFocus: false }} />
                    </div>
                </div>

                <div className='flex flex-col gap-2'>
                    <H4 className='text-base'>{isWithdrawal ? _('Transferred to') : _('Transferred from')}</H4>
                    <RecommendedTransferAccount transaction={selectedTransaction} onAccountChange={onAccountChange} />
                    <BankOrCashPicker company={selectedTransaction.company ?? ''} bankAccount={selectedTransaction.bank_account ?? ''} onAccountChange={onAccountChange} selectedAccount={selectedAccount} />
                </div>
                <div className='flex flex-col gap-2 py-2'>
                    <div className='flex items-end justify-between gap-4'>
                        <div className='flex-1'>
                            <AccountFormField
                                name="paid_from"
                                label={_("Paid From")}
                                account_type={['Bank', 'Cash']}
                                readOnly={isWithdrawal}
                                filterFunction={(account) => account.name !== selectedBankAccount.account}
                                isRequired
                            />
                        </div>

                        <div className='pb-2'>
                            {direction === 'ltr' ? <ArrowRight /> : <ArrowLeft />}
                        </div>
                        <div className='flex-1'>
                            <AccountFormField
                                name="paid_to"
                                label={_("Paid To")}
                                account_type={['Bank', 'Cash']}
                                isRequired
                                readOnly={!isWithdrawal}
                                filterFunction={(account) => account.name !== selectedBankAccount.account}
                            />
                        </div>
                    </div>
                </div>
                <Separator />
                <div className='flex flex-col gap-2'>
                    <div className='grid grid-cols-2 gap-4'>


                        <SmallTextField
                            name='remarks'
                            label={_("Custom Remarks")}
                            formDescription={_("This will be auto-populated if not set.")}
                        />
                        <div
                            data-slot="form-item"
                            className="flex flex-col gap-2"
                        >
                            <Label>{_("Attachments")}</Label>
                            <FileDropzone files={files} setFiles={setFiles} />
                        </div>
                    </div>
                </div>
                <DialogFooter>
                    <DialogClose asChild>
                        <Button size='md' variant={'outline'} disabled={loading}>{_("Cancel")}</Button>
                    </DialogClose>
                    <Button size='md' type='submit' disabled={loading}>{_("Transfer")}</Button>
                </DialogFooter>
            </div>
        </form>
    </Form>
}


const BankOrCashPicker = ({ bankAccount, onAccountChange, selectedAccount, company }: { selectedAccount: string, bankAccount: string, onAccountChange: (account: string) => void, company?: string }) => {

    const { banks } = useGetBankAccounts(undefined, (bank) => bank.name !== bankAccount)

    return <div className='grid grid-cols-4 gap-4'>
        {banks.map((bank) => (
            <button
                className={cn('text-left border p-2 rounded-md flex items-center gap-2 cursor-pointer outline-[0.5px] transition-all duration-200 hover:bg-surface-gray-1 dark:hover:bg-surface-gray-3',
                    selectedAccount === bank.account ? 'border-outline-gray-5 outline-outline-gray-5 bg-surface-gray-1 dark:bg-surface-gray-3' : 'border-outline-gray-2 outline-outline-gray-2'
                )}
                type='button'
                key={bank.account}
                onClick={() => onAccountChange(bank.account ?? '')}
            >
                <BankLogo bank={bank} iconSize='24px' imageClassName='w-12 h-12' />
                <div className='flex flex-col gap-1'>
                    <span className='font-semibold text-sm'>{bank.account_name} {bank.bank_account_no && <span className='text-xs text-ink-gray-5'>({bank.bank_account_no})</span>}</span>
                    <span className='text-xs text-ink-gray-5'>{bank.account}</span>
                </div>
            </button>
        ))}
        <CashPicker company={company ?? ''} selectedAccount={selectedAccount} setSelectedAccount={onAccountChange} />
    </div>

}

const CashPicker = ({ company, selectedAccount, setSelectedAccount }: { company: string, selectedAccount: string, setSelectedAccount: (account: string) => void }) => {

    const { data } = useFrappeGetCall('frappe.client.get_value', {
        doctype: 'Company',
        filters: company,
        fieldname: 'default_cash_account'
    }, undefined, {
        revalidateOnFocus: false,
        revalidateIfStale: false,
    })

    const account = data?.message?.default_cash_account

    if (account) {
        return <button className={cn('text-left border p-2 rounded-md flex items-center gap-2 cursor-pointer outline-[0.5px] transition-all duration-200 hover:bg-surface-gray-1 dark:hover:bg-surface-gray-3',
            selectedAccount === account ? 'border-outline-gray-5 outline-outline-gray-5 bg-surface-gray-1 dark:bg-surface-gray-3' : 'border-outline-gray-2 outline-outline-gray-2'
        )}
            type='button'
            onClick={() => setSelectedAccount(account ?? '')}
        >
            <div className='flex items-center justify-center h-10 w-10'>
                <Banknote size='24px' />
            </div>
            <div className='flex flex-col gap-1'>
                <span className='font-semibold text-sm'>Cash</span>
                <span className='text-xs text-ink-gray-5'>{data?.message?.default_cash_account}</span>
            </div>
        </button>
    }

    return null
}


const RecommendedTransferAccount = ({ transaction, onAccountChange }: { transaction: UnreconciledTransaction, onAccountChange: (account: string, is_mirror: boolean) => void }) => {

    const { setValue, watch } = useFormContext<InternalTransferFormFields>()

    const mirrorTransactionName = watch('mirror_transaction_name')
    const paid_from = watch('paid_from')
    const paid_to = watch('paid_to')

    const { data } = useFrappeGetCall('erpnext.accounts.doctype.bank_reconciliation_tool.bank_reconciliation_tool.search_for_transfer_transaction', {
        transaction_id: transaction.name
    }, undefined, {
        revalidateOnFocus: false,
        revalidateIfStale: false,
    })

    // Get bank accounts to find the logo
    const { banks } = useGetBankAccounts()

    const bank = useMemo(() => {
        if (data?.message?.bank_account && banks) {
            return banks.find(bank => bank.name === data.message.bank_account)
        }
        return null
    }, [data?.message?.bank_account, banks])

    const selectTransaction = () => {
        if (data?.message) {
            setValue('mirror_transaction_name', data.message.name)
            onAccountChange(data.message.account, true)
        }
    }

    if (data?.message) {

        const isWithdrawal = data.message.withdrawal && data.message.withdrawal > 0

        const amount = isWithdrawal ? data.message.withdrawal : data.message.deposit
        const currency = data.message.currency

        const isAccountSelected = isWithdrawal ? paid_from === data.message.account : paid_to === data.message.account

        const isSuggested = mirrorTransactionName === data?.message?.name && isAccountSelected

        return (<div className='pb-2'>
            <div className={cn("flex justify-between items-start gap-3 p-3 border rounded-lg shadow-sm",
                isSuggested ? "border-outline-green-4 bg-surface-green-1" : "border-outline-violet-2 bg-surface-violet-2/50")}>
                <div>
                    <div className='flex flex-col gap-3'>
                        <div className={cn("flex items-center gap-2 shrink-0",
                            isSuggested ? "text-ink-green-4" : "text-ink-violet-4"
                        )}>
                            <BadgeCheck className="w-4 h-4" />
                            <span className="text-sm font-medium">{_("Suggested Transfer to {0}", [data.message.account])}</span>
                        </div>
                        <div className='flex flex-col gap-1'>
                            <span className='text-p-sm'>{_("The system found a mirror transaction ({0}) in another account with the same amount and date.", [data.message.name])}</span>
                            <span className='text-p-sm'>{_("Accepting the suggestion will reconcile both transactions.")}</span>
                        </div>

                        <div className='flex flex-col gap-1.5'>
                            <div className='flex items-center gap-1'>
                                <Calendar size='16px' />
                                <span className='text-sm'>{formatDate(data.message.date, 'Do MMM YYYY')}</span>
                            </div>
                            <span className='text-sm line-clamp-1' title={data.message.description}>{data.message.description}</span>
                        </div>
                    </div>
                </div>
                <div className='flex flex-col items-end justify-between gap-2 h-full w-[30%]'>
                    <div className="flex items-center gap-2">
                        <BankLogo bank={bank} iconSize='24px' imageClassName='h-8 max-w-24' iconClassName={cn(isSuggested ? "text-ink-green-3" : "text-purple-600")} />
                    </div>
                    <div className='flex gap-1'>
                        <div className={cn('flex items-center gap-1 text-end px-0 justify-end py-1 rounded-sm',
                            isWithdrawal ? 'text-ink-red-3' : 'text-ink-green-3'
                        )}>
                            {isWithdrawal ? <ArrowUpRight className="w-5 h-5 text-ink-red-3" /> : <ArrowDownRight className="w-5 h-5 text-ink-green-3" />}
                            <span className='text-sm font-semibold uppercase'>{isWithdrawal ? _('Transferred Out') : _('Received')}</span>
                        </div>
                    </div>
                    <span className='font-semibold font-numeric text-lg text-end pe-0.5'>{formatCurrency(amount, currency)}</span>
                    <div className='pt-1'>
                        <Button
                            onClick={selectTransaction}
                            theme={isSuggested ? "green" : "violet"}
                            size="md"
                            type='button'
                        >
                            {isSuggested ? <CheckCircle /> : <CheckIcon />}
                            {isSuggested ? _("Accepted") : _("Use Suggestion")}
                        </Button>
                    </div>
                </div>
            </div>
        </div>
        )
    }

    return null
}

export default TransferModalContent
