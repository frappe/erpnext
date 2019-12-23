frappe.listview_settings['Company'] = {
    onload: () => {
        frappe.breadcrumbs.add({
            type: 'Custom',
            module: __('Accounts'),
            label: __('Accounts'),
            route: '#modules/Accounts'
        });
    }
}