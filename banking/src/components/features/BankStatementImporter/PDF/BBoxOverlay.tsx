import { RefObject, useEffect, useRef, useState } from 'react'
import { cn } from '@/lib/utils'

type Bbox = [number, number, number, number]

const MIN_SIZE = 8 // PDF points

// Keep the box valid: normalise flipped edges, enforce a min size, clamp to the page.
const clampBbox = (bbox: Bbox, pageWidth: number, pageHeight: number): Bbox => {
    let [x0, top, x1, bottom] = bbox
    if (x1 < x0) [x0, x1] = [x1, x0]
    if (bottom < top) [top, bottom] = [bottom, top]
    x0 = Math.max(0, Math.min(x0, pageWidth - MIN_SIZE))
    top = Math.max(0, Math.min(top, pageHeight - MIN_SIZE))
    x1 = Math.min(pageWidth, Math.max(x1, x0 + MIN_SIZE))
    bottom = Math.min(pageHeight, Math.max(bottom, top + MIN_SIZE))
    return [x0, top, x1, bottom]
}

const HANDLES = [
    { id: 'nw', className: 'left-0 top-0 -translate-x-1/2 -translate-y-1/2 cursor-nwse-resize' },
    { id: 'ne', className: 'right-0 top-0 translate-x-1/2 -translate-y-1/2 cursor-nesw-resize' },
    { id: 'sw', className: 'left-0 bottom-0 -translate-x-1/2 translate-y-1/2 cursor-nesw-resize' },
    { id: 'se', className: 'right-0 bottom-0 translate-x-1/2 translate-y-1/2 cursor-nwse-resize' },
]

type Props = {
    bbox: Bbox
    pageWidth: number
    pageHeight: number
    color: { border: string; bg: string; swatch: string }
    label: string
    included: boolean
    disabled?: boolean
    containerRef: RefObject<HTMLDivElement | null>
    onCommit: (bbox: Bbox) => void
}

/** A draggable + corner-resizable rectangle over a rendered PDF page. Coordinates are in PDF
 *  points (top-left origin); pixel deltas are converted using the container's rendered size. */
const BBoxOverlay = ({ bbox, pageWidth, pageHeight, color, label, included, disabled, containerRef, onCommit }: Props) => {
    const [draft, setDraft] = useState<Bbox>(bbox)
    const draftRef = useRef<Bbox>(bbox)
    const drag = useRef<{ mode: string; startX: number; startY: number; start: Bbox } | null>(null)

    // Reset to the authoritative bbox whenever it changes (e.g. after a server re-extract).
    useEffect(() => {
        setDraft(bbox)
        draftRef.current = bbox
    }, [bbox])

    const apply = (next: Bbox) => {
        draftRef.current = next
        setDraft(next)
    }

    const onPointerDown = (e: React.PointerEvent) => {
        if (disabled) return
        e.preventDefault()
        e.stopPropagation()
        const mode = (e.target as HTMLElement).dataset.handle ?? 'move'
        ;(e.currentTarget as HTMLElement).setPointerCapture(e.pointerId)
        drag.current = { mode, startX: e.clientX, startY: e.clientY, start: draftRef.current }
    }

    const onPointerMove = (e: React.PointerEvent) => {
        if (!drag.current || !containerRef.current) return
        const rect = containerRef.current.getBoundingClientRect()
        const dx = ((e.clientX - drag.current.startX) / rect.width) * pageWidth
        const dy = ((e.clientY - drag.current.startY) / rect.height) * pageHeight
        let [x0, top, x1, bottom] = drag.current.start
        const m = drag.current.mode
        if (m === 'move') {
            x0 += dx
            x1 += dx
            top += dy
            bottom += dy
        } else {
            if (m.includes('w')) x0 += dx
            if (m.includes('e')) x1 += dx
            if (m.includes('n')) top += dy
            if (m.includes('s')) bottom += dy
        }
        apply(clampBbox([x0, top, x1, bottom], pageWidth, pageHeight))
    }

    const onPointerUp = (e: React.PointerEvent) => {
        if (!drag.current) return
        ;(e.currentTarget as HTMLElement).releasePointerCapture(e.pointerId)
        drag.current = null
        onCommit(draftRef.current)
    }

    const [x0, top, x1, bottom] = draft

    return (
        <div
            className={cn(
                'absolute touch-none border-2',
                color.border,
                included ? color.bg : 'opacity-40',
                disabled ? 'pointer-events-none' : 'cursor-move',
            )}
            style={{
                left: `${(x0 / pageWidth) * 100}%`,
                top: `${(top / pageHeight) * 100}%`,
                width: `${((x1 - x0) / pageWidth) * 100}%`,
                height: `${((bottom - top) / pageHeight) * 100}%`,
            }}
            onPointerDown={onPointerDown}
            onPointerMove={onPointerMove}
            onPointerUp={onPointerUp}
        >
            <span className={cn('pointer-events-none absolute -top-5 left-0 rounded px-1 text-[10px] font-medium text-white', color.swatch)}>
                {label}
            </span>
            {!disabled &&
                HANDLES.map((handle) => (
                    <span
                        key={handle.id}
                        data-handle={handle.id}
                        className={cn('absolute size-2.5 rounded-sm border border-white', color.swatch, handle.className)}
                    />
                ))}
        </div>
    )
}

export default BBoxOverlay
