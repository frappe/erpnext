export type Summary = {
    value: number,
    indicator?: "Red" | "Green" | "Blue",
    label: string,
    datatype: "Int" | "Float" | "Currency" | "Percent"
}


// eslint-disable-next-line @typescript-eslint/no-explicit-any
export interface QueryReportReturnType<T = any> {
    prepared_report: boolean,
    report_summary: Summary[],
    result: T[],
    columns: unknown[],
    add_total_row: boolean,
    doc?: {
        queued_at: string,
        report_end_time: string,
    }
}