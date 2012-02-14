wn.require('lib/js/lib/jscolor/jscolor.js');

cur_frm.cscript.onload_post_render = function() {
	cur_frm.fields_dict.background_color.input.className = 'color';
	jscolor.bind();
}