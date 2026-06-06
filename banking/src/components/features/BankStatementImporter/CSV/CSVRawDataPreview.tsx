import { useEffect, useRef, useState } from "react"
import { toast } from "sonner"
import _ from "@/lib/translate"
import RawTableGrid from "../RawTableGrid"
import {
    applyColumnMappingChange,
    ColumnMapsTo,
    GetStatementDetailsResponse,
    useSetHeaderIndex,
    useUpdateColumnMapping,
} from "../import_utils"
import { BankStatementImportLogColumnMap } from "@/types/Accounts/BankStatementImportLogColumnMap"

type Mapping = Pick<BankStatementImportLogColumnMap, "index" | "maps_to" | "header_text" | "variable">

const toMapping = (columns?: BankStatementImportLogColumnMap[]): Mapping[] =>
    (columns ?? []).map((c) => ({
        index: c.index,
        maps_to: c.maps_to,
        header_text: c.header_text,
        variable: c.variable,
    }))

const headerToState = (index?: number) => (index != null && index >= 0 ? index : null)

const CSVRawDataPreview = ({
    data,
    mutate,
}: {
    data: GetStatementDetailsResponse
    mutate: () => void
}) => {
    const isCompleted = data.doc.status === "Completed"

    const [mapping, setMapping] = useState<Mapping[]>(() => toMapping(data.doc.column_mapping))
    const [headerIndex, setHeaderIndex] = useState<number | null>(() =>
        headerToState(data.doc.detected_header_index),
    )

    const { call: updateMapping, loading: savingMapping } = useUpdateColumnMapping()
    const { call: setHeader, loading: savingHeader } = useSetHeaderIndex()

    const mappingRef = useRef(mapping)
    const saveTimer = useRef<ReturnType<typeof setTimeout>>(undefined)

    useEffect(() => () => clearTimeout(saveTimer.current), [])

    const columnMappingRecord: Record<number, ColumnMapsTo> = {}
    mapping.forEach((c) => {
        if (c.maps_to) columnMappingRecord[c.index] = c.maps_to as ColumnMapsTo
    })

    const commitMapping = (next: Mapping[]) => {
        mappingRef.current = next
        setMapping(next)
    }

    // Persist mapping edits (debounced) so the transaction preview updates in realtime.
    const scheduleSaveMapping = () => {
        if (isCompleted) return
        clearTimeout(saveTimer.current)
        saveTimer.current = setTimeout(() => {
            updateMapping({ statement_import_id: data.doc.name, column_mapping: mappingRef.current })
                .then(() => mutate())
                .catch(() => toast.error(_("Could not save the column mapping.")))
        }, 500)
    }

    const onChangeMapping = (columnIndex: number, mapsTo: ColumnMapsTo) => {
        if (isCompleted) return
        commitMapping(applyColumnMappingChange(mappingRef.current, columnIndex, mapsTo))
        scheduleSaveMapping()
    }

    const onSetHeader = (rowIndex: number | null) => {
        if (isCompleted) return
        setHeaderIndex(rowIndex)
        setHeader({ statement_import_id: data.doc.name, header_index: rowIndex ?? -1 })
            .then((res) => {
                // The backend re-derives the mapping for the new header; sync local state.
                const doc = res?.message?.doc
                if (doc) {
                    commitMapping(toMapping(doc.column_mapping))
                    setHeaderIndex(headerToState(doc.detected_header_index))
                }
                mutate()
            })
            .catch(() => toast.error(_("Could not update the header row.")))
    }

    return (
        <RawTableGrid
            rows={data.raw_data}
            columnMapping={columnMappingRecord}
            headerIndex={headerIndex}
            editable={!isCompleted}
            disabled={isCompleted || savingMapping || savingHeader}
            onChangeMapping={onChangeMapping}
            onSetHeader={onSetHeader}
        />
    )
}

export default CSVRawDataPreview
