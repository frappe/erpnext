import { useAtom } from "jotai"
import { SelectedBank, selectedBankAccountAtom } from "./bankRecAtoms"
import { useCallback } from "react"
import { useGetBankAccounts, useGetUnreconciledTransactions } from "./utils"
import { cn } from "@/lib/utils"
import { getTimeago } from "@/lib/date"
import ErrorBanner from "@/components/ui/error-banner"
import _ from "@/lib/translate"
import { Badge } from "@/components/ui/badge"
import { useTheme } from "@/components/ui/theme-provider"
import BankLogo from "@/components/common/BankLogo"
import { Empty, EmptyContent, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from "@/components/ui/empty"
import { LandmarkIcon } from "lucide-react"
import { Button } from "@/components/ui/button"
import { useCurrentCompany } from "@/hooks/useCurrentCompany"

const BankPicker = ({ className }: { className?: string }) => {

    const [selectedBank, setSelectedBank] = useAtom(selectedBankAccountAtom)

    const onLoadingSuccess = useCallback((data?: SelectedBank[]) => {
        // If the bank is already selected, then don't set it again
        if (selectedBank) {
            // Check if selected bank is in the data
            if (data?.some((bank: SelectedBank) => bank.name === selectedBank.name)) {
                return
            }
        }
        if (!data) return
        if (data.length === 1) {
            setSelectedBank(data[0])
        } else if (data.length > 1) {
            const defaultBank = data.find((bank: SelectedBank) => bank.is_default)
            if (defaultBank) {
                setSelectedBank(defaultBank)
            } else {
                // Select the first available bank account
                setSelectedBank(data[0])
            }
        }
    }, [setSelectedBank, selectedBank])

    const selectedCompany = useCurrentCompany()

    const { banks, isLoading, error } = useGetBankAccounts(onLoadingSuccess)

    const { themeValue } = useTheme()

    if (isLoading) {
        return null
    }

    if (error) {
        return <ErrorBanner error={error} />
    }

    if (banks?.length === 0) {
        return <Empty>
            <EmptyMedia>
                <LandmarkIcon />
            </EmptyMedia>
            <EmptyHeader>
                <EmptyTitle>{_("No bank accounts found")}</EmptyTitle>
                <EmptyDescription>{_("You have not added any bank accounts to your company.")}</EmptyDescription>
            </EmptyHeader>
            <EmptyContent>
                <Button asChild>
                    <a href={`/desk/bank-account?company=${encodeURIComponent(selectedCompany)}&is_company_account=1`}>
                        {_("Configure Bank Accounts")}
                    </a>
                </Button>
            </EmptyContent>
        </Empty>
    }
    return (
        <div
            className={cn("flex gap-3 items-stretch w-full overflow-x-auto pe-4",
                banks?.length > 4 ? 'pb-2' : '', className,
            )}
            style={{
                scrollbarWidth: 'thin',
                scrollbarColor: themeValue === 'Dark' ? 'var(--surface-gray-2) var(--surface-gray-1)' : 'rgb(209 213 219) rgb(243 244 246)',
            }}
        >
            {
                banks?.map((bank) => (
                    <BankPickerItem key={bank.name} bank={bank} />
                ))
            }
        </div>
    )
}

const BankPickerItem = ({ bank }: { bank: SelectedBank }) => {

    const [selectedBank, setSelectedBank] = useAtom(selectedBankAccountAtom)

    const isSelected = selectedBank?.name === bank.name

    const { mutate } = useGetUnreconciledTransactions()

    const onSelect = () => {
        setSelectedBank(bank)
        mutate()
    }

    return <div
        role="button"
        title={`Select ${bank.account_name}`}
        onClick={onSelect}
        className={cn('rounded-md border border-outline-gray-1 max-w-60 min-w-60 p-2 overflow-hidden cursor-pointer',
            isSelected ? 'border-outline-gray-5 bg-surface-gray-1' : 'hover:bg-surface-gray-1'
        )}
    >


        <BankLogo bank={bank} className="mb-2" />

        <div className="flex flex-col gap-1">
            <div className="flex gap-2 items-center">
                <span className={cn("text-sm font-medium line-clamp-1 text-ink-gray-8")}>{bank.account_name}</span>
                {bank.account_type && <Badge variant='subtle' size='sm' theme='gray'>
                    {bank.account_type?.slice(0, 24)}
                </Badge>}
            </div>

            <span title={_("GL Account")} className={cn("text-ellipsis line-clamp-1 text-sm text-ink-gray-6")}>{bank.account}</span>
            {bank.last_integration_date && <span className="text-xs text-ink-gray-5">{_("Last Synced Transaction")}: {getTimeago(bank.last_integration_date)}</span>}
        </div>

    </div >
}

export default BankPicker