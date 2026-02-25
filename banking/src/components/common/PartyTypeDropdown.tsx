import { Select, SelectValue, SelectTrigger, SelectContent, SelectItem } from '@/components/ui/select'
import _ from '@/lib/translate'
import { useFrappeGetDocList } from 'frappe-react-sdk'
import { ComponentProps, useMemo } from 'react'
import { FormControl } from '../ui/form'

export type PartyTypeDropdownProps = {
    value?: string,
    onChange?: (value: string) => void,
    readOnly?: boolean,
    disabled?: boolean,
    /** Set this to order the parties so that suggested types are shown first */
    type?: 'Receivable' | 'Payable'
    /** Set this to true if you want to hide other options by type. e.g. - if type is Receivable, Payable options like "Supplier" will be hidden */
    hideOptionsByType?: boolean,
    valueProps?: ComponentProps<typeof SelectValue>,
    triggerProps?: ComponentProps<typeof SelectTrigger>,
    // If true, the component will be wrapped in a FormControl component
    useInForm?: boolean
}

const PartyTypeDropdown = ({ value, onChange, readOnly, disabled, type, hideOptionsByType, valueProps, triggerProps, useInForm }: PartyTypeDropdownProps) => {

    const { data } = useFrappeGetDocList("Party Type", {
        fields: ['name', 'account_type'],
        orderBy: {
            field: 'creation',
            order: 'asc'
        }
    }, `party_types`, {
        revalidateIfStale: false,
        revalidateOnFocus: false,
        revalidateOnReconnect: false,
    })

    const filteredData = useMemo(() => {

        let options = data ?? [
            { name: "Customer", account_type: "Receivable" },
            { name: "Supplier", account_type: "Payable" },
            { name: "Employee", account_type: "Payable" },
            { name: "Shareholder", account_type: "Payable" },
        ]

        if (hideOptionsByType && type) {
            options = options.filter((option) => option.account_type === type)
        }

        // Order by type if type is set
        if (type) {
            options = options.sort((a) => a.account_type === type ? -1 : 1)
        }

        return options
    }, [data, type, hideOptionsByType])

    const onSelect = (value: string) => {
        if (!readOnly) {
            onChange?.(value)
        }
    }

    return (
        <Select onValueChange={onSelect} value={value} disabled={disabled}>
            {useInForm ? <FormControl>
                <SelectTrigger tabIndex={0} disabled={disabled || readOnly} {...triggerProps}>
                    <SelectValue placeholder={_("Type")} aria-readonly={readOnly} {...valueProps} />
                </SelectTrigger>
            </FormControl> : <SelectTrigger tabIndex={0} {...triggerProps}>
                <SelectValue placeholder={_("Type")} aria-readonly={readOnly} {...valueProps} />
            </SelectTrigger>
            }
            <SelectContent>
                {filteredData.map((option) => (
                    <SelectItem key={option.name} value={option.name}>{option.name}</SelectItem>
                ))}
            </SelectContent>
        </Select>
    )
}

export default PartyTypeDropdown