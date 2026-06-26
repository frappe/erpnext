import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { Dialog, DialogTitle, DialogContent, DialogHeader, DialogDescription } from "@/components/ui/dialog"
import { FormField, FormItem, FormLabel, FormControl } from "@/components/ui/form"
import { AccountFormField, CurrencyFormField, DataField, LinkFormField, PartyTypeFormField, SelectFormField, SmallTextField } from "@/components/ui/form-elements"
import { Label } from "@/components/ui/label"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import { SelectItem } from "@/components/ui/select"
import { Separator } from "@/components/ui/separator"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import { H4, Paragraph } from "@/components/ui/typography"
import { today } from "@/lib/date"
import _ from "@/lib/translate"
import { cn } from "@/lib/utils"
import { BankTransactionRule } from "@/types/Accounts/BankTransactionRule"
import { BankTransactionRuleAccounts } from "@/types/Accounts/BankTransactionRuleAccounts"
import { FrappeConfig, FrappeContext } from "frappe-react-sdk"
import { ArrowDownRight, ArrowDownUp, ArrowRightLeftIcon, ArrowUpRight, LandmarkIcon, Plus, PlusCircleIcon, ReceiptIcon, Settings, Trash2 } from "lucide-react"
import { ChangeEvent, useCallback, useContext, useMemo, useRef, useState } from "react"
import { useFieldArray, useFormContext, useWatch } from "react-hook-form"

export const RuleForm = ({ isEdit = false }: { isEdit?: boolean }) => {

    return <div className="flex flex-col gap-4">
        <DataField
            name='rule_name'
            label={_("Rule Name")}
            disabled={isEdit}
            isRequired
            inputProps={{
                maxLength: 140,
                disabled: isEdit,
                placeholder: _("Bank Charges, Salary, etc."),
                autoFocus: true,
                className: "dark:disabled:bg-surface-gray-2"
            }}
            rules={{
                required: _("Rule name is required")
            }}
        />

        <CompanySelector />

        <SmallTextField
            name='rule_description'
            label={_("Rule Description")}
            inputProps={{
                placeholder: _("Any debit transaction with the keyword 'Bank Fee'.")
            }}
        />

        <TransactionTypeSelector />

        <div className="grid grid-cols-2 gap-2 pt-1">
            <CurrencyFormField
                name='min_amount'
                label={_("Minimum Amount")}
            />

            <CurrencyFormField
                name='max_amount'
                label={_("Maximum Amount")}
            />
        </div>

        <DescriptionRules />

        <Separator />

        <RuleAction />
    </div>
}

const CompanySelector = () => {

    const { setValue } = useFormContext<BankTransactionRule>()

    return <LinkFormField
        name='company'
        label={_("Company")}
        doctype="Company"
        isRequired
        rules={{
            required: _("Company is required"),
            onChange: () => {
                setValue('account', '')
            }
        }}
    />

}

