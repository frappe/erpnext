import { Button } from '@/components/ui/button'
import { Dialog, DialogClose, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import ErrorBanner from '@/components/ui/error-banner'
import { Form } from '@/components/ui/form'
import { DataField } from '@/components/ui/form-elements'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import _ from '@/lib/translate'
import { AccountsSettings } from '@/types/Accounts/AccountsSettings'
import { useFrappeGetDoc, useFrappeUpdateDoc } from 'frappe-react-sdk'
import { SettingsIcon } from 'lucide-react'
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
            <DialogContent>
                <SettingsDialogContent onClose={() => setIsOpen(false)} />
            </DialogContent>
        </Dialog>
    )
}

const SettingsDialogContent = ({ onClose }: { onClose: VoidFunction }) => {

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