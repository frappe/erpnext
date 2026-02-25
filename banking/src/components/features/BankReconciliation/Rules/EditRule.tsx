import { Button } from "@/components/ui/button"
import ErrorBanner from "@/components/ui/error-banner"
import { Form } from "@/components/ui/form"
import { SheetClose, SheetFooter } from "@/components/ui/sheet"
import _ from "@/lib/translate"
import { MintBankTransactionRule } from "@/types/Mint/MintBankTransactionRule"
import { useFrappeGetDoc, useFrappeUpdateDoc } from "frappe-react-sdk"
import { toast } from "sonner"
import { RuleForm } from "./RuleForm"
import { useForm } from "react-hook-form"
import { Skeleton } from "@/components/ui/skeleton"

type Props = {
    onClose: VoidFunction,
    ruleID: string
}

const EditRule = ({ onClose, ruleID }: Props) => {

    const { data: rule, isValidating, error, mutate } = useFrappeGetDoc<MintBankTransactionRule>("Mint Bank Transaction Rule", ruleID, undefined, {
        revalidateOnMount: true
    })

    if (isValidating) {

        return <div className="px-4 flex flex-col gap-4 h-full">
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />

            <SheetFooter>
                <SheetClose asChild>
                    <Button type='button' variant='outline'>
                        {_("Close")}
                    </Button>
                </SheetClose>
            </SheetFooter>
        </div>
    }

    if (error) {
        return <div className="px-4 flex flex-col gap-4 h-full">
            <ErrorBanner error={error} />

            <SheetFooter>
                <SheetClose asChild>
                    <Button type='button' variant='outline'>
                        {_("Close")}
                    </Button>
                </SheetClose>
            </SheetFooter>
        </div>
    }

    if (rule) {
        return <EditRuleForm rule={rule} onClose={onClose} mutate={mutate} />
    }

    return null


}

const EditRuleForm = ({ rule, onClose, mutate }: { rule: MintBankTransactionRule, onClose: VoidFunction, mutate: VoidFunction }) => {

    const form = useForm<MintBankTransactionRule>({
        defaultValues: {
            ...rule,
        }
    })

    const { updateDoc, loading, error } = useFrappeUpdateDoc<MintBankTransactionRule>()

    const onSubmit = (data: MintBankTransactionRule) => {
        updateDoc("Mint Bank Transaction Rule", rule.name, data)
            .then(() => {
                toast.success(_("Rule updated."))
                mutate()
                onClose()
            })
    }

    return (
        <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="flex flex-col justify-between h-full overflow-y-auto">
                <div className="flex flex-col gap-4 px-4 pb-4">
                    {error && <ErrorBanner error={error} />}
                    <RuleForm isEdit />
                </div>

                <SheetFooter>
                    <Button type='submit' disabled={loading}>
                        {_("Save")}
                    </Button>
                    <SheetClose asChild>
                        <Button type='button' variant='outline' disabled={loading}>
                            {_("Close")}
                        </Button>
                    </SheetClose>
                </SheetFooter>
            </form>
        </Form>
    )
}

export default EditRule