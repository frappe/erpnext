import * as React from "react"
import {
    type Cell,
    type ColumnDef,
    type ColumnSizingState,
    type Header,
    type OnChangeFn,
    type Row,
    type RowSelectionState,
    flexRender,
    functionalUpdate,
    getCoreRowModel,
    useReactTable,
} from "@tanstack/react-table"
import { useVirtualizer } from "@tanstack/react-virtual"
import { useDebounceCallback } from "usehooks-ts"

import { Checkbox } from "@/components/ui/checkbox"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import { cn } from "@/lib/utils"
import { useDirection } from "./direction"

/** Optional per-column layout hints for `ListView`. */
export type ListViewColumnMeta = {
    /** CSS grid track (`1fr`, `2fr`, `minmax(0,1fr)`). When set, used instead of TanStack pixel `size` in `grid-template-columns`. */
    gridWidth?: string
    align?: "left" | "center" | "right"
    /**
     * Tabular figures for stable digit width. Default: on when `align` is `right` (amounts); set `false` to opt out, or `true` for dates/IDs.
     */
    tabularNums?: boolean
    /**
     * Full text for an overflow tooltip (shown only when the cell truncates). If omitted, a string `accessorKey` value is used when available.
     */
    getTooltipText?: (row: unknown) => string | null | undefined
    /** `false` disables the overflow tooltip for this column. */
    truncateTooltip?: boolean
    /**
     * `false` skips single-line truncation for cells with custom layouts (e.g. action buttons). Default `true`.
     */
    truncate?: boolean
}

function alignClass(meta: ListViewColumnMeta | undefined) {
    switch (meta?.align) {
        case "center":
            return "justify-center text-center"
        case "right":
            return "justify-end text-end"
        default:
            return "justify-start text-start"
    }
}

function tabularNumsClass(meta: ListViewColumnMeta | undefined) {
    if (meta?.tabularNums === false) return ""
    if (meta?.tabularNums === true) return "tabular-nums"
    if (meta?.align === "right") return "tabular-nums"
    return ""
}

function resolveTooltipLabel<TData>(
    row: Row<TData>,
    meta: ListViewColumnMeta | undefined,
    columnDef: ColumnDef<TData, unknown>,
): string | undefined {
    if (meta?.truncateTooltip === false) return undefined
    const fromMeta = meta?.getTooltipText?.(row.original as unknown)
    if (fromMeta != null && String(fromMeta).length > 0) {
        return String(fromMeta)
    }
    const key = "accessorKey" in columnDef ? columnDef.accessorKey : undefined
    if (key !== undefined && key !== null && key !== "") {
        try {
            const v = row.getValue(String(key))
            if (v != null && v !== "") return String(v)
        } catch {
            /* column may not expose a value */
        }
    }
    return undefined
}

function ListViewCellBody<TData>({
    cell,
    row,
    meta,
    children,
}: {
    cell: Cell<TData, unknown>
    row: Row<TData>
    meta: ListViewColumnMeta | undefined
    children: React.ReactNode
}) {
    const ref = React.useRef<HTMLDivElement>(null)
    const [overflowing, setOverflowing] = React.useState(false)
    const direction = useDirection()

    const tooltipLabel = resolveTooltipLabel(row, meta, cell.column.columnDef)
    const tooltipAlign = meta?.align === "right" && direction === "ltr" ? "end" : "start"

    const measure = React.useCallback(() => {
        const el = ref.current
        if (!el) return
        setOverflowing(el.scrollWidth > el.clientWidth + 1)
    }, [])

    React.useLayoutEffect(() => {
        measure()
    }, [measure, children, tooltipLabel])

    React.useEffect(() => {
        const el = ref.current
        if (!el || typeof ResizeObserver === "undefined") return
        const ro = new ResizeObserver(measure)
        ro.observe(el)
        return () => ro.disconnect()
    }, [measure])

    if (meta?.truncate === false) {
        return <div className="min-w-0 flex-1 overflow-visible">{children}</div>
    }

    const inner = (
        <div
            ref={ref}
            className={cn(
                "min-h-0 min-w-0 flex-1 truncate",
            )}
        >
            {children}
        </div>
    )

    if (!tooltipLabel || !overflowing) {
        return inner
    }

    return (
        <Tooltip delayDuration={400}>
            <TooltipTrigger asChild>{inner}</TooltipTrigger>
            <TooltipContent
                side="bottom"
                align={tooltipAlign}
                className="max-w-sm text-balance wrap-break-word"
            >
                {tooltipLabel}
            </TooltipContent>
        </Tooltip>
    )
}

