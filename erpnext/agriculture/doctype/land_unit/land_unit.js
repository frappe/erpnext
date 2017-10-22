// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Land Unit', {
	refresh: function(frm) {
		if(!frm.doc.parent_land_unit) {
			frm.set_read_only();
			frm.set_intro(__("This is a root land unit and cannot be edited."));
		} else {
			frm.set_intro(null);
		}
		if(frm.doc.land_unit_type == 'Block') {
			frm.doc.is_group = 0
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
			var map = L.map('map').setView([frm.doc.latitude, frm.doc.longitude], 13);
		
			L.tileLayer('http://{s}.tile.osm.org/{z}/{x}/{y}.png', {
				attribution: '&copy; <a href="http://osm.org/copyright">OpenStreetMap</a> contributors'
			}).addTo(map);
			
			var MyCustomMarker = L.Icon.extend({
				options: {
						shadowUrl: null,
						iconAnchor: new L.Point(12, 12),
						iconSize: new L.Point(24, 24),
						iconUrl: 'assets/erpnext/images/leaflet/farmer.png'
				}
			});
			
			L.marker([frm.doc.latitude, frm.doc.longitude], { icon: new MyCustomMarker() }).addTo(map)
				.bindPopup('Map Center')
				.openPopup();
			
			if (frm.fields_dict.coordinates.value) {
				geojsonFeature = JSON.parse(frm.doc.coordinates)
				// map.addLayer(geojsonFeature);
			}
			var editableLayers = L.geoJson(geojsonFeature).addTo(map);
			//
			//var editableLayers = new L.FeatureGroup();
			map.addLayer(editableLayers);
			
			
			var options = {
				position: 'topleft',
				draw: {
						polyline: {
								shapeOptions: {
										color: '#f357a1',
										weight: 10
								}
						},
						polygon: {
								allowIntersection: false, // Restricts shapes to simple polygons
								drawError: {
										color: '#e1e100', // Color the shape will turn when intersects
										message: '<strong>Oh snap!<strong> you can\'t draw that!' // Message that will show when intersect
								},
								shapeOptions: {
										color: '#f357a1'
								}
						},
						circle: true,
						rectangle: {
								shapeOptions: {
										clickable: false
								}
						},
						marker: {
								icon: new MyCustomMarker()
						}
				},
				edit: {
						featureGroup: editableLayers, //REQUIRED!!
						remove: true
				}
			};
			
			var drawControl = new L.Control.Draw(options);
			map.addControl(drawControl);
			
			map.on('draw:created', function(e) {
				var type = e.layerType,
						layer = e.layer;
				if (type === 'marker') {
						layer.bindPopup('A popup!');
				}
				editableLayers.addLayer(layer);
				//console.log("The editable layer is {0}", [JSON.stringify(editableLayers.toGeoJSON())])
				frm.doc.coordinates = JSON.stringify(editableLayers.toGeoJSON())
			
			});
			
			map.on('draw:deleted', function(e) {
				var type = e.layerType,
						layer = e.layer;
				editableLayers.removeLayer(layer);
				frm.doc.coordinates = JSON.stringify(editableLayers.toGeoJSON())
			});
			
			map.on('draw:edited', function(e) {
				var type = e.layerType,
						layer = e.layer;
				editableLayers.removeLayer(layer);
				frm.doc.coordinates = JSON.stringify(editableLayers.toGeoJSON())
			});
			//console.log("The editable layer is {0}", [JSON.stringify(editableLayers.toGeoJSON())])
			// frm.doc.coordinates= JSON.stringify(editableLayers.toGeoJSON())[0]
		}
	}
});
