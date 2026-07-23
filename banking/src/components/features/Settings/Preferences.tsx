import ErrorBanner from "@/components/ui/error-banner"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Separator } from "@/components/ui/separator"
import { SettingsPanelDescription, SettingsPanelHeader, SettingsPanelTitle, SettingsPanelContent } from "@/components/ui/settings-dialog"
import { Switch } from "@/components/ui/switch"
import { useTheme } from "@/components/ui/theme-provider"
import _ from "@/lib/translate"
import { AccountsSettings } from "@/types/Accounts/AccountsSettings"
import { useFrappeGetDoc, useFrappeUpdateDoc } from "frappe-react-sdk"
import { toast } from "sonner"


export const Preferences = () => {


    const { data: accountsSettings, mutate, error: fetchError, isLoading } = useFrappeGetDoc<AccountsSettings>("Accounts Settings", "Accounts Settings", undefined, {
        revalidateOnFocus: false
    })

    const { updateDoc, error } = useFrappeUpdateDoc<AccountsSettings>()

    const onUpdate = <K extends keyof AccountsSettings>(field: K, value: AccountsSettings[K]) => {
        mutate(updateDoc("Accounts Settings", "Accounts Settings", {
            [field]: value
        }), {
            optimisticData: {
                ...accountsSettings as AccountsSettings,
                [field]: value
            },
            revalidate: false,
        }).then(() => {
            toast.success(_("Preferences updated"), {
                dismissible: true,
                duration: 500,
            })
        })
    }

    return <>

        <SettingsPanelHeader>
            <SettingsPanelTitle>{_("Preferences")}</SettingsPanelTitle>
            <SettingsPanelDescription>{_("Configure settings for the banking module")}</SettingsPanelDescription>
        </SettingsPanelHeader>
        <SettingsPanelContent>

            <div className='flex flex-col gap-4 w-full'>
                {fetchError && <ErrorBanner error={fetchError} />}
                {error && <ErrorBanner error={error} />}

                <div className="flex flex-col flex-1">

                    <ThemeSwitcher />

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
                                className="dark:disabled:bg-surface-gray-2"
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
                                className="dark:disabled:bg-surface-gray-2"
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
                                className="dark:disabled:bg-surface-gray-2"
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


const ThemeSwitcher = () => {

    const { theme, setTheme } = useTheme()

    const themeCards: Array<{ value: "Light" | "Dark" | "Automatic", label: string }> = [
        {
            value: "Light",
            label: _("Light"),
        },
        {
            value: "Dark",
            label: _("Dark"),
        },
        {
            value: "Automatic",
            label: _("System"),
        },
    ]

    return <div className="flex flex-col gap-3 pb-3">
        <div className="flex flex-col">
            <Label className="text-p-base text-ink-gray-6">{_("Theme")}</Label>
            <p className="text-p-sm text-ink-gray-5">
                {_("Switch between light, dark, or system theme")}
            </p>
        </div>
        <div className="flex gap-3">
            {themeCards.map((option) => {
                const selected = theme === option.value

                return (
                    <button
                        key={option.value}
                        type="button"
                        onClick={() => setTheme(option.value)}
                        aria-pressed={selected}
                        className={`flex-1 basis-0 min-w-0 overflow-hidden rounded-lg border cursor-pointer transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-outline-blue-4 ${selected ? "border-outline-gray-5" : "border-outline-gray-modals hover:border-outline-gray-4"}`}
                    >
                        {option.value === "Automatic" ? (
                            <div className="flex w-full min-w-0">
                                <ThemePreviewWindow theme="light" roundedClass="rounded-tl-[10.5px]" />
                                <ThemePreviewWindow theme="dark" roundedClass="rounded-tr-[10.5px]" />
                            </div>
                        ) : (
                            <ThemePreviewWindow theme={option.value === "Light" ? "light" : "dark"} roundedClass="rounded-t-[10.5px]" />
                        )}
                        <div className="flex items-center justify-between px-3 py-2 border-t border-outline-gray-modals">
                            <div className="text-base text-ink-gray-7">{option.label}</div>
                            <span className={`rounded-full size-3.5 ${selected ? "border-4 border-outline-gray-5" : "border border-outline-gray-4"}`} />
                        </div>
                    </button>
                )
            })}
        </div>
    </div>

}

const ThemePreviewWindow = ({ theme, roundedClass }: { theme: "light" | "dark", roundedClass: string }) => {
    const isLight = theme === "light"
    const frameClass = isLight ? "bg-white border-gray-100" : "bg-gray-900 border-gray-800"
    const subtleSurfaceClass = isLight ? "bg-gray-50" : "bg-gray-800"
    const mutedLineClass = isLight ? "bg-gray-200" : "bg-gray-700"
    const mutedLineStrongClass = isLight ? "bg-gray-300" : "bg-gray-600"
    const dividerClass = isLight ? "border-gray-100" : "border-gray-800"
    const cardClass = isLight ? "bg-white border-gray-200" : "bg-gray-900 border-gray-700"

    return <div className={`flex flex-1 min-w-0 pl-5 pt-3.5 ${isLight ? "bg-surface-gray-2" : "bg-surface-gray-3"} ${roundedClass}`}>
        <div className={`w-full rounded-tl-sm border ${frameClass}`}>
            <div className={`flex gap-[3px] py-[3px] px-1 border-b ${dividerClass}`}>
                <div className="size-1.5 bg-[#FF5F57] rounded-full" />
                <div className="size-1.5 bg-[#FEBC2D] rounded-full" />
                <div className="size-1.5 bg-[#28C840] rounded-full" />
            </div>
            <div className="p-1.5">
                <div className={`flex items-center gap-1.5 p-1 rounded-sm border ${subtleSurfaceClass} ${dividerClass}`}>
                    <div className={`h-2 w-8 rounded-full ${mutedLineStrongClass}`} />
                    <div className={`h-2 w-6 rounded-full ${mutedLineClass}`} />
                    <div className={`h-2 w-7 rounded-full ml-auto ${mutedLineClass}`} />
                </div>
                <div className="grid grid-cols-2 gap-1 mt-1.5">
                    <div className={`rounded-sm border p-1 ${cardClass}`}>
                        <div className={`h-1.5 w-full rounded-full ${mutedLineStrongClass}`} />
                        <div className={`h-1.5 w-4/5 rounded-full mt-1 ${mutedLineClass}`} />
                        <div className={`h-1.5 w-3/5 rounded-full mt-1 ${mutedLineClass}`} />
                    </div>
                    <div className={`rounded-sm border p-1 ${cardClass}`}>
                        <div className="flex items-center justify-between gap-1">
                            <div className={`h-1.5 w-2/5 rounded-full ${mutedLineStrongClass}`} />
                            {/* <div className={`h-2.5 w-5 rounded-sm border ${chipClass}`} /> */}
                        </div>
                        <div className={`h-1.5 w-full rounded-full mt-1 ${mutedLineClass}`} />
                        <div className={`h-1.5 w-3/4 rounded-full mt-1 ${mutedLineClass}`} />
                    </div>
                </div>
            </div>
        </div>
    </div>
}