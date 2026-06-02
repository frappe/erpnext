import { useMemo } from 'react'
import {
    ArrowDownRightIcon,
    ArrowUpDownIcon,
    ArrowUpRightIcon,
    BanknoteIcon,
    CalendarIcon,
    DollarSignIcon,
    FileTextIcon,
    ListIcon,
    ReceiptIcon,
} from 'lucide-react'
import _ from '@/lib/translate'
import { cn } from '@/lib/utils'
import { Table, TableBody, TableCell, TableHead, TableRow } from '@/components/ui/table'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { COLUMN_MAPS_TO_OPTIONS, ColumnMapsTo } from './import_utils'

const AMOUNT_COLUMNS: ColumnMapsTo[] = ['Amount', 'Withdrawal', 'Deposit', 'Balance']
const DATE_LIKE = /\d{1,4}[/\-.\s]\d{1,2}[/\-.\s]\d{1,4}|\d{1,2}[\s-][a-z]{3}/i

type Props = {
    rows: string[][]
    /** Column index -> mapped field */
    columnMapping: Record<number, ColumnMapsTo>
    headerIndex: number | null
    editable?: boolean
    disabled?: boolean
    onChangeMapping?: (columnIndex: number, mapsTo: ColumnMapsTo) => void
    /** Set the header row (or null to mark the table as having no header). */
    onSetHeader?: (rowIndex: number | null) => void
}

/**
 * A preview of extracted rows with CSV-style colour coding: the header row is highlighted,
 * detected transaction rows are green, and mapped columns are emphasised. When `editable`, a
 * compact row of column -> field dropdowns sits at the top, and row numbers can be clicked to
 * set/clear the header row.
 */
