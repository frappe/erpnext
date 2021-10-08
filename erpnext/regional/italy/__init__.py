# coding=utf-8

fiscal_regimes = [
    "RF01-Ordinario",
    "RF02-Contribuenti minimi (art.1, c.96-117, L. 244/07)",
    "RF04-Agricoltura e attività connesse e pesca (artt.34 e 34-bis, DPR 633/72)",
    "RF05-Vendita sali e tabacchi (art.74, c.1, DPR. 633/72)",
    "RF06-Commercio fiammiferi (art.74, c.1, DPR  633/72)",
    "RF07-Editoria (art.74, c.1, DPR  633/72)",
    "RF08-Gestione servizi telefonia pubblica (art.74, c.1, DPR 633/72)",
    "RF09-Rivendita documenti di trasporto pubblico e di sosta (art.74, c.1, DPR  633/72)",
    "RF10-Intrattenimenti, giochi e altre attività di cui alla tariffa allegata al DPR 640/72 (art.74, c.6, DPR 633/72)",
    "RF11-Agenzie viaggi e turismo (art.74-ter, DPR 633/72)",
    "RF12-Agriturismo (art.5, c.2, L. 413/91)",
    "RF13-Vendite a domicilio (art.25-bis, c.6, DPR  600/73)",
    "RF14-Rivendita beni usati, oggetti d’arte, d’antiquariato o da collezione (art.36, DL 41/95)",
    "RF15-Agenzie di vendite all’asta di oggetti d’arte, antiquariato o da collezione (art.40-bis, DL 41/95)",
    "RF16-IVA per cassa P.A. (art.6, c.5, DPR 633/72)",
    "RF17-IVA per cassa (art. 32-bis, DL 83/2012)",
    "RF18-Altro",
    "RF19-Regime forfettario (art.1, c.54-89, L. 190/2014)"
]

tax_exemption_reasons = [
    "N1-Escluse ex art. 15",
    "N2-Non Soggette",
    "N3-Non Imponibili",
    "N4-Esenti",
    "N5-Regime del margine / IVA non esposta in fattura",
    "N6-Inversione Contabile",
    "N7-IVA assolta in altro stato UE"
]

mode_of_payment_codes = [
    "MP01-Contanti",
    "MP02-Assegno",
    "MP03-Assegno circolare",
    "MP04-Contanti presso Tesoreria",
    "MP05-Bonifico",
    "MP06-Vaglia cambiario",
    "MP07-Bollettino bancario",
    "MP08-Carta di pagamento",
    "MP09-RID",
    "MP10-RID utenze",
    "MP11-RID veloce",
    "MP12-RIBA",
    "MP13-MAV",
    "MP14-Quietanza erario",
    "MP15-Giroconto su conti di contabilità speciale",
    "MP16-Domiciliazione bancaria",
    "MP17-Domiciliazione postale",
    "MP18-Bollettino di c/c postale",
    "MP19-SEPA Direct Debit",
    "MP20-SEPA Direct Debit CORE",
    "MP21-SEPA Direct Debit B2B",
    "MP22-Trattenuta su somme già riscosse"
]

vat_collectability_options = [
    "I-Immediata",
    "D-Differita",
    "S-Scissione dei Pagamenti"
]

state_codes = {'Siracusa': 'SR', 'Bologna': 'BO', 'Grosseto': 'GR', 'Caserta': 'CE', 'Alessandria': 'AL', 'Ancona': 'AN', 'Pavia': 'PV',
 'Benevento or Beneventum': 'BN', 'Modena': 'MO', 'Lodi': 'LO', 'Novara': 'NO', 'Avellino': 'AV', 'Verona': 'VR', 'Forli-Cesena': 'FC',
 'Caltanissetta': 'CL', 'Brescia': 'BS', 'Rieti': 'RI', 'Treviso': 'TV', 'Ogliastra': 'OG', 'Olbia-Tempio': 'OT', 'Bergamo': 'BG',
 'Napoli': 'NA', 'Campobasso': 'CB', 'Fermo': 'FM', 'Roma': 'RM', 'Lucca': 'LU', 'Rovigo': 'RO', 'Piacenza': 'PC', 'Monza and Brianza': 'MB',
 'La Spezia': 'SP', 'Pescara': 'PE', 'Vercelli': 'VC', 'Enna': 'EN', 'Nuoro': 'NU', 'Medio Campidano': 'MD', 'Trieste': 'TS', 'Aosta': 'AO',
 'Firenze': 'FI', 'Trapani': 'TP', 'Messina': 'ME', 'Teramo': 'TE', 'Udine': 'UD', 'Verbano-Cusio-Ossola': 'VB', 'Padua': 'PD',
 'Reggio Emilia': 'RE', 'Frosinone': 'FR', 'Taranto': 'TA', 'Catanzaro': 'CZ', 'Belluno': 'BL', 'Pordenone': 'PN', 'Viterbo': 'VT',
 'Gorizia': 'GO', 'Vatican City': 'SCV', 'Ferrara': 'FE', 'Chieti': 'CH', 'Crotone': 'KR', 'Foggia': 'FG', 'Perugia': 'PG', 'Bari': 'BA',
 'Massa-Carrara': 'MS', 'Pisa': 'PI', 'Latina': 'LT', 'Salerno': 'SA', 'Turin': 'TO', 'Lecco': 'LC', 'Lecce': 'LE', 'Pistoia': 'PT', 'Como': 'CO',
 'Barletta-Andria-Trani': 'BT', 'Mantua': 'MN', 'Ragusa': 'RG', 'Macerata': 'MC', 'Imperia': 'IM', 'Palermo': 'PA', 'Matera': 'MT', "L'Aquila": 'AQ',
 'Milano': 'MI', 'Catania': 'CT', 'Pesaro e Urbino': 'PU', 'Potenza': 'PZ', 'Republic of San Marino': 'RSM', 'Genoa': 'GE', 'Brindisi': 'BR',
 'Cagliari': 'CA', 'Siena': 'SI', 'Vibo Valentia': 'VV', 'Reggio Calabria': 'RC', 'Ascoli Piceno': 'AP', 'Carbonia-Iglesias': 'CI', 'Oristano': 'OR',
 'Asti': 'AT', 'Ravenna': 'RA', 'Vicenza': 'VI', 'Savona': 'SV', 'Biella': 'BI', 'Rimini': 'RN', 'Agrigento': 'AG', 'Prato': 'PO', 'Cuneo': 'CN',
 'Cosenza': 'CS', 'Livorno or Leghorn': 'LI', 'Sondrio': 'SO', 'Cremona': 'CR', 'Isernia': 'IS', 'Trento': 'TN', 'Terni': 'TR', 'Bolzano/Bozen': 'BZ',
 'Parma': 'PR', 'Varese': 'VA', 'Venezia': 'VE', 'Sassari': 'SS', 'Arezzo': 'AR'}
