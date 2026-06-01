import _ from '@/lib/translate'
import { GetStatementDetailsResponse } from '../import_utils'
import { flt, formatCurrency } from '@/lib/numbers'
import { formatDate } from '@/lib/date'
import { bankRecDateAtom } from '../../BankReconciliation/bankRecAtoms'
import { AlertCircleIcon, ChevronLeftIcon, ChevronRightIcon, ExternalLinkIcon, InfoIcon, Loader2Icon } from 'lucide-react'
import { H2, H3, Paragraph } from '@/components/ui/typography'
import { FileTypeIcon } from '@/components/ui/file-dropzone'
import { getFileExtension } from '@/lib/file'
import { Table, TableBody, TableCaption, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Separator } from '@/components/ui/separator'
import { Button } from '@/components/ui/button'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { useFrappeEventListener, useFrappePostCall } from 'frappe-react-sdk'
import { toast } from 'sonner'
import ErrorBanner from '@/components/ui/error-banner'
import { Link, useNavigate } from 'react-router-dom'
import { useMemo, useState } from 'react'
import { Progress } from '@/components/ui/progress'
import { useSetAtom } from 'jotai'
import { useDirection } from '@/components/ui/direction'
import BankLogo from '@/components/common/BankLogo'
import { useGetBankAccounts } from '../../BankReconciliation/utils'
import { BankStatementImportLog } from '@/types/Accounts/BankStatementImportLog'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Dialog, DialogClose, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'

const parseDateFormat = (dateFormat: string) => {

    const charMap = {
        "%d": "DD",
        "%m": "MM",
        "%Y": "YYYY",
        "%y": "YY",
        "%b": "MMM",
        "%B": "MMMM",
    }

    let label = dateFormat

    Object.keys(charMap).forEach((char) => {
        label = label.replace(char, charMap[char as keyof typeof charMap])
    })

    return dateFormat

}

type Props = {
    data: GetStatementDetailsResponse,
}

