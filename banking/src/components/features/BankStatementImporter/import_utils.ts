import { BankStatementImportLog } from "@/types/Accounts/BankStatementImportLog"
import { useFrappeGetCall } from "frappe-react-sdk"


export interface GetStatementDetailsResponse {
    doc: BankStatementImportLog,
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
        transaction_type?: string,
        debit_credit?: string,
        included_fee?: number,
        excluded_fee?: number,
        party_name?: string,
        party_account_number?: string,
        party_iban?: string,
    }>,
    date_format: string,
    raw_data: Array<Array<string>>,
    currency: string,
}

export const useGetStatementDetails = (id: string) => {
    return useFrappeGetCall<{ message: GetStatementDetailsResponse }>("erpnext.accounts.doctype.bank_statement_import_log.bank_statement_import_log.get_statement_details", {
        statement_import_id: id,
    }, undefined, {
        revalidateOnFocus: false
    })

}