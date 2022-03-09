frappe.ui.form.on('Sales Invoice', {
	onload: function(frm) {
		'use strict';
		const CHARCODE_A = 'A'.charCodeAt(0);
		const CHARCODE_0 = '0'.charCodeAt(0);
		const FORMAT = /^[0-9A-Z]{1,}$/;
		const FORMAT_RF = /^RF[0-9]{2}[A-Z0-9]{1,21}$/;
		const FORMAT_RF_BODY = /^[A-Z0-9]{1,21}$/;
		const FORMAT_RF_HEAD = 'RF';

		var iso7064 = {
			compute: function(rawValue) {
				const value = stringifyInput1(rawValue);
				if (!value.match(FORMAT)) {
					throw new Error('Invalid data format; expecting: \'' + FORMAT + '\', found: \'' + value + '\'');
				}
				return mod97(value);
			},
			computeWithoutCheck: function(rawValue) {
				return mod97(rawValue);
			}
		};

		function stringifyInput1(rawValue) {
			if (rawValue === null || rawValue === undefined) {
				throw new Error('Expecting \'rawValue\' of type \'string\', found: \'' + rawValue + '\'');
			}
			if (typeof rawValue !== 'string') {
				throw new Error('Expecting \'rawValue\' of type \'string\', found: \'' + (typeof rawValue) + '\'');
			}
			return rawValue;
		}

		function mod97(value) {
			var buffer = 0;
			var charCode;
			for (var i = 0; i < value.length; i += 1) {
				charCode = value.charCodeAt(i);
				buffer = charCode + (charCode >= CHARCODE_A ? buffer * 100 - CHARCODE_A + 10 : buffer * 10 - CHARCODE_0);
				if (buffer > 1000000) {
					buffer %= 97;
				}
			}
			return buffer % 97;
		}

		var iso11649 = {
			generate: function(rawValue) {
				const value = stringifyInput2(rawValue);
				if (!value.match(FORMAT_RF_BODY)) {
					throw new Error('Invalid Creditor Reference format; expecting: \'' + FORMAT_RF_BODY + '\', found: \'' + value + '\'');
				}
				return FORMAT_RF_HEAD + ('0' + (98 - iso7064.computeWithoutCheck(value + FORMAT_RF_HEAD + '00'))).slice(-2) + value;
			},
			validate: function(rawValue) {
				const value = stringifyInput2(rawValue);
				if (!value.match(FORMAT_RF)) {
					throw new Error('Invalid Creditor Reference format; expecting: \'' + FORMAT_RF + '\', found: \'' + value + '\'');
				}
				return iso7064.computeWithoutCheck(value.substring(4, value.length) + value.substring(0, 4)) === 1;
			}
		};

		function stringifyInput2(rawValue, valueName = 'rawValue') {
			if (rawValue !== null && rawValue !== undefined) {
				switch (typeof rawValue) {
					case 'string':
						return rawValue.toUpperCase().replace(/[^0-9A-Z]/g, '');
					default:
						throw new Error('Expecting ' + valueName + ' of type \'string\', found: \'' + (typeof rawValue) + '\'');
				}
			}
			throw new Error('Expecting ' + valueName + ' of type \'string\', found: \'' + rawValue + '\'');
		}
		var random = Math.floor(Math.random() * 999999999999);
		var generatorRF = iso11649.generate(`'${ random }'`);
		var generatorRFStr = generatorRF.replace(/(.{4})(?=.)/g, '$1 ');
		if (frm.is_new()) {
			frm.set_value('reference_number', generatorRFStr);
			frm.set_value('reference_number_full', generatorRF);
		}
	}
});
