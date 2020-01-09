frappe.provide('frappe.dashboards.chart_sources');

frappe.dashboards.chart_sources["Cameras"] = {
        method: "erpnext.accounts.dashboard_chart_source.cameras.cameras.get",
        filters: [
                {
                        fieldname: "item_code",
                        label: __("Item"),
                        fieldtype: "Link",
                        options: "Item",
                        reqd: 1
                },
                {
                        fieldname: "status",
                        label: __("Status"),
                        fieldtype: "Link",
                        options: "Serial No State",
                        reqd: 1
                },
        ]
};
