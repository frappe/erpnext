import { useLayoutEffect, useRef } from "react"

/**
 * Pins a scrollable list back to the top whenever the search term changes.
 *
 * Dropdowns that do their own filtering (`shouldFilter={false}`) swap a long list for a much
 * shorter one while the scroll container keeps its previous offset - which can leave the
 * auto-selected first item scrolled out of view.
 *
 * Returns a ref to attach to the scroll container (e.g. `CommandList`).
 */
const useResetScrollOnSearch = (search: string) => {
    const listRef = useRef<HTMLDivElement>(null)

    // Layout effect so the reset lands before paint, avoiding a visible jump.
    useLayoutEffect(() => {
        listRef.current?.scrollTo({ top: 0 })
    }, [search])

    return listRef
}

export default useResetScrollOnSearch
