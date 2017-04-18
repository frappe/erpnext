
	Module = Accounts
	DocType = Sales Invoice
	Standard = No
	Print Format Type = Client


	<!--
		Sample Print Format for ERPNext
		Please use at your own discretion
		For suggestions and contributions:
			https://github.com/frappe/erpnext-print-templates

		Freely usable under MIT license
	-->

	<!-- Style Settings -->
	<style>
		/*
			common style for whole page
			This should include:
			+ page size related settings
			+ font family settings
			+ line spacing settings
		*/
		@media screen {
			body {
				width: 8.3in;
			}
		}

		html, body, div, span, td {
			font-family: "Helvetica", "Arial", sans-serif;
			font-size: 12px;
		}

		body {
			padding: 10px;
			margin: auto;
			font-size: 12px;
	        line-height: 150%;
		}

		.common {
			font-family: "Helvetica", "Arial", sans-serif !important;
			font-size: 12px;
			padding: 10px 0px;
		}

		table {
			border-collapse: collapse;
			width: 100%;
			vertical-align: top;
			border-style: none !important;
		}

		table td {
			padding: 2px 0px;
			border-style: none !important;
		}
		
		table h1, h2, h3, h4, h5, h6 {
			padding: 0px;
			margin: 0px;
		}

		table.header-table td {
			vertical-align: top;
		}

		table.header-table h1 {
			text-transform: uppercase;
			color: white;
			font-size: 55px;
			font-style: italic;
		}

		table.header-table thead tr:nth-child(1) div {
			height: 24px;
			background-color: #696969;
			vertical-align: middle;
			padding: 12px 0px 0px 0px;
			width: 100%;
		}

		div.page-body table td:nth-child(6),
		div.page-body table td:nth-child(7) {
			text-align: right;
		}

		div.page-body table tr td {
			background-color: #DCDCDC !important;
		}

		div.page-body table tr:nth-child(1) td {
			background-color: #696969 !important;
			color: white !important;
		}

		table.footer-table td {
			vertical-align: top;
		}

		table.footer-table td table td:nth-child(2),
		table.footer-table td table td:nth-child(3) {
			text-align: right;
		}

		table.footer-table tfoot td {
			background-color: #696969;
			height: 10px;
		}

		.imp-details {
			background-color: #DCDCDC;
		}
	</style>


	<!-- Javascript -->
	<script>
		si_std = {
			print_item_table: function() {
				var table = print_table(
					'Sales Invoice',
					doc.name,
					'entries',
					'Sales Invoice Item',
					[// Here specify the table columns to be displayed
						'SR', 'item_name', 'description', 'qty', 'stock_uom',
						'rate', 'amount'
					],
					[// Here specify the labels of column headings
						'Sr', 'Item Name', 'Description', 'Qty',
						'UoM', 'Basic Rate', 'Amount'
					],
					[// Here specify the column widths
						'3%', '20%', '37%', '5%',
						'5%', '15%', '15%'
					],
					null,
					null,
					{
						'description' : function(data_row) {
							if(data_row.discount_percentage) {
								var to_append = '<div style="padding-left: 15px;"><i>Discount: ' + 
									data_row.discount_percentage + '% on ' + 
									format_currency(data_row.price_list_rate, doc.currency) + '</i></div>';
								if(data_row.description.indexOf(to_append)==-1) {
									return data_row.description + to_append;
								} else { return data_row.description; }
							} else {
								return data_row.description;
							}
						}
					}
				);

				// This code takes care of page breaks
				if(table.appendChild) {
					out = table.innerHTML;
				} else {
					out = '';
					for(var i=0; i < (table.length-1); i++) {
						out += table[i].innerHTML + 
							'<div style = "page-break-after: always;" \
							class = "page_break"></div>\
							<div class="page-settings"></div>';
					}
					out += table[table.length-1].innerHTML;
				}
				return out;
			},


			print_other_charges: function(parent) {
				var oc = getchildren('Sales Taxes and Charges', doc.name, 'other_charges');
				var rows = '<table width=100%>\n';
				for(var i=0; i<oc.length; i++) {
					if(!oc[i].included_in_print_rate) {
						rows +=
							'<tr>\n' +
								'\t<td>' + oc[i].description + '</td>\n' +
								'\t<td style="width: 38%; text-align: right;">' + format_currency(oc[i].tax_amount, doc.currency) + '</td>\n' +
							'</tr>\n';
					}
				}

				if(doc.discount_amount) {
					rows += '<tr>\n' + 
							'\t<td>Discount Amount</td>\n' + 
							'\t<td style="width: 38%; text-align: right;">' + format_currency(doc.discount_amount, doc.currency) + '</td>\n' + 
						'</tr>\n';
				}

				return rows + '</table>\n';
			}
		};
	</script>


	<!-- Page Layout Settings -->
	<div class='common page-header'>
		<!-- 
			Page Header will contain
				+ table 1
					+ table 1a
						- Name
						- Address
						- Contact
						- Mobile No
					+ table 1b
						- Voucher Date
						- Due Date
		-->
		<table class='header-table' cellspacing=0>
			<thead>
				<tr><td colspan=2><div><script>'<h1>' + (doc.select_print_heading || 'Invoice') + '</h1>'</script></div></td></tr>
				<tr><td colspan=2><div style="height:15px"></div></td></tr>
			</thead>
			<tbody>
				<tr>
					<td width=60%><table width=100% cellspacing=0><tbody>
						<tr>
							<td width=39%><b>Name</b></td>
							<td><script>doc.customer_name</script></td>
						</tr>
						<tr>
							<td><b>Address</b></td>
							<td><script>replace_newlines(doc.address_display)</script></td>
						</tr>
						<tr>
							<td><b>Contact</b></td>
							<td><script>doc.contact_display</script></td>
						</tr>
					</tbody></table></td>
					<td><table width=100% cellspacing=0><tbody>
						<tr class='imp-details'>
							<td><b>Invoice No.</b></td>
							<td><script>cur_frm.docname</script></td>
						</tr>
						<tr>
							<td width=40%><b>Invoice Date</b></td>
							<td><script>date.str_to_user(doc.posting_date)</script></td>
						<tr>
	                    <tr>
	        				<td width=40%><script>
	                            (doc.convert_into_recurring_invoice && doc.recurring_id)
	                            ?"<b>Invoice Period</b>"
	                            :"";
	    					</script></td>
							<td><script>
	                            (doc.convert_into_recurring_invoice && doc.recurring_id)
	                            ?(date.str_to_user(doc.invoice_period_from_date) +
	                                ' to ' + date.str_to_user(doc.invoice_period_to_date))
	                            :"";
	                        </script></td>
						<tr>
						<tr>
							<td><b>Due Date</b></td>
							<td><script>date.str_to_user(doc.due_date)</script></td>
						<tr>					
					</tbody></table></td>
				</tr>
			</tbody>
			<tfoot>
			
			</tfoot>
		</table>
	</div>
	<div class='common page-body'>
		<!-- 
			Page Body will contain
				+ table 2
					- Sales Invoice Data
		-->
		<script>si_std.print_item_table()</script>
	</div>
	<div class='common page-footer'>
		<!-- 
			Page Footer will contain
				+ table 3
					- Terms and Conditions
					- Total Rounded Amount Calculation
					- Total Rounded Amount in Words
		-->
		<table class='footer-table' width=100% cellspacing=0>
			<thead>
				
			</thead>
			<tbody>
				<tr>
					<td width=60% style='padding-right: 10px;'>
						<b>Terms, Conditions &amp; Other Information:</b><br />
						<script>doc.terms</script>
					</td>
					<td>
						<table cellspacing=0 width=100%><tbody>
							<tr>
								<td>Net Total</td>
								<td style="width: 38%; text-align: right;"><script>
									format_currency(doc.net_total_export, doc.currency)
								</script></td>
							</tr>
							<tr><td colspan=3><script>si_std.print_other_charges()</script></td></tr>
							<tr>
								<td>Grand Total</td>
								<td style="width: 38%; text-align: right;"><script>
									format_currency(doc.grand_total_export, doc.currency)
								</script></td>
							</tr>
							<tr style='font-weight: bold' class='imp-details'>
								<td>Rounded Total</td>
								<td style="width: 38%; text-align: right;"><script>
									format_currency(doc.rounded_total_export, doc.currency)
								</script></td>
							</tr>
						</tbody></table>
						<br /><b>In Words</b><br />
						<i><script>doc.in_words_export</script></i>
					</td>
				</tr>		
			</tbody>
			<tfoot>
				<tr><td colspan=2><div></div></td><tr>
			</tfoot>
		</table>
	</div>
