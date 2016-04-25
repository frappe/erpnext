
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
			font-family: "Arial", sans-serif;
			font-size: 12px;
		}

		body {
			padding: 10px;
			margin: auto;
			font-size: 12px;
		}

		.common {
			font-family: "Arial", sans-serif !important;
			font-size: 12px;
			padding: 0px;
		}

		table {
			width: 100% !important;
			vertical-align: top;
		}

		table td {
			padding: 2px 0px;
		}

		table, td {
			border-collapse: collapse !important;
			padding: 0px;
			margin: 0px !important;
		}
		
		table h1, h2, h3, h4, h5, h6 {
			padding: 0px;
			margin: 0px;
		}

		table.header-table td {
			vertical-align: top;
		}

		table.header-table h3 {
			color: gray;
		}

		table.header-table thead td {
			padding: 5px;
		}

		table.header-table > thead,
		table.header-table > tbody > tr > td,
		table.footer-table > tbody > tr > td {
			border: 1px solid black;
			padding: 5px;
		}

		table.footer-table > tbody,
		table.header-table > thead {
			border-bottom: 3px solid black;
		}

		table.header-table > thead {
			border-top: 3px solid black;
		}

		div.page-body table td:nth-child(6),
		div.page-body table td:nth-child(7) {
			text-align: right;
		}

		div.page-body td {
			background-color: white !important;
			border: 1px solid black !important;
		}

		table.footer-table td {
			vertical-align: top;
		}

		table.footer-table td table td:nth-child(2),
		table.footer-table td table td:nth-child(3) {
			text-align: right;
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
								'\t<td></td>\n' +
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
				<tr><td colspan=2><script>'<h1>' + (doc.select_print_heading || 'Invoice') + '</h1>'</script></td></tr>
				<tr><td colspan=2><h3><script>cur_frm.docname</script></h3></td></tr>
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
							<tr style='font-weight: bold'>
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
			
			</tfoot>
		</table>
	</div>
