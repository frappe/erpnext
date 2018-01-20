from fedex_config import fedex_config

class FedExController():
	""" A Higher-Level wrapper for Fedex python library
		which handles API like Shipment, Tracking, GET Rate
		& other supplementary tasks. """

	def __init__(self, args):
		self.args = args
		self.config_obj = fedex_config()

	def validate(self):
		pass