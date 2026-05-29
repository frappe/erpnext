import { Table, TableBody, TableCell, TableHead, TableRow } from "@/components/ui/table"
import { cn } from "@/lib/utils"
import { ArrowDownRightIcon, ArrowUpDownIcon, ArrowUpRightIcon, BanknoteIcon, CalendarIcon, DollarSignIcon, FileTextIcon, ListIcon, ReceiptIcon } from "lucide-react"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import _ from "@/lib/translate"
import { GetStatementDetailsResponse } from "../import_utils"
import { useMemo } from "react"
import { BankStatementImportLogColumnMap } from "@/types/Accounts/BankStatementImportLogColumnMap"


const CSVRawDataPreview = ({ data }: { data: GetStatementDetailsResponse }) => {

    const column_mapping: Record<StandardColumnTypes, number> = useMemo(() => {

        const col_map: Record<string, number> = {}

        data.doc.column_mapping?.forEach(col => {
            if (col.maps_to && col.maps_to !== "Do not import") {
                col_map[col.maps_to] = col.index;
            }
        })

        return col_map

    }, [data])

    const validColumns = Object.values(column_mapping)

    // Reverse the column mapping to get a map of column index to variable name
    const columnIndexMap: Record<number, StandardColumnTypes> = Object.fromEntries(Object.entries(column_mapping).map(([variable, columnIndex]) => [columnIndex, variable as StandardColumnTypes]))

    // Loop over the contents of the CSV file and show a preview - highlight the header row and the transaction rows
    return (
        <Table containerClassName="rounded-none">
            <TableBody>
                {data.raw_data.map((row, index) => {

                    const isHeaderRow = index === data.doc.detected_header_index;
                    const isTransactionRow = index >= (data.doc.detected_transaction_starting_index ?? 0) && index <= (data.doc.detected_transaction_ending_index ?? 0);

                    return <TableRow key={index}
                        title={isHeaderRow ? "Header Row" : ""}
                        className={cn({
                            // "bg-yellow-100": isHeaderRow,
                            // "hover:bg-yellow-100": isHeaderRow,
                            "bg-green-50 hover:bg-green-50 dark:bg-green-700 dark:hover:bg-green-700": isTransactionRow,
                            "text-ink-gray-5/70": !isTransactionRow && !isHeaderRow,
                        })}>
                        {isHeaderRow ? <TableHead className="bg-yellow-100 hover:bg-yellow-100 dark:bg-yellow-400 text-center font-semibold text-ink-gray-8">
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
                                    isValidColumn ? "bg-yellow-100 hover:bg-yellow-100 dark:bg-yellow-400" : "bg-surface-gray-2",
                                )}>
                                    <div className={cn("flex items-center text-xs gap-1 px-1 text-ink-gray-8 font-medium", {
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
                                        "bg-green-100 dark:bg-green-400 hover:bg-green-100 dark:hover:bg-green-400": isValidColumn && isTransactionRow,
                                        "text-ink-gray-5": !isValidColumn && isTransactionRow,
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

type StandardColumnTypes = BankStatementImportLogColumnMap['maps_to'];

const ColumnHeaderIcon = ({ columnType }: { columnType?: StandardColumnTypes }) => {
    if (!columnType) {
        return null
    }

    if (columnType === 'Amount') {
        return <DollarSignIcon className="w-4 h-4" />
    }

    if (columnType === 'Withdrawal') {
        return <ArrowUpRightIcon className="w-4 h-4 text-ink-red-3" />
    }

    if (columnType === 'Deposit') {
        return <ArrowDownRightIcon className="w-4 h-4 text-ink-green-3" />
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

    if (columnType === 'Debit/Credit') {
        return <ArrowUpDownIcon className="w-4 h-4" />
    }

    return null
}

export default CSVRawDataPreview