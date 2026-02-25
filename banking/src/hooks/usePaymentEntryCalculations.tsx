import { flt } from "@/lib/numbers"
import { PaymentEntryDeduction } from "@/types/Accounts/PaymentEntryDeduction"
import { PaymentEntryReference } from "@/types/Accounts/PaymentEntryReference"
import { useCallback } from "react"
import { useFormContext } from "react-hook-form"

export const usePaymentEntryCalculations = () => {

    const { setValue, getValues, watch } = useFormContext()

    const payment_type = watch('payment_type')

    const allocatePartyAmount = (paid_amount: number) => {
        const deductionsTable = getValues('deductions') ?? []
        const party_type = getValues('party_type')

        let total_positive_outstanding_including_order = 0
        let total_negative_outstanding = 0
        const total_deductions = deductionsTable.reduce((acc: number, row: PaymentEntryDeduction) => acc + row.amount, 0)

        paid_amount -= total_deductions

        const references = getValues('references') ?? []
        references.forEach((ref: PaymentEntryReference) => {
            if (flt(ref.outstanding_amount) > 0) {
                total_positive_outstanding_including_order += flt(ref.outstanding_amount)
            } else {
                total_negative_outstanding += Math.abs(flt(ref.outstanding_amount))
            }
        })
        let allocated_negative_outstanding = 0
        let allocated_positive_outstanding = 0
        if (
            (payment_type == "Receive" && party_type == "Customer") ||
            (payment_type == "Pay" && party_type == "Supplier")
        ) {
            if (total_positive_outstanding_including_order > paid_amount) {
                const remaining_outstanding = total_positive_outstanding_including_order - paid_amount
                allocated_negative_outstanding = total_negative_outstanding < remaining_outstanding ? total_negative_outstanding : remaining_outstanding
            }

            allocated_positive_outstanding = paid_amount + allocated_negative_outstanding
        } else {
            total_negative_outstanding = flt(total_negative_outstanding)
            if (paid_amount > total_negative_outstanding) {
                allocated_positive_outstanding = total_negative_outstanding - paid_amount
                allocated_negative_outstanding = paid_amount + (total_positive_outstanding_including_order < allocated_positive_outstanding ? total_positive_outstanding_including_order : allocated_positive_outstanding)
            }
        }

        references.forEach((ref: PaymentEntryReference, index: number) => {
            if (flt(ref.outstanding_amount) > 0 && allocated_positive_outstanding >= 0) {
                setValue(`references.${index}.allocated_amount`, (flt(ref.outstanding_amount) >= allocated_positive_outstanding) ?
                    allocated_positive_outstanding : ref.outstanding_amount)

                allocated_positive_outstanding -= flt(ref.allocated_amount)
            } else if (flt(ref.outstanding_amount) < 0 && allocated_negative_outstanding) {
                setValue(`references.${index}.allocated_amount`, (flt(ref.outstanding_amount) >= allocated_negative_outstanding) ?
                    -1 * allocated_negative_outstanding : ref.outstanding_amount)
                allocated_negative_outstanding -= flt(ref.allocated_amount)
            }
        })

        setTotalAllocatedAmount()
    }

    const setDifferenceAmount = useCallback((value: number) => {
        const base_total_allocated_amount = getValues('base_total_allocated_amount') ?? 0
        const base_received_amount = getValues('base_received_amount') ?? 0
        const base_paid_amount = getValues('base_paid_amount') ?? 0
        const deductionsTable = getValues('deductions') ?? []
        const base_total_taxes_and_charges = getValues('base_total_taxes_and_charges') ?? 0
        let difference_amount = 0
        const base_party_amount = base_total_allocated_amount + flt(value)
        if (payment_type == "Receive") {
            difference_amount = base_party_amount - base_received_amount
        }
        else if (payment_type == "Pay") {
            difference_amount = base_paid_amount - base_party_amount
        }
        else {
            difference_amount = base_paid_amount - base_received_amount
        }
        const total_deductions = deductionsTable.reduce((acc: number, row: PaymentEntryDeduction) => acc + row.amount, 0)
        setValue('difference_amount', difference_amount - total_deductions + base_total_taxes_and_charges)
    }, [getValues, setValue, payment_type])

    const setUnallocatedAmount = useCallback(() => {
        const deductionsTable = getValues('deductions') ?? []
        const base_total_allocated_amount = getValues('base_total_allocated_amount') ?? 0
        const base_received_amount = getValues('base_received_amount') ?? 0
        const total_allocated_amount = getValues('total_allocated_amount') ?? 0
        const paid_amount = getValues('paid_amount') ?? 0
        const base_total_taxes_and_charges = getValues('base_total_taxes_and_charges') ?? 0
        const base_paid_amount = getValues('base_paid_amount') ?? 0
        const received_amount = getValues('received_amount') ?? 0
        const party = getValues('party')
        let unallocated_amount = 0
        const total_deductions = deductionsTable.reduce((acc: number, row: PaymentEntryDeduction) => acc + row.amount, 0)
        if (party) {
            if (payment_type == "Receive" && base_total_allocated_amount < base_received_amount + total_deductions
                && total_allocated_amount < paid_amount + total_deductions) {
                unallocated_amount = base_received_amount + total_deductions + base_total_taxes_and_charges
                    - base_total_allocated_amount
            } else if (payment_type == "Pay"
                && base_total_allocated_amount < base_paid_amount - total_deductions
                && total_allocated_amount < received_amount + total_deductions) {
                unallocated_amount = base_paid_amount + base_total_taxes_and_charges - (total_deductions
                    + base_total_allocated_amount)
            }
        }
        setValue('unallocated_amount', unallocated_amount)
        setDifferenceAmount(unallocated_amount)
    }, [getValues, setValue, payment_type, setDifferenceAmount])

    const setTotalAllocatedAmount = useCallback(() => {
        let total_allocated_amount = 0
        let base_total_allocated_amount = 0

        const references = getValues('references')
        references?.forEach((ref: PaymentEntryReference) => {
            if (ref.allocated_amount) {
                total_allocated_amount += flt(ref.allocated_amount)
                base_total_allocated_amount += flt(ref.allocated_amount)
            }
        })
        setValue('total_allocated_amount', Math.abs(total_allocated_amount))
        setValue('base_total_allocated_amount', Math.abs(base_total_allocated_amount))
        setUnallocatedAmount()
    }, [getValues, setValue, setUnallocatedAmount])

    return {
        setTotalAllocatedAmount,
        setUnallocatedAmount,
        setDifferenceAmount,
        allocatePartyAmount
    }
}