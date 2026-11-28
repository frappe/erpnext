const METHOD = "erpnext.manufacturing.page.shop_floor.shop_floor.";

export const call = (method, args = {}) => window.frappe.xcall(METHOD + method, args);

export const __ = (text, replace) => window.__(text, replace);

export const go = (...parts) => window.frappe.set_route("shop-floor", ...parts);

export const openForm = (doctype, name) => window.frappe.set_route("Form", doctype, name);

export const notify = (message, indicator = "green") => window.frappe.show_alert({ message, indicator });
