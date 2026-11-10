import { useAtom } from 'jotai'
import { bankRecDateAtom } from './bankRecAtoms'
import { useMemo, useState } from 'react'
import { AVAILABLE_TIME_PERIODS, formatDate, getDatesForTimePeriod, TimePeriod } from '@/lib/date'
import { Button } from '@/components/ui/button'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { ChevronDownIcon, ChevronLeftIcon, ChevronRight } from 'lucide-react'
import { Command, CommandGroup, CommandInput, CommandItem, CommandList } from '@/components/ui/command'
import { parse } from "chrono-node"
import { Calendar } from '@/components/ui/calendar'
import useFiscalYear from '@/hooks/useFiscalYear'
import dayjs from 'dayjs'
import _ from '@/lib/translate'
import { useDirection } from '@/components/ui/direction'
import useResetScrollOnSearch from '@/hooks/useResetScrollOnSearch'

const DATE_FORMAT = 'YYYY-MM-DD'

/** Current fiscal year plus this many previous ones, for quarter/year options. */
const PREVIOUS_FISCAL_YEARS = 2

type DateOption = {
    /** Stable id - used as the cmdk value and the React key. */
    key: string
    label: string
    translatedLabel: string
    fromDate: string
    toDate: string
    format: string
    /** Extra terms to match against, beyond the labels and dates. */
    keywords?: string[]
    /** Whether to show this option when the search box is empty. */
    isDefault?: boolean
}

/**
 * Fiscal years keep the same month/day boundaries year on year, so previous years can be
 * derived by subtracting whole years instead of fetching them. Works for both Jan-Dec and
 * Apr-Mar style fiscal years.
 */
const fiscalYearLabel = (start: dayjs.Dayjs, end: dayjs.Dayjs) =>
    start.year() === end.year() ? `${start.year()}` : `${start.year()}-${end.year()}`

