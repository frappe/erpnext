// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.listview_settings['Subcontracting Order'] = {
    get_indicator: (doc) => {
        const status_colors = {
            "Draft": "grey",
            "Open": "orange",
            "Partially Received": "yellow",
            "Completed": "green",
            "Material Transferred": "blue",
            "Partial Material Transferred": "yellow"
        };
        return [__(doc.status), status_colors[doc.status], "status,=," + doc.status];
    }
};