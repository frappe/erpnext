
frappe.listview_settings['Lead'] = {
    hide_name_column: true,
	add_fields: ["status","sub_status","lead_number","company_name","date"],
	get_indicator: function(doc) {
		if(doc.status=="Open") {
			return [__("Open"), "red", "doc.status,=,Open"];
		} else if(doc.status=="Contacted") {
			return [__("Contacted"), "blue", "doc.status,=,Contacted"];
		}else if(doc.status=="Success") {
			return [__("Success"), "green", "doc.status,=,Success"];
		}else if(doc.status=="Close") {
			return [__("Close"), "black", "doc.status,=,Close"];
		}
	},
    onload: function(me) {
		me.$page.find(`div[data-fieldname='name']`).addClass('hide');
    },
}