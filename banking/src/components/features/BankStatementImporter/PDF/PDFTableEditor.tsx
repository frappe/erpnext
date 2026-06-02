import { useEffect, useMemo, useRef, useState } from 'react'
import { toast } from 'sonner'
import { ChevronDownIcon, ChevronLeftIcon, ChevronRightIcon, FileTextIcon, Loader2Icon, TableIcon } from 'lucide-react'
import _ from '@/lib/translate'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Switch } from '@/components/ui/switch'
import { Label } from '@/components/ui/label'
import { H3, Paragraph } from '@/components/ui/typography'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import ErrorBanner from '@/components/ui/error-banner'
import RawTableGrid from '../RawTableGrid'
import BBoxOverlay from './BBoxOverlay'
import {
    applyColumnMappingChange,
    ColumnMapsTo,
    GetStatementDetailsResponse,
    PDFTable,
    useReextractPDFTable,
    useSetPDFTableHeader,
    useUpdatePDFTables,
} from '../import_utils'

type Props = {
    data: GetStatementDetailsResponse
    mutate: () => void
}

// Distinct overlay colours per table on a page.
const OVERLAY_COLORS = [
    { border: 'border-blue-500', bg: 'bg-blue-500/10', swatch: 'bg-blue-500' },
    { border: 'border-purple-500', bg: 'bg-purple-500/10', swatch: 'bg-purple-500' },
    { border: 'border-amber-500', bg: 'bg-amber-500/10', swatch: 'bg-amber-500' },
    { border: 'border-teal-500', bg: 'bg-teal-500/10', swatch: 'bg-teal-500' },
]

const columnMappingRecord = (table: PDFTable): Record<number, ColumnMapsTo> => {
    const map: Record<number, ColumnMapsTo> = {}
    table.column_mapping?.forEach((col) => {
        map[col.index] = col.maps_to
    })
    return map
}

