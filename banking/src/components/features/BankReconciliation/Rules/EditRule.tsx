import { Button } from "@/components/ui/button"
import ErrorBanner from "@/components/ui/error-banner"
import { Form } from "@/components/ui/form"
import _ from "@/lib/translate"
import { BankTransactionRule } from "@/types/Accounts/BankTransactionRule"
import { FrappeError, useFrappeGetDoc, useFrappeUpdateDoc } from "frappe-react-sdk"
import { toast } from "sonner"
import { RuleForm } from "./RuleForm"
import { useForm } from "react-hook-form"
import { Skeleton } from "@/components/ui/skeleton"
import { SettingsPanelContent, SettingsPanelDescription, SettingsPanelHeader, SettingsPanelTitle } from "@/components/ui/settings-dialog"
import { useHotkeys } from "react-hotkeys-hook"

type Props = {
    onClose: VoidFunction,
    ruleID: string
}

const EditRule = ({ onClose, ruleID }: Props) => {

    const { data: rule, isValidating, error, mutate } = useFrappeGetDoc<BankTransactionRule>("Bank Transaction Rule", ruleID, undefined, {
        revalidateOnMount: true
    })

    const { updateDoc, loading, error: updateError } = useFrappeUpdateDoc<BankTransactionRule>()

    const onSubmit = (data: BankTransactionRule) => {
        updateDoc("Bank Transaction Rule", ruleID, data)
            .then(() => {
                toast.success(_("Rule updated."))
                mutate()
                onClose()
            })
    }

    return <>
        <SettingsPanelHeader
            actions={
                <div className="flex items-center gap-2">
                    <Button variant='outline' size='md' type='button' onClick={() => onClose()}>{_("Cancel")}</Button>
                    <Button type='submit' form='rule-form' size='md' disabled={isValidating || loading}>
                        {_("Save")}
                    </Button>
                </div>
            }
        >
            <SettingsPanelTitle>
                {rule?.rule_name}
            </SettingsPanelTitle>
            <SettingsPanelDescription className="sr-only">
                {_("Edit this rule")}
            </SettingsPanelDescription>
        </SettingsPanelHeader>
        <SettingsPanelContent className="px-0">
            {isValidating && <div className="px-4 flex flex-col gap-4 h-full">
                <Skeleton className="h-10 w-full" />
                <Skeleton className="h-10 w-full" />
                <Skeleton className="h-10 w-full" />
                <Skeleton className="h-10 w-full" />
                <Skeleton className="h-10 w-full" />
            </div>}

            {error && <div className="px-4 flex flex-col gap-4 h-full">
                <ErrorBanner error={error} />
            </div>}
            {rule && <EditRuleForm rule={rule} onSubmit={onSubmit} error={updateError} />}
        </SettingsPanelContent>
    </>


}

const EditRuleForm = ({ rule, onSubmit, error }: { rule: BankTransactionRule, onSubmit: (data: BankTransactionRule) => void, error?: FrappeError | null }) => {

    const form = useForm<BankTransactionRule>({
        defaultValues: {
            ...rule,
        }
    })

    useHotkeys('meta+s', () => {
        form.handleSubmit(onSubmit)()
    }, {
        enabled: true,
        preventDefault: true,
        enableOnFormTags: true
    })

    return (
        <Form {...form}>
            <form id='rule-form' onSubmit={form.handleSubmit(onSubmit)} className="flex flex-col justify-between h-full overflow-y-auto px-2">
                <div className="flex flex-col gap-4">
                    {error && <ErrorBanner error={error} />}
                    <RuleForm isEdit />
                </div>
            </form>
        </Form>
    )
}

export default EditRule