const BankRecDateFilter = () => {

    const [bankRecDate, setBankRecDate] = useAtom(bankRecDateAtom)

    const { fiscalYear } = useFiscalYear()

    const today = useMemo(() => dayjs().format(DATE_FORMAT), [])

    const allOptions = useMemo(() => {
        const standardOptions: DateOption[] = AVAILABLE_TIME_PERIODS.map((period) => {
            const dates = getDatesForTimePeriod(period)
            return {
                key: period,
                label: period,
                translatedLabel: dates.translatedLabel ?? _(period),
                fromDate: dates.fromDate,
                toDate: dates.toDate,
                format: dates.format,
                isDefault: true,
            }
        })

        if (!fiscalYear) {
            return standardOptions
        }

        const currentStart = dayjs(fiscalYear.year_start_date)
        const currentEnd = dayjs(fiscalYear.year_end_date)

        const quarterOptions: DateOption[] = []
        const fiscalYearOptions: DateOption[] = []

        // Static literals so the translation extractor can find them.
        const quarterLabels = [_("Q1"), _("Q2"), _("Q3"), _("Q4")]

        for (let yearsAgo = 0; yearsAgo <= PREVIOUS_FISCAL_YEARS; yearsAgo++) {
            const start = currentStart.subtract(yearsAgo, 'year')
            const end = currentEnd.subtract(yearsAgo, 'year')
            // Keep the real name for the current year; derive it for the earlier ones.
            const yearLabel = yearsAgo === 0 ? fiscalYear.name : fiscalYearLabel(start, end)

            for (let quarter = 0; quarter < 4; quarter++) {
                const quarterStart = start.add(quarter * 3, 'month')
                // End the day before the next quarter starts, clamped to the fiscal year end
                // so a short fiscal year can't spill over.
                const nextQuarterStart = start.add((quarter + 1) * 3, 'month')
                const quarterEnd = nextQuarterStart.subtract(1, 'day').isAfter(end)
                    ? end
                    : nextQuarterStart.subtract(1, 'day')

                if (quarterStart.isAfter(end)) continue

                quarterOptions.push({
                    key: `Q${quarter + 1}-${yearLabel}`,
                    label: `Q${quarter + 1}: ${yearLabel}`,
                    translatedLabel: `${quarterLabels[quarter]}: ${yearLabel}`,
                    fromDate: quarterStart.format(DATE_FORMAT),
                    toDate: quarterEnd.format(DATE_FORMAT),
                    format: 'MMM YYYY',
                    keywords: ['quarter', `q${quarter + 1}`, yearLabel],
                    // Only the current fiscal year's quarters clutter the default list;
                    // older ones stay searchable.
                    isDefault: yearsAgo === 0,
                })
            }

            const label = yearsAgo === 0
                ? 'This Fiscal Year'
                : yearsAgo === 1
                    ? 'Last Fiscal Year'
                    : `FY ${yearLabel}`

            fiscalYearOptions.push({
                key: `fiscal-year-${yearLabel}`,
                label,
                translatedLabel: yearsAgo <= 1 ? _(label) : `${_("FY")} ${yearLabel}`,
                fromDate: start.format(DATE_FORMAT),
                toDate: end.format(DATE_FORMAT),
                format: 'MMM YYYY',
                keywords: ['fiscal year', yearLabel],
                isDefault: yearsAgo <= 1,
            })
        }

        // "This Month"/"Last Month" first, then quarters and fiscal years, then the rest.
        const topRanked = standardOptions.filter((o) => o.label === 'This Month' || o.label === 'Last Month')
        const bottomRanked = standardOptions.filter((o) => o.label !== 'This Month' && o.label !== 'Last Month')

        return [...topRanked, ...quarterOptions, ...fiscalYearOptions, ...bottomRanked]
    }, [fiscalYear])

    // Reconciliation only looks backwards, so a period that hasn't started is never useful.
    const selectableOptions = useMemo(
        () => allOptions.filter((option) => option.fromDate <= today),
        [allOptions, today],
    )

    const [open, setOpen] = useState(false)
    const [value, setValue] = useState("")

    // We filter ourselves (`shouldFilter={false}`) so that the parsed-date suggestion can be a
    // real CommandItem alongside the predefined options, and keyboard navigation covers both.
    const filteredOptions = useMemo(() => {
        const query = value.trim().toLowerCase()

        if (!query) {
            return selectableOptions.filter((option) => option.isDefault)
        }

        const tokens = query.split(/\s+/)

        return selectableOptions.filter((option) => {
            const haystack = [
                option.label,
                option.translatedLabel,
                ...(option.keywords ?? []),
                option.fromDate,
                option.toDate,
            ].join(' ').toLowerCase()

            return tokens.every((token) => haystack.includes(token))
        })
    }, [selectableOptions, value])

    const parsedOption = useMemo(() => parseDateRange(value), [value])

    // Filtering shortens the list, so pin the scroll back to the top to keep the
    // auto-selected first option in view.
    const listRef = useResetScrollOnSearch(value)

    // Don't show a parsed suggestion that duplicates an option already in the list.
    const showParsedOption = parsedOption
        && !filteredOptions.some((o) => o.fromDate === parsedOption.fromDate && o.toDate === parsedOption.toDate)

    const timePeriod: TimePeriod | string = useMemo(() => {
        if (bankRecDate.fromDate && bankRecDate.toDate) {
            for (const period of allOptions) {
                if (period.fromDate === bankRecDate.fromDate && period.toDate === bankRecDate.toDate) {
                    return period.label;
                }
            }
            return "Date Range";
        } else {
            return "Date Range";
        }
    }, [bankRecDate.fromDate, bankRecDate.toDate, allOptions]);

    const handleTimePeriodChange = (fromDate: string, toDate: string) => {
        setBankRecDate({ fromDate, toDate })
        setValue("")
        setOpen(false)
    }

    const dateObj = useMemo(() => {
        return {
            from: new Date(bankRecDate.fromDate),
            to: new Date(bankRecDate.toDate)
        }
    }, [bankRecDate.fromDate, bankRecDate.toDate])

    const direction = useDirection()

    const RangeArrow = direction === 'ltr'
        ? <ChevronRight className='text-[12px] text-ink-gray-5/70' />
        : <ChevronLeftIcon className='text-[12px] text-ink-gray-5/70' />

    return <div className='flex items-center'>
        <Popover open={open} onOpenChange={setOpen}>
            <PopoverTrigger asChild>
                <Button
                    variant={'outline'}
                    aria-expanded={open}
                    size='md'
                    className='rounded-e-none border-e-0'
                    role="combobox">
                    {allOptions.find((period) => period.label === timePeriod)?.translatedLabel ?? _(timePeriod)}

                    <ChevronDownIcon />
                </Button>
            </PopoverTrigger>

            <PopoverContent className="w-84 p-1" align='start'>
                <Command shouldFilter={false}>

                    <CommandInput placeholder={_("e.g. Last 3 weeks, Q1, May 2025")} onValueChange={setValue} value={value} />
                    <CommandList ref={listRef} className='max-h-80'>
                        {showParsedOption && parsedOption && (
                            <CommandGroup heading={_("Matched date")}>
                                <CommandItem
                                    value='parsed-date-range'
                                    className='flex justify-between'
                                    onSelect={() => handleTimePeriodChange(parsedOption.fromDate, parsedOption.toDate)}>
                                    <span className='max-w-[45%] truncate'>{value}</span>
                                    <span className='text-xs text-ink-gray-5 flex items-center gap-1 text-end whitespace-nowrap'>
                                        {parsedOption.fromDate === parsedOption.toDate
                                            ? formatDate(parsedOption.fromDate, 'Do MMM YYYY')
                                            : <>{formatDate(parsedOption.fromDate, 'Do MMM YY')} {RangeArrow} {formatDate(parsedOption.toDate, 'Do MMM YY')}</>}
                                    </span>
                                </CommandItem>
                            </CommandGroup>
                        )}

                        {filteredOptions.length > 0 && (
                            <CommandGroup>
                                {filteredOptions.map((period) => (
                                    <CommandItem
                                        key={period.key}
                                        value={period.key}
                                        className='flex justify-between'
                                        onSelect={() => handleTimePeriodChange(period.fromDate, period.toDate)}>
                                        <span>
                                            {period.translatedLabel}
                                        </span>
                                        <span className='text-xs text-ink-gray-5 flex items-center gap-1 text-end whitespace-nowrap'>
                                            {formatDate(period.fromDate, period.format)} {RangeArrow} {formatDate(period.toDate, period.format)}
                                        </span>
                                    </CommandItem>
                                ))}
                            </CommandGroup>
                        )}

                        {!showParsedOption && filteredOptions.length === 0 && (
                            <div className='p-2 text-sm text-ink-gray-5'>
                                {_("No results found")}
                            </div>
                        )}
                    </CommandList>
                </Command>

            </PopoverContent>
        </Popover>

        <Popover>
            <PopoverTrigger asChild>
                <Button variant={'outline'} className='rounded-s-none' size='md'>
                    {formatDate(bankRecDate.fromDate)} - {formatDate(bankRecDate.toDate)}
                </Button>
            </PopoverTrigger>
            <PopoverContent className='w-auto overflow-hidden p-0' align='end'>
                <Calendar
                    mode='range'
                    captionLayout='dropdown'
                    selected={{
                        from: dateObj.from,
                        to: dateObj.to
                    }}
                    numberOfMonths={2}
                    defaultMonth={dateObj.from}
                    onSelect={(date) => {
                        if (date) {
                            setBankRecDate({ fromDate: formatDate(date.from, 'YYYY-MM-DD'), toDate: formatDate(date.to, 'YYYY-MM-DD') })
                        }
                    }}
                />
            </PopoverContent>
        </Popover>
    </div>
}

