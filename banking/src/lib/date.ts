import dayjs from 'dayjs';
import utc from 'dayjs/plugin/utc';
import timezone from 'dayjs/plugin/timezone';
import advancedFormat from 'dayjs/plugin/advancedFormat';
import relativeTime from 'dayjs/plugin/relativeTime';
import quarterOfYear from 'dayjs/plugin/quarterOfYear'
import customParseFormat from 'dayjs/plugin/customParseFormat';
import _ from '@/lib/translate';

dayjs.extend(utc);
dayjs.extend(timezone);
dayjs.extend(advancedFormat);
dayjs.extend(relativeTime);
dayjs.extend(quarterOfYear);
dayjs.extend(customParseFormat);

const FRAPPE_DATE_FORMAT = "YYYY-MM-DD"

export const getUserDateFormat = () => {

    return window?.frappe?.boot?.user?.defaults?.date_format.toUpperCase() || window?.frappe.boot.sysdefaults.date_format.toUpperCase()

}
// const FRAPPE_DATETIME_FORMAT = "YYYY-MM-DD HH:mm:ss"

export type TimePeriod = 'This Week' | 'This Month' | 'This Quarter' | 'This Year' | 'Last Week' | 'Last Month' | 'Last Quarter' | 'Last Year' | 'Date Range'

export const AVAILABLE_TIME_PERIODS: TimePeriod[] = [
    'This Month',
    'This Week',
    'This Quarter',
    'This Year',
    'Last Week',
    'Last Month',
    'Last Quarter',
    'Last Year',
];

/**
 * Get the start and end dates for a given time period
 * @param timePeriod - The time period to get the dates for
 * @param format - The date format to use (defaults to FRAPPE_DATE_FORMAT)
 * @param baseDate - Optional base date to use for calculations (defaults to current date)
 * @returns The start and end dates in specified format, or empty strings if invalid
 */
export const getDatesForTimePeriod = (
    timePeriod: TimePeriod,
    format: string = FRAPPE_DATE_FORMAT,
    baseDate?: string
) => {

    const daysJSObject = baseDate ? dayjs(baseDate) : dayjs()

    // Based on the time period, get the start and end dates

    if (timePeriod === 'This Week') {
        return {
            fromDate: daysJSObject.startOf('week').format(format),
            toDate: daysJSObject.endOf('week').format(format),
            format: "Do MMM 'YY",
            translatedLabel: _('This Week')
        }
    }

    if (timePeriod === 'This Month' || timePeriod === 'Date Range') {
        return {
            fromDate: daysJSObject.startOf('month').format(format),
            toDate: daysJSObject.endOf('month').format(format),
            format: "Do MMM 'YY",
            translatedLabel: _('This Month')
        }
    }

    if (timePeriod === 'This Quarter') {
        return {
            fromDate: daysJSObject.startOf('quarter').format(format),
            toDate: daysJSObject.endOf('quarter').format(format),
            format: 'MMM YYYY',
            translatedLabel: _('This Quarter')
        }
    }

    if (timePeriod === 'This Year') {
        return {
            fromDate: daysJSObject.startOf('year').format(format),
            toDate: daysJSObject.endOf('year').format(format),
            format: 'MMM YYYY',
            translatedLabel: _('This Year')
        }
    }

    if (timePeriod === 'Last Week') {
        const lastWeek = daysJSObject.subtract(1, 'week')
        return {
            fromDate: lastWeek.startOf('week').format(format),
            toDate: lastWeek.endOf('week').format(format),
            format: "Do MMM 'YY",
            translatedLabel: _('Last Week')
        }
    }

    if (timePeriod === 'Last Month') {
        const lastMonth = daysJSObject.subtract(1, 'month')
        return {
            fromDate: lastMonth.startOf('month').format(format),
            toDate: lastMonth.endOf('month').format(format),
            format: "Do MMM 'YY",
            translatedLabel: _('Last Month')
        }
    }

    if (timePeriod === 'Last Quarter') {
        const lastQuarter = daysJSObject.subtract(1, 'quarter')
        return {
            fromDate: lastQuarter.startOf('quarter').format(format),
            toDate: lastQuarter.endOf('quarter').format(format),
            format: 'MMM YYYY',
            translatedLabel: _('Last Quarter')
        }
    }

    if (timePeriod === 'Last Year') {
        const lastYear = daysJSObject.subtract(1, 'year')
        return {
            fromDate: lastYear.startOf('year').format(format),
            toDate: lastYear.endOf('year').format(format),
            format: 'MMM YYYY',
            translatedLabel: _('Last Year')
        }
    }

    return {
        fromDate: '',
        toDate: '',
        format: 'Do MMM YY',
        translatedLabel: _('Date Range')
    }
}

const toUserTimezone = (timestamp: string) => {

    const systemTimezone = window.frappe?.boot?.time_zone?.system
    const userTimezone = window.frappe?.boot?.time_zone?.user

    if (systemTimezone && userTimezone) {
        return dayjs.tz(timestamp, systemTimezone).clone().tz(userTimezone)
    } else {
        return dayjs(timestamp)
    }

}

export const getTimeago = (date?: string) => {
    if (date) {
        const userDate = toUserTimezone(date)
        return userDate.fromNow()
    }
    return ''
}

export const formatDate = (date?: string | Date, format?: string) => {

    if (!format) {
        format = getUserDateFormat()
    }

    if (date) {
        return dayjs(date).format(format)
    }
    return ''
}

/**
 * Utility function to convert a date string to a Date object
 * @param date 
 * @returns 
 */
export const toDate = (date: string, format: string = "YYYY-MM-DD") => {
    return dayjs(date, format).toDate()
}

export const today = () => {
    return dayjs().format(FRAPPE_DATE_FORMAT)
}