# Copyright (c) 2013, Hash Include Solutions FZC and contributors
# For license information, please see license.txt


from perceptrons.selling.report.sales_analytics.sales_analytics import Analytics


def execute(filters=None):
	return Analytics(filters).run()