const referentialKeywords = ["last", "this", "next", "previous"]

/** chrono exposes `knownValues` on ParsingComponents but doesn't type it publicly. */
const knownValuesOf = (components: unknown): Record<string, number> =>
    (components as { knownValues?: Record<string, number> })?.knownValues ?? {}

/**
 * How far back a parsed date must move to land in the past. Reconciliation only ever looks
 * backwards, so an ambiguous input that chrono resolves into the future - "December" typed in
 * September, or a bare weekday like "Friday" - is pulled to its most recent past occurrence.
 * An explicitly stated year is respected; a range that is still future gets discarded later.
 *
 * This returns a shift rather than a date so that a range can be moved as a single unit -
 * shifting its start and end independently would distort or invert it.
 */
const pastShift = (date: Date, knownValues: Record<string, number>) => {
    const today = dayjs()
    let candidate = dayjs(date)

    if (!candidate.isAfter(today, 'date') || knownValues.year !== undefined) {
        return { amount: 0, unit: 'year' as const }
    }

    // A bare weekday repeats weekly, everything else (month/day) repeats yearly.
    const unit = knownValues.weekday !== undefined && knownValues.day === undefined
        ? 'day' as const
        : 'year' as const
    const step = unit === 'day' ? 7 : 1
    let amount = 0

    for (let i = 0; i < 200 && candidate.isAfter(today, 'date'); i++) {
        candidate = candidate.subtract(step, unit)
        amount += step
    }

    return { amount, unit }
}