/** Component to render a radio group as a toggle group with options for All, Withdrawal, Deposit */
const TransactionTypeSelector = () => {

    const { control } = useFormContext<BankTransactionRule>()

    return (
        <FormField
            control={control}
            name='transaction_type'
            render={({ field }) => (
                <FormItem className="space-y-1">
                    <FormLabel className="text-sm font-medium">
                        {_("Transaction Type")}<span className="text-ink-red-3">*</span>
                    </FormLabel>
                    <FormControl>
                        <RadioGroup
                            onValueChange={field.onChange}
                            value={field.value}
                            className="grid grid-cols-3 gap-2 w-full"
                        >
                            <FormItem className="flex items-center">
                                <FormControl>
                                    <RadioGroupItem
                                        value="Any"
                                        className="peer sr-only hidden"
                                    />
                                </FormControl>
                                <FormLabel
                                    className={cn(
                                        "w-full flex items-center justify-center gap-2 px-4 py-2 text-sm font-medium rounded-md border cursor-pointer transition-all hover:bg-surface-gray-1 hover:text-ink-gray-8",
                                        "peer-data-[state=checked]:bg-surface-gray-7 peer-data-[state=checked]:text-ink-white peer-data-[state=checked]:border-outline-gray-5 peer-data-[state=checked]:hover:bg-surface-gray-7 peer-data-[state=checked]:hover:text-ink-white"
                                    )}
                                >
                                    <ArrowDownUp className="w-5 h-5" />
                                    {_("All")}
                                </FormLabel>
                            </FormItem>
                            <FormItem className="flex items-center">
                                <FormControl>
                                    <RadioGroupItem
                                        value="Withdrawal"
                                        className="peer sr-only hidden"
                                    />
                                </FormControl>
                                <FormLabel
                                    className={cn(
                                        "w-full flex items-center justify-center gap-2 px-4 py-2 text-sm font-medium rounded-md border cursor-pointer transition-all hover:bg-surface-gray-1 hover:text-ink-gray-8",
                                        "peer-data-[state=checked]:bg-surface-red-5 peer-data-[state=checked]:text-white peer-data-[state=checked]:border-bg-surface-red-5 peer-data-[state=checked]:hover:bg-surface-red-5 peer-data-[state=checked]:hover:text-white"
                                    )}
                                >
                                    <ArrowUpRight className="w-5 h-5 peer-data-[state=checked]:text-ink-red-3" />
                                    {_("Withdrawal")}
                                </FormLabel>
                            </FormItem>
                            <FormItem className="flex items-center">
                                <FormControl>
                                    <RadioGroupItem
                                        value="Deposit"
                                        className="peer sr-only hidden"
                                    />
                                </FormControl>
                                <FormLabel
                                    className={cn(
                                        "w-full flex items-center justify-center gap-2 px-4 py-2 text-sm font-medium rounded-md border cursor-pointer transition-all hover:bg-surface-gray-1 hover:text-ink-gray-8",
                                        "peer-data-[state=checked]:bg-surface-green-5 peer-data-[state=checked]:text-white peer-data-[state=checked]:border-surface-green-5 peer-data-[state=checked]:hover:bg-surface-green-5 peer-data-[state=checked]:hover:text-white"
                                    )}
                                >
                                    <ArrowDownRight className="w-5 h-5 peer-data-[state=checked]:text-white" />
                                    {_("Deposit")}
                                </FormLabel>
                            </FormItem>
                        </RadioGroup>
                    </FormControl>
                </FormItem>
            )}
        />
    )
}

const DescriptionRules = () => {

    const { control } = useFormContext<BankTransactionRule>()

    const { fields, append, remove } = useFieldArray({
        control,
        name: "description_rules"
    })

    const addRow = () => {
        // @ts-expect-error - we don't need all fields here
        append({ check: "Contains" })
    }

    return (
        <div className="flex flex-col gap-2 pt-1">
            <span className="text-sm font-medium">{_("Rules to match against the transaction description")} <span className="text-ink-red-3">*</span></span>
            {fields.map((field, index) => (
                <div key={field.id} className="flex w-full items-center gap-2">
                    <div className="min-w-36">
                        <SelectFormField
                            label={_("Type of check")}
                            hideLabel
                            name={`description_rules.${index}.check`}
                            rules={{
                                required: _("This is required")
                            }}>
                            <SelectItem value="Contains">{_("Contains")}</SelectItem>
                            <SelectItem value="Starts With">{_("Starts with")}</SelectItem>
                            <SelectItem value="Ends With">{_("Ends with")}</SelectItem>
                            <SelectItem value="Regex">{_("Regex")}</SelectItem>
                        </SelectFormField>
                    </div>
                    <div className="w-full">
                        <DataField
                            name={`description_rules.${index}.value`}
                            label={_("Value")}
                            hideLabel
                            inputProps={{
                                placeholder: _("Bank Fee, Salary, etc."),
                            }}
                        />
                    </div>
                    <div>
                        <Button variant="ghost" theme='red' type='button' isIconButton onClick={() => remove(index)} disabled={fields.length === 1}>
                            <Trash2 />
                        </Button>
                    </div>
                </div>
            ))}

            <div>
                <Button variant="outline" type='button' onClick={addRow}>
                    <PlusCircleIcon />
                    {_("Add Rule")}
                </Button>
            </div>

        </div>
    )
}