const StatementDetails = ({ data }: Props) => {
    const dateFormat = parseDateFormat(data.date_format)

    const { call, loading, error } = useFrappePostCall<{ docs: BankStatementImportLog[] }>('run_doc_method')

    const navigate = useNavigate()

    const setDates = useSetAtom(bankRecDateAtom)

    const direction = useDirection()

    const onImport = () => {

        call({
            docs: data.doc,
            method: 'insert_transactions'
        }).then((response) => {
            const doc = response.docs ? response.docs[0] : undefined
            if (doc && doc.start_date && doc.end_date) {
                setDates({
                    fromDate: doc.start_date,
                    toDate: doc.end_date,
                })
            }
            toast.success(_("Bank statement imported."))
            navigate(`/`)
        }).catch(() => {
            toast.error(_("There was an error while importing the bank statement."))
        })

    }

    const [progress, setProgress] = useState(0)

    useFrappeEventListener("bank-rec-statement-import-progress", (event) => {
        setProgress(event.progress)
    })

    const file_name = data.doc.file.split("/").pop() ?? ""

    const { banks } = useGetBankAccounts()

    const bank = useMemo(() => {

        return banks?.find((bank) => bank.name === data.doc.bank_account)

    }, [data.doc.bank_account, banks])

    return (
        <div className='flex flex-col gap-4'>
            <div className='flex flex-col gap-4'>
                <div className='flex justify-between items-center'>
                    <Button size='sm' variant='outline' asChild>
                        <Link to="/statement-importer">
                            {direction === 'ltr' ? <ChevronLeftIcon /> : <ChevronRightIcon />}
                            {_("Back")}
                        </Link>
                    </Button>
                    {data.doc.status === 'Completed' ? <Badge theme='green'>{_("Completed")}</Badge> :
                        <Button onClick={onImport} disabled={loading || data.final_transactions?.length === 0} size='sm' type='button'>
                            {loading ? <Loader2Icon className='size-4 animate-spin' /> : null}
                            {loading ? _("Importing...") : _("Import {0} transactions", [data.final_transactions?.length?.toString() || "0"])}</Button>
                    }
                </div>
                <div className='flex items-start gap-4'>
                    <div className='flex flex-col gap-1'>
                        <H2 className='text-lg border-0 p-0'>{_("Statement Details")}</H2>
                        <Paragraph className='text-p-sm'><span>
                            {_("We've auto-detected the details of the statement file.")}
                        </span><br />
                            <span>
                                {_("Please review the details below and click the 'Import' button to proceed.")}
                            </span>
                        </Paragraph>
                    </div>
                </div>

                {progress > 0 && <div className='flex flex-col gap-2'><Progress value={progress} max={100} size="lg" />
                    <span className='text-sm'>{_("Importing {0} transactions", [progress.toString()])}
                    </span>
                </div>}

                {error && <ErrorBanner error={error} />}

                <Table>
                    <TableBody>
                        <TableRow>
                            <TableHead>{_("Bank Account")}</TableHead>
                            <TableCell>
                                <div className='flex items-center gap-2'>
                                    <BankLogo bank={bank} />
                                    <span className="tracking-tight text-sm font-medium">{bank?.account_name}</span>
                                    <span title="GL Account" className="text-sm">{bank?.account}</span>
                                </div>
                            </TableCell>
                        </TableRow>
                        <TableRow>
                            <TableHead>{_("Statement File")}</TableHead>
                            <TableCell>
                                <div className='flex items-center gap-2'>
                                    <FileTypeIcon fileType={getFileExtension(file_name)} size='md' showBackground={false} />
                                    {file_name}
                                </div>
                            </TableCell>
                        </TableRow>
                        <TableRow>
                            <TableHead>{_("Transaction Dates")}</TableHead>
                            <TableCell>{_("{0} to {1}", [formatDate(data.doc.start_date, "Do MMMM YYYY"), formatDate(data.doc.end_date, "Do MMMM YYYY")])}</TableCell>
                        </TableRow>
                        <TableRow>
                            <TableHead>{_("Number of Transactions")}</TableHead>
                            <TableCell>{data.doc.number_of_transactions}</TableCell>
                        </TableRow>
                        <TableRow>
                            <TableHead>{_("Total Debits")}</TableHead>
                            <TableCell><span className='font-numeric'>{formatCurrency(flt(data.doc.total_debits, 2), data.currency)}</span> <span className='text-ink-gray-5 font-sans'>({data.doc.total_debit_transactions} {data.doc.total_debit_transactions === 1 ? _("transaction") : _("transactions")})</span></TableCell>
                        </TableRow>
                        <TableRow>
                            <TableHead>{_("Total Credits")}</TableHead>
                            <TableCell><span className='font-numeric'>{formatCurrency(flt(data.doc.total_credits, 2), data.currency)}</span> <span className='text-ink-gray-5 font-sans'>({data.doc.total_credit_transactions} {data.doc.total_credit_transactions === 1 ? _("transaction") : _("transactions")})</span></TableCell>
                        </TableRow>
                        <TableRow>
                            <TableHead>{_("Closing Balance as of {}", [formatDate(data.doc.end_date, "Do MMMM YYYY")])}</TableHead>
                            <TableCell className='font-numeric'>{formatCurrency(flt(data.doc.closing_balance, 2), data.currency)}</TableCell>
                        </TableRow>
                        <TableRow>
                            <TableHead>
                                <div className='flex items-center gap-2'>
                                    {_("Detected Amount Format")} <Tooltip>
                                        <TooltipTrigger><InfoIcon size={16} /></TooltipTrigger>
                                        <TooltipContent>
                                            {_("The amount format detected in the statement file. This is used to parse the deposit and withdrawal values from each row.")}
                                        </TooltipContent>
                                    </Tooltip>
                                </div>
                            </TableHead>
                            <TableCell>{data.doc.detected_amount_format}</TableCell>
                        </TableRow>
                        <TableRow>
                            <TableHead>
                                <div className='flex items-center gap-2'>
                                    {_("Detected Date Format")}
                                    <Tooltip>
                                        <TooltipTrigger><InfoIcon size={16} /></TooltipTrigger>
                                        <TooltipContent>
                                            {_("The date format detected in the statement file. This is used to parse the date values.")}
                                        </TooltipContent>
                                    </Tooltip>
                                </div>
                            </TableHead>
                            <TableCell>
                                {dateFormat || data.date_format} (e.g.{" "}
                                {formatDate(new Date(), dateFormat || "YYYY-MM-DD")})
                            </TableCell>
                        </TableRow>
                    </TableBody>
                </Table>
            </div>

            {data.doc.status === "Not Started" ? <>

                <ConflictingTransactions transactions={data.conflicting_transactions} />

                <Separator />

                <div className='flex flex-col gap-4'>
                    <div className='flex flex-col gap-1'>
                        <H3 className='text-base border-0 p-0'>{_("Preview Transactions")}</H3>
                        {data.final_transactions?.length === 1 ? (
                            <Paragraph className='text-p-sm'>{_("We've found 1 transaction in the statement file that will be imported into the system. Please review the details below and click the 'Import' button to proceed.")}</Paragraph>
                        ) : (
                            <Paragraph className='text-p-sm'>{_("{0} transactions will be imported into the system. Please review the details below and click the 'Import' button to proceed.", [data.final_transactions?.length?.toString() || "0"])}</Paragraph>
                        )}
                    </div>
                    <div className='max-h-[400px] overflow-scroll pb-2'>
                        <Table>
                            <TableCaption>{_("Transactions to be imported into the system")}</TableCaption>
                            <TableHeader>
                                <TableRow>
                                    <TableHead className='w-8'>#</TableHead>
                                    <TableHead>{_("Date")}</TableHead>
                                    <TableHead>{_("Description")}</TableHead>
                                    <TableHead>{_("Ref.")}</TableHead>
                                    <TableHead className='text-end'>{_("Withdrawal")}</TableHead>
                                    <TableHead className='text-end'>{_("Deposit")}</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {data.final_transactions?.map((transaction, index) => (
                                    <TableRow key={index}>
                                        <TableCell className='w-8'>{index + 1}</TableCell>
                                        <TableCell>{formatDate(transaction.date)}</TableCell>
                                        <TableCell className='max-w-[200px] w-fit overflow-hidden text-ellipsis'>{transaction.description}</TableCell>
                                        <TableCell className='max-w-[100px] w-fit overflow-hidden text-ellipsis'>{transaction.reference}</TableCell>
                                        <TableCell className='text-end font-numeric'>{formatCurrency(transaction.withdrawal, data.currency)}</TableCell>
                                        <TableCell className='text-end font-numeric'>{formatCurrency(transaction.deposit, data.currency)}</TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    </div>
                </div>
            </> : null}
        </div>

    )
}

const ConflictingTransactions = ({ transactions }: { transactions: GetStatementDetailsResponse["conflicting_transactions"] }) => {

    if (transactions.length === 0) {
        return null
    }

    return <>
        <Alert theme="red">
            <AlertCircleIcon />
            <AlertTitle>{_("Conflicting Transactions")}</AlertTitle>
            <AlertDescription>
                {transactions.length === 1 ? _("We've found 1 existing transaction in the system that conflicts with the transactions in the statement file. Are you sure you want to proceed with the import?")
                    : _("We've found {0} existing transactions in the system that conflict with the transactions in the statement file. Are you sure you want to proceed with the import?", [transactions.length.toString()])}

                <div className='py-2'>
                    <Dialog>
                        <DialogTrigger asChild>
                            <Button
                                size='sm'
                                type='button'
                                theme='red'
                                variant='solid'>
                                <span>{transactions.length > 1 ? _("View transactions") : _("View transaction")}</span>
                            </Button>
                        </DialogTrigger>
                        <DialogContent className='min-w-7xl'>
                            <DialogHeader>
                                <DialogTitle>{_("Conflicting Transactions")}</DialogTitle>
                                <DialogDescription>
                                    {transactions.length === 1 ? _("We've found 1 existing transaction in the system that conflicts with the transactions in the statement file. Are you sure you want to proceed with the import?")
                                        : _("We've found {0} existing transactions in the system that conflict with the transactions in the statement file. Are you sure you want to proceed with the import?", [transactions.length.toString()])}
                                </DialogDescription>
                            </DialogHeader>

                            <div className='max-h-[400px] overflow-scroll pb-2'>
                                <Table>
                                    <TableCaption>{_("Existing transactions in the system belonging to the same bank account and date range")}</TableCaption>
                                    <TableHeader>
                                        <TableRow>
                                            <TableHead>{_("Date")}</TableHead>
                                            <TableHead>{_("Description")}</TableHead>
                                            <TableHead>{_("Ref.")}</TableHead>
                                            <TableHead className='text-end'>{_("Withdrawal")}</TableHead>
                                            <TableHead className='text-end'>{_("Deposit")}</TableHead>
                                            <TableHead></TableHead>
                                        </TableRow>
                                    </TableHeader>
                                    <TableBody>
                                        {transactions.map((transaction) => (
                                            <TableRow key={transaction.name}>
                                                <TableCell>{formatDate(transaction.date)}</TableCell>
                                                <TableCell title={transaction.description} className='max-w-[200px] w-fit overflow-hidden text-ellipsis'>{transaction.description}</TableCell>
                                                <TableCell title={transaction.reference_number} className='max-w-[100px] w-fit overflow-hidden text-ellipsis'>{transaction.reference_number ? transaction.reference_number : "-"}</TableCell>
                                                <TableCell className='text-end font-numeric'>{formatCurrency(transaction.withdrawal, transaction.currency)}</TableCell>
                                                <TableCell className='text-end font-numeric'>{formatCurrency(transaction.deposit, transaction.currency)}</TableCell>
                                                <TableCell className='text-end'>
                                                    <Tooltip>
                                                        <TooltipTrigger asChild>
                                                            <Button variant='link' isIconButton asChild className='text-ink-gray-5 hover:text-black p-0 h-4'>
                                                                <a href={`/desk/bank-transaction/${transaction.name}`} target='_blank' rel='noopener noreferrer'>
                                                                    <ExternalLinkIcon />
                                                                </a>
                                                            </Button>
                                                        </TooltipTrigger>
                                                        <TooltipContent>
                                                            {_("Open {0} in a new tab", [transaction.name])}
                                                        </TooltipContent>
                                                    </Tooltip>

                                                </TableCell>
                                            </TableRow>
                                        ))}
                                    </TableBody>
                                </Table>
                            </div>
                            <DialogFooter>
                                <DialogClose asChild>
                                    <Button variant={'outline'} size='md' type='button'>{_("Close")}</Button>
                                </DialogClose>
                            </DialogFooter>
                        </DialogContent>

                    </Dialog>
                </div>
            </AlertDescription>
        </Alert>
    </>
}

export default StatementDetails