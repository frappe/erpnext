// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

let soil_edit_order = [0,1,2];

frappe.ui.form.on('Soil Texture', {
	refresh: function(frm) {
	},
	validate: function(frm) {
		if (frm.doc.clay_composition < 0 || frm.doc.sand_composition < 0 || frm.doc.silt_composition < 0 )
			frappe.throw("Soil Composition cannot have negetive values")
	},
	clay_composition: function(frm) {
		if (frm.doc.clay_composition > 100 || frm.doc.clay_composition < 0)
			frappe.throw("Clay Composition should be a value between 0 and 100")
		soil_edit_order[0] = Math.max.apply(Math, soil_edit_order)+1;
		frm.doc.soil_type = get_soil_type(frm.doc.clay_composition, frm.doc.sand_composition, frm.doc.silt_composition);
		frm.refresh_fields();
	},
	sand_composition: function(frm) {
		if (frm.doc.sand_composition > 100 || frm.doc.sand_composition < 0)
			frappe.throw("Sand Composition should be a value between 0 and 100")
		soil_edit_order[1] = Math.max.apply(Math, soil_edit_order)+1;
		frm.doc.soil_type = get_soil_type(frm.doc.clay_composition, frm.doc.sand_composition, frm.doc.silt_composition);
		frm.refresh_fields();
	},
	silt_composition: function(frm) {
		if (frm.doc.silt_composition > 100 || frm.doc.silt_composition < 0)
			frappe.throw("Silt Composition should be a value between 0 and 100")
		soil_edit_order[2] = Math.max.apply(Math, soil_edit_order)+1;
		frm.doc.soil_type = get_soil_type(frm.doc.clay_composition, frm.doc.sand_composition, frm.doc.silt_composition);
		frm.refresh_fields();
	}
});

let get_soil_type = (clay, sand, silt) => {
	if (soil_edit_order.reduce((a, b) => a + b, 0) < 5) return "Undefined";
	last_edit_index = soil_edit_order.indexOf(Math.min.apply(Math, soil_edit_order));

	sand = parseFloat(sand);
	clay = parseFloat(clay);
	silt = parseFloat(silt);

	soil = [clay, sand, silt];
	soil[last_edit_index] = 100 - soil.reduce((a, b) => a + b, 0) + soil[last_edit_index];
	[clay, sand, silt] = soil;

	if (last_edit_index == 0) cur_frm.doc.clay_composition = soil[last_edit_index];
	else if (last_edit_index == 1) cur_frm.doc.sand_composition = soil[last_edit_index];
	else cur_frm.doc.silt_composition = soil[last_edit_index];

	if((silt + 1.5*clay) < 15){
		return 'Sand';
	}else if((silt + 1.5*clay >= 15) && (silt + 2*clay < 30)){
		return 'Loamy Sand';
	}else if((clay >= 7 && clay < 20) && (sand > 52) && ((silt + 2*clay) >= 30) || (clay < 7 && silt < 50 && (silt+2*clay)>=30)){
		return 'Sandy Loam';
	}else if((clay >= 7 && clay < 27) && (silt >= 28 && silt < 50) && (sand <= 52)){
		return 'Loam';
	}else if((silt >= 50 && (clay >= 12 && clay < 27)) || ((silt >= 50 && silt < 80) && clay < 12)){
		return 'Silt Loam';
	}else if(silt >= 80 && clay < 12){
		return 'Silt';
	}else if((clay >= 20 && clay < 35) && (silt < 28) && (sand > 45)) 	{
		return 'Sandy Clay Loam';
	}else if((clay >= 27 && clay < 40) && (sand > 20 && sand <= 45)){
		return 'Clay Loam';
	}else if((clay >= 27 && clay < 40) && (sand  <= 20)){
		return 'Silty Clay Loam';
	}else if(clay >= 35 && sand > 45){
		return 'Sandy Clay';
	}else if(clay >= 40 && silt >= 40){
		return 'Silty Clay';
	}else if(clay >= 40 && sand <= 45 && silt < 40){
		return 'Clay';
	}else{
		return 'Undefined';
	}
}
