import { useFrappeGetCall } from "frappe-react-sdk"

export const useDocType = (doctype: string, with_parent: 0 | 1 = 1, cached_timestamp?: Date) => {

    // @ts-expect-error Locals is available in the FrappeContext
    const localData = locals?.['DocType']?.[doctype] || null
    const { data, error, isLoading } = useFrappeGetCall('frappe.desk.form.load.getdoctype', {
        doctype: doctype,
        with_parent: with_parent,
        cached_timestamp: cached_timestamp ?? null,
    }, localData || !doctype ? null : undefined, {
        onSuccess: (data) => {
            if (data) {
                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                data?.docs?.forEach((d: any) => {
                    // @ts-expect-error Frappe is available in the window
                    frappe.model.add_to_locals(d)
                })
            }
        },
        revalidateIfStale: false,
        revalidateOnFocus: false,
    })

    return {
        data: localData || (data?.docs?.[0] ?? null),
        error,
        isLoading: localData ? false : isLoading
    }
}