const METHOD = "erpnext.manufacturing.page.plant_builder.plant_builder.";

export const call = (method, args = {}) => window.frappe.xcall(METHOD + method, args);

export const __ = (text, replace) => window.__(text, replace);

export const setRoute = (...parts) => window.frappe.set_route("plant-builder", ...parts);

export const openForm = (doctype, name) => window.frappe.set_route("Form", doctype, name);

export const openList = (doctype, filters) => window.frappe.set_route("List", doctype, filters);
