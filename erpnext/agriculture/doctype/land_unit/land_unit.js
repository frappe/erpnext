// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

// Code for finding the area of editable features drawn on the geolocation control



RADIUS = 6378137;
FLATTENING_DENOM = 298.257223563
FLATTENING = 1/FLATTENING_DENOM;
POLAR_RADIUS = RADIUS*(1-FLATTENING);

function geometry(_) {
	var area = 0, i;
	switch (_.type) {
		case 'Polygon':
			return polygonArea(_.coordinates);
		case 'MultiPolygon':
			for (i = 0; i < _.coordinates.length; i++) {
					area += polygonArea(_.coordinates[i]);
			}
			return area;
		case 'Point':
		case 'MultiPoint':
		case 'LineString':
		case 'MultiLineString':
			return 0;
		case 'GeometryCollection':
			for (i = 0; i < _.geometries.length; i++) {
					area += geometry(_.geometries[i]);
			}
			return area;
	}
}

function polygonArea(coords) {
	var area = 0;
	if (coords && coords.length > 0) {
		area += Math.abs(ringArea(coords[0]));
		for (var i = 1; i < coords.length; i++) {
			area -= Math.abs(ringArea(coords[i]));
		}
	}
	return area;
}

function ringArea(coords) {
	var p1, p2, p3, lowerIndex, middleIndex, upperIndex, i,
	area = 0,
	coordsLength = coords.length;

	if (coordsLength > 2) {
		for (i = 0; i < coordsLength; i++) {
			if (i === coordsLength - 2) {// i = N-2
				lowerIndex = coordsLength - 2;
				middleIndex = coordsLength -1;
				upperIndex = 0;
			} else if (i === coordsLength - 1) {// i = N-1
				lowerIndex = coordsLength - 1;
				middleIndex = 0;
				upperIndex = 1;
			} else { // i = 0 to N-3
				lowerIndex = i;
				middleIndex = i+1;
				upperIndex = i+2;
			}
			p1 = coords[lowerIndex];
			p2 = coords[middleIndex];
			p3 = coords[upperIndex];
			area += ( rad(p3[0]) - rad(p1[0]) ) * Math.sin( rad(p2[1]));
		}

		area = area * RADIUS * RADIUS / 2;
	}

	return area;
}

function rad(_) {
	return _ * Math.PI / 180;
}

function compute_layer_area(layers) {
	layer_area = 0;

	feature_layers = Object.keys(layers).map((key) => key)

	feature_layers = feature_layers.map((key) => {
    	if(layers[key].hasOwnProperty('feature')){
    	    return layers[key]['feature'];
    	}
		}).filter((value) => value);
	
	if(feature_layers.length){
		feature_layers.forEach((feature_layer) => {
			if(feature_layer['geometry']['type'] == "Point" && feature_layer['properties']['point_type'] == "circle"){
				layer_area += Math.PI * feature_layer['properties']['radius'] * feature_layer['properties']['radius'];
			} else {
				layer_area += geometry(feature_layer['geometry']);
			}
		});
	}

	return layer_area;
}

frappe.ui.form.on('Land Unit', {
	validate(frm){
		let new_area = parseFloat(compute_layer_area(frm.fields_dict.location.map._layers).toFixed(3));
		area_difference =  new_area - frm.doc.area;
		frm.doc.area_difference = area_difference;
		frm.doc.area = new_area; 
	},
	onload_post_render(frm){
		if(!frm.doc.location && frm.doc.latitude && frm.doc.longitude)	{
			frm.fields_dict.location.map.setView([frm.doc.latitude, frm.doc.longitude],13);
		}
		else {
			frm.doc.latitude = frm.fields_dict.location.map.getCenter()['lat'];
			frm.doc.longitude = frm.fields_dict.location.map.getCenter()['lng'];
			frm.save();
		}
	},
	refresh: function(frm) {
		if(!frm.doc.parent_land_unit) {
			frm.set_read_only();
			frm.set_intro(__("This is a root land unit and cannot be edited."));
		} else {
			frm.set_intro(null);
		}
	}
});
