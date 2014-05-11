// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

$.extend(cur_frm.cscript, {
	onload: function() {
		if(cur_frm.doc.__quotation_series) {
			cur_frm.fields_dict.quotation_series.df.options = cur_frm.doc.__quotation_series;
		}
	}
});