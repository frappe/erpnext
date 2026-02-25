import { Button } from "@/components/ui/button"
import ErrorBanner from "@/components/ui/error-banner"
import { Form } from "@/components/ui/form"
import { SheetClose, SheetFooter } from "@/components/ui/sheet"
import { useCurrentCompany } from "@/hooks/useCurrentCompany"
import _ from "@/lib/translate"
import { MintBankTransactionRule } from "@/types/Mint/MintBankTransactionRule"
import { useFrappeCreateDoc } from "frappe-react-sdk"
import { toast } from "sonner"
import { RuleForm } from "./RuleForm"
import { useForm } from "react-hook-form"

type Props = {
    onCreate: VoidFunction
}

const CreateNewRule = ({ onCreate }: Props) => {

    const currentCompany = useCurrentCompany()

    const form = useForm<MintBankTransactionRule>({
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

    const { createDoc, loading, error } = useFrappeCreateDoc<MintBankTransactionRule>()

    const onSubmit = (data: MintBankTransactionRule) => {
        createDoc("Mint Bank Transaction Rule", data)
            .then(() => {
                toast.success(_("Rule created successfully"))
                onCreate()
            })
    }

    return (
        <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="flex flex-col justify-between h-full overflow-y-auto">
                <div className="flex flex-col gap-4 px-4 pb-4">
                    {error && <ErrorBanner error={error} />}
                    <RuleForm />
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

export default CreateNewRule