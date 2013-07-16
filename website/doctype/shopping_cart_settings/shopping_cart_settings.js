$.extend(cur_frm.cscript, {
	onload: function() {
		if(cur_frm.doc.__quotation_series) {
			cur_frm.fields_dict.quotation_series.df.options = cur_frm.doc.__quotation_series;
		}
	}
});