import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import _ from '@/lib/translate'
import { useAtomValue } from 'jotai'
import { bankRecSelectedTransactionAtom, selectedBankAccountAtom } from './bankRecAtoms'
import { formatDate } from '@/lib/date'
import { formatCurrency } from '@/lib/numbers'
import { ArrowDownRight, ArrowUpRight } from 'lucide-react'

const SelectedTransactionsTable = () => {

    const selectedBankAccount = useAtomValue(selectedBankAccountAtom)

    const transactions = useAtomValue(bankRecSelectedTransactionAtom(selectedBankAccount?.name ?? ''))
    return (
        <Table>
            <TableHeader>
                <TableRow>
                    <TableHead>
                        {_("Date")}
                    </TableHead>
                    <TableHead>
                        {_("Description")}
                    </TableHead>
                    <TableHead className="text-end">
                        {_("Amount")}
                    </TableHead>
                </TableRow>
            </TableHeader>
            <TableBody>
                {transactions.map((transaction) => (
                    <TableRow key={transaction.name}>
                        <TableCell>{formatDate(transaction.date)}</TableCell>
                        <TableCell className="max-w-96 text-ellipsis overflow-hidden" title={transaction.description}>{transaction.description}</TableCell>
                        <TableCell className="text-end flex items-center justify-end gap-1">
                            {transaction.withdrawal && transaction.withdrawal > 0 ? <ArrowUpRight className="w-4 h-4 text-ink-red-3" /> : <ArrowDownRight className="w-4 h-4 text-ink-green-3" />}
                            <span className="font-numeric font-medium">
                                {formatCurrency(transaction.unallocated_amount, transaction.currency ?? '')}
                            </span>
                        </TableCell>
                    </TableRow>
                ))}
            </TableBody>
        </Table>
    )
}

export default SelectedTransactionsTable