function gridTemplateFromHeaders<TData>(headers: Header<TData, unknown>[]) {
    return headers
        .map((header) => {
            const meta = header.column.columnDef.meta as ListViewColumnMeta | undefined
            if (meta?.gridWidth) {
                return meta.gridWidth
            }
            return `${header.getSize()}px`
        })
        .join(" ")
}

function defaultGetRowId<TData>(row: TData, index: number) {
    const r = row as Record<string, unknown>
    if (r && typeof r.name === "string") return r.name
    if (r && typeof r.id === "string") return r.id
    return String(index)
}

export type ListViewProps<TData> = {
    data: TData[]
    columns: ColumnDef<TData, unknown>[]
    /**
     * Stable row id for selection and keys. Defaults to `name`, then `id`, then row index (index is fragile if data order changes).
     */
    getRowId?: (originalRow: TData, index: number) => string
    /** Pixel height of each body row (default 40, matches frappe-ui ListView). */
    rowHeight?: number
    className?: string
    /** Classes for the scrollable viewport (default includes max-height). */
    scrollAreaClassName?: string
    /** Max height of the scroll area; number is pixels. Default `420`. */
    maxHeight?: number | string
    emptyState?: React.ReactNode
    enableColumnResizing?: boolean
    columnSizing?: ColumnSizingState
    onColumnSizingChange?: OnChangeFn<ColumnSizingState>
    /** Debounced callback for persisting widths (e.g. localStorage). */
    onColumnSizingCommit?: (sizing: ColumnSizingState) => void
    columnSizingCommitDelayMs?: number
    enableRowSelection?: boolean
    rowSelection?: RowSelectionState
    onRowSelectionChange?: OnChangeFn<RowSelectionState>
    onRowClick?: (row: TData, event: React.MouseEvent) => void
}

