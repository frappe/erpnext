import { useFrappeGetCall } from "frappe-react-sdk"

const useFiscalYear = () => {

    return useFrappeGetCall("erpnext.accounts.utils.get_fiscal_year", undefined, 'fiscal_year', {
        revalidateOnFocus: false,
        revalidateIfStale: false,
        revalidateOnReconnect: false
    })

}

export default useFiscalYear