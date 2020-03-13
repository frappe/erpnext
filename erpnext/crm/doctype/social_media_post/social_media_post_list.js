frappe.listview_settings['Social Media Post'] = {
    add_fields: ["status","post_status"],
    get_indicator: function(doc) {
        return [__(doc.post_status), {
            "Scheduled": "orange",
            "Posted": "green"
            }[doc.post_status]];
        }
}