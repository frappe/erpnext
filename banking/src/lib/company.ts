
export const getCompanyCurrency = (company: string) => {
    // @ts-expect-error - Locals is synced
    return locals[':Company']?.[company]?.['default_currency']
}

export const getCompanyCostCenter = (company: string) => {
    // @ts-expect-error - Locals is synced
    return locals[':Company']?.[company]?.['cost_center']
}

export const getCompany = (company: string) => {
    // @ts-expect-error - Locals is synced
    return locals?.[':Company']?.[company]
}