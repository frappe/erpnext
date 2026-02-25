import { Table, TableBody, TableCell, TableHead, TableRow } from "@/components/ui/table"
import { cn } from "@/lib/utils"
import { ArrowDownRightIcon, ArrowUpRightIcon, BanknoteIcon, CalendarIcon, DollarSignIcon, FileTextIcon, ListIcon, ReceiptIcon } from "lucide-react"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import _ from "@/lib/translate"
import { GetStatementDetailsResponse } from "../import_utils"


const CSVRawDataPreview = ({ data }: { data: GetStatementDetailsResponse }) => {

    const validColumns = Object.values(data.column_mapping)

    // Reverse the column mapping to get a map of column index to variable name
    const columnIndexMap: Record<number, StandardColumnTypes> = Object.fromEntries(Object.entries(data.column_mapping).map(([variable, columnIndex]) => [columnIndex, variable as StandardColumnTypes]))

    // Loop over the contents of the CSV file and show a preview - highlight the header row and the transaction rows
    return (
        <Table>
            <TableBody>
                {data.data.map((row, index) => {

                    const isHeaderRow = index === data.header_index;
                    const isTransactionRow = index >= data.transaction_starting_index && index <= data.transaction_ending_index;

                    return <TableRow key={index}
                        title={isHeaderRow ? "Header Row" : ""}
                        className={cn({
                            // "bg-yellow-100": isHeaderRow,
                            // "hover:bg-yellow-100": isHeaderRow,
                            "bg-green-50": isTransactionRow,
                            "hover:bg-green-50": isTransactionRow,
                            "text-muted-foreground/70": !isTransactionRow && !isHeaderRow,
                        })}>
                        {isHeaderRow ? <TableHead className="bg-yellow-100 hover:bg-yellow-100 text-center">
                            {index + 1}
                        </TableHead> :
                            <TableCell className="text-center px-1 py-0.5">
                                {index + 1}
                            </TableCell>
                        }
                        {row.map((cell, cellIndex) => {

                            const isValidColumn = validColumns.includes(cellIndex);
                            const columnType = columnIndexMap[cellIndex];
                            const isAmountColumn = ["Amount", "Withdrawal", "Deposit", "Balance"].includes(columnType);

                            if (isHeaderRow) {
                                return <TableHead key={cellIndex} className={cn("max-w-[250px] w-fit overflow-hidden text-ellipsis py-0.5",
                                    isValidColumn ? "bg-yellow-100 hover:bg-yellow-100" : "bg-muted",
                                )}>
                                    <div className={cn("flex items-center text-xs gap-1 px-1", {
                                        "justify-end": isAmountColumn && isValidColumn
                                    })}>
                                        {columnType && <Tooltip>
                                            <TooltipTrigger>
                                                <ColumnHeaderIcon columnType={columnType} />
                                            </TooltipTrigger>
                                            <TooltipContent>
                                                {_(columnType)}
                                            </TooltipContent>
                                        </Tooltip>
                                        }
                                        {cell}
                                    </div>
                                </TableHead>
                            } else {
                                return <TableCell key={cellIndex} className={cn("max-w-[200px] w-fit overflow-hidden text-ellipsis py-0.5",
                                    {
                                        "bg-green-100": isValidColumn && isTransactionRow,
                                        "hover:bg-green-100": isValidColumn && isTransactionRow,
                                        "text-muted-foreground": !isValidColumn && isTransactionRow,
                                    }
                                )} >
                                    <div className={cn("min-h-5 flex items-center text-xs px-1", {
                                        "justify-end": isAmountColumn && isValidColumn && isTransactionRow
                                    })} title={cell}>
                                        {cell}
                                    </div>
                                </TableCell>
                            }
                        }

                        )}
                    </TableRow>
                })}
            </TableBody>
        </Table >
    )
}

type StandardColumnTypes = 'Amount' | 'Date' | 'Description' | 'Reference' | 'Transaction Type' | 'Balance' | 'Withdrawal' | 'Deposit';

const ColumnHeaderIcon = ({ columnType }: { columnType?: StandardColumnTypes }) => {
    if (!columnType) {
        return null
    }

    if (columnType === 'Amount') {
        return <DollarSignIcon className="w-4 h-4" />
    }

    if (columnType === 'Withdrawal') {
        return <ArrowUpRightIcon className="w-4 h-4 text-destructive" />
    }

    if (columnType === 'Deposit') {
        return <ArrowDownRightIcon className="w-4 h-4 text-green-500" />
    }

    if (columnType === 'Balance') {
        return <BanknoteIcon className="w-4 h-4" />
    }

    if (columnType === 'Date') {
        return <CalendarIcon className="w-4 h-4" />
    }

    if (columnType === 'Description') {
        return <FileTextIcon className="w-4 h-4" />
    }

    if (columnType === 'Reference') {
        return <ReceiptIcon className="w-4 h-4" />
    }

    if (columnType === 'Transaction Type') {
        return <ListIcon className="w-4 h-4" />
    }

    return null
}

export default CSVRawDataPreview