import { Button } from '@/components/ui/button'
import { Dialog, DialogClose, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import ErrorBanner from '@/components/ui/error-banner'
import { Form } from '@/components/ui/form'
import { DataField } from '@/components/ui/form-elements'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
// import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
// import { getErrorMessage } from '@/lib/frappe'
import _ from '@/lib/translate'
import { MintSettings } from '@/types/Mint/MintSettings'
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
                        <Button variant={'outline'} size='icon'>
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

    const form = useForm<MintSettings>({
        defaultValues: {
            transfer_match_days: 4,
            // google_project_id: "",
            // google_processor_location: "us",
            // google_service_account_json_key: "",
            // bank_statement_gdoc_processor: "",
        }
    })

    const { mutate, error: fetchError } = useFrappeGetDoc<MintSettings>("Mint Settings", "Mint Settings", undefined, {
        onSuccess: (data) => {
            form.reset(data)
        },
        revalidateOnFocus: false
    })

    const { updateDoc, loading, error } = useFrappeUpdateDoc<MintSettings>()

    const onSubmit = (data: MintSettings) => {
        updateDoc("Mint Settings", "Mint Settings", data)
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
                <DialogDescription>{_("Configure settings for Mint.")}</DialogDescription>
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
                    formDescription={_("For example, if set to 4, Mint will try to find matching transactions in other banks 4 days before and after the transaction date. This is because transactions can clear on different days on different bank accounts.")}
                />

                {/* <H4 className='text-sm font-semibold'>Google Document AI</H4> */}

                {/* <DataField
                    name='google_project_id'
                    label={_("Google Project ID")}
                    isRequired
                    formDescription={_("The Google Project ID is used to authenticate with the Google Cloud Platform.")}
                />

                <FormField
                    control={form.control}
                    name={"google_processor_location"}
                    render={({ field }) => (
                        <FormItem className='flex flex-col'>
                            <FormLabel>{_("Google Document Processor Location")}<span className="text-destructive">*</span></FormLabel>
                            <Select onValueChange={field.onChange} defaultValue={field.value}>
                                <FormControl>
                                    <SelectTrigger className='w-full'>
                                        <SelectValue placeholder={_("Select Location")} />
                                    </SelectTrigger>
                                </FormControl>
                                <SelectContent>
                                    <SelectItem value="us">{_("US")}</SelectItem>
                                    <SelectItem value="eu">{_("EU")}</SelectItem>
                                </SelectContent>
                            </Select>
                            <FormDescription>{_("Location where the document processor is run.")}</FormDescription>
                            <FormMessage />
                        </FormItem>
                    )}
                />

                <DataField
                    name='google_service_account_json_key'
                    label={_("Google Service Account JSON Key")}
                    isRequired
                    inputProps={{
                        type: "password"
                    }}
                    formDescription={_("Paste the Service Key (JSON) from the Google Cloud Console.")}
                />

                {data && data.google_project_id && data.google_service_account_json_key && <ProcessorField />} */}

            </div>

            <DialogFooter className='mt-2'>
                <DialogClose asChild>
                    <Button variant={'outline'} disabled={loading}>{_("Close")}</Button>
                </DialogClose>
                <Button type='submit' disabled={loading}>{_("Save")}</Button>
            </DialogFooter>
        </form>
    </Form>
}


// const ProcessorField = () => {

//     const form = useFormContext()

//     const { data, error, mutate } = useFrappeGetCall("mint.apis.google_ai.get_list_of_processors", {
//         processor_type: "BANK_STATEMENT"
//     }, undefined, {
//         revalidateOnFocus: false,
//         revalidateIfStale: false
//     })

//     const { call: createProcessor } = useFrappePostCall('mint.apis.google_ai.create_document_processor')

//     const onProcessorCreate = () => {
//         createProcessor({})
//             .then((data) => {
//                 mutate()
//                 form.setValue("bank_statement_gdoc_processor", data.message.id)
//             }).catch((error) => {
//                 toast.error(_("Failed to create processor"), {
//                     description: getErrorMessage(error)
//                 })
//             })
//     }

//     return <div>
//         {error && <ErrorBanner error={error} />}
//         {data && <div className='flex flex-col gap-2'>
//             <FormField
//                 control={form.control}
//                 name={"bank_statement_gdoc_processor"}
//                 render={({ field }) => (
//                     <FormItem className='flex flex-col'>
//                         <FormLabel>{_("Bank Statement Processor")}<span className="text-destructive">*</span></FormLabel>
//                         <Select onValueChange={field.onChange} value={field.value}>
//                             <FormControl>
//                                 <SelectTrigger className='w-full'>
//                                     <SelectValue placeholder={_("Select Processor")} />
//                                 </SelectTrigger>
//                             </FormControl>
//                             <SelectContent>
//                                 {data?.message.map((processor: { id: string, display_name: string }) => (
//                                     <SelectItem key={processor.id} value={processor.id}>{processor.display_name} ({processor.id})</SelectItem>
//                                 ))}
//                             </SelectContent>
//                         </Select>
//                         <FormDescription>{_("Location where the document processor is run.")}</FormDescription>
//                         <FormMessage />
//                     </FormItem>
//                 )}
//             />

//             {data.message.length === 0 && <div>
//                 <Button variant={'outline'} type='button' onClick={onProcessorCreate}>{_("Create New Bank Statement Processor")}</Button>
//             </div>}
//         </div>
//         }
//     </div>

// }

export default Settings