
frappe.listview_settings['Lead'] = {
    hide_name_column: true,
    onload: function(me) {
      me.$page.find(`div[data-fieldname='name']`).addClass('hide');
    },
        
}