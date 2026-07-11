import { getCurrencyNumberFormat, getCurrencyProperty, getCurrencySymbol } from "./currency";
import { getSystemDefault } from "./frappe";
import _ from "@/lib/translate";

export const formatCurrency = (value?: number, currency: string = '', decimals: number = 2) => {

    if (!value) {
        value = 0
    }

    if (!currency) {
        currency = getSystemDefault('currency') ?? ''
    }
    const format = get_number_format(currency);
    const symbol = getCurrencySymbol(currency);

    const show_symbol_on_right = getCurrencyProperty(currency, 'symbol_on_right') ?? false;

    if (decimals === undefined) {
        decimals = getSystemDefault('currency_precision') || null;
    }

    if (symbol) {
        if (show_symbol_on_right) {
            return format_number(value, format, decimals) + " " + _(symbol);
        }
        return _(symbol) + " " + format_number(value, format, decimals);
    } else {
        return format_number(value, format, decimals);
    }
}

const replace_all = (str: string, search: string, replace: string) => {
    return str.split(search).join(replace);
};

const number_format_info = {
    "#,###.##": { decimal_str: ".", group_sep: "," },
    "#.###,##": { decimal_str: ",", group_sep: "." },
    "# ###.##": { decimal_str: ".", group_sep: " " },
    "# ###,##": { decimal_str: ",", group_sep: " " },
    "#'###.##": { decimal_str: ".", group_sep: "'" },
    "#, ###.##": { decimal_str: ".", group_sep: ", " },
    "#,##,###.##": { decimal_str: ".", group_sep: "," },
    "#,###.###": { decimal_str: ".", group_sep: "," },
    "#.###": { decimal_str: "", group_sep: "." },
    "#,###": { decimal_str: "", group_sep: "," },
};

const format_number = (v?: number, format?: string, decimals?: number | null) => {
    if (!format) {
        format = get_number_format();
        if (decimals == null) decimals = cint(getSystemDefault("float_precision")) || 3;
    }

    const info = get_number_format_info(format);

    // Fix the decimal first, toFixed will auto fill trailing zero.
    if (decimals == null) decimals = info.precision;

    v = flt(v, decimals, format);

    let is_negative = false;
    if (v < 0) is_negative = true;
    v = Math.abs(v);

    const val = v.toFixed(decimals)

    const part = val.split(".");

    // get group position and parts
    let group_position = info.group_sep ? 3 : 0;

    if (group_position) {
        const integer = part[0];
        let str = "";
        for (let i = integer.length; i >= 0; i--) {
            let l = replace_all(str, info.group_sep, "").length;
            if (format == "#,##,###.##" && str.indexOf(",") != -1) {
                // INR
                group_position = 2;
                l += 1;
            }

            str += integer.charAt(i);

            if (l && !((l + 1) % group_position) && i != 0) {
                str += info.group_sep;
            }
        }
        part[0] = str.split("").reverse().join("");
    }
    if (part[0] + "" == "") {
        part[0] = "0";
    }

    // join decimal
    part[1] = part[1] && info.decimal_str ? info.decimal_str + part[1] : "";

    // join
    return (is_negative ? "-" : "") + part[0] + part[1];
};

function get_number_format_info(format: string) {
    let info: { decimal_str: string, group_sep: string, precision?: number } = number_format_info[format as keyof typeof number_format_info];

    if (!info) {
        info = { decimal_str: ".", group_sep: "," };
    }

    // get the precision from the number format
    info.precision = format.split(info.decimal_str).slice(1)[0].length;

    return info;
}

function get_number_format(currency?: string): string {
    return (
        (cint(getSystemDefault("use_number_format_from_currency")) &&
            currency &&
            getCurrencyNumberFormat(currency)) ||
        getSystemDefault("number_format") ||
        "#,###.##"
    )
}

