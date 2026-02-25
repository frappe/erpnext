import { useFrappeGetCall } from "frappe-react-sdk"


export interface GetStatementDetailsResponse {
    file_name: string,
    file_path: string,
    data: Array<Array<string>>,
    header_index: number,
    header_row: Array<string>,
    column_mapping: Record<string, number>,
    transaction_starting_index: number,
    transaction_ending_index: number,
    transaction_rows: Array<{
        date_format: string,
        date?: string,
        amount?: number,
        withdrawal?: number,
        deposit?: number,
        balance?: number,
        reference?: string,
        description?: string,
        transaction_type?: string,
    }>,
    date_format: string,
    amount_format: string,
    statement_start_date: string,
    statement_end_date: string,
    closing_balance: number,
    conflicting_transactions: Array<{
        name: string,
        date: string,
        withdrawal: number,
        deposit: number,
        description: string,
        reference_number: string,
        currency: string,
    }>,
    final_transactions: Array<{
        date: string,
        withdrawal: number,
        deposit: number,
        description: string,
        reference: string,
        transaction_type: string,
    }>,
    currency: string,
}

export const useGetStatementDetails = (fileURL: string, bankAccount: string) => {
    return useFrappeGetCall<{ message: GetStatementDetailsResponse }>("mint.apis.statement_import.get_statement_details", {
        file_url: fileURL,
        bank_account: bankAccount,
    }, undefined, {
        revalidateOnFocus: false
    })

}