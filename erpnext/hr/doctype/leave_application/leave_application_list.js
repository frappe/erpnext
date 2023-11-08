frappe.listview_settings["Leave Application"] = {
    add_fields: ["leave_type", "employee", "employee_name", "total_leave_days", "from_date", "to_date"],
    has_indicator_for_draft: 1,
    get_indicator: function (doc) {
        let status_color = {
            "Approved": "green",
            "Rejected": "red",
            "Open": "orange",
            "Cancelled": "red",
            "Submitted": "blue"
        };
        return [__(doc.status), status_color[doc.status], "status,=," + doc.status];
    },
    hide_name_column: true,
    onload: function (me) {
        me.$page.find(`div[data-fieldname='application_number']`).addClass('hide');
        me.$page.find(`div[class= "filter-selector"]`).addClass('hide');
        me.$page.find('.page-head .menu-btn-group').css('display', 'none');
        var inputElement = me.$page.find('input[data-fieldname="name"]');
    inputElement.attr('placeholder', 'Application Number');
    }
};