const PDFTableEditor = ({ data, mutate }: Props) => {
    const isCompleted = data.doc.status === 'Completed'

    const [tables, setTables] = useState<PDFTable[]>(() => data.pdf_tables ?? [])
    const [viewMode, setViewMode] = useState<'pdf' | 'table'>('pdf')
    const [pageIndex, setPageIndex] = useState(0)
    const [collapsed, setCollapsed] = useState<Set<number>>(new Set())

    const toggleCollapsed = (tableIndex: number) =>
        setCollapsed((prev) => {
            const next = new Set(prev)
            if (next.has(tableIndex)) {
                next.delete(tableIndex)
            } else {
                next.add(tableIndex)
            }
            return next
        })

    const { call, loading, error } = useUpdatePDFTables()
    const { call: reextract, loading: reextracting } = useReextractPDFTable()
    const { call: setHeaderCall, loading: settingHeader } = useSetPDFTableHeader()
    const busy = loading || reextracting || settingHeader

    // Persist edits automatically (debounced) so the transaction preview updates in realtime.
    const tablesRef = useRef(tables)
    const saveTimer = useRef<ReturnType<typeof setTimeout>>(undefined)
    const reextractTimer = useRef<ReturnType<typeof setTimeout>>(undefined)

    const scheduleSave = () => {
        if (isCompleted) return
        clearTimeout(saveTimer.current)
        saveTimer.current = setTimeout(() => {
            call({ statement_import_id: data.doc.name, tables: tablesRef.current })
                .then(() => mutate())
                .catch(() => toast.error(_('Could not save the table settings.')))
        }, 500)
    }

    // After a bbox change, re-extract that table's rows from the new region (debounced).
    // The target is read inside the timeout so it always reflects the committed bbox.
    const scheduleReextract = (tableIndex: number) => {
        if (isCompleted) return
        clearTimeout(reextractTimer.current)
        reextractTimer.current = setTimeout(() => {
            const target = tablesRef.current[tableIndex]
            reextract({
                statement_import_id: data.doc.name,
                page: target.page,
                table_index: target.table_index,
                bbox: target.bbox,
            })
                .then((res) => {
                    commitTables(res?.message?.pdf_tables ?? [])
                    mutate()
                })
                .catch(() => toast.error(_('Could not re-extract the table.')))
        }, 500)
    }

    useEffect(() => () => {
        clearTimeout(saveTimer.current)
        clearTimeout(reextractTimer.current)
    }, [])

    const pages = useMemo(() => Array.from(new Set(tables.map((t) => t.page))).sort((a, b) => a - b), [tables])
    const currentPage = pages[pageIndex]
    // Keep the table's position in the flat array so edits target the right one.
    const pageTables = useMemo(
        () => tables.map((table, index) => ({ table, index })).filter((t) => t.table.page === currentPage),
        [tables, currentPage],
    )

    // Keep tablesRef in sync synchronously so the debounced save/re-extract never read stale state.
    const commitTables = (next: PDFTable[]) => {
        tablesRef.current = next
        setTables(next)
    }

    const updateTable = (tableIndex: number, updater: (table: PDFTable) => PDFTable) => {
        commitTables(tablesRef.current.map((t, i) => (i === tableIndex ? updater(t) : t)))
        scheduleSave()
    }

    const onChangeMapping = (tableIndex: number, columnIndex: number, mapsTo: ColumnMapsTo) => {
        updateTable(tableIndex, (table) => ({
            ...table,
            column_mapping: applyColumnMappingChange(table.column_mapping, columnIndex, mapsTo),
        }))
    }

    const onToggleIncluded = (tableIndex: number, included: boolean) =>
        updateTable(tableIndex, (table) => ({ ...table, included }))

    const onBboxCommit = (tableIndex: number, bbox: [number, number, number, number]) => {
        commitTables(tablesRef.current.map((t, i) => (i === tableIndex ? { ...t, bbox } : t)))
        scheduleReextract(tableIndex)
    }

    // Set/clear the header row of a table; the backend re-derives the column mapping.
    const onSetHeader = (tableIndex: number, headerIndex: number | null) => {
        commitTables(tablesRef.current.map((t, i) => (i === tableIndex ? { ...t, header_index: headerIndex } : t)))
        const target = tablesRef.current[tableIndex]
        setHeaderCall({
            statement_import_id: data.doc.name,
            page: target.page,
            table_index: target.table_index,
            header_index: headerIndex ?? -1,
        })
            .then((res) => {
                commitTables(res?.message?.pdf_tables ?? [])
                mutate()
            })
            .catch(() => toast.error(_('Could not update the header row.')))
    }

    if (tables.length === 0) {
        return (
            <div className="p-4">
                <Paragraph className="text-p-sm text-ink-gray-5">
                    {_('No tables were extracted from this PDF.')}
                </Paragraph>
            </div>
        )
    }

    return (
        <div className="flex flex-col gap-3 p-4">
            <div className="flex flex-col gap-1">
                <H3 className="text-base border-0 p-0">{_('Detected Tables')}</H3>
                <Paragraph className="text-p-sm">
                    {_('Review each page. In the Table view, map each column, click a row number to set/clear the header row, and exclude anything that is not transactions (ads, summaries).')}
                </Paragraph>
            </div>

            {error && <ErrorBanner error={error} />}

            <div className="flex items-center justify-between gap-2">
                <Tabs value={viewMode} onValueChange={(v) => setViewMode(v as 'pdf' | 'table')}>
                    <TabsList variant="subtle">
                        <TabsTrigger value="pdf"><FileTextIcon />{_('PDF')}</TabsTrigger>
                        <TabsTrigger value="table"><TableIcon />{_('Table')}</TabsTrigger>
                    </TabsList>
                </Tabs>

                <div className="flex items-center gap-1">
                    {busy && (
                        <span className="flex items-center gap-1 pe-1 text-xs text-ink-gray-5">
                            <Loader2Icon className="size-3 animate-spin" />
                            {reextracting ? _('Re-extracting') : _('Saving')}
                        </span>
                    )}
                    <Button
                        variant="ghost"
                        isIconButton
                        disabled={pageIndex === 0}
                        onClick={() => setPageIndex((i) => Math.max(0, i - 1))}
                    >
                        <ChevronLeftIcon />
                    </Button>
                    <span className="min-w-24 text-center text-sm text-ink-gray-7">
                        {_('Page {0} of {1}', [currentPage.toString(), pages.length.toString()])}
                    </span>
                    <Button
                        variant="ghost"
                        isIconButton
                        disabled={pageIndex >= pages.length - 1}
                        onClick={() => setPageIndex((i) => Math.min(pages.length - 1, i + 1))}
                    >
                        <ChevronRightIcon />
                    </Button>
                </div>
            </div>

            {viewMode === 'pdf' ? (
                <PageView
                    pageTables={pageTables}
                    disabled={isCompleted}
                    onToggleIncluded={onToggleIncluded}
                    onBboxCommit={onBboxCommit}
                />
            ) : (
                <div className="flex flex-col gap-4">
                    {pageTables.map(({ table, index }, position) => {
                        const isCollapsed = collapsed.has(index)
                        return (
                            <div
                                key={index}
                                className={cn('flex flex-col rounded border border-outline-gray-2', !table.included && 'opacity-60')}
                            >
                                <div className="flex items-center justify-between p-2">
                                    <span className="ps-1 text-sm font-medium text-ink-gray-8">
                                        {_('Table {0}', [(position + 1).toString()])}
                                    </span>
                                    <div className="flex items-center gap-2">
                                        <IncludeToggle
                                            id={`tbl-${index}`}
                                            checked={table.included}
                                            disabled={isCompleted}
                                            onCheckedChange={(c) => onToggleIncluded(index, c)}
                                        />
                                        <Button variant="ghost" size="sm" isIconButton onClick={() => toggleCollapsed(index)}>
                                            <ChevronDownIcon className={cn('transition-transform', isCollapsed && '-rotate-90')} />
                                        </Button>
                                    </div>
                                </div>
                                {!isCollapsed && (
                                    <div className="overflow-auto border-t border-outline-gray-2">
                                        <RawTableGrid
                                            rows={table.rows}
                                            columnMapping={columnMappingRecord(table)}
                                            headerIndex={table.header_index}
                                            editable
                                            disabled={isCompleted}
                                            onChangeMapping={(columnIndex, mapsTo) => onChangeMapping(index, columnIndex, mapsTo)}
                                            onSetHeader={(rowIndex) => onSetHeader(index, rowIndex)}
                                        />
                                    </div>
                                )}
                            </div>
                        )
                    })}
                </div>
            )}
        </div>
    )
}