const RuleAction = () => {

    const { control } = useFormContext<BankTransactionRule>()

    const classify_as = useWatch({ control, name: "classify_as" })
    const party_type = useWatch({ control, name: "party_type" })
    const bank_entry_type = useWatch({ control, name: "bank_entry_type" })

    const accountType = useMemo(() => {
        if (classify_as === "Payment Entry") {
            return party_type === "Supplier" ? ["Payable"] : ["Receivable"]
        }

        if (classify_as === "Transfer") {
            return ["Bank", "Cash", "Temporary"]
        }

        return undefined

    }, [classify_as, party_type])

    return (
        <div className="flex flex-col gap-4">
            <H4 className="text-base text-ink-gray-7">{_("If rule matches, then:")}</H4>

            <SelectFormField
                name='classify_as'
                isRequired
                label={_("Suggest creating a")}
                formDescription={_("This will just suggest creating a new entry, and will not automatically create it.")}
                rules={{
                    required: _("This is required")
                }}
            >
                <SelectItem value="Bank Entry"><LandmarkIcon /> {_("Bank Entry")}</SelectItem>
                <SelectItem value="Payment Entry"><ReceiptIcon /> {_("Payment Entry")}</SelectItem>
                <SelectItem value="Transfer"><ArrowRightLeftIcon /> {_("Transfer")}</SelectItem>
            </SelectFormField>

            {classify_as === "Bank Entry" && (<SelectFormField
                name='bank_entry_type'
                isRequired
                label={_("Create Bank Entry against")}
                rules={{
                    required: _("This is required")
                }}
            >
                <SelectItem value="Single Account">{_("Single Account")}</SelectItem>
                <SelectItem value="Multiple Accounts">{_("Multiple Accounts (Journal Template)")}</SelectItem>
            </SelectFormField>)}


            {classify_as === "Payment Entry" && (
                <div className='grid grid-cols-4 gap-4'>
                    <div className="col-span-1">
                        <PartyTypeFormField
                            name='party_type'
                            label={_("Party Type")}
                            isRequired
                            inputProps={{
                                triggerProps: {
                                    className: 'w-full'
                                },
                            }}
                            rules={{
                                required: "Party Type is required"
                            }}
                        />
                    </div>
                    <div className="col-span-3">
                        <PartyField />
                    </div>
                </div>
            )}

            {(((bank_entry_type === "Single Account" || !bank_entry_type) && classify_as === "Bank Entry") || classify_as !== "Bank Entry") && (<AccountFormField
                name='account'
                label={_("Account")}
                isRequired
                rules={{
                    required: _("Account is required")
                }}
                account_type={accountType}
            />)}

            {bank_entry_type === "Multiple Accounts" && classify_as === "Bank Entry" && <MultipleAccountsSelection />}
        </div>
    )
}

const PartyField = () => {

    const { control, setValue } = useFormContext<BankTransactionRule>()

    const party_type = useWatch({
        control,
        name: `party_type`
    })

    const { call } = useContext(FrappeContext) as FrappeConfig

    const company = useWatch({ control, name: 'company' })

    const onChange = (event: ChangeEvent<HTMLInputElement>) => {
        // Fetch the party and account
        if (event.target.value) {
            call.get('erpnext.accounts.doctype.payment_entry.payment_entry.get_party_details', {
                company: company,
                party_type: party_type,
                party: event.target.value,
                date: today()
            }).then((res) => {
                setValue('account', res.message.party_account)
            })
        } else {
            // Clear the account
            setValue('account', '')
        }

    }

    if (!party_type) {
        return <DataField
            name={`party`}
            label={_("Party")}
            isRequired
            inputProps={{
                disabled: true,
            }}
        />
    }

    return <LinkFormField
        name={`party`}
        label={_("Party")}
        rules={{
            onChange
        }}
        doctype={party_type}

    />
}

