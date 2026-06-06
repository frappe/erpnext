export const getCurrencySymbol = (currency: string) => {
    // @ts-expect-error - Boot is available
    if (frappe.boot) {
        // @ts-expect-error - Boot is available
        if (frappe.boot.sysdefaults && frappe.boot.sysdefaults.hide_currency_symbol == "Yes")
            return "";
        // @ts-expect-error - Boot is available
        if (!currency) currency = frappe.boot.sysdefaults.currency;

        return getCurrencyProperty(currency, 'symbol') || currency;
    } else {
        return getCurrencyProperty(currency, 'symbol') || currency
    }
}

export const getCurrencyNumberFormat = (currency: string) => {
    return getCurrencyProperty(currency, 'number_format')
}


export const getCurrencyProperty = (currency: string, property: 'symbol' | 'symbol_on_right' | 'number_format') => {
    // @ts-expect-error - Locals is synced
    return locals[':Currency']?.[currency]?.[property]
}