// ERPNext - web based ERP (http://erpnext.com)
// Copyright (C) 2012 Web Notes Technologies Pvt Ltd
// 
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
// 
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
// 
// You should have received a copy of the GNU General Public License
// along with this program.  If not, see <http://www.gnu.org/licenses/>.

erpnext.StockGridReport = wn.views.TreeGridReport.extend({
	get_item_warehouse: function(warehouse, item) {
		if(!this.item_warehouse[item]) this.item_warehouse[item] = {};
		if(!this.item_warehouse[item][warehouse]) this.item_warehouse[item][warehouse] = {
			balance_qty: 0.0, balance_value: 0.0, fifo_stack: []
		};
		return this.item_warehouse[item][warehouse];
	},
	
	get_value_diff: function(wh, sl, is_fifo) {			
		// value
		if(sl.qty > 0) {
			// incoming - rate is given
			var rate = sl.incoming_rate;	
			var add_qty = sl.qty;
			if(wh.balance_qty < 0) {
				// negative valuation
				// only add value of quantity if
				// the balance goes above 0
				add_qty = wh.balance_qty + sl.qty;
				if(add_qty < 0) {
					add_qty = 0;
				}
			}
			var value_diff = (rate * add_qty);
		
			if(add_qty)
				wh.fifo_stack.push([add_qty, sl.incoming_rate, sl.posting_date]);
		} else {
			// outgoing
			if(sl.serial_no) {
				var value_diff = -1 * this.get_serialized_value_diff(sl);
			} else if(is_fifo) {
				var value_diff = this.get_fifo_value_diff(wh, sl);
			} else {
				// average rate for weighted average
				var rate = (wh.balance_qty.toFixed(2) == 0.00 ? 0 : 
					flt(wh.balance_value) / flt(wh.balance_qty));
			
				// no change in value if negative qty
				if((wh.balance_qty + sl.qty).toFixed(2) >= 0.00)
					var value_diff = (rate * sl.qty);
				else 
					var value_diff = -wh.balance_value;
			}
		}

		// update balance (only needed in case of valuation)
		wh.balance_qty += sl.qty;
		wh.balance_value += value_diff;
		
		return value_diff;
	},
	get_fifo_value_diff: function(wh, sl) {
		// get exact rate from fifo stack
		var fifo_stack = (wh.fifo_stack || []).reverse();
		var fifo_value_diff = 0.0;
		var qty = -sl.qty;
	
		for(var i=0, j=fifo_stack.length; i<j; i++) {
			var batch = fifo_stack.pop();
			if(batch[0] >= qty) {
				batch[0] = batch[0] - qty;
				fifo_value_diff += (qty * batch[1]);
			
				qty = 0.0;
				if(batch[0]) {
					// batch still has qty put it back
					fifo_stack.push(batch);
				}
			
				// all qty found
				break;
			} else {
				// consume this batch fully
				fifo_value_diff += (batch[0] * batch[1]);
				qty = qty - batch[0];
			}
		}
		if(qty) {
			// msgprint("Negative values not allowed for FIFO valuation!\
			// Item " + sl.item_code.bold() + " on " + dateutil.str_to_user(sl.posting_datetime).bold() +
			// " becomes negative. Values computed will not be accurate.");
		}
	
		// reset the updated stack
		wh.fifo_stack = fifo_stack.reverse();
		return -fifo_value_diff;
	},
	
	get_serialized_value_diff: function(sl) {
		var me = this;
		
		var value_diff = 0.0;
		
		$.each(sl.serial_no.trim().split("\n"), function(i, sr) {
			if(sr) {
				value_diff += flt(me.serialized_buying_rates[sr.trim()]);
			}
		});
		
		return value_diff;
	},
	
	get_serialized_buying_rates: function() {
		var serialized_buying_rates = {};
		
		$.each(wn.report_dump.data["Stock Ledger Entry"], function(i, sle) {
			if(sle.qty > 0 && sle.serial_no) {
				$.each(sle.serial_no.trim().split("\n"), function(i, sr) {
					if(sr && sle.incoming_rate !== undefined) {
						serialized_buying_rates[sr.trim()] = flt(sle.incoming_rate);
					}
				});
			}
		});
		
		return serialized_buying_rates;
	},
});