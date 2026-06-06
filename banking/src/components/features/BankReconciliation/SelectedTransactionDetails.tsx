import { useMemo } from 'react'
import { ArrowDownRight, ArrowUpRight, Calendar } from 'lucide-react'
import { formatCurrency } from '@/lib/numbers'
import { formatDate } from '@/lib/date'
import { UnreconciledTransaction, useGetBankAccounts } from './utils'
import { getCompanyCurrency } from '@/lib/company'
import { Card, CardContent } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import _ from '@/lib/translate'
import BankLogo from '@/components/common/BankLogo'

type Props = {
    transaction: UnreconciledTransaction,
    showAccount?: boolean,
    account?: string
}

const SelectedTransactionDetails = ({ transaction, showAccount = false, account }: Props) => {

    const isWithdrawal = transaction.withdrawal && transaction.withdrawal > 0

    const { banks } = useGetBankAccounts()

    const bank = useMemo(() => {
        if (transaction.bank_account) {
            return banks?.find((bank) => bank.name === transaction.bank_account)
        }
        return null
    }, [transaction.bank_account, banks])

    const amount = transaction.withdrawal ? transaction.withdrawal : transaction.deposit

    const currency = transaction.currency || getCompanyCurrency(transaction.company ?? '')

    return (
        <Card className='py-4'>
            <CardContent className='px-4'>
                <div className='flex flex-col gap-2'>
                    <div className='flex justify-between'>
                        <div className='flex flex-col gap-2'>
                            <div className='flex flex-col gap-1'>
                                <BankLogo bank={bank} iconSize='30px' imageClassName='h-10 max-w-20' />
                                <span className='font-medium text-sm'>{transaction.bank_account}</span>
                            </div>
                            <div className='flex items-center gap-1'>
                                <Calendar size='16px' />
                                <span className='text-sm'>{formatDate(transaction.date, 'Do MMM YYYY')}</span>
                            </div>
                        </div>
                        <div className='flex flex-col gap-1'>
                            <div className={cn('flex items-center gap-1 text-end px-0 justify-end py-1 rounded-sm',
                                isWithdrawal ? 'text-ink-red-3' : 'text-ink-green-3'
                            )}>
                                {isWithdrawal ? <ArrowUpRight className="w-5 h-5 text-ink-red-3" /> : <ArrowDownRight className="w-5 h-5 text-ink-green-3" />}
                                <span className='text-sm font-semibold uppercase'>{isWithdrawal ? _('Spent') : _('Received')}</span>
                            </div>
                            <span className='font-semibold font-numeric text-lg text-end pe-0.5'>{formatCurrency(amount, currency)}</span>
                            {transaction.unallocated_amount && transaction.unallocated_amount !== amount ? <span className='text-ink-gray-5'>{_("Unallocated")}: {formatCurrency(transaction.unallocated_amount)}</span> : null}
                        </div>
                    </div>
                    <div className='flex flex-col gap-1'>
                        <span className='text-sm'>{transaction.description}</span>
                        {transaction.reference_number ? <span className='text-sm text-ink-gray-5'>{_("Ref")}: {transaction.reference_number}</span> : null}
                        {showAccount && account ? <span className='text-sm text-ink-gray-5'>{_("GL Account")}: {account}</span> : null}
                    </div>

                </div>
            </CardContent >
        </Card >
    )
}

export default SelectedTransactionDetails