import { Button } from "@/components/ui/button"
import ErrorBanner from "@/components/ui/error-banner"
import { Form } from "@/components/ui/form"
import { useCurrentCompany } from "@/hooks/useCurrentCompany"
import _ from "@/lib/translate"
import { BankTransactionRule } from "@/types/Accounts/BankTransactionRule"
import { useFrappeCreateDoc } from "frappe-react-sdk"
import { toast } from "sonner"
import { RuleForm } from "./RuleForm"
import { useForm } from "react-hook-form"
import { SettingsPanelHeader, SettingsPanelDescription, SettingsPanelTitle, SettingsPanelContent } from "@/components/ui/settings-dialog"
import { useHotkeys } from "react-hotkeys-hook"

type Props = {
    onCreate: VoidFunction
}

const CreateNewRule = ({ onCreate }: Props) => {

    const currentCompany = useCurrentCompany()

    const form = useForm<BankTransactionRule>({
        defaultValues: {
            rule_name: "",
            company: currentCompany,
            rule_description: "",
            transaction_type: "Any",
            classify_as: 'Bank Entry',
            bank_entry_type: "Single Account",
            description_rules: [{
                check: "Contains",
            }]
        }
    })

    const { createDoc, loading, error } = useFrappeCreateDoc<BankTransactionRule>()

    const onSubmit = (data: BankTransactionRule) => {
        createDoc("Bank Transaction Rule", data)
            .then(() => {
                toast.success(_("Rule created successfully"))
                onCreate()
            })
    }


    useHotkeys('meta+s', () => {
        form.handleSubmit(onSubmit)()
    }, {
        enabled: true,
        preventDefault: true,
        enableOnFormTags: true
    })

    return (
        <>
            <SettingsPanelHeader
                actions={
                    <div className="flex items-center gap-2">
                        <Button variant='outline' size='md' type='button' onClick={() => onCreate()}>{_("Cancel")}</Button>
                        <Button type='submit' form='rule-form' size='md' disabled={loading}>
                            {_("Save")}
                        </Button>
                    </div>
                }
            >
                <SettingsPanelTitle>
                    {_("New Rule")}
                </SettingsPanelTitle>
                <SettingsPanelDescription>
                    {_("Create a new rule to automatically classify transactions.")}
                </SettingsPanelDescription>
            </SettingsPanelHeader>
            <SettingsPanelContent className="px-0">
                <Form {...form}>
                    <form id='rule-form' onSubmit={form.handleSubmit(onSubmit)} className="flex flex-col justify-between h-full overflow-y-auto px-2">
                        <div className="flex flex-col gap-4">
                            {error && <ErrorBanner error={error} />}
                            <RuleForm />
                        </div>
                    </form>
                </Form>
            </SettingsPanelContent>
        </>

    )
}

export default CreateNewRule