const MultipleAccountsSelection = () => {


    const { control } = useFormContext<BankTransactionRule>()

    const accounts = useWatch({
        control,
        name: 'accounts'
    }) ?? []

    const [isConfigureAccountsModalOpen, setIsConfigureAccountsModalOpen] = useState(false)



    return <div className="flex flex-col gap-2">
        <div className="flex justify-between gap-2">
            <Label>{_("Journal Template Accounts")}<span className="text-ink-red-3">*</span></Label>
            <Button variant="outline" type="button" onClick={() => setIsConfigureAccountsModalOpen(true)}><Settings /> {_("Configure Accounts")}</Button>
        </div>


        <Table>
            <TableHeader>
                <TableRow>
                    <TableHead>{_("Account")}</TableHead>
                    <TableHead className="text-end">{_("Debit")}</TableHead>
                    <TableHead className="text-end">{_("Credit")}</TableHead>
                </TableRow>
            </TableHeader>
            <TableBody>
                {accounts.length === 0 && (
                    <TableRow>
                        <TableCell colSpan={3} className="text-center">
                            <div className="py-2 flex flex-col gap-2 items-center">
                                <span>{_("No accounts configured")}</span>
                                <Button variant="subtle" type="button" onClick={() => setIsConfigureAccountsModalOpen(true)}>{_("Configure Accounts")}</Button>
                            </div>
                        </TableCell>
                    </TableRow>
                )}
                {accounts.map((account, index) => (
                    <TableRow key={index}>
                        <TableCell>{account.account}</TableCell>
                        {index === accounts.length - 1 ? <TableCell className="text-end bg-surface-gray-1" colSpan={2}>
                            <Tooltip>
                                <TooltipTrigger asChild>
                                    <span className="text-ink-gray-5">{_("This is auto computed to balance the journal entry.")}</span>
                                </TooltipTrigger>
                                <TooltipContent>
                                    {_("Based on the above entries, the balance amount (debit or credit) will be set for the last row to balance the journal entry.")}
                                </TooltipContent>
                            </Tooltip>
                        </TableCell> : <>
                            <TableCell className="font-numeric text-end"><AmountFormulaRenderer value={account.debit} /></TableCell>
                            <TableCell className="font-numeric text-end"><AmountFormulaRenderer value={account.credit} /></TableCell>
                        </>}
                    </TableRow>
                ))}
            </TableBody>
        </Table>

        <ConfigureAccountsModal open={isConfigureAccountsModalOpen} onClose={() => setIsConfigureAccountsModalOpen(false)} />
    </div>
}

const AmountFormulaRenderer = ({ value }: { value?: string }) => {

    // If it's a string and cannot be a number, then show it as a formula

    if (isNaN(Number(value))) {

        let calculatedValue = "";

        try {
            calculatedValue = window.eval(`const transaction_amount = 200; ${value}`);
        } catch (error: unknown) {
            console.error(error);
            calculatedValue = "Error";
        }

        const isComputationValid = !isNaN(Number(calculatedValue)) && calculatedValue !== undefined && calculatedValue !== null;

        return <Tooltip>
            <TooltipTrigger asChild>
                <span className={cn("font-numeric text-end tabular-nums underline underline-offset-4", isComputationValid ? "" : "text-ink-red-3")}>{value}</span>
            </TooltipTrigger>
            <TooltipContent className={isComputationValid ? "" : "bg-surface-red-5"} arrowClassName={isComputationValid ? "" : "bg-surface-red-5 fill-surface-red-5"}>
                <p className="text-sm">
                    {isComputationValid ? _("This is a formula based value.") : _("This is not a valid formula. Check the variable used in the formula.")}
                    <br /><br />
                    {_("Example: If the transaction amount is 200, then this will be calculated as {} = {}", [value ?? "", calculatedValue])}
                </p>
            </TooltipContent>
        </Tooltip>
    }

    return <span className="font-numeric text-end tabular-nums">{value}</span>
}

const ConfigureAccountsModal = ({ open, onClose }: { open: boolean, onClose: () => void }) => {


    return <Dialog
        open={open}
        onOpenChange={onClose}
    >
        <DialogContent className='min-w-[95vw]'>
            <ConfigureAccountsModalContent />
        </DialogContent>
    </Dialog>
}