function ListViewInner<TData>({
    data,
    columns: userColumns,
    getRowId: getRowIdProp,
    rowHeight = 40,
    className,
    scrollAreaClassName,
    maxHeight = 420,
    emptyState,
    enableColumnResizing = true,
    columnSizing: controlledColumnSizing,
    onColumnSizingChange: controlledOnColumnSizingChange,
    onColumnSizingCommit,
    columnSizingCommitDelayMs = 250,
    enableRowSelection = false,
    rowSelection: controlledRowSelection,
    onRowSelectionChange: controlledOnRowSelectionChange,
    onRowClick,
}: ListViewProps<TData>) {
    const parentRef = React.useRef<HTMLDivElement>(null)

    const [internalColumnSizing, setInternalColumnSizing] = React.useState<ColumnSizingState>({})
    const columnSizing = controlledColumnSizing ?? internalColumnSizing

    const [internalRowSelection, setInternalRowSelection] = React.useState<RowSelectionState>({})
    const rowSelection = controlledRowSelection ?? internalRowSelection
    const setRowSelection = controlledOnRowSelectionChange ?? setInternalRowSelection

    const debouncedSizingCommit = useDebounceCallback(
        (sizing: ColumnSizingState) => {
            onColumnSizingCommit?.(sizing)
        },
        columnSizingCommitDelayMs,
    )

    const selectionColumn = React.useMemo<ColumnDef<TData, unknown>>(
        () => ({
            id: "__list_view_select__",
            size: 36,
            minSize: 36,
            maxSize: 36,
            enableResizing: false,
            meta: {
                truncate: false,
                truncateTooltip: false,
            } satisfies ListViewColumnMeta,
            header: ({ table }) => (
                <div className="flex size-full items-center justify-center">
                    <Checkbox
                        aria-label="Select all rows"
                        checked={
                            table.getIsAllRowsSelected()
                                ? true
                                : table.getIsSomeRowsSelected()
                                    ? "indeterminate"
                                    : false
                        }
                        onCheckedChange={(value) => table.toggleAllRowsSelected(value === true)}
                        onClick={(e) => e.stopPropagation()}
                    />
                </div>
            ),
            cell: ({ row }) => (
                <div className="flex size-full items-center justify-center">
                    <Checkbox
                        aria-label="Select row"
                        checked={row.getIsSelected()}
                        onCheckedChange={(value) => row.toggleSelected(value === true)}
                        onClick={(e) => e.stopPropagation()}
                    />
                </div>
            ),
        }),
        [],
    )

    const columns = React.useMemo(() => {
        if (!enableRowSelection) return userColumns
        return [selectionColumn, ...userColumns]
    }, [enableRowSelection, selectionColumn, userColumns])

    const getRowId = React.useCallback(
        (originalRow: TData, index: number) =>
            (getRowIdProp ?? defaultGetRowId)(originalRow, index),
        [getRowIdProp],
    )

    const onColumnSizingChangeInternal = React.useCallback<OnChangeFn<ColumnSizingState>>(
        (updater) => {
            if (controlledOnColumnSizingChange) {
                controlledOnColumnSizingChange(updater)
                return
            }
            setInternalColumnSizing((old) => {
                const next = functionalUpdate(updater, old)
                debouncedSizingCommit(next)
                return next
            })
        },
        [controlledOnColumnSizingChange, debouncedSizingCommit],
    )

    const direction = useDirection()

    const table = useReactTable({
        data,
        columns,
        defaultColumn: {
            minSize: 50,
            size: 150,
        },
        columnResizeMode: "onChange",
        columnResizeDirection: direction,
        enableColumnResizing,
        getCoreRowModel: getCoreRowModel(),
        getRowId,
        onColumnSizingChange: onColumnSizingChangeInternal,
        onRowSelectionChange: setRowSelection,
        state: {
            columnSizing,
            rowSelection,
        },
        enableRowSelection,
    })

    const headerGroup = table.getHeaderGroups()[0]
    const gridTemplateColumns = headerGroup
        ? gridTemplateFromHeaders(headerGroup.headers)
        : ""

    const { rows } = table.getRowModel()

    const rowVirtualizer = useVirtualizer({
        count: rows.length,
        getScrollElement: () => parentRef.current,
        estimateSize: () => rowHeight,
        overscan: 10,
    })

    const maxHeightStyle =
        typeof maxHeight === "number" ? `${maxHeight}px` : maxHeight

    if (data.length === 0) {
        return (
            <div
                className={cn(
                    "bg-surface-gray-2 text-ink-gray-5 flex min-h-32 items-center justify-center rounded-md px-4 text-sm",
                    className,
                )}
            >
                {emptyState ?? "No data"}
            </div>
        )
    }

    /** Tracks + column gaps + horizontal padding (`px-2` × 2) so header and body share one scroll width. */
    const colCount = headerGroup?.headers.length ?? 0
    const minTableOuterWidth =
        table.getCenterTotalSize() +
        Math.max(0, colCount - 1) * 16 +
        16

    return (
        <div className={cn("flex min-w-0 flex-col", className)} role="grid">
            <div
                ref={parentRef}
                className={cn("min-h-0 overflow-auto", scrollAreaClassName)}
                style={{ maxHeight: maxHeightStyle }}
            >
                {headerGroup ? (
                    <div
                        className="bg-surface-gray-2 sticky top-0 z-10 mb-2 grid w-full items-center gap-x-4 rounded p-2"
                        role="row"
                        style={{
                            display: "grid",
                            gridTemplateColumns,
                            minWidth: `max(100%, ${minTableOuterWidth}px)`,
                            boxSizing: "border-box",
                        }}
                    >
                        {headerGroup.headers.map((header) => {
                            const meta = header.column.columnDef.meta as ListViewColumnMeta | undefined
                            return (
                                <div
                                    key={header.id}
                                    className={cn(
                                        "text-ink-gray-5 group relative flex min-w-0 items-center px-0 text-sm",
                                        alignClass(meta),
                                    )}
                                    role="columnheader"
                                >
                                    <div className="min-w-0 flex-1 truncate">
                                        {header.isPlaceholder
                                            ? null
                                            : flexRender(header.column.columnDef.header, header.getContext())}
                                    </div>
                                    {enableColumnResizing && header.column.getCanResize() ? (
                                        <>
                                            <span
                                                aria-hidden
                                                className={cn(
                                                    "pointer-events-none absolute ltr:-right-2 rtl:-left-2 z-1 w-0.5 bg-gray-400",
                                                    "opacity-0 transition-[opacity,background-color] ease-in-out duration-150",
                                                    "group-hover:opacity-100 group-hover:bg-gray-400",
                                                    header.column.getIsResizing() && "bg-outline-gray-6 opacity-100",
                                                )}
                                                style={{ height: "100%" }}
                                            />
                                            <div
                                                role="separator"
                                                aria-orientation="vertical"
                                                aria-label="Resize column"
                                                onMouseDown={(e) => {
                                                    e.preventDefault()
                                                    document.body.classList.add("select-none", "cursor-col-resize")
                                                    const end = () => {
                                                        document.body.classList.remove("select-none", "cursor-col-resize")
                                                        window.removeEventListener("mouseup", end)
                                                        window.removeEventListener("touchend", end)
                                                    }
                                                    window.addEventListener("mouseup", end)
                                                    window.addEventListener("touchend", end)
                                                    header.getResizeHandler()(e)
                                                }}
                                                onTouchStart={header.getResizeHandler()}
                                                className="absolute top-0 ltr:-right-2 rtl:-left-2 z-10 h-full w-2 max-w-[12px] cursor-col-resize touch-none select-none bg-transparent"
                                            />
                                        </>
                                    ) : null}
                                </div>
                            )
                        })}
                    </div>
                ) : null}

                <div
                    className="relative w-full"
                    style={{
                        height: `${rowVirtualizer.getTotalSize()}px`,
                        minWidth: `max(100%, ${minTableOuterWidth}px)`,
                        boxSizing: "border-box",
                    }}
                >
                    {rowVirtualizer.getVirtualItems().map((virtualRow) => {
                        const row = rows[virtualRow.index]
                        if (!row) return null
                        const leadDataColumnIndex = enableRowSelection ? 1 : 0
                        return (
                            <div
                                key={row.id}
                                data-index={virtualRow.index}
                                role="row"
                                className={cn(
                                    "ease-in-out absolute top-0 ltr:left-0 rtl:right-0 w-full min-w-0 rounded px-2 transition-all duration-300",
                                    // virtualRow.index > 0 && "border-t border-outline-gray-1",
                                    !row.getIsSelected() && "hover:bg-surface-menu-bar",
                                    row.getIsSelected() && "bg-surface-gray-2 hover:bg-surface-gray-3",
                                    onRowClick && "cursor-pointer",
                                )}
                                style={{
                                    display: "grid",
                                    gridTemplateColumns,
                                    boxSizing: "border-box",
                                    columnGap: "1rem",
                                    height: `${rowHeight}px`,
                                    transform: `translateY(${virtualRow.start}px)`,
                                }}
                                onClick={(e) => {
                                    if (onRowClick) onRowClick(row.original, e)
                                }}
                            >
                                {virtualRow.index > 0 && <div className="absolute top-0 inset-s-2 inset-e-2 h-px bg-outline-gray-1" />}
                                {row.getVisibleCells().map((cell, cellIndex) => {
                                    const meta = cell.column.columnDef.meta as ListViewColumnMeta | undefined
                                    return (
                                        <div
                                            key={cell.id}
                                            role="gridcell"
                                            className={cn(
                                                "flex min-w-0 items-center overflow-hidden text-sm",
                                                cellIndex === leadDataColumnIndex
                                                    ? "text-ink-gray-8"
                                                    : "text-ink-gray-7",
                                                alignClass(meta),
                                                tabularNumsClass(meta),
                                            )}
                                        >
                                            <ListViewCellBody cell={cell} row={row} meta={meta}>
                                                {flexRender(cell.column.columnDef.cell, cell.getContext())}
                                            </ListViewCellBody>
                                        </div>
                                    )
                                })}


                            </div>
                        )
                    })}
                </div>
            </div>
        </div>
    )
}

/**
 * Div-based list with CSS Grid columns, optional resize handles, row virtualization, and frappe-ui–aligned Espresso tokens.
 */
export function ListView<TData>(props: ListViewProps<TData>) {
    return <ListViewInner {...props} />
}

export type { ColumnSizingState, RowSelectionState }