const RawTableGrid = ({ rows, columnMapping, headerIndex, editable, disabled, onChangeMapping, onSetHeader }: Props) => {
    // Tabular (XLSX) cells can be numbers/dates, not strings - coerce so .trim()/render are safe.
    const stringRows = useMemo(
        () => rows.map((row) => row.map((cell) => (cell == null ? '' : String(cell)))),
        [rows],
    )
    const numColumns = useMemo(() => stringRows.reduce((max, row) => Math.max(max, row.length), 0), [stringRows])

    const validColumns = useMemo(
        () => Object.entries(columnMapping).filter(([, m]) => m && m !== 'Do not import').map(([i]) => Number(i)),
        [columnMapping],
    )
    const dateColumn = useMemo(() => Object.entries(columnMapping).find(([, m]) => m === 'Date')?.[0], [columnMapping])
    const amountColumns = useMemo(
        () => Object.entries(columnMapping).filter(([, m]) => ['Amount', 'Withdrawal', 'Deposit'].includes(m)).map(([i]) => Number(i)),
        [columnMapping],
    )

    // Approximate the backend's transaction-row detection so the highlighting tracks edits live.
    const transactionRows = useMemo(() => {
        const set = new Set<number>()
        if (dateColumn === undefined) return set
        const dateIdx = Number(dateColumn)
        stringRows.forEach((row, index) => {
            if (index === headerIndex) return
            const dateCell = (row[dateIdx] ?? '').trim()
            if (!dateCell || !DATE_LIKE.test(dateCell)) return
            if (amountColumns.some((c) => (row[c] ?? '').trim() !== '')) set.add(index)
        })
        return set
    }, [stringRows, headerIndex, dateColumn, amountColumns])

    return (
        <Table containerClassName="rounded-none">
            <TableBody>
                {editable && (
                    <TableRow className="border-b border-outline-gray-2 bg-surface-white hover:bg-surface-white">
                        <TableHead className="w-8 p-1" />
                        {Array.from({ length: numColumns }).map((_unused, columnIndex) => (
                            <TableHead key={columnIndex} className="p-1 align-top">
                                <Select
                                    disabled={disabled}
                                    value={columnMapping[columnIndex] ?? 'Do not import'}
                                    onValueChange={(value) => onChangeMapping?.(columnIndex, value as ColumnMapsTo)}
                                >
                                    <SelectTrigger variant="outline" inputSize="sm" className="h-7 w-full">
                                        <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                        {COLUMN_MAPS_TO_OPTIONS.map((option) => (
                                            <SelectItem key={option} value={option}>
                                                <span className="flex items-center gap-1.5">
                                                    <ColumnHeaderIcon columnType={option} />
                                                    {_(option)}
                                                </span>
                                            </SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            </TableHead>
                        ))}
                    </TableRow>
                )}

                {stringRows.map((row, index) => {
                    const isHeaderRow = index === headerIndex
                    const isTransactionRow = transactionRows.has(index)

                    return (
                        <TableRow
                            key={index}
                            className={cn({
                                'bg-green-50 hover:bg-green-50 dark:bg-green-700 dark:hover:bg-green-700': isTransactionRow,
                                'bg-yellow-100 hover:bg-yellow-100 dark:bg-yellow-400': isHeaderRow,
                                'text-ink-gray-5/70': !isTransactionRow && !isHeaderRow,
                            })}
                        >
                            {editable && onSetHeader ? (
                                <TableCell className="h-px w-8 p-0 text-center">
                                    <Tooltip>
                                        <TooltipTrigger asChild>
                                            <button
                                                type="button"
                                                disabled={disabled}
                                                onClick={() => onSetHeader(isHeaderRow ? null : index)}
                                                className={cn(
                                                    'flex h-full w-full items-center justify-center px-1 text-ink-gray-6 hover:bg-surface-gray-3',
                                                    isHeaderRow && 'font-semibold text-ink-gray-8',
                                                )}
                                            >
                                                {index + 1}
                                            </button>
                                        </TooltipTrigger>
                                        <TooltipContent>
                                            {isHeaderRow
                                                ? _('This is the header row. Click to mark the table as having no header.')
                                                : _('Click to set this as the header row.')}
                                        </TooltipContent>
                                    </Tooltip>
                                </TableCell>
                            ) : (
                                <TableCell className="w-8 px-1 py-0.5 text-center text-ink-gray-6">{index + 1}</TableCell>
                            )}

                            {Array.from({ length: numColumns }).map((_unused, cellIndex) => {
                                const columnType = columnMapping[cellIndex]
                                const isValidColumn = validColumns.includes(cellIndex)
                                const isAmountColumn = AMOUNT_COLUMNS.includes(columnType)
                                const cellText = row[cellIndex] ?? ''

                                // Read-only header row: icon + label.
                                if (isHeaderRow) {
                                    return (
                                        <TableCell key={cellIndex} className="max-w-[200px] overflow-hidden text-ellipsis py-1">
                                            <div className="flex items-center gap-1 px-1 text-xs font-medium text-ink-gray-8">
                                                {columnType && (
                                                    <Tooltip>
                                                        <TooltipTrigger>
                                                            <ColumnHeaderIcon columnType={columnType} />
                                                        </TooltipTrigger>
                                                        <TooltipContent>{_(columnType)}</TooltipContent>
                                                    </Tooltip>
                                                )}
                                                {cellText}
                                            </div>
                                        </TableCell>
                                    )
                                }

                                return (
                                    <TableCell
                                        key={cellIndex}
                                        className={cn('max-w-[200px] overflow-hidden text-ellipsis py-0.5', {
                                            'bg-green-100 dark:bg-green-400 hover:bg-green-100 dark:hover:bg-green-400': isValidColumn && isTransactionRow,
                                            'text-ink-gray-5': !isValidColumn && isTransactionRow,
                                        })}
                                    >
                                        <div
                                            className={cn('min-h-5 flex items-center px-1 text-xs', {
                                                'justify-end': isAmountColumn && isValidColumn && isTransactionRow,
                                            })}
                                            title={cellText}
                                        >
                                            {cellText}
                                        </div>
                                    </TableCell>
                                )
                            })}
                        </TableRow>
                    )
                })}
            </TableBody>
        </Table>
    )
}

const ColumnHeaderIcon = ({ columnType }: { columnType?: ColumnMapsTo }) => {
    switch (columnType) {
        case 'Amount':
            return <DollarSignIcon className="size-4" />
        case 'Withdrawal':
            return <ArrowUpRightIcon className="size-4 text-ink-red-3" />
        case 'Deposit':
            return <ArrowDownRightIcon className="size-4 text-ink-green-3" />
        case 'Balance':
            return <BanknoteIcon className="size-4" />
        case 'Date':
            return <CalendarIcon className="size-4" />
        case 'Description':
            return <FileTextIcon className="size-4" />
        case 'Reference':
            return <ReceiptIcon className="size-4" />
        case 'Transaction Type':
            return <ListIcon className="size-4" />
        case 'Debit/Credit':
            return <ArrowUpDownIcon className="size-4" />
        default:
            return null
    }
}

export default RawTableGrid
