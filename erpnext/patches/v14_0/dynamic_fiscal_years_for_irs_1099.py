import frappe


def execute():
	# pull from_year and to_year dynamically in irs_1099 print format
	irs_1099_print_format = frappe.get_doc("Print Format", "IRS 1099 Form")
	irs_1099_print_format.html = """
		{% set from_year, to_year = doc.get_fiscal_years_for_irs_1099() %}

		<div id="copy_a" style="position: relative; top:0cm; width:17cm;height:28.0cm;">
		<table>
		<tbody>
			<tr style="height:12mm">
			<td class="tbs rbs lbs bbs" style="width:86mm" colspan="4" ; rowspan="3">PAYER'S name, street address,
				city or town, state or province, country, ZIP<br>or foreign postal code, and telephone no.<br>
				{{ company or "" }}<br>
				{{ payer_street_address or "" }}
				{{ doc.get_feed() }}
			</td>
			<td class="tbs rbs lbs bbs" style="width:35mm">1 Rents</td>
			<td class="tbs rbs lbs bbs" style="width:25mm" rowspan="2">OMB No. 1545-0115<br>
				<yone>{{ from_year }}</yone>
				<ytwo>{{ to_year }}</ytwo><br>Form 1099-MISC
			</td>
			<td class="lbs bbs" style="width:38mm" colspan="2" rowspan="2">Miscellaneous Income</td>
			</tr>
			<tr style="height:12mm">
			<td class="tbs rbs lbs bbs" style="width:35mm">2 Royalties</td>
			</tr>
			<tr style="height:9mm">
			<td class="tbs rbs lbs bbs">3 Other Income<br>{{ payments or "" }}</td>
			<td class="tbs rbs lbs bbs" colspan="2">4 Federal Income tax withheld</td>
			<td class="tbs lbs bbs" style="width:29mm" rowspan="2">Copy A<br>For<br>Internal Revenue<br>Service
				Center<br><br>File with Form 1096</td>
			</tr>
			<tr style="height:16mm">
			<td class="tbs rbs lbs bbs" style="width:43mm">PAYER'S TIN<br>{{ company_tin or "" }}</td>

			<td class="tbs rbs lbs bbs" colspan="3">RECIPIENT'S TIN<br><br>{{ tax_id or "None" }}</td>
			<td class="tbs rbs lbs bbs">Fishing boat proceeds</td>
			<td class="tbs rbs lbs bbs" colspan="2">6 Medical and health care payments</td>
			</tr>
			<tr style="height:12mm">
			<td class="tbs rbs lbs bbs" colspan="4">RECIPIENT'S name <br>{{ supplier or "" }}</td>
			<td class="tbs rbs lbs bbs">7 Nonemployee compensation<br>
			</td>
			<td class="tbs rbs lbs bbs" colspan="2">Substitute payments in lieu of dividends or interest</td>
			<td class="tbs lbs bbs" rowspan="6">For Privacy Act<br>and Paperwork<br>Reduction Act<br>Notice, see
				the<br>2018 General<br>Instructions for<br>Certain<br>Information<br>Returns.</td>
			</tr>
			<tr style="height:6mm">
			<td class="tbs rbs lbs bbs" colspan="4" rowspan="2">Street address (including apt. no.)<br>
				{{ recipient_street_address or "" }}
			</td>
			<td class="tbs rbs lbs bbs">$___________</td>
			<td class="tbs rbs lbs bbs" colspan="2">$___________</td>
			</tr>
			<tr style="height:7mm">
			<td class="tbs rbs lbs bbs" rowspan="2">9 Payer made direct sales of<br>$5,000 or more of consumer
				products<br>to a buyer<br>(recipient) for resale</td>
			<td class="tbs rbs lbs" colspan="2">10 Crop insurance proceeds</td>
			</tr>
			<tr style="height:5mm">
			<td class="tbs rbs lbs bbs" colspan="4" rowspan="2">City or town, state or province, country, and ZIP or
				foreign postal code<br>
				{{ recipient_city_state or "" }}
			</td>
			<td style="vertical-align:bottom" class=" rbs lbs bbs" colspan="2">$___________</td>
			</tr>
			<tr style="height:9mm">
			<td class="tbs rbs lbs bbs">11</td>
			<td class="tbs rbs lbs bbs" colspan=2>12</td>
			</tr>
			<tr style="height:13mm">
			<td class="tbs rbs lbs bbs" colspan="2">Account number (see instructions)</td>
			<td class="tbs rbs lbs bbs" style="width:16mm">FACTA filing<br>requirement</td>
			<td class="tbs rbs lbs bbs" style="width:14mm">2nd TIN not.</td>
			<td class="tbs rbs lbs bbs">13 Excess golden parachute payments<br>$___________</td>
			<td class="tbs rbs lbs bbs" colspan="2">14 Gross proceeds paid to an<br>attorney<br>$___________</td>
			</tr>
			<tr style="height:12mm">
			<td class="tbs rbs lbs ">15a Section 409A deferrals</td>
			<td class="tbs rbs lbs " colspan="3">15b Section 409 income</td>
			<td class="tbs rbs lbs ">16 State tax withheld</td>
			<td class="tbs rbs lbs " colspan="2">17 State/Payer's state no.</td>
			<td class="tbs lbs">18 State income</td>
			</tr>
			<tr>
			<td class="lbs rbs bbs">$</td>
			<td class="lbs rbs bbs" colspan="3">$</td>
			<td class="lbs rbs bbs tbd">$</td>
			<td class="lbs rbs bbs tbd" colspan="2"></td>
			<td class="lbs bbs tbd">$</td>
			</tr>

			<tr style="height:8mm">
			<td class="tbs" colspan="8">Form 1099-MISC Cat. No. 14425J www.irs.gov/Form1099MISC Department of the
				Treasury - Internal Revenue Service</td>
			</tr>

		</tbody>
		</table>
		</div>
		<div id="copy_1" style="position: relative; top:0cm; width:17cm;height:28.0cm;">
		<table>
		<tbody>
			<tr style="height:12mm">
			<td class="tbs rbs lbs bbs" style="width:86mm" colspan="4" ; rowspan="3">PAYER'S name, street address,
				city or town, state or province, country, ZIP<br>or foreign postal code, and telephone no.<br>
				{{ company or ""}}<b r>
				{{ payer_street_address or "" }}
			</td>
			<td class="tbs rbs lbs bbs" style="width:35mm">1 Rents</td>
			<td class="tbs rbs lbs bbs" style="width:25mm" rowspan="2">OMB No. 1545-0115<br>
				<yone>{{ from_year }}</yone>
				<ytwo>{{ to_year }}</ytwo><br>Form 1099-MISC
			</td>
			<td class="lbs bbs" style="width:38mm" colspan="2" rowspan="2">Miscellaneous Income</td>
			</tr>
			<tr style="height:12mm">
			<td class="tbs rbs lbs bbs" style="width:35mm">2 Royalties</td>
			</tr>
			<tr style="height:9mm">
			<td class="tbs rbs lbs bbs">3 Other Income<br>
				{{ payments or "" }}
			</td>
			<td class="tbs rbs lbs bbs" colspan="2">4 Federal Income tax withheld</td>
			<td class="tbs lbs bbs" style="width:29mm" rowspan="2">Copy 1<br>For State Tax<br>Department</td>
			</tr>
			<tr style="height:16mm">
			<td class="tbs rbs lbs bbs" style="width:43mm">PAYER'S TIN<br>
				{{ company_tin or "" }}
			</td>
			<td class="tbs rbs lbs bbs" colspan="3">RECIPIENT'S TIN<br>
				{{ tax_id or "" }}
			</td>
			<td class="tbs rbs lbs bbs">Fishing boat proceeds</td>
			<td class="tbs rbs lbs bbs" colspan="2">6 Medical and health care payments</td>
			</tr>
			<tr style="height:12mm">
			<td class="tbs rbs lbs bbs" colspan="4">RECIPIENT'S name</td>
			{{ supplier or "" }}
			<td class="tbs rbs lbs bbs">7 Nonemployee compensation<br>
			</td>
			<td class="tbs rbs lbs bbs" colspan="2">Substitute payments in lieu of dividends or interest</td>
			<td class="tbs lbs bbs" rowspan="6"></td>
			</tr>
			<tr style="height:6mm">
			<td class="tbs rbs lbs bbs" colspan="4" rowspan="2">Street address (including apt. no.)<br>
				{{ recipient_street_address or "" }}
			</td>
			<td class="tbs rbs lbs bbs">$___________</td>
			<td class="tbs rbs lbs bbs" colspan="2">$___________</td>
			</tr>
			<tr style="height:7mm">
			<td class="tbs rbs lbs bbs" rowspan="2">9 Payer made direct sales of<br>$5,000 or more of consumer
				products<br>to a buyer<br>(recipient) for resale</td>
			<td class="tbs rbs lbs" colspan="2">10 Crop insurance proceeds</td>
			</tr>
			<tr style="height:5mm">
			<td class="tbs rbs lbs bbs" colspan="4" rowspan="2">City or town, state or province, country, and ZIP or
				foreign postal code<br>
				{{ recipient_city_state or "" }}
			</td>
			<td style="vertical-align:bottom" class=" rbs lbs bbs" colspan="2">$___________</td>
			</tr>
			<tr style="height:9mm">
			<td class="tbs rbs lbs bbs">11</td>
			<td class="tbs rbs lbs bbs" colspan=2>12</td>
			</tr>
			<tr style="height:13mm">
			<td class="tbs rbs lbs bbs" colspan="2">Account number (see instructions)</td>
			<td class="tbs rbs lbs bbs" style="width:16mm">FACTA filing<br>requirement</td>
			<td class="tbs rbs lbs bbs" style="width:14mm">2nd TIN not.</td>
			<td class="tbs rbs lbs bbs">13 Excess golden parachute payments<br>$___________</td>
			<td class="tbs rbs lbs bbs" colspan="2">14 Gross proceeds paid to an<br>attorney<br>$___________</td>
			</tr>
			<tr style="height:12mm">
			<td class="tbs rbs lbs ">15a Section 409A deferrals</td>
			<td class="tbs rbs lbs " colspan="3">15b Section 409 income</td>
			<td class="tbs rbs lbs ">16 State tax withheld</td>
			<td class="tbs rbs lbs " colspan="2">17 State/Payer's state no.</td>
			<td class="tbs lbs">18 State income</td>
			</tr>
			<tr>
			<td class="lbs rbs bbs">$</td>
			<td class="lbs rbs bbs" colspan="3">$</td>
			<td class="lbs rbs bbs tbd">$</td>
			<td class="lbs rbs bbs tbd" colspan="2"></td>
			<td class="lbs bbs tbd">$</td>
			</tr>

			<tr style="height:8mm">
			<td class="tbs" colspan="8">Form 1099-MISC Cat. No. 14425J www.irs.gov/Form1099MISC Department of the
				Treasury - Internal Revenue Service</td>
			</tr>

		</tbody>
		</table>
		</div>
		<style>
			body {
				font-family: 'Helvetica', sans-serif;
				font-size: 5.66pt;
			}

			yone {
				font-family: 'Helvetica', sans-serif;
				font-size: 14pt;
				color: black;
				-webkit-text-fill-color: white;
				/* Will override color (regardless of order) */
				-webkit-text-stroke-width: 1px;
				-webkit-text-stroke-color: black;
			}

			ytwo {
				font-family: 'Helvetica', sans-serif;
				font-size: 14pt;
				color: black;
				-webkit-text-stroke-width: 1px;
				-webkit-text-stroke-color: black;
			}

			table,
			th,
			td {
				font-family: 'Helvetica', sans-serif;
				font-size: 5.66pt;
				border: none;
			}

			.tbs {
				border-top: 1px solid black;
			}

			.bbs {
				border-bottom: 1px solid black;
			}

			.lbs {
				border-left: 1px solid black;
			}

			.rbs {
				border-right: 1px solid black;
			}

			.allBorder {
				border-top: 1px solid black;
				border-right: 1px solid black;
				border-left: 1px solid black;
				border-bottom: 1px solid black;
			}

			.bottomBorderOnlyDashed {
				border-bottom: 1px dashed black;
			}

			.tbd {
				border-top: 1px dashed black;
			}

			.address {
				vertical-align: bottom;
			}
		</style>
	"""

	irs_1099_print_format.save()