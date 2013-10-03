# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes

# reason field

def execute():
	change_map = {
		"Lead": [
			["Lead Lost", "Lead"],
			["Not interested", "Do Not Contact"],
			["Opportunity Made", "Opportunity"],
			["Contacted", "Replied"],
			["Attempted to Contact", "Replied"],
			["Contact in Future", "Interested"],
		],
		"Opportunity": [
			["Quotation Sent", "Quotation"],
			["Order Confirmed", "Quotation"],
			["Opportunity Lost", "Lost"],
		],
		"Quotation": [
			["Order Confirmed", "Ordered"],
			["Order Lost", "Lost"]
		],
		"Support Ticket": [
			["Waiting for Customer", "Replied"],
			["To Reply", "Open"],
		]
	}	