/**
 * Parse free text into a past date range, or return undefined when it can't be parsed or
 * resolves entirely into the future.
 */
const parseDateRange = (value: string): { fromDate: string, toDate: string } | undefined => {
    if (!value.trim()) return undefined

    const parsedDate = parse(value, undefined, { forwardDate: false })

    if (!parsedDate || parsedDate.length === 0) return undefined

    const result = parsedDate[0]
    const startKnownValues = knownValuesOf(result.start)

    // Anchor the shift on the start and apply it to both ends, so an explicit range like
    // "1st Sept to 30th Sept" keeps its shape instead of having only its end rolled back.
    const shift = pastShift(result.start.date(), startKnownValues)
    const startDate = dayjs(result.start.date()).subtract(shift.amount, shift.unit).toDate()
    const endDate = result.end
        ? dayjs(result.end.date()).subtract(shift.amount, shift.unit).toDate()
        : undefined

    const today = new Date()
    let range: { fromDate: Date, toDate: Date }

    if (endDate) {
        const endKnownValues = knownValuesOf(result.end)
        // chrono ends "Apr 2025 to Jun 2025" on the 1st of June, but the user means all of it.
        const rangeEnd = endKnownValues.month && !endKnownValues.day
            ? dayjs(endDate).endOf('month').toDate()
            : endDate
        range = { fromDate: startDate, toDate: rangeEnd }
    } else if (startKnownValues.month && !startKnownValues.day) {
        // The user only wants a specific month like "May 2025" - span the whole month
        range = { fromDate: dayjs(startDate).startOf('month').toDate(), toDate: dayjs(startDate).endOf('month').toDate() }
    } else if (startKnownValues.month && startKnownValues.day && !referentialKeywords.some(keyword => value.toLowerCase().includes(keyword))) {
        // If month and day is known, then we should not assume that the user wants to get everything until today
        range = { fromDate: startDate, toDate: startDate }
    } else {
        range = { fromDate: startDate, toDate: today }
    }

    // A range that hasn't started yet is never useful for reconciliation. A range that merely
    // ends in the future is kept as typed, the same way "This Month" spans the whole month.
    if (dayjs(range.fromDate).isAfter(today, 'date')) return undefined

    if (dayjs(range.toDate).isBefore(range.fromDate, 'date')) {
        range = { fromDate: range.toDate, toDate: range.fromDate }
    }

    return {
        fromDate: dayjs(range.fromDate).format(DATE_FORMAT),
        toDate: dayjs(range.toDate).format(DATE_FORMAT),
    }
}

export default BankRecDateFilter
