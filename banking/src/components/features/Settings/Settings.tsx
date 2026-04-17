import { Button } from '@/components/ui/button'
import { Dialog, DialogClose, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import ErrorBanner from '@/components/ui/error-banner'
import { Form } from '@/components/ui/form'
import { DataField } from '@/components/ui/form-elements'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import _ from '@/lib/translate'
import { cn } from '@/lib/utils'
import { AccountsSettings } from '@/types/Accounts/AccountsSettings'
import { useFrappeGetDoc, useFrappeUpdateDoc } from 'frappe-react-sdk'
import { LandmarkIcon, SettingsIcon, SlidersVerticalIcon, ZapIcon } from 'lucide-react'
import { createContext, PropsWithChildren, useContext, useState } from 'react'
import { useForm } from 'react-hook-form'
import { toast } from 'sonner'

const Settings = () => {

    const [isOpen, setIsOpen] = useState(false)

    return (
        <Dialog open={isOpen} onOpenChange={setIsOpen}>
            <Tooltip>
                <TooltipTrigger asChild>
                    <DialogTrigger asChild>
                        <Button variant={'outline'} isIconButton size='md'>
                            <SettingsIcon />
                        </Button>
                    </DialogTrigger>
                </TooltipTrigger>
                <TooltipContent>
                    {_("Settings")}
                </TooltipContent>
            </Tooltip>
            <DialogContent className='min-w-5xl p-0'>
                <SettingsDialogContent onClose={() => setIsOpen(false)} />
            </DialogContent>
        </Dialog>
    )
}

const SettingsSwitcherContext = createContext<{
    currentPage: string
    setCurrentPage: (page: string) => void
}>({
    currentPage: "",
    setCurrentPage: () => { }
})


const SettingsDialogContent = ({ onClose }: { onClose: VoidFunction }) => {

    const [page, setPage] = useState("preferences")


    return <SettingsSwitcherContext
        value={{
            currentPage: page,
            setCurrentPage: setPage
        }}>
        <div className='flex h-[calc(100vh-8rem)] bg-surface-menu-bar'>

            <SettingsSidebar />

            <div className='flex flex-col flex-1 overflow-y-auto bg-surface-modal'></div>

        </div>
    </SettingsSwitcherContext>


}



const SettingsSidebar = () => {

    return <div className='flex flex-col w-56 bg-surface-menu-bar rounded-l-lg shrink-0 overflow-y-auto m-1'>

        <SettingsSidebarGroupHeader>Configuration</SettingsSidebarGroupHeader>

        <SettingsSidebarGroup>
            <SettingsSidebarItem
                icon={<SlidersVerticalIcon />}
                label="Preferences"
                value="preferences" />

            <SettingsSidebarItem
                icon={<ZapIcon />}
                label="Matching Rules"
                value="rules" />
            <SettingsSidebarItem
                icon={<LandmarkIcon />}
                label="Bank Accounts"
                value="bank-accounts" />

        </SettingsSidebarGroup>

    </div>

}

const SettingsSidebarGroupHeader = ({ children }: PropsWithChildren) => {

    return <div className="h-7.5 px-2 py-[7px] my-[3px] flex cursor-pointer gap-1.5 text-xs font-regular text-ink-gray-5 transition-all duration-300 ease-in-out sticky top-0 z-10 bg-surface-menu-bar">
        <span>{children}</span>
    </div>

}

const SettingsSidebarGroup = ({ children }: PropsWithChildren) => {
    return <nav className='space-y-[3px] px-1'>
        {children}
    </nav>
}

const SettingsSidebarItem = ({ icon, label, value }: { icon?: React.ReactNode, label: string, value: string }) => {

    const { currentPage, setCurrentPage } = useContext(SettingsSwitcherContext)

    return <button
        onClick={() => setCurrentPage(value)}
        className={cn("flex h-7.5 cursor-pointer items-center rounded text-ink-gray-6 duration-300 ease-in-out focus:outline-none focus:transition-none focus-visible:rounded focus-visible:ring-2 focus-visible:ring-outline-gray-3 w-full",
            value === currentPage ? "bg-surface-selected shadow-sm hover:bg-surface-selected" : "hover:bg-surface-gray-3"
        )}>
        <div className='flex w-full items-center justify-between duration-300 ease-in-out px-2 py-[7px]'>
            <div className='flex items-center truncate'>
                <div className="[&_svg:not([class*='size-'])]:size-4 text-ink-gray-6 [&_svg:not([class*='text-'])]:text-ink-gray-6">
                    {icon}
                </div>

                <span className='flex-1 shrink-0 truncate text-sm duration-300 ease-in-out ml-2 w-auto opacity-100 text-ink-gray-6'>
                    {label}
                </span>

            </div>
        </div>
    </button>
}

const BankingSettings = () => {
    const form = useForm<AccountsSettings>({
        defaultValues: {
            transfer_match_days: 4,
            // google_project_id: "",
            // google_processor_location: "us",
            // google_service_account_json_key: "",
            // bank_statement_gdoc_processor: "",
        }
    })

    const { mutate, error: fetchError } = useFrappeGetDoc<AccountsSettings>("Accounts Settings", "Accounts Settings", undefined, {
        onSuccess: (data) => {
            form.reset(data)
        },
        revalidateOnFocus: false
    })

    const { updateDoc, loading, error } = useFrappeUpdateDoc<AccountsSettings>()

    const onSubmit = (data: AccountsSettings) => {
        updateDoc("Accounts Settings", "Accounts Settings", data)
            .then(() => {
                toast.success(_("Settings updated"))
                mutate()
                onClose()
            })
    }



    return <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)}>
            <DialogHeader>
                <DialogTitle>{_("Settings")}</DialogTitle>
                <DialogDescription>{_("Configure settings for banking.")}</DialogDescription>
            </DialogHeader>
            <div className='flex flex-col gap-4 w-full py-4'>
                {fetchError && <ErrorBanner error={fetchError} />}
                {error && <ErrorBanner error={error} />}

                <DataField
                    name='transfer_match_days'
                    label={_("Number of days to match transfers")}
                    isRequired
                    inputProps={{
                        type: 'number',
                        inputMode: 'numeric',
                    }}
                    formDescription={_("For example, if set to 4, the system will try to find matching transactions in other banks 4 days before and after the transaction date. This is because transactions can clear on different days on different bank accounts.")}
                />

            </div>

            <DialogFooter className='mt-2'>
                <DialogClose asChild>
                    <Button variant={'outline'} disabled={loading} size='md'>{_("Close")}</Button>
                </DialogClose>
                <Button type='submit' disabled={loading} size='md'>{_("Save")}</Button>
            </DialogFooter>
        </form>
    </Form>
}

export default Settings