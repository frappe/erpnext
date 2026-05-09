import { useAtomValue } from "jotai"
import { atomWithStorage } from "jotai/utils"

export const selectedCompanyAtom = atomWithStorage<string>('bank-rec-selected-company', window.frappe?.boot?.user?.defaults?.company || '')

export const useCurrentCompany = () => {
    const selectedCompany = useAtomValue(selectedCompanyAtom)
    return selectedCompany ? selectedCompany : (window.frappe?.boot?.user?.defaults?.company as string)
}