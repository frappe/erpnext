// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Land Unit', {
    onload: function(frm) {},
    refresh: function(frm) {
        // frappe.msgprint('Refresh')
        if (!frm.doc.parent_land_unit) {
            frm.set_read_only();
            frm.set_intro(__("This is a root territory and cannot be edited."));
        } else {
            frm.set_intro(null);
        }

        frappe.require([
            "assets/erpnext/js/leaflet/leaflet.js",
            "assets/erpnext/css/leaflet/leaflet.css",
            "assets/erpnext/js/leaflet/leaflet.draw.js",
            "assets/erpnext/css/leaflet/leaflet.draw.css"
        ], init_location);

        function init_location() {
            $(frm.fields_dict.location.$wrapper[0]).html('<div id="map" style="height:500px"></div>');

            //Leaflet proto code
            L.Icon.Default.imagePath = 'assets/erpnext/images/leaflet';
            var map = L.map('map').setView([19.0800, 72.8961], 13);

            L.tileLayer('http://{s}.tile.osm.org/{z}/{x}/{y}.png', {
                attribution: '&copy; <a href="http://osm.org/copyright">OpenStreetMap</a> contributors'
            }).addTo(map);

            L.marker([19.0800, 72.8961]).addTo(map)
                .bindPopup('A pretty CSS3 popup.<br> Easily customizable.')
                .openPopup();

            //
        }
    }
});