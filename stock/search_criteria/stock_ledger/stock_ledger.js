report.customize_filters = function() {
  this.add_filter({fieldname:'item_name', label:'Item Name', fieldtype:'Data', options:'', parent:'Item'});
  this.add_filter({fieldname:'description', label:'Description', fieldtype:'Small Text', options: '', parent:'Item'});
}