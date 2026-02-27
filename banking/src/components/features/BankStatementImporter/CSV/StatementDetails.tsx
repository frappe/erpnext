import _ from '@/lib/translate'
import { GetStatementDetailsResponse } from '../import_utils'
import { flt, formatCurrency } from '@/lib/numbers'
import { formatDate } from '@/lib/date'
import { bankRecDateAtom, SelectedBank } from '../../BankReconciliation/bankRecAtoms'
import { ChevronLeftIcon, ExternalLinkIcon, InfoIcon, Landmark, Loader2Icon } from 'lucide-react'
import { H2, H3, H4, Paragraph } from '@/components/ui/typography'
import { FileTypeIcon } from '@/components/ui/file-dropzone'
import { getFileExtension } from '@/lib/file'
import { Table, TableBody, TableCaption, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Separator } from '@/components/ui/separator'
import { Button } from '@/components/ui/button'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { useFrappeEventListener, useFrappePostCall } from 'frappe-react-sdk'
import { toast } from 'sonner'
import ErrorBanner from '@/components/ui/error-banner'
import { useNavigate } from 'react-router-dom'
import { useState } from 'react'
import { Progress } from '@/components/ui/progress'
import { useSetAtom } from 'jotai'

const AMOUNT_FORMAT_LABEL_MAP = {
    "separate_columns_for_withdrawal_and_deposit": _("Separate columns for withdrawal and deposit"),
    "dr_cr_in_amount": _('Amount column has "CR"/"DR" values'),
    "positive_negative_in_amount": _("Amount column has positive/negative values"),
    "cr_dr_in_transaction_type": _('Transaction type column has "CR"/"DR" values'),
    "deposit_withdrawal_in_transaction_type": _('Transaction type column has "Deposit"/"Withdrawal" values'),
}

const DATE_FORMAT_LABEL_MAP: Record<string, { label: string; dayjsFormat: string }> = {
    "%d-%m-%Y": {
        label: "DD-MM-YYYY",
        dayjsFormat: "DD-MM-YYYY",
    },
    "%m-%d-%Y": {
        label: "MM-DD-YYYY",
        dayjsFormat: "MM-DD-YYYY",
    },
    "%Y-%m-%d": {
        label: "YYYY-MM-DD",
        dayjsFormat: "YYYY-MM-DD",
    },
    "%d-%m-%y": {
        label: "DD-MM-YY",
        dayjsFormat: "DD-MM-YY",
    },
    "%m-%d-%y": {
        label: "MM-DD-YY",
        dayjsFormat: "MM-DD-YY",
    },
    "%y-%m-%d": {
        label: "YY-MM-DD",
        dayjsFormat: "YY-MM-DD",
    },
    "%y-%b-%d": {
        label: "YY-MMM-DD",
        dayjsFormat: "YY-MMM-DD",
    },
    "%d/%m/%Y": {
        label: "DD/MM/YYYY",
        dayjsFormat: "DD/MM/YYYY",
    },
    "%m/%d/%Y": {
        label: "MM/DD/YYYY",
        dayjsFormat: "MM/DD/YYYY",
    },
    "%Y/%m/%d": {
        label: "YYYY/MM/DD",
        dayjsFormat: "YYYY/MM/DD",
    },
    "%d/%m/%y": {
        label: "DD/MM/YY",
        dayjsFormat: "DD/MM/YY",
    },
    "%m/%d/%y": {
        label: "MM/DD/YY",
        dayjsFormat: "MM/DD/YY",
    },
    "%y/%m/%d": {
        label: "YY/MM/DD",
        dayjsFormat: "YY/MM/DD",
    },
    "%d/%b/%y": {
        label: "DD/MMM/YY",
        dayjsFormat: "DD/MMM/YY",
    },
    "%d.%m.%Y": {
        label: "DD.MM.YYYY",
        dayjsFormat: "DD.MM.YYYY",
    },
    "%m.%d.%Y": {
        label: "MM.DD.YYYY",
        dayjsFormat: "MM.DD.YYYY",
    },
    "%Y.%m.%d": {
        label: "YYYY.MM.DD",
        dayjsFormat: "YYYY.MM.DD",
    },
    "%d.%m.%y": {
        label: "DD.MM.YY",
        dayjsFormat: "DD.MM.YY",
    },
    "%m.%d.%y": {
        label: "MM.DD.YY",
        dayjsFormat: "MM.DD.YY",
    },
    "%y.%m.%d": {
        label: "YY.MM.DD",
        dayjsFormat: "YY.MM.DD",
    },
    "%d %b %Y": {
        label: "DD MMM YYYY",
        dayjsFormat: "DD MMM YYYY",
    },
    "%d %B %Y": {
        label: "DD MMMM YYYY",
        dayjsFormat: "DD MMMM YYYY",
    },
    "%d/%b/%Y": {
        label: "DD/MMM/YYYY",
        dayjsFormat: "DD/MMM/YYYY",
    }
}

type Props = {
    data: GetStatementDetailsResponse,
    bank: SelectedBank | null,
    onBack: () => void
}

