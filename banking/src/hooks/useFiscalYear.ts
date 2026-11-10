import { useFrappeGetCall } from "frappe-react-sdk"
import { useMemo } from "react"
import dayjs from "dayjs"
import { useCurrentCompany } from "./useCurrentCompany"

export type FiscalYear = {
    name: string
    year_start_date: string
    year_end_date: string
}

/**
 * The fiscal year containing today, for the currently selected company.
 *
 * `company` matters in multi-company setups, where fiscal years can be restricted to
 * specific companies. `date` matters because without it `get_fiscal_year` returns the newest
 * fiscal year in the system (they're ordered by start date, descending) - which may be one
 * created in advance for a year that hasn't started.
 */
const useFiscalYear = () => {
    const company = useCurrentCompany()

    const { data, ...rest } = useFrappeGetCall<{ message: FiscalYear | [string, string, string] | false }>(
        "erpnext.accounts.utils.get_fiscal_year",
        {
            date: dayjs().format("YYYY-MM-DD"),
            company,
            as_dict: 1,
            // Return nothing instead of throwing/msgprinting when no fiscal year covers today.
            raise_on_missing: 0,
            verbose: 0,
        },
        company ? `fiscal_year_${company}` : null,
        {
            revalidateOnFocus: false,
            revalidateIfStale: false,
            revalidateOnReconnect: false
        }
    )

    // get_fiscal_year returns a dict with as_dict, a (name, start, end) tuple without it, and
    // false when there's no match - normalise all three.
    const fiscalYear = useMemo<FiscalYear | undefined>(() => {
        const message = data?.message
        if (!message) return undefined

        if (Array.isArray(message)) {
            const [name, year_start_date, year_end_date] = message
            return { name, year_start_date, year_end_date }
        }

        return message
    }, [data])

    return { fiscalYear, ...rest }
}

export default useFiscalYear
