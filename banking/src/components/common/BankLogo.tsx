import { cn } from '@/lib/utils'
import { SelectedBank } from '../features/BankReconciliation/bankRecAtoms'
import { useTheme } from '../ui/theme-provider'
import { Landmark } from 'lucide-react'
import { H4 } from '../ui/typography'

const BankLogo = ({ bank, className, imageClassName, iconSize = '18px', iconClassName }: { bank?: SelectedBank | null, className?: string, imageClassName?: string, iconSize?: string, iconClassName?: string }) => {

    const { themeValue } = useTheme()
    return (
        <div className={cn('h-6 flex items-center gap-1', className)}> {bank?.logo ? <img
            src={`/assets/erpnext/images/bank-logos/${themeValue === 'Dark' ? (bank.logoDark ?? bank.logo) : bank.logo}`}
            alt={bank.bank || bank.name || ''}
            className={cn("h-6 max-w-22 me-auto object-contain", imageClassName, {
                'dark:invert dark:brightness-0': bank.darkModeInvert
            }, bank.logoClassName)}
        /> : <>
            <Landmark size={iconSize} className={iconClassName} />
            <H4 className={cn("text-xs -mb-0.5", {
            })}>{bank?.bank ?? ''}</H4>
        </>
        }</div>
    )
}

export default BankLogo