const ConfigureAccountsModalContent = () => {

    const { control, getValues, setValue } = useFormContext<BankTransactionRule>()

    const { call } = useContext(FrappeContext) as FrappeConfig

    // const costCenterMapRef = useRef<Record<string, string>>({})

    const partyMapRef = useRef<Record<string, string>>({})

    const onPartyChange = (value: string, index: number) => {
        // Get the account for the party type
        if (value) {
            if (partyMapRef.current[value]) {
                setValue(`accounts.${index}.account`, partyMapRef.current[value])
            } else {
                call.get('erpnext.accounts.party.get_party_account', {
                    party: value,
                    party_type: getValues(`accounts.${index}.party_type`),
                    company: company
                }).then((result: { message: string }) => {
                    setValue(`accounts.${index}.account`, result.message)
                    partyMapRef.current[value] = result.message
                })
            }
        } else {
            setValue(`accounts.${index}.account`, '')
        }
    }

    const transaction_type = useWatch({
        name: 'transaction_type',
        control,
    })

    const { fields, append, remove } = useFieldArray({
        control,
        name: 'accounts'
    })


    const [selectedRows, setSelectedRows] = useState<number[]>([])

    const onSelectRow = useCallback((index: number) => {
        setSelectedRows(prev => {
            if (prev.includes(index)) {
                return prev.filter(i => i !== index)
            }
            return [...prev, index]
        })
    }, [])

    const onSelectAll = useCallback(() => {
        setSelectedRows(prev => {
            if (prev.length === fields.length) {
                return []
            }
            return [...fields.map((_, index) => index)]
        })
    }, [fields])

    const onAdd = () => {
        append({
            party_type: '',
            party: '',
            account: '',
            debit: '',
            credit: '',
            user_remark: ''
        } as BankTransactionRuleAccounts, {
            focusName: `accounts.${fields.length}.account`
        })
    }

    const onRemove = useCallback(() => {
        remove(selectedRows)
        setSelectedRows([])
    }, [remove, selectedRows])

    const isWithdrawal = transaction_type === 'Withdrawal'

    const company = useWatch({
        name: 'company',
        control,
    })

    return <>
        <DialogHeader>
            <DialogTitle>{_("Configure Accounts for Bank Entry")}</DialogTitle>
            <DialogDescription>{_("Add all accounts that you want to split the transaction into.")}</DialogDescription>
        </DialogHeader>
        <div className="flex flex-col gap-2">
            <Table>
                <TableHeader>
                    <TableRow>
                        <TableHead><Checkbox
                            disabled={fields.length === 0}
                            // Make this accessible to screen readers
                            aria-label={_("Select all")}
                            checked={selectedRows.length > 0 && selectedRows.length === fields.length}
                            onCheckedChange={onSelectAll} /></TableHead>
                        <TableHead>{_("Party")}</TableHead>
                        <TableHead>{_("Account")} <span className="text-ink-red-3">*</span></TableHead>
                        {/* <TableHead>{_("Cost Center")}</TableHead> */}
                        <TableHead>{_("Remarks")}</TableHead>
                        <TableHead className="text-end">{_("Debit")}</TableHead>
                        <TableHead className="text-end">{_("Credit")}</TableHead>
                    </TableRow>
                </TableHeader>
                <TableBody>
                    <TableRow className="bg-surface-gray-1 cursor-not-allowed" title={_("This is the row for the bank account. It will be auto populated based on the bank transaction.")}>
                        <TableCell>
                            <Checkbox disabled />
                        </TableCell>
                        <TableCell className="align-top">
                        </TableCell>
                        <TableCell className="align-top text-ink-gray-5">
                            <span className="px-2">
                                Bank GL Account
                            </span>
                        </TableCell>
                        <TableCell className="align-top">
                        </TableCell>

                        <TableCell className={"align-top text-end"}>
                            <span className="text-ink-gray-5 text-sm">
                                {transaction_type === "Withdrawal" || transaction_type === "Any" ? _("Will be auto-populated") : ""}
                            </span>
                        </TableCell>
                        <TableCell className={"text-end align-top"}>
                            <span className="text-ink-gray-5 text-sm">
                                {transaction_type === "Deposit" || transaction_type === "Any" ? _("Will be auto-populated") : ""}
                            </span>
                        </TableCell>
                    </TableRow>
                    {fields.map((field, index) => (
                        <TableRow key={field.id}>
                            <TableCell>
                                <Checkbox
                                    checked={selectedRows.includes(index)}
                                    onCheckedChange={() => onSelectRow(index)}
                                    // Make this accessible to screen readers
                                    aria-label={_("Select row {0}", [String(index + 1)])}
                                />
                            </TableCell>

                            <TableCell className="align-top">
                                <div className="flex">
                                    <PartyTypeFormField
                                        name={`accounts.${index}.party_type`}
                                        label={_("Party Type")}
                                        isRequired
                                        hideLabel
                                        inputProps={{
                                            type: isWithdrawal ? 'Payable' : 'Receivable',
                                            triggerProps: {
                                                className: 'rounded-e-none',
                                                tabIndex: -1
                                            },
                                        }} />
                                    <PartyRowField index={index} onChange={onPartyChange} />
                                </div>

                            </TableCell>
                            <TableCell className="align-top">
                                <AccountFormField
                                    name={`accounts.${index}.account`}
                                    label={_("Account")}
                                    rules={{
                                        required: _("Account is required"),
                                        // onChange: (event) => {
                                        //     onAccountChange(event.target.value, index)
                                        // }
                                    }}
                                    buttonClassName="min-w-64"
                                    isRequired
                                    hideLabel
                                />
                            </TableCell>
                            {/* <TableCell className="align-top">
                                <LinkFormField
                                    doctype="Cost Center"
                                    name={`accounts.${index}.cost_center`}
                                    label={_("Cost Center")}
                                    filters={[["company", "=", company], ["is_group", "=", 0], ["disabled", "=", 0]]}
                                    buttonClassName="min-w-48"
                                    readOnly={index === 0}
                                    hideLabel
                                />
                            </TableCell> */}
                            <TableCell className="align-top">
                                <DataField
                                    name={`accounts.${index}.user_remark`}
                                    label={_("Remarks")}
                                    inputProps={{
                                        placeholder: _("e.g. Bank Charges"),
                                        className: 'min-w-64',
                                    }}
                                    hideLabel
                                />
                            </TableCell>
                            <TableCell
                                className={cn("text-end align-top", index === fields.length - 1 ? "cursor-not-allowed" : "")}
                                title={index === fields.length - 1 ? _("This is the last row. It will be auto populated based on the bank transaction.") : ""}>
                                <DataField
                                    name={`accounts.${index}.debit`}
                                    label={_("Debit")}
                                    disabled={index === fields.length - 1}
                                    inputProps={{
                                        className: 'text-end',
                                        placeholder: _("0.00"),
                                        disabled: index === fields.length - 1
                                    }}
                                    hideLabel
                                />
                            </TableCell>
                            <TableCell
                                className={cn("text-end align-top", index === fields.length - 1 ? "cursor-not-allowed" : "")}
                                title={index === fields.length - 1 ? _("This is the last row. It will be auto populated based on the bank transaction.") : ""}>
                                <DataField
                                    name={`accounts.${index}.credit`}
                                    label={_("Credit")}
                                    disabled={index === fields.length - 1}
                                    inputProps={{
                                        className: 'text-end',
                                        placeholder: _("0.00"),
                                        disabled: index === fields.length - 1
                                    }}
                                    hideLabel
                                />
                            </TableCell>
                        </TableRow>
                    ))}
                </TableBody>
            </Table>
            <div className="flex justify-between gap-2">
                <div className="flex gap-2 justify-end">
                    <div>
                        <Button size='sm' type='button' variant={'outline'} onClick={onAdd}><Plus /> {_("Add Row")}</Button>
                    </div>
                    {selectedRows.length > 0 && <div>
                        <Button size='sm' type='button' theme="red" onClick={onRemove}><Trash2 /> {_("Remove")}</Button>
                    </div>}
                </div>
            </div>
            <div className="py-4">
                <Separator />
            </div>

            <div className="flex flex-col gap-2">
                <H4 className="text-base text-ink-gray-7">{_("Help")}</H4>

                <Paragraph className="text-p-sm">{(_("You can set up the rule to split the transaction across multiple accounts."))}
                    <br />{_("You can also add credit or debit values to pre-fill - these support both static values (like 200) or formulas (like transaction_amount * 0.25).")}
                    <br />
                    <br />
                    <span className="font-medium">{_("Example")}:</span>
                    <br />
                    <span className="font-numeric text-sm">
                        transaction_amount * 0.25
                    </span>
                    <br />
                    <span>
                        {_("In this case, the amount will be calculated as 25% of the transaction amount. If the transaction amount is 200, then this will be calculated as 200 * 0.25 = 50.")}
                    </span>
                </Paragraph>
            </div>


        </div>
    </>
}


const PartyRowField = ({ index, onChange }: { index: number, onChange: (value: string, index: number) => void }) => {

    const { control } = useFormContext<BankTransactionRule>()

    const party_type = useWatch({
        control,
        name: `accounts.${index}.party_type`
    })

    if (!party_type) {
        return <DataField
            name={`accounts.${index}.party`}
            label={_("Party")}
            isRequired
            inputProps={{
                disabled: true,
                className: 'rounded-s-none border-s-0 min-w-64'
            }}
            hideLabel
        />
    }

    return <LinkFormField
        name={`accounts.${index}.party`}
        label={_("Party")}
        rules={{
            onChange: (event) => {
                onChange(event.target.value, index)
            },
        }}
        hideLabel
        buttonClassName="rounded-s-none border-s-0 min-w-64"
        doctype={party_type}

    />
}
