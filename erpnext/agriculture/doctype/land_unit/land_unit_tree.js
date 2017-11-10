frappe.treeview_settings["Land Unit"] = {
	fields:[
		{fieldtype:'Check', fieldname:'is_container',
			label:__('Is Container ?')}, 
		{fieldtype:'Float', fieldname:'latitude',
			label:__('Latitude')}, 
		{fieldtype:'Float', fieldname:'longitude',
			label:__('Longitude')}
	],
	ignore_fields:["parent_land_unit"]
}