const StatementDetails = ({ data, bank, onBack }: Props) => {
    const dateFormatMeta = DATE_FORMAT_LABEL_MAP[data.date_format as keyof typeof DATE_FORMAT_LABEL_MAP]

    const { call, loading, error } = useFrappePostCall<{ message: { success: boolean, start_date: string, end_date: string } }>('mint.apis.statement_import.import_statement')

    const navigate = useNavigate()

    const setDates = useSetAtom(bankRecDateAtom)

    const onImport = () => {

        call({
            file_url: data.file_path,
            bank_account: bank?.name,
        }).then((response) => {
            if (response.message.start_date && response.message.end_date) {
                setDates({
                    fromDate: response.message.start_date,
                    toDate: response.message.end_date,
                })
            }
            toast.success(_("Bank statement imported."))
            navigate(`/`)
        }).catch(() => {
            toast.error(_("There was an error while importing the bank statement."))
        })

    }

    const [progress, setProgress] = useState(0)

    useFrappeEventListener("mint-statement-import-progress", (event) => {
        setProgress(event.progress)
    })

    return (
        <div className='flex flex-col gap-4'>
            <div className='flex flex-col gap-4'>
                <div className='flex justify-between items-center'>
                    <Button size='sm' variant='outline' onClick={onBack}>
                        <ChevronLeftIcon />
                        {_("Back")}
                    </Button>
                    <Button onClick={onImport} disabled={loading} size='sm' type='button'>
                        {loading ? <Loader2Icon className='size-4 animate-spin' /> : null}
                        {loading ? _("Importing...") : _("Import {0} transactions", [data.final_transactions?.length?.toString() || "0"])}</Button>
                </div>
                <div className='flex items-start gap-4'>
                    <div className='flex flex-col gap-1'>
                        <H2 className='text-lg border-0 p-0'>{_("Statement Details")}</H2>
                        <Paragraph className='text-sm'><span>
                            {_("We've auto-detected the details of the statement file.")}
                        </span><br />
                            <span>
                                {_("Please review the details below and click the 'Import' button to proceed.")}
                            </span>
                        </Paragraph>
                    </div>
                </div>

                {progress > 0 && <div className='flex flex-col gap-2'><Progress value={progress} max={100} />
                    <span className='text-sm'>{_("Importing {0} transactions", [progress.toString()])}
                    </span>
                </div>}

                {error && <ErrorBanner error={error} />}

                <Table>
                    <TableBody>
                        <TableRow>
                            <TableHead className='bg-muted/70'>{_("Bank Account")}</TableHead>
                            <TableCell>
                                <div className='flex items-center gap-2'>
                                    {bank?.logo ? <img
                                        src={`/assets/erpnext/banking/${bank.logo}`}
                                        alt={bank.bank || bank.name || ''}
                                        className="max-w-24 object-left h-8 object-contain"
                                    /> : <div className="rounded-md flex items-center h-8 gap-2">
                                        <Landmark size={'30px'} />
                                        <H4 className="text-base mb-0">{bank?.bank}</H4>
                                    </div>}
                                    <span className="tracking-tight text-sm font-medium">{bank?.account_name}</span>
                                    <span title="GL Account" className="text-sm">{bank?.account}</span>
                                </div>
                            </TableCell>
                        </TableRow>
                        <TableRow>
                            <TableHead className='bg-muted/70'>{_("Statement File")}</TableHead>
                            <TableCell>
                                <div className='flex items-center gap-2'>
                                    <FileTypeIcon fileType={getFileExtension(data.file_name)} size='md' showBackground={false} />
                                    {data.file_name}
                                </div>
                            </TableCell>
                        </TableRow>
                        <TableRow>
                            <TableHead className='bg-muted/70'>{_("Transaction Dates")}</TableHead>
                            <TableCell>{_("{0} to {1}", [formatDate(data.statement_start_date, "Do MMMM YYYY"), formatDate(data.statement_end_date, "Do MMMM YYYY")])}</TableCell>
                        </TableRow>
                        <TableRow>
                            <TableHead className='bg-muted/70'>{_("Number of Transactions")}</TableHead>
                            <TableCell>{data.transaction_rows.length}</TableCell>
                        </TableRow>
                        <TableRow>
                            <TableHead className='bg-muted/70'>{_("Closing Balance as of {}", [formatDate(data.statement_end_date, "Do MMMM YYYY")])}</TableHead>
                            <TableCell className='font-mono'>{formatCurrency(flt(data.closing_balance, 2))}</TableCell>
                        </TableRow>
                        <TableRow>
                            <TableHead className='bg-muted/70'>
                                <div className='flex items-center gap-2'>
                                    {_("Detected Amount Format")} <Tooltip>
                                        <TooltipTrigger><InfoIcon size={16} /></TooltipTrigger>
                                        <TooltipContent>
                                            {_("The amount format detected in the statement file. This is used to parse the deposit and withdrawal values from each row.")}
                                        </TooltipContent>
                                    </Tooltip>
                                </div>
                            </TableHead>
                            <TableCell>{AMOUNT_FORMAT_LABEL_MAP[data.amount_format as keyof typeof AMOUNT_FORMAT_LABEL_MAP]}</TableCell>
                        </TableRow>
                        <TableRow>
                            <TableHead className='bg-muted/70'>
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
                                {dateFormatMeta?.label || data.date_format} (e.g.{" "}
                                {formatDate(new Date(), dateFormatMeta?.dayjsFormat || "YYYY-MM-DD")})
                            </TableCell>
                        </TableRow>
                    </TableBody>
                </Table>
            </div>

            {data.conflicting_transactions.length > 0 && <Separator />}

            {data.conflicting_transactions.length > 0 ? <div className='flex flex-col gap-4'>
                <div className='flex flex-col gap-1'>
                    <H3 className='text-base border-0 p-0'>{_("Conflicting Transactions")}</H3>
                    {data.conflicting_transactions.length === 1 ? (
                        <Paragraph className='text-sm'>{_("We've found 1 existing transaction in the system that conflicts with the transactions in the statement file. Are you sure you want to proceed with the import?")}</Paragraph>
                    ) : (
                        <Paragraph className='text-sm'>{_("We've found {0} existing transactions in the system that conflict with the transactions in the statement file. Are you sure you want to proceed with the import?", [data.conflicting_transactions.length.toString()])}</Paragraph>
                    )}
                </div>
                <div className='max-h-[400px] overflow-scroll border border-border rounded-md pb-2'>
                    <Table>
                        <TableCaption>{_("Existing transactions in the system belonging to the same bank account and date range")}</TableCaption>
                        <TableHeader>
                            <TableRow>
                                <TableHead>{_("Date")}</TableHead>
                                <TableHead>{_("Description")}</TableHead>
                                <TableHead>{_("Ref.")}</TableHead>
                                <TableHead className='text-right'>{_("Withdrawal")}</TableHead>
                                <TableHead className='text-right'>{_("Deposit")}</TableHead>

                                <TableHead></TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {data.conflicting_transactions.map((transaction) => (
                                <TableRow key={transaction.name}>
                                    <TableCell>{formatDate(transaction.date)}</TableCell>
                                    <TableCell>{transaction.description}</TableCell>
                                    <TableCell>{transaction.reference_number ? transaction.reference_number : "-"}</TableCell>
                                    <TableCell className='text-right font-mono'>{formatCurrency(transaction.withdrawal, transaction.currency)}</TableCell>
                                    <TableCell className='text-right font-mono'>{formatCurrency(transaction.deposit, transaction.currency)}</TableCell>
                                    <TableCell className='text-right'>
                                        <Tooltip>
                                            <TooltipTrigger asChild>
                                                <Button variant='link' isIconButton asChild className='text-muted-foreground hover:text-black p-0 h-4'>
                                                    <a href={`/app/bank-transaction/${transaction.name}`} target='_blank' rel='noopener noreferrer'>
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

            </div> : null}

            <Separator />

            <div className='flex flex-col gap-4'>
                <div className='flex flex-col gap-1'>
                    <H3 className='text-base border-0 p-0'>{_("Preview Transactions")}</H3>
                    {data.final_transactions?.length === 1 ? (
                        <Paragraph className='text-sm'>{_("We've found 1 transaction in the statement file that will be imported into the system. Please review the details below and click the 'Import' button to proceed.")}</Paragraph>
                    ) : (
                        <Paragraph className='text-sm'>{_("{0} transactions will be imported into the system. Please review the details below and click the 'Import' button to proceed.", [data.final_transactions?.length?.toString() || "0"])}</Paragraph>
                    )}
                </div>
                <div className='max-h-[400px] overflow-scroll border border-border rounded-md pb-2'>
                    <Table>
                        <TableCaption>{_("Transactions to be imported into the system")}</TableCaption>
                        <TableHeader>
                            <TableRow>
                                <TableHead className='w-8'>#</TableHead>
                                <TableHead>{_("Date")}</TableHead>
                                <TableHead>{_("Description")}</TableHead>
                                <TableHead>{_("Ref.")}</TableHead>
                                <TableHead className='text-right'>{_("Withdrawal")}</TableHead>
                                <TableHead className='text-right'>{_("Deposit")}</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {data.final_transactions?.map((transaction, index) => (
                                <TableRow key={index}>
                                    <TableCell className='w-8'>{index + 1}</TableCell>
                                    <TableCell>{formatDate(transaction.date)}</TableCell>
                                    <TableCell className='max-w-[200px] w-fit overflow-hidden text-ellipsis'>{transaction.description}</TableCell>
                                    <TableCell className='max-w-[100px] w-fit overflow-hidden text-ellipsis'>{transaction.reference}</TableCell>
                                    <TableCell className='text-right font-mono'>{formatCurrency(transaction.withdrawal, data.currency)}</TableCell>
                                    <TableCell className='text-right font-mono'>{formatCurrency(transaction.deposit, data.currency)}</TableCell>
                                </TableRow>
                            ))}
                        </TableBody>
                    </Table>
                </div>
            </div>
        </div>

    )
}

export default StatementDetails