import { useDocType } from "@/hooks/useDocType";
import { getSystemDefault, slug } from "@/lib/frappe";
import { Filter, useFrappeGetCall } from "frappe-react-sdk"
import { useLayoutEffect, useMemo, useRef, useState } from "react";
import { canCreateDocument } from "@/lib/permissions";
import { useDebounceValue } from "usehooks-ts";
import { Popover, PopoverContent, PopoverTrigger } from "../ui/popover";
import { FormControl } from "../ui/form";
import { ChevronsUpDownIcon, ExternalLink } from "lucide-react";
import { Button } from "../ui/button";
import { cn } from "@/lib/utils";
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from "../ui/command";
import _ from "@/lib/translate";
import ErrorBanner from "../ui/error-banner";

export interface ResultItem {
    value: string,
    description: string,
    label?: string
}

export interface LinkFieldComboboxProps {
    /** DocType to be fetched */
    doctype: string;
    /** Filters to be applied. Default: none */
    filters?: Filter[]
    /** Number of records to paginate with. Default: Comes from System Settings or 10 */
    limit?: number;
    /** 
   * API to call to fetch records.
   * 
   * Default: `frappe.desk.search.search_link`
   * 
   * If you want to use a custom API, you can pass the path to the API here.
   * 
   * The API should return a list of documents in the following format:
   * [{value: string, description: string, label?: string}] - where the value is the ID of the document.
   * 
   * If the API sends a label, it will be used as the label in the dropdown.
  */
    searchAPIPath?: string;
    /**
    * Field you want to search against in the doctype.
    * 
    * Default: `name`
    * 
    * If you want to search against a different field, you can pass the fieldname here.
    * 
    * If you want to search against multiple fields, you can try using the `searchAPIPath` prop to call a custom API,
    * or use a custom query in the `customQuery` prop.
    */
    searchfield?: string;
    /** 
     * Custom query to be used to fetch records.
     * 
     * If you want to use a custom query, you can pass the query here.
     * 
     * The query should be in the following format:
     * {
     *  query: string,
     *  filters: {
     *      fieldname: string,
     *      operator: string,
     *      value: string
     *  }
     * }
     */
    customQuery?: {
        /** Path to function for the query. 
         * 
         * Refer: Item/Supplier query
         */
        query: string,
        /** Filters are usually an object instead of an array in a custom query */
        filters?: Record<string, string | number | boolean>,
    },
    /** 
     * Used for certain queries where a reference doctype is needed.
     * 
     * For example when searching a supplier in a "Purchase Invoice", the reference_doctype is "Purchase Invoice"
     */
    reference_doctype?: string,
    /** Placeholder for the dropdown. Default: `doctype` */
    placeholder?: string;
    /** 
     * Should the field be read-only. 
     */
    readOnly?: boolean;
    /** Should the field be disabled. Default: false */
    disabled?: boolean;
    /**
    * Function to filter the options based on the input value/other criteria.
    * 
    * For example, you might want to limit the companies shown in the dropdown since they have been already added (like in Cost Codes)
    */
    filterFn?: (option: ResultItem, inputValue: string) => boolean,
    value?: string,
    onChange: (value: string) => void,
    /** If true, the component will be wrapped in a FormControl component */
    useInForm?: boolean,
    /** Button Class name */
    buttonClassName?: string
}
const LinkFieldCombobox = ({
    doctype,
    reference_doctype,
    filters = [],
    value,
    onChange,
    readOnly,
    disabled,
    filterFn,
    placeholder = `Select ${doctype}`,
    customQuery,
    searchfield,
    searchAPIPath = "frappe.desk.search.search_link",
    limit,
    useInForm,
    buttonClassName
}: LinkFieldComboboxProps) => {

    const pageLimit = useMemo(() => limit || getSystemDefault('link_field_results_limit') || 20, [limit])

    /** Load the Doctype meta so that we can determine the search fields + the name of the title field */
    const { data: meta } = useDocType(doctype)

    const userCanCreate = useMemo(() => canCreateDocument(doctype), [doctype])

    const [open, setOpen] = useState(false)

    const [searchInput, setSearchInput] = useDebounceValue('', 400)

    const { data: linkTitleData } = useFrappeGetCall('frappe.client.get_value', {
        doctype,
        filters: JSON.stringify({
            name: value
        }),
        fieldname: meta?.title_field
    }, (meta?.show_title_field_in_link ?? false) && (meta?.title_field) && value ? `link_title::${doctype}::${value}` : null, {
        revalidateIfStale: false,
        revalidateOnFocus: false,
        revalidateOnReconnect: false,
    })

    const linkTitle = meta?.title_field && meta?.show_title_field_in_link ? (linkTitleData?.message?.[meta?.title_field] ?? value) : value

    const buttonRef = useRef<HTMLButtonElement>(null)

    const [width, setWidth] = useState(320)

    useLayoutEffect(() => {
        if (buttonRef.current) {
            setWidth(buttonRef.current.getBoundingClientRect().width)
        }
    }, [])

    const { data, error, isLoading } = useFrappeGetCall<{ message: ResultItem[] }>(searchAPIPath, {
        doctype,
        txt: searchInput,
        page_length: pageLimit,
        query: customQuery?.query,
        searchfield,
        filters: JSON.stringify(customQuery?.filters || filters || []),
        reference_doctype,
    }, () => {
        if (!open) {
            return null
        } else {
            let key = `${searchAPIPath}_${doctype}_${searchInput}`

            if (pageLimit) {
                key += `_${pageLimit}`
            }

            if (customQuery?.filters) {
                key += `_${JSON.stringify(customQuery.filters)}`
            } else if (filters) {
                key += `_${JSON.stringify(filters)}`
            }

            if (customQuery && customQuery.query) {
                key += `_${customQuery.query}`
            }

            if (reference_doctype) {
                key += `_${reference_doctype}`
            }

            if (searchfield && searchfield !== 'name') {
                key += `_${searchfield}`
            }

            return key

        }
    }, {
        revalidateOnFocus: false,
        revalidateIfStale: false,
        shouldRetryOnError: false,
        revalidateOnReconnect: false,
    })

    const onOpenChange = (open: boolean) => {
        if (readOnly) return
        setOpen(open)
        setSearchInput("")
    }

    const onSelect = (value: string) => {
        onChange?.(value)
        setOpen(false)
    }

    const items = filterFn ? data?.message?.slice(0, 50).filter((item) => filterFn(item, searchInput)) : data?.message

    return (
        <Popover open={open} onOpenChange={onOpenChange} modal={true}>
            <PopoverTrigger asChild>
                {useInForm ? <FormControl>
                    <Button
                        variant="outline"
                        role="combobox"
                        ref={buttonRef}
                        tabIndex={0}
                        disabled={disabled || readOnly}
                        aria-expanded={open}
                        aria-readonly={readOnly}
                        className={cn("w-full justify-between font-normal group",
                            readOnly ? "bg-muted" : ""
                            , buttonClassName)}>
                        {linkTitle || placeholder}

                        <div className="flex items-center gap-1">
                            {value && <a href={`/app/${slug(doctype)}/${value}`} target="_blank" className="group-hover:block hidden">
                                <ExternalLink className="h-4 w-4 shrink-0 opacity-50" />
                            </a>}
                            <ChevronsUpDownIcon className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                        </div>
                    </Button>
                </FormControl>
                    : <Button
                        variant="outline"
                        role="combobox"
                        ref={buttonRef}
                        disabled={disabled}
                        aria-expanded={open}
                        className={cn("w-full justify-between font-normal",
                            readOnly ? "bg-muted" : ""
                            , buttonClassName)}>
                        {value || placeholder}

                        <ChevronsUpDownIcon className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                    </Button>}
            </PopoverTrigger>
            <PopoverContent className="p-0" style={{ minWidth: width }} align="start">
                {error && <ErrorBanner error={error} />}
                <Command shouldFilter={false} className="w-full">
                    <CommandInput placeholder={placeholder} onValueChange={setSearchInput} />
                    <CommandList>
                        <CommandEmpty>{isLoading ? _("Loading...") : _("No results found.")}</CommandEmpty>
                        <CommandGroup>
                            {items?.map((result) => (
                                <CommandItem key={result.value} onSelect={() => onSelect(result.value)} className="flex flex-col items-start gap-0.5">
                                    <span className="font-medium">
                                        {result.label || result.value}
                                    </span>
                                    {result.description && <span className="text-xs text-muted-foreground">
                                        {result.description}
                                    </span>}
                                </CommandItem>
                            ))}
                            {userCanCreate && <CommandItem asChild>
                                <a href={`/app/${slug(doctype)}/new-${slug(doctype)}-1`}
                                    target="_blank"
                                    className="hover:underline underline-offset-4 cursor-pointer flex justify-between items-center">
                                    {_("Create New {0}", [doctype])}

                                    <ExternalLink />
                                </a>

                            </CommandItem>}
                        </CommandGroup>


                    </CommandList>
                </Command>
            </PopoverContent>

        </Popover>
    )
}

export default LinkFieldCombobox