export const flt = (value?: number | string | null, decimals?: number, number_format?: string, rounding_method?: string) => {
    if (value === undefined || value === null || value === "") return 0

    if (typeof value !== "number") {
        value = value + "";

        // strip currency symbol if exists
        if (value.indexOf(" ") != -1) {
            // using slice(1).join(" ") because space could also be a group separator
            const parts = value.split(" ");
            value = isNaN(parseFloat(parts[0])) ? parts.slice(parts.length - 1).join(" ") : value;
        }

        value = strip_number_groups(value, number_format);

        value = parseFloat(value as string);
        if (isNaN(value)) value = 0;
    }

    if (decimals != null) return _round(value, decimals, rounding_method);
    return value;
}

function strip_number_groups(v: string, number_format?: string) {
    if (!number_format) number_format = get_number_format();
    const info = get_number_format_info(number_format);

    // strip groups (,)
    const group_regex = new RegExp(info.group_sep === "." ? "\\." : info.group_sep, "g");
    v = v.replace(group_regex, "");

    // replace decimal separator with (.)
    if (info.decimal_str !== "." && info.decimal_str !== "") {
        const decimal_regex = new RegExp(info.decimal_str, "g");
        v = v.replace(decimal_regex, ".");
    }

    return v;
}

const _round = (num: number, precision: number, rounding_method?: string) => {

    rounding_method = rounding_method || getSystemDefault('rounding_method') || "Banker's Rounding (legacy)";

    const is_negative = num < 0 ? true : false;

    if (rounding_method == "Banker's Rounding (legacy)") {
        const d = cint(precision);
        const m = Math.pow(10, d);
        const n = +(d ? Math.abs(num) * m : Math.abs(num)).toFixed(8); // Avoid rounding errors
        const i = Math.floor(n),
            f = n - i;
        let r = !precision && f == 0.5 ? (i % 2 == 0 ? i : i + 1) : Math.round(n);
        r = d ? r / m : r;
        return is_negative ? -r : r;
    } else if (rounding_method == "Banker's Rounding") {
        if (num == 0) return 0.0;
        precision = cint(precision);

        const multiplier = Math.pow(10, precision);
        num = Math.abs(num) * multiplier;

        const floor_num = Math.floor(num);
        const decimal_part = num - floor_num;

        // For explanation of this method read python flt implementation notes.
        const epsilon = 2.0 ** (Math.log2(Math.abs(num)) - 52.0);

        if (Math.abs(decimal_part - 0.5) < epsilon) {
            num = floor_num % 2 == 0 ? floor_num : floor_num + 1;
        } else {
            num = Math.round(num);
        }
        num = num / multiplier;
        return is_negative ? -num : num;
    } else if (rounding_method == "Commercial Rounding") {
        if (num == 0) return 0.0;

        const digits = cint(precision);
        const multiplier = Math.pow(10, digits);

        num = num * multiplier;

        // For explanation of this method read python flt implementation notes.
        let epsilon = 2.0 ** (Math.log2(Math.abs(num)) - 52.0);
        if (is_negative) {
            epsilon = -1 * epsilon;
        }

        num = Math.round(num + epsilon);
        return num / multiplier;
    } else {
        throw new Error(`Unknown rounding method ${rounding_method}`);
    }
}


export const cint = (v: boolean | string | number, def?: boolean | string | number) => {
    if (v === true) return 1;
    if (v === false) return 0;
    v = v + "";
    if (v !== "0") v = lstrip(v, ["0"]);
    v = parseInt(v); // eslint-ignore-line
    if (isNaN(v)) v = def === undefined ? 0 : def;
    return v as number;
};

export const lstrip = (s: string, chars?: string[]) => {
    if (!chars) chars = ["\n", "\t", " "];
    // strip left
    let first_char = s.substring(0, 1);
    while (chars.includes(first_char)) {
        s = s.substring(1);
        first_char = s.substring(0, 1);
    }
    return s;
};

export const getCurrencyFormatInfo = (currency?: string) => {
    const format = get_number_format(currency);
    return get_number_format_info(format);
};