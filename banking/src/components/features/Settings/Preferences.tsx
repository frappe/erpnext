import ErrorBanner from "@/components/ui/error-banner"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Separator } from "@/components/ui/separator"
import { SettingsPanelDescription, SettingsPanelHeader, SettingsPanelTitle, SettingsPanelContent } from "@/components/ui/settings-dialog"
import { Switch } from "@/components/ui/switch"
import _ from "@/lib/translate"
import { AccountsSettings } from "@/types/Accounts/AccountsSettings"
import { useFrappeGetDoc, useFrappeUpdateDoc } from "frappe-react-sdk"
import { toast } from "sonner"


export const Preferences = () => {


    const { data: accountsSettings, mutate, error: fetchError, isLoading } = useFrappeGetDoc<AccountsSettings>("Accounts Settings", "Accounts Settings", undefined, {
        revalidateOnFocus: false
    })

    const { updateDoc, error } = useFrappeUpdateDoc<AccountsSettings>()

    const onUpdate = (field: keyof AccountsSettings, value: any) => {
        mutate(updateDoc("Accounts Settings", "Accounts Settings", {
            [field]: value
        }), {
            optimisticData: {
                ...accountsSettings as AccountsSettings,
                [field]: value
            },
            revalidate: false,
        }).then(() => {
            toast.success(_("Preferences updated"))
        })
    }

    return <>

        <SettingsPanelHeader>
            <SettingsPanelTitle>{_("Preferences")}</SettingsPanelTitle>
            <SettingsPanelDescription>{_("Configure default settings for the banking module")}</SettingsPanelDescription>
        </SettingsPanelHeader>
        <SettingsPanelContent>

            <div className='flex flex-col gap-4 w-full'>
                {fetchError && <ErrorBanner error={fetchError} />}
                {error && <ErrorBanner error={error} />}

                <div className="flex flex-col flex-1">

                    <div className="flex justify-between items-center gap-8 py-3">
                        <div className="flex flex-col">
                            <Label htmlFor="transfer_match_days" className="text-p-base text-ink-gray-6">{_("Number of days to match transfers")}</Label>
                            <p className="text-p-sm text-ink-gray-5">
                                {_("For example, if set to 4, the system will try to find matching transfer transactions in other banks 4 days before and after the transaction date. This is because transactions can clear on different days on different bank accounts.")}
                            </p>
                        </div>
                        <div className="min-w-40 flex justify-end">
                            <Select disabled={isLoading} onValueChange={(value) => onUpdate("transfer_match_days", Number(value))} value={accountsSettings?.transfer_match_days?.toString()}>
                                <SelectTrigger id="transfer_match_days" className="min-w-32">
                                    <SelectValue placeholder={_("Select number of days")} />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="0">{_("Same day")}</SelectItem>
                                    <SelectItem value="1">{_("Within 1 day")}</SelectItem>
                                    <SelectItem value="2">{_("Within 2 days")}</SelectItem>
                                    <SelectItem value="3">{_("Within 3 days")}</SelectItem>
                                    <SelectItem value="4">{_("Within 4 days")}</SelectItem>
                                    <SelectItem value="5">{_("Within 5 days")}</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>
                    </div>

                    <Separator />

                    <div className="flex justify-between items-center gap-8 py-3">
                        <div className="flex flex-col">
                            <Label htmlFor="automatically_run_rules_on_unreconciled_transactions" className="text-p-base text-ink-gray-6">{_("Automatically run rules on unreconciled transactions")}</Label>
                            <p className="text-p-sm text-ink-gray-5">
                                {_("This will automatically run transaction matching rules on unreconciled transactions every hour.")}
                            </p>
                        </div>
                        <div className="flex justify-end">
                            <Switch
                                id="automatically_run_rules_on_unreconciled_transactions"
                                disabled={isLoading}
                                checked={accountsSettings?.automatically_run_rules_on_unreconciled_transactions === 1}
                                onCheckedChange={(checked) => onUpdate("automatically_run_rules_on_unreconciled_transactions", checked ? 1 : 0)}
                            />
                        </div>
                    </div>

                    <Separator />

                    <div className="flex justify-between items-center gap-8 py-3">
                        <div className="flex flex-col">
                            <Label htmlFor="enable_party_matching" className="text-p-base text-ink-gray-6">{_("Enable automatic party matching")}</Label>
                            <p className="text-p-sm text-ink-gray-5">
                                {_("The system will attempt to automatically match a party to a bank transaction based on account number or IBAN.")}

                            </p>
                        </div>
                        <div className="flex justify-end">
                            <Switch
                                id="enable_party_matching"
                                disabled={isLoading}
                                checked={accountsSettings?.enable_party_matching === 1}
                                onCheckedChange={(checked) => onUpdate("enable_party_matching", checked ? 1 : 0)}
                            />
                        </div>
                    </div>

                    <Separator />

                    <div className="flex justify-between items-center gap-8 py-3">
                        <div className="flex flex-col">
                            <Label htmlFor="enable_fuzzy_matching" className="text-p-base text-ink-gray-6">{_("Enable party name/description fuzzy matching")}</Label>
                            <p className="text-p-sm text-ink-gray-5">
                                {_("If a party cannot be matched by account number or IBAN, the system will try fuzzy matching using the party name and transaction description.")}

                            </p>
                        </div>
                        <div className="flex justify-end">
                            <Switch
                                id="enable_fuzzy_matching"
                                disabled={accountsSettings?.enable_party_matching !== 1 || isLoading}
                                checked={accountsSettings?.enable_fuzzy_matching === 1}
                                onCheckedChange={(checked) => onUpdate("enable_fuzzy_matching", checked ? 1 : 0)}
                            />
                        </div>
                    </div>

                </div>



                {/* <DataField
                            name='transfer_match_days'
                            label={_("Number of days to match transfers")}
                            isRequired
                            inputProps={{
                                type: 'number',
                                inputMode: 'numeric',
                            }}
                            formDescription={_("For example, if set to 4, the system will try to find matching transactions in other banks 4 days before and after the transaction date. This is because transactions can clear on different days on different bank accounts.")}
                        /> */}

            </div>
        </SettingsPanelContent>
    </>
}