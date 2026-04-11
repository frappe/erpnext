import { useAtom, useSetAtom } from "jotai"
import { SelectedBank, selectedBankAccountAtom } from "./bankRecAtoms"
import { useCallback } from "react"
import { useGetBankAccounts, useGetUnreconciledTransactions } from "./utils"
import { cn } from "@/lib/utils"
import { Landmark } from "lucide-react"
import { H4 } from "@/components/ui/typography"
import { getTimeago } from "@/lib/date"
import ErrorBanner from "@/components/ui/error-banner"
import _ from "@/lib/translate"
import { Badge } from "@/components/ui/badge"

const BankPicker = ({ className, size = 'base' }: { className?: string, size?: 'base' | 'sm' }) => {

    const setSelectedBank = useSetAtom(selectedBankAccountAtom)

    const onLoadingSuccess = useCallback((data?: SelectedBank[]) => {
        if (!data) return
        if (data.length === 1) {
            setSelectedBank(data[0])
        } else if (data.length > 1) {
            const defaultBank = data.find((bank: SelectedBank) => bank.is_default)
            if (defaultBank) {
                setSelectedBank(defaultBank)
            }
        }
    }, [setSelectedBank])

    const { banks, isLoading, error } = useGetBankAccounts(onLoadingSuccess)

    if (isLoading) {
        return null
    }

    if (error) {
        return <ErrorBanner error={error} />
    }
    return (
        <div
            className={cn("flex gap-3 items-stretch w-full overflow-x-auto bank-picker-scrollbar pr-4",
                banks?.length > 4 ? 'pb-2' : '', className,
            )}
            style={{
                scrollbarWidth: 'thin',
                scrollbarColor: 'rgb(209 213 219) rgb(243 244 246)',
            }}
        >
            {
                banks?.map((bank) => (
                    <BankPickerItem key={bank.name} bank={bank} size={size} />
                ))
            }
        </div>
    )
}

const BankPickerItem = ({ bank, size = 'base' }: { bank: SelectedBank, size?: 'base' | 'sm' }) => {

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
        className={cn('rounded-md border border-outline-gray-1 min-w-80 p-2 overflow-hidden cursor-pointer',
            isSelected ? 'border-outline-gray-5 bg-surface-gray-1' : 'hover:bg-surface-gray-1',
            {
                "max-w-60 min-w-60": size === 'sm',
            }
        )}
    >
        {bank.logo ? <img
            src={`/assets/erpnext/banking/${bank.logo}`}
            alt={bank.bank || bank.name || ''}
            className={cn("max-w-24 object-left h-10 object-contain mb-1", {
                'h-6 max-w-18 mb-2': size === 'sm',
            })}
        /> : <div className={cn("rounded-md flex items-center h-10 gap-2", {
            "h-6 mb-2": size === 'sm',
        })}>
            <Landmark size={size === 'sm' ? '16px' : '30px'} />
            <H4 className={cn("text-base mb-0", {
                'text-xs': size === 'sm',
            })}>{bank.bank}</H4>
        </div>}

        <div className="flex flex-col gap-1">
            <div className="flex gap-2 items-center">
                <span className={cn("text-sm font-medium line-clamp-1 text-ink-gray-8")}>{bank.account_name}</span>
                {bank.account_type && <Badge variant='subtle' size='sm' theme='gray'>
                    {bank.account_type?.slice(0, 24)}
                </Badge>}
            </div>

            <span title={_("GL Account")} className={cn("text-ellipsis line-clamp-1 text-sm text-ink-gray-6")}>{bank.account}</span>
            {bank.last_integration_date && size !== 'sm' && <span className="text-xs text-ink-gray-5">{_("Last Synced Transaction")}: {getTimeago(bank.last_integration_date)}</span>}
        </div>

    </div >
}

export default BankPicker