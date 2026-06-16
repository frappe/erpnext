function _(txt: string, replace?: string[], context = null) {
    if (!txt) return txt;
    if (typeof txt != "string") return txt;

    let translated_text = "";

    const key = txt; // txt.replace(/\n/g, "");
    if (window.frappe) {
        if (context) {
            translated_text = window.frappe._messages[`${key}:${context}`];
        }

        if (!translated_text) {
            translated_text = window.frappe?._messages?.[key] || txt;
        }

    } else {
        translated_text = txt;
    }

    if (replace && typeof replace === "object") {
        translated_text = format(translated_text, replace);
    }
    return translated_text;
};

function format(str: string, args: string[]) {
    if (str == undefined) return str;

    let unkeyed_index = 0;
    return str.replace(
        /\{(\w*)\}/g,
        function (match, key) {
            if (key === "") {
                key = unkeyed_index;
                unkeyed_index++;
            }
            if (key == +key) {
                return args[key] ?? match;
            }
            return ""
        }
    );
}
export default _;