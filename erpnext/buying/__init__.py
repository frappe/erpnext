from __future__ import unicode_literals
import frappe

install_docs = [
	{"param_name":"total_accepted_items","name":"Total Accepted Items","doctype":"Supplier Scorecard Variable","variable_label":"Total Accepted Items","path":"get_total_accepted_items"},
	{"param_name":"total_accepted_amount","name":"Total Accepted Amount","doctype":"Supplier Scorecard Variable","variable_label":"Total Accepted Amount","path":"get_total_accepted_amount"},
	{"param_name":"total_rejected_items","name":"Total Rejected Items","doctype":"Supplier Scorecard Variable","variable_label":"Total Rejected Items","path":"get_total_rejected_items"},
	{"param_name":"total_rejected_amount","name":"Total Rejected Amount","doctype":"Supplier Scorecard Variable","variable_label":"Total Rejected Amount","path":"get_total_rejected_amount"},
	{"param_name":"total_received_items","name":"Total Received Items","doctype":"Supplier Scorecard Variable","variable_label":"Total Received Items","path":"get_total_received_items"},
	{"param_name":"total_received_amount","name":"Total Received Amount","doctype":"Supplier Scorecard Variable","variable_label":"Total Received Amount","path":"get_total_received_amount"},
	{"param_name":"rfq_response_days","name":"RFQ Response Days","doctype":"Supplier Scorecard Variable","variable_label":"RFQ Response Days","path":"get_rfq_response_days"},
	{"param_name":"sq_total_items","name":"SQ Total Items","doctype":"Supplier Scorecard Variable","variable_label":"SQ Total Items","path":"get_sq_total_items"},
	{"param_name":"sq_total_number","name":"SQ Total Number","doctype":"Supplier Scorecard Variable","variable_label":"SQ Total Number","path":"get_sq_total_number"},
	{"param_name":"rfq_total_number","name":"RFQ Total Number","doctype":"Supplier Scorecard Variable","variable_label":"RFQ Total Number","path":"get_rfq_total_number"},
	{"param_name":"rfq_total_items","name":"RFQ Total Items","doctype":"Supplier Scorecard Variable","variable_label":"RFQ Total Items","path":"get_rfq_total_items"},
	{"param_name":"tot_item_days","name":"Total Item Days","doctype":"Supplier Scorecard Variable","variable_label":"Total Item Days","path":"get_item_workdays"},
	{"param_name":"on_time_shipment_num","name":"# of On Time Shipments","doctype":"Supplier Scorecard Variable","variable_label":"# of On Time Shipments","path":"get_on_time_shipments"},
	{"param_name":"cost_of_delayed_shipments","name":"Cost of Delayed Shipments","doctype":"Supplier Scorecard Variable","variable_label":"Cost of Delayed Shipments","path":"get_cost_of_delayed_shipments"},
	{"param_name":"cost_of_on_time_shipments","name":"Cost of On Time Shipments","doctype":"Supplier Scorecard Variable","variable_label":"Cost of On Time Shipments","path":"get_cost_of_on_time_shipments"},
	{"param_name":"total_working_days","name":"Total Working Days","doctype":"Supplier Scorecard Variable","variable_label":"Total Working Days","path":"get_total_workdays"},
	{"param_name":"tot_cost_shipments","name":"Total Cost of Shipments","doctype":"Supplier Scorecard Variable","variable_label":"Total Cost of Shipments","path":"get_total_cost_of_shipments"},
	{"param_name":"tot_days_late","name":"Total Days Late","doctype":"Supplier Scorecard Variable","variable_label":"Total Days Late","path":"get_total_days_late"},
	{"param_name":"average_days_late","name":"Average Days Late","doctype":"Supplier Scorecard Variable","variable_label":"Average Days Late","path":"get_avg_ship_days_late"},
	{"param_name":"total_shipments","name":"Total Shipments","doctype":"Supplier Scorecard Variable","variable_label":"Total Shipments","path":"get_total_shipments"},
	{"min_grade":0.0,"name":"Very Poor","prevent_rfqs":1,"notify_supplier":0,"doctype":"Supplier Scorecard Standing","max_grade":30.0,"prevent_pos":1,"standing_color":"Red","notify_employee":0,"standing_name":"Very Poor"},
	{"min_grade":30.0,"name":"Poor","prevent_rfqs":1,"notify_supplier":0,"doctype":"Supplier Scorecard Standing","max_grade":50.0,"prevent_pos":0,"standing_color":"Red","notify_employee":0,"standing_name":"Poor"},
	{"min_grade":50.0,"name":"Average","prevent_rfqs":0,"notify_supplier":0,"doctype":"Supplier Scorecard Standing","max_grade":80.0,"prevent_pos":0,"standing_color":"Green","notify_employee":0,"standing_name":"Average"},
	{"min_grade":80.0,"name":"Excellent","prevent_rfqs":0,"notify_supplier":0,"doctype":"Supplier Scorecard Standing","max_grade":100.0,"prevent_pos":0,"standing_color":"Blue","notify_employee":0,"standing_name":"Excellent"},
	

]