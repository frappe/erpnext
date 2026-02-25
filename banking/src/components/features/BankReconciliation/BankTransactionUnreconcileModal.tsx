import { AlertDialog, AlertDialogOverlay, AlertDialogContent, AlertDialogHeader, AlertDialogTitle, AlertDialogDescription, AlertDialogFooter, AlertDialogCancel, AlertDialogAction } from "@/components/ui/alert-dialog"
import { useAtom, useAtomValue } from "jotai"
import { bankRecDateAtom, bankRecUnreconcileModalAtom, selectedBankAccountAtom } from "./bankRecAtoms"
import { useMemo } from "react"
import { useFrappeGetDoc, useFrappePostCall, useSWRConfig } from "frappe-react-sdk"
import { BankTransaction } from "@/types/Accounts/BankTransaction"
import { toast } from "sonner"
import ErrorBanner from "@/components/ui/error-banner"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { formatCurrency } from "@/lib/numbers"
import { Badge } from "@/components/ui/badge"
import { slug } from "@/lib/frappe"
import SelectedTransactionDetails from "./SelectedTransactionDetails"
import _ from "@/lib/translate"

const BankTransactionUnreconcileModal = () => {

    const [unreconcileModal, setBankRecUnreconcileModal] = useAtom(bankRecUnreconcileModalAtom)

    const onOpenChange = (v: boolean) => {
        if (!v) {
            setBankRecUnreconcileModal('')
        }
    }

    return <AlertDialog open={!!unreconcileModal} onOpenChange={onOpenChange}>
        <AlertDialogOverlay />
        <AlertDialogContent className="min-w-2xl">
            <AlertDialogHeader>
                <AlertDialogTitle>{_("Undo Transaction Reconciliation")}</AlertDialogTitle>
                <AlertDialogDescription>
                    {_("Are you sure you want to unreconcile this transaction?")}
                </AlertDialogDescription>
            </AlertDialogHeader>
            <BankTransactionUnreconcileModalContent />
        </AlertDialogContent>
    </AlertDialog>


}

const BankTransactionUnreconcileModalContent = () => {
    const bankAccount = useAtomValue(selectedBankAccountAtom)
    const dates = useAtomValue(bankRecDateAtom)

    const { mutate } = useSWRConfig()

    const [unreconcileModal, setBankRecUnreconcileModal] = useAtom(bankRecUnreconcileModalAtom)

    const { data: transaction, error } = useFrappeGetDoc<BankTransaction>('Bank Transaction', unreconcileModal)

    const { call, loading, error: unreconcileError } = useFrappePostCall('mint.apis.bank_reconciliation.unreconcile_transaction')

    const onUnreconcile = (event: React.MouseEvent<HTMLButtonElement>) => {
        call({
            transaction_name: unreconcileModal
        }).then(() => {
            // Mutate the transactions list, unreconciled transactions list and account closing balance
            mutate(`bank-reconciliation-bank-transactions-${bankAccount?.name}-${dates.fromDate}-${dates.toDate}`)
            mutate(`bank-reconciliation-unreconciled-transactions-${bankAccount?.name}-${dates.fromDate}-${dates.toDate}`)
            mutate(`bank-reconciliation-account-closing-balance-${bankAccount?.name}-${dates.toDate}`)
            toast.success(_("Transaction Unreconciled"))
            setBankRecUnreconcileModal('')
        })

        event.preventDefault()
    }

    const vouchersWhichWillBeCancelled = useMemo(() => {
        return transaction?.payment_entries?.filter((payment) => payment.reconciliation_type === 'Voucher Created')
    }, [transaction])

    return <div>
        <div className="flex flex-col gap-3">
            {error && <ErrorBanner error={error} />}
            {unreconcileError && <ErrorBanner error={unreconcileError} />}
            {transaction && <SelectedTransactionDetails transaction={transaction} />}
            <span className="font-medium text-sm">{_("This transaction has been reconciled with the following document(s):")}</span>
            <Table>
                <TableHeader>
                    <TableRow>
                        <TableHead>{_("Document")}</TableHead>
                        <TableHead>{_("Amount")}</TableHead>
                        <TableHead>{_("Reconciliation Type")}</TableHead>
                    </TableRow>
                </TableHeader>
                <TableBody>
                    {transaction?.payment_entries?.map((voucher) => {
                        return <TableRow key={voucher.name}>
                            <TableCell>
                                <a className="underline underline-offset-4"
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    href={`/app/${slug(voucher.payment_document as string)}/${voucher.payment_entry}`}
                                >
                                    {`${_(voucher.payment_document)}: ${voucher.payment_entry}`}
                                </a>
                            </TableCell>
                            <TableCell>{formatCurrency(voucher.allocated_amount)}</TableCell>
                            <TableCell>{voucher.reconciliation_type === 'Voucher Created' ?
                                <Badge className="bg-green-600 text-white rounded-sm">{_(voucher.reconciliation_type)}</Badge> :
                                <Badge className="rounded-sm">{_(voucher.reconciliation_type ?? "Matched")}</Badge>}</TableCell>
                        </TableRow>
                    })}
                </TableBody>
            </Table>
            <div className="py-4">
                {vouchersWhichWillBeCancelled && vouchersWhichWillBeCancelled?.length > 0 && <span>The following documents will be <strong>cancelled</strong>:</span>}
                {vouchersWhichWillBeCancelled && vouchersWhichWillBeCancelled?.length > 0 && <ol className="ml-6 list-disc [&>li]:mt-2">
                    {vouchersWhichWillBeCancelled?.map((voucher) => {
                        return <li key={voucher.name}>{_(voucher.payment_document)}: {voucher.payment_entry}</li>
                    })}
                </ol>}
            </div>
        </div>
        <AlertDialogFooter>
            <AlertDialogCancel disabled={loading}>{_("Cancel")}</AlertDialogCancel>
            <AlertDialogAction onClick={onUnreconcile} variant="destructive" disabled={loading}>
                {_("Unreconcile")}
            </AlertDialogAction>
        </AlertDialogFooter>
    </div>
}

export default BankTransactionUnreconcileModal