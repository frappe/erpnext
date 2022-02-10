from erpnext.vehicles.vehicle_stock import VehicleStockReport


def execute(filters=None):
	return VehicleStockReport(filters).run(report_domain="Service")
