import { Button } from '@/components/ui/button'
import { Dialog, DialogTrigger } from '@/components/ui/dialog'
import ErrorBanner from '@/components/ui/error-banner'
import { Form } from '@/components/ui/form'
import { DataField } from '@/components/ui/form-elements'
import {
    SettingsDialog,
    SettingsPanel,
    SettingsPanelDescription,
    SettingsPanelHeader,
    SettingsPanels,
    SettingsPanelTitle,
    SettingsTabGroup,
    SettingsTabItem,
    SettingsTabs,
    useSettingsDialog,
    SettingsPanelContent,
} from '@/components/ui/settings-dialog'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import _ from '@/lib/translate'
import { AccountsSettings } from '@/types/Accounts/AccountsSettings'
import { useFrappeGetDoc, useFrappeUpdateDoc } from 'frappe-react-sdk'
import { LandmarkIcon, ListIcon, SettingsIcon, SlidersVerticalIcon, ZapIcon } from 'lucide-react'
import { useState } from 'react'
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
            <SettingsDialog defaultValue="preferences" onClose={() => setIsOpen(false)}>
                <SettingsTabs>
                    <SettingsTabGroup header={_("Configuration")}>
                        <SettingsTabItem
                            icon={<SlidersVerticalIcon />}
                            label={_("Preferences")}
                            value="preferences"
                        />
                        <SettingsTabItem
                            icon={<ZapIcon />}
                            label={_("Matching Rules")}
                            value="rules"
                        />
                    </SettingsTabGroup>

                    <SettingsTabGroup header={_("Setup")}>
                        <SettingsTabItem
                            icon={<LandmarkIcon />}
                            label={_("Bank Accounts")}
                            value="bank-accounts"
                        />
                        <SettingsTabItem
                            icon={<ListIcon />}
                            label={_("Masters")}
                            value="masters"
                        />
                    </SettingsTabGroup>
                </SettingsTabs>

                <SettingsPanels>
                    <SettingsPanel value="preferences">
                        <BankingSettings />
                    </SettingsPanel>
                    <SettingsPanel value="rules" />
                    <SettingsPanel value="bank-accounts" />
                    <SettingsPanel value="masters" />
                </SettingsPanels>
            </SettingsDialog>
        </Dialog>
    )
}

const BankingSettings = () => {
    const { onClose } = useSettingsDialog()

    const form = useForm<AccountsSettings>({
        defaultValues: {
            transfer_match_days: 4,
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
                onClose?.()
            })
    }

    return <>

        <SettingsPanelHeader>
            <SettingsPanelTitle>{_("Preferences")}</SettingsPanelTitle>
            <SettingsPanelDescription>{_("Configure default settings for the banking module.")}</SettingsPanelDescription>
        </SettingsPanelHeader>
        <SettingsPanelContent>
            <Form {...form}>
                <form onSubmit={form.handleSubmit(onSubmit)}>

                    <div className='flex flex-col gap-4 w-full'>
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

                    <div className='flex justify-end mt-2'>
                        <Button type='submit' disabled={loading} size='md'>{_("Save")}</Button>
                    </div>
                </form>
            </Form>
        </SettingsPanelContent>
    </>
}

export default Settings
