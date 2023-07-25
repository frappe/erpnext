/* eslint-disable */

frappe.query_reports["Simple Customer Ledger"] = {
	"filters": [
    		{
		    	"fieldname":"customer_name",
		    	"label": __("Name"),
		    	"fieldtype": "Link",
		    	'options': 'Customer',
		    	"reqd": 1
        	},
			

		{
		    	"fieldname":"from_date",
		    	"label": __("From Date"),
		    	"fieldtype": "Date",
		    	"reqd": 0
        	},
			{
		    	"fieldname":"to_date",
		    	"label": __("To Date"),
		    	"fieldtype": "Date",
		    	"reqd": 0
        	},
			{
		    	"fieldname":"show_aging",
		    	"label": __("Show Summary"),
				"fieldtype": "Check",
        	},
			
	],
	"formatter": function(value, row, column, data, default_formatter) {
	
		value = default_formatter(value, row, column, data);
		if(data && data.hasOwnProperty('voucher_no') && data.voucher_no.toUpperCase().includes('SR-')){
		    value = '<b style="color: green;">'+value+'</b>';
		}
		if(data && data.voucher_no && data.voucher_no.toUpperCase().includes('JV-')){
		    value = '<b style="color: red;">'+value+'</b>';
		}
		else if(data && data.debit > 0){
		    value = '<b style="color: blue;">'+value+'</b>';
		}
		
		return value;
	    },

}


erpnext.utils.add_dimensions('Simple Customer Ledger', 3);