type PageViewProps = {
    pageTables: { table: PDFTable; index: number }[]
    disabled: boolean
    onToggleIncluded: (tableIndex: number, included: boolean) => void
    onBboxCommit: (tableIndex: number, bbox: [number, number, number, number]) => void
}

const PageView = ({ pageTables, disabled, onToggleIncluded, onBboxCommit }: PageViewProps) => {
    const containerRef = useRef<HTMLDivElement>(null)
    const pageImage = pageTables[0]?.table.page_image
    const pageWidth = pageTables[0]?.table.page_width ?? 1
    const pageHeight = pageTables[0]?.table.page_height ?? 1

    if (!pageImage) {
        return (
            <Paragraph className="text-p-sm text-ink-gray-5">
                {_('No page image is available for this page.')}
            </Paragraph>
        )
    }

    return (
        <div className="flex flex-col gap-3">
            {!disabled && (
                <Paragraph className="text-xs text-ink-gray-5">
                    {_('Drag a box to move it, or drag a corner to resize. The table is re-read from the new region automatically.')}
                </Paragraph>
            )}
            <div ref={containerRef} className="relative w-full overflow-auto rounded border border-outline-gray-2 bg-surface-gray-1">
                <img src={pageImage} alt={_('Page preview')} className="w-full" />
                {pageTables.map(({ table, index }, position) => {
                    const color = OVERLAY_COLORS[position % OVERLAY_COLORS.length]
                    return (
                        <BBoxOverlay
                            key={index}
                            bbox={table.bbox}
                            pageWidth={pageWidth}
                            pageHeight={pageHeight}
                            color={color}
                            label={_('Table {0}', [(position + 1).toString()])}
                            included={table.included}
                            disabled={disabled}
                            containerRef={containerRef}
                            onCommit={(bbox) => onBboxCommit(index, bbox)}
                        />
                    )
                })}
            </div>

            <div className="flex flex-col gap-1.5">
                {pageTables.map(({ table, index }, position) => {
                    const color = OVERLAY_COLORS[position % OVERLAY_COLORS.length]
                    return (
                        <div key={index} className="flex items-center justify-between rounded border border-outline-gray-2 px-2 py-1.5">
                            <div className="flex items-center gap-2">
                                <span className={cn('size-3 rounded-sm', color.swatch)} />
                                <span className="text-xs">{_('Table {0}', [(position + 1).toString()])}</span>
                            </div>
                            <IncludeToggle
                                id={`pdf-tbl-${index}`}
                                checked={table.included}
                                disabled={disabled}
                                onCheckedChange={(c) => onToggleIncluded(index, c)}
                            />
                        </div>
                    )
                })}
            </div>
        </div>
    )
}

const IncludeToggle = ({
    id,
    checked,
    disabled,
    onCheckedChange,
}: {
    id: string
    checked: boolean
    disabled: boolean
    onCheckedChange: (checked: boolean) => void
}) => (
    <div className="flex items-center gap-2">
        <Label htmlFor={id} className="text-xs text-ink-gray-6">{_('Include')}</Label>
        <Switch id={id} checked={checked} disabled={disabled} onCheckedChange={onCheckedChange} />
    </div>
)

export default PDFTableEditor
