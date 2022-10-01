# coding: utf-8
"""Constants used in datev.py."""

TRANSACTION_COLUMNS = [
	# All possible columns must tbe listed here, because DATEV requires them to
	# be present in the CSV.
	# ---
	# Umsatz
	"Umsatz (ohne Soll/Haben-Kz)",
	"Soll/Haben-Kennzeichen",
	"WKZ Umsatz",
	"Kurs",
	"Basis-Umsatz",
	"WKZ Basis-Umsatz",
	# Konto/Gegenkonto
	"Konto",
	"Gegenkonto (ohne BU-Schlüssel)",
	"BU-Schlüssel",
	# Datum
	"Belegdatum",
	# Rechnungs- / Belegnummer
	"Belegfeld 1",
	# z.B. Fälligkeitsdatum Format: TTMMJJ
	"Belegfeld 2",
	# Skonto-Betrag / -Abzug (Der Wert 0 ist unzulässig)
	"Skonto",
	# Beschreibung des Buchungssatzes
	"Buchungstext",
	# Mahn- / Zahl-Sperre (1 = Postensperre)
	"Postensperre",
	"Diverse Adressnummer",
	"Geschäftspartnerbank",
	"Sachverhalt",
	# Keine Mahnzinsen
	"Zinssperre",
	# Link auf den Buchungsbeleg (Programmkürzel + GUID)
	"Beleglink",
	# Beleginfo
	"Beleginfo - Art 1",
	"Beleginfo - Inhalt 1",
	"Beleginfo - Art 2",
	"Beleginfo - Inhalt 2",
	"Beleginfo - Art 3",
	"Beleginfo - Inhalt 3",
	"Beleginfo - Art 4",
	"Beleginfo - Inhalt 4",
	"Beleginfo - Art 5",
	"Beleginfo - Inhalt 5",
	"Beleginfo - Art 6",
	"Beleginfo - Inhalt 6",
	"Beleginfo - Art 7",
	"Beleginfo - Inhalt 7",
	"Beleginfo - Art 8",
	"Beleginfo - Inhalt 8",
	# Zuordnung des Geschäftsvorfalls für die Kostenrechnung
	"KOST1 - Kostenstelle",
	"KOST2 - Kostenstelle",
	"KOST-Menge",
	# USt-ID-Nummer (Beispiel: DE133546770)
	"EU-Mitgliedstaat u. USt-IdNr.",
	# Der im EU-Bestimmungsland gültige Steuersatz
	"EU-Steuersatz",
	# I = Ist-Versteuerung,
	# K = keine Umsatzsteuerrechnung
	# P = Pauschalierung (z. B. für Land- und Forstwirtschaft),
	# S = Soll-Versteuerung
	"Abw. Versteuerungsart",
	# Sachverhalte gem. § 13b Abs. 1 Satz 1 Nrn. 1.-5. UStG
	"Sachverhalt L+L",
	# Steuersatz / Funktion zum L+L-Sachverhalt (Beispiel: Wert 190 für 19%)
	"Funktionsergänzung L+L",
	# Bei Verwendung des BU-Schlüssels 49 für „andere Steuersätze“ muss der
	# steuerliche Sachverhalt mitgegeben werden
	"BU 49 Hauptfunktionstyp",
	"BU 49 Hauptfunktionsnummer",
	"BU 49 Funktionsergänzung",
	# Zusatzinformationen, besitzen den Charakter eines Notizzettels und können
	# frei erfasst werden.
	"Zusatzinformation - Art 1",
	"Zusatzinformation - Inhalt 1",
	"Zusatzinformation - Art 2",
	"Zusatzinformation - Inhalt 2",
	"Zusatzinformation - Art 3",
	"Zusatzinformation - Inhalt 3",
	"Zusatzinformation - Art 4",
	"Zusatzinformation - Inhalt 4",
	"Zusatzinformation - Art 5",
	"Zusatzinformation - Inhalt 5",
	"Zusatzinformation - Art 6",
	"Zusatzinformation - Inhalt 6",
	"Zusatzinformation - Art 7",
	"Zusatzinformation - Inhalt 7",
	"Zusatzinformation - Art 8",
	"Zusatzinformation - Inhalt 8",
	"Zusatzinformation - Art 9",
	"Zusatzinformation - Inhalt 9",
	"Zusatzinformation - Art 10",
	"Zusatzinformation - Inhalt 10",
	"Zusatzinformation - Art 11",
	"Zusatzinformation - Inhalt 11",
	"Zusatzinformation - Art 12",
	"Zusatzinformation - Inhalt 12",
	"Zusatzinformation - Art 13",
	"Zusatzinformation - Inhalt 13",
	"Zusatzinformation - Art 14",
	"Zusatzinformation - Inhalt 14",
	"Zusatzinformation - Art 15",
	"Zusatzinformation - Inhalt 15",
	"Zusatzinformation - Art 16",
	"Zusatzinformation - Inhalt 16",
	"Zusatzinformation - Art 17",
	"Zusatzinformation - Inhalt 17",
	"Zusatzinformation - Art 18",
	"Zusatzinformation - Inhalt 18",
	"Zusatzinformation - Art 19",
	"Zusatzinformation - Inhalt 19",
	"Zusatzinformation - Art 20",
	"Zusatzinformation - Inhalt 20",
	# Wirkt sich nur bei Sachverhalt mit SKR 14 Land- und Forstwirtschaft aus,
	# für andere SKR werden die Felder beim Import / Export überlesen bzw.
	# leer exportiert.
	"Stück",
	"Gewicht",
	# 1 = Lastschrift
	# 2 = Mahnung
	# 3 = Zahlung
	"Zahlweise",
	"Forderungsart",
	# JJJJ
	"Veranlagungsjahr",
	# TTMMJJJJ
	"Zugeordnete Fälligkeit",
	# 1 = Einkauf von Waren
	# 2 = Erwerb von Roh-Hilfs- und Betriebsstoffen
	"Skontotyp",
	# Allgemeine Bezeichnung, des Auftrags / Projekts.
	"Auftragsnummer",
	# AA = Angeforderte Anzahlung / Abschlagsrechnung
	# AG = Erhaltene Anzahlung (Geldeingang)
	# AV = Erhaltene Anzahlung (Verbindlichkeit)
	# SR = Schlussrechnung
	# SU = Schlussrechnung (Umbuchung)
	# SG = Schlussrechnung (Geldeingang)
	# SO = Sonstige
	"Buchungstyp",
	"USt-Schlüssel (Anzahlungen)",
	"EU-Mitgliedstaat (Anzahlungen)",
	"Sachverhalt L+L (Anzahlungen)",
	"EU-Steuersatz (Anzahlungen)",
	"Erlöskonto (Anzahlungen)",
	# Wird beim Import durch SV (Stapelverarbeitung) ersetzt.
	"Herkunft-Kz",
	# Wird von DATEV verwendet.
	"Leerfeld",
	# Format TTMMJJJJ
	"KOST-Datum",
	# Vom Zahlungsempfänger individuell vergebenes Kennzeichen eines Mandats
	# (z.B. Rechnungs- oder Kundennummer).
	"SEPA-Mandatsreferenz",
	# 1 = Skontosperre
	# 0 = Keine Skontosperre
	"Skontosperre",
	# Gesellschafter und Sonderbilanzsachverhalt
	"Gesellschaftername",
	# Amtliche Nummer aus der Feststellungserklärung
	"Beteiligtennummer",
	"Identifikationsnummer",
	"Zeichnernummer",
	# Format TTMMJJJJ
	"Postensperre bis",
	# Gesellschafter und Sonderbilanzsachverhalt
	"Bezeichnung SoBil-Sachverhalt",
	"Kennzeichen SoBil-Buchung",
	# 0 = keine Festschreibung
	# 1 = Festschreibung
	"Festschreibung",
	# Format TTMMJJJJ
	"Leistungsdatum",
	# Format TTMMJJJJ
	"Datum Zuord. Steuerperiode",
	# OPOS-Informationen, Format TTMMJJJJ
	"Fälligkeit",
	# G oder 1 = Generalumkehr
	# 0 = keine Generalumkehr
	"Generalumkehr (GU)",
	# Steuersatz für Steuerschlüssel
	"Steuersatz",
	# Beispiel: DE für Deutschland
	"Land",
]

DEBTOR_CREDITOR_COLUMNS = [
	# All possible columns must tbe listed here, because DATEV requires them to
	# be present in the CSV.
	# Columns "Leerfeld" have been replaced with "Leerfeld #" to not confuse pandas
	# ---
	"Konto",
	"Name (Adressatentyp Unternehmen)",
	"Unternehmensgegenstand",
	"Name (Adressatentyp natürl. Person)",
	"Vorname (Adressatentyp natürl. Person)",
	"Name (Adressatentyp keine Angabe)",
	"Adressatentyp",
	"Kurzbezeichnung",
	"EU-Land",
	"EU-USt-IdNr.",
	"Anrede",
	"Titel/Akad. Grad",
	"Adelstitel",
	"Namensvorsatz",
	"Adressart",
	"Straße",
	"Postfach",
	"Postleitzahl",
	"Ort",
	"Land",
	"Versandzusatz",
	"Adresszusatz",
	"Abweichende Anrede",
	"Abw. Zustellbezeichnung 1",
	"Abw. Zustellbezeichnung 2",
	"Kennz. Korrespondenzadresse",
	"Adresse gültig von",
	"Adresse gültig bis",
	"Telefon",
	"Bemerkung (Telefon)",
	"Telefon Geschäftsleitung",
	"Bemerkung (Telefon GL)",
	"E-Mail",
	"Bemerkung (E-Mail)",
	"Internet",
	"Bemerkung (Internet)",
	"Fax",
	"Bemerkung (Fax)",
	"Sonstige",
	"Bemerkung (Sonstige)",
	"Bankleitzahl 1",
	"Bankbezeichnung 1",
	"Bankkonto-Nummer 1",
	"Länderkennzeichen 1",
	"IBAN 1",
	"Leerfeld 1",
	"SWIFT-Code 1",
	"Abw. Kontoinhaber 1",
	"Kennz. Haupt-Bankverb. 1",
	"Bankverb. 1 Gültig von",
	"Bankverb. 1 Gültig bis",
	"Bankleitzahl 2",
	"Bankbezeichnung 2",
	"Bankkonto-Nummer 2",
	"Länderkennzeichen 2",
	"IBAN 2",
	"Leerfeld 2",
	"SWIFT-Code 2",
	"Abw. Kontoinhaber 2",
	"Kennz. Haupt-Bankverb. 2",
	"Bankverb. 2 gültig von",
	"Bankverb. 2 gültig bis",
	"Bankleitzahl 3",
	"Bankbezeichnung 3",
	"Bankkonto-Nummer 3",
	"Länderkennzeichen 3",
	"IBAN 3",
	"Leerfeld 3",
	"SWIFT-Code 3",
	"Abw. Kontoinhaber 3",
	"Kennz. Haupt-Bankverb. 3",
	"Bankverb. 3 gültig von",
	"Bankverb. 3 gültig bis",
	"Bankleitzahl 4",
	"Bankbezeichnung 4",
	"Bankkonto-Nummer 4",
	"Länderkennzeichen 4",
	"IBAN 4",
	"Leerfeld 4",
	"SWIFT-Code 4",
	"Abw. Kontoinhaber 4",
	"Kennz. Haupt-Bankverb. 4",
	"Bankverb. 4 Gültig von",
	"Bankverb. 4 Gültig bis",
	"Bankleitzahl 5",
	"Bankbezeichnung 5",
	"Bankkonto-Nummer 5",
	"Länderkennzeichen 5",
	"IBAN 5",
	"Leerfeld 5",
	"SWIFT-Code 5",
	"Abw. Kontoinhaber 5",
	"Kennz. Haupt-Bankverb. 5",
	"Bankverb. 5 gültig von",
	"Bankverb. 5 gültig bis",
	"Leerfeld 6",
	"Briefanrede",
	"Grußformel",
	"Kundennummer",
	"Steuernummer",
	"Sprache",
	"Ansprechpartner",
	"Vertreter",
	"Sachbearbeiter",
	"Diverse-Konto",
	"Ausgabeziel",
	"Währungssteuerung",
	"Kreditlimit (Debitor)",
	"Zahlungsbedingung",
	"Fälligkeit in Tagen (Debitor)",
	"Skonto in Prozent (Debitor)",
	"Kreditoren-Ziel 1 (Tage)",
	"Kreditoren-Skonto 1 (%)",
	"Kreditoren-Ziel 2 (Tage)",
	"Kreditoren-Skonto 2 (%)",
	"Kreditoren-Ziel 3 Brutto (Tage)",
	"Kreditoren-Ziel 4 (Tage)",
	"Kreditoren-Skonto 4 (%)",
	"Kreditoren-Ziel 5 (Tage)",
	"Kreditoren-Skonto 5 (%)",
	"Mahnung",
	"Kontoauszug",
	"Mahntext 1",
	"Mahntext 2",
	"Mahntext 3",
	"Kontoauszugstext",
	"Mahnlimit Betrag",
	"Mahnlimit %",
	"Zinsberechnung",
	"Mahnzinssatz 1",
	"Mahnzinssatz 2",
	"Mahnzinssatz 3",
	"Lastschrift",
	"Verfahren",
	"Mandantenbank",
	"Zahlungsträger",
	"Indiv. Feld 1",
	"Indiv. Feld 2",
	"Indiv. Feld 3",
	"Indiv. Feld 4",
	"Indiv. Feld 5",
	"Indiv. Feld 6",
	"Indiv. Feld 7",
	"Indiv. Feld 8",
	"Indiv. Feld 9",
	"Indiv. Feld 10",
	"Indiv. Feld 11",
	"Indiv. Feld 12",
	"Indiv. Feld 13",
	"Indiv. Feld 14",
	"Indiv. Feld 15",
	"Abweichende Anrede (Rechnungsadresse)",
	"Adressart (Rechnungsadresse)",
	"Straße (Rechnungsadresse)",
	"Postfach (Rechnungsadresse)",
	"Postleitzahl (Rechnungsadresse)",
	"Ort (Rechnungsadresse)",
	"Land (Rechnungsadresse)",
	"Versandzusatz (Rechnungsadresse)",
	"Adresszusatz (Rechnungsadresse)",
	"Abw. Zustellbezeichnung 1 (Rechnungsadresse)",
	"Abw. Zustellbezeichnung 2 (Rechnungsadresse)",
	"Adresse Gültig von (Rechnungsadresse)",
	"Adresse Gültig bis (Rechnungsadresse)",
	"Bankleitzahl 6",
	"Bankbezeichnung 6",
	"Bankkonto-Nummer 6",
	"Länderkennzeichen 6",
	"IBAN 6",
	"Leerfeld 7",
	"SWIFT-Code 6",
	"Abw. Kontoinhaber 6",
	"Kennz. Haupt-Bankverb. 6",
	"Bankverb 6 gültig von",
	"Bankverb 6 gültig bis",
	"Bankleitzahl 7",
	"Bankbezeichnung 7",
	"Bankkonto-Nummer 7",
	"Länderkennzeichen 7",
	"IBAN 7",
	"Leerfeld 8",
	"SWIFT-Code 7",
	"Abw. Kontoinhaber 7",
	"Kennz. Haupt-Bankverb. 7",
	"Bankverb 7 gültig von",
	"Bankverb 7 gültig bis",
	"Bankleitzahl 8",
	"Bankbezeichnung 8",
	"Bankkonto-Nummer 8",
	"Länderkennzeichen 8",
	"IBAN 8",
	"Leerfeld 9",
	"SWIFT-Code 8",
	"Abw. Kontoinhaber 8",
	"Kennz. Haupt-Bankverb. 8",
	"Bankverb 8 gültig von",
	"Bankverb 8 gültig bis",
	"Bankleitzahl 9",
	"Bankbezeichnung 9",
	"Bankkonto-Nummer 9",
	"Länderkennzeichen 9",
	"IBAN 9",
	"Leerfeld 10",
	"SWIFT-Code 9",
	"Abw. Kontoinhaber 9",
	"Kennz. Haupt-Bankverb. 9",
	"Bankverb 9 gültig von",
	"Bankverb 9 gültig bis",
	"Bankleitzahl 10",
	"Bankbezeichnung 10",
	"Bankkonto-Nummer 10",
	"Länderkennzeichen 10",
	"IBAN 10",
	"Leerfeld 11",
	"SWIFT-Code 10",
	"Abw. Kontoinhaber 10",
	"Kennz. Haupt-Bankverb. 10",
	"Bankverb 10 gültig von",
	"Bankverb 10 gültig bis",
	"Nummer Fremdsystem",
	"Insolvent",
	"SEPA-Mandatsreferenz 1",
	"SEPA-Mandatsreferenz 2",
	"SEPA-Mandatsreferenz 3",
	"SEPA-Mandatsreferenz 4",
	"SEPA-Mandatsreferenz 5",
	"SEPA-Mandatsreferenz 6",
	"SEPA-Mandatsreferenz 7",
	"SEPA-Mandatsreferenz 8",
	"SEPA-Mandatsreferenz 9",
	"SEPA-Mandatsreferenz 10",
	"Verknüpftes OPOS-Konto",
	"Mahnsperre bis",
	"Lastschriftsperre bis",
	"Zahlungssperre bis",
	"Gebührenberechnung",
	"Mahngebühr 1",
	"Mahngebühr 2",
	"Mahngebühr 3",
	"Pauschalberechnung",
	"Verzugspauschale 1",
	"Verzugspauschale 2",
	"Verzugspauschale 3",
	"Alternativer Suchname",
	"Status",
	"Anschrift manuell geändert (Korrespondenzadresse)",
	"Anschrift individuell (Korrespondenzadresse)",
	"Anschrift manuell geändert (Rechnungsadresse)",
	"Anschrift individuell (Rechnungsadresse)",
	"Fristberechnung bei Debitor",
	"Mahnfrist 1",
	"Mahnfrist 2",
	"Mahnfrist 3",
	"Letzte Frist",
]

ACCOUNT_NAME_COLUMNS = [
	# Account number
	"Konto",
	# Account name
	"Kontenbeschriftung",
	# Language of the account name
	# "de-DE" or "en-GB"
	"Sprach-ID",
]


class DataCategory:

	"""Field of the CSV Header."""

	DEBTORS_CREDITORS = "16"
	ACCOUNT_NAMES = "20"
	TRANSACTIONS = "21"
	POSTING_TEXT_CONSTANTS = "67"


class FormatName:

	"""Field of the CSV Header, corresponds to DataCategory."""

	DEBTORS_CREDITORS = "Debitoren/Kreditoren"
	ACCOUNT_NAMES = "Kontenbeschriftungen"
	TRANSACTIONS = "Buchungsstapel"
	POSTING_TEXT_CONSTANTS = "Buchungstextkonstanten"


class Transactions:
	DATA_CATEGORY = DataCategory.TRANSACTIONS
	FORMAT_NAME = FormatName.TRANSACTIONS
	FORMAT_VERSION = "9"
	COLUMNS = TRANSACTION_COLUMNS


class DebtorsCreditors:
	DATA_CATEGORY = DataCategory.DEBTORS_CREDITORS
	FORMAT_NAME = FormatName.DEBTORS_CREDITORS
	FORMAT_VERSION = "5"
	COLUMNS = DEBTOR_CREDITOR_COLUMNS


class AccountNames:
	DATA_CATEGORY = DataCategory.ACCOUNT_NAMES
	FORMAT_NAME = FormatName.ACCOUNT_NAMES
	FORMAT_VERSION = "2"
	COLUMNS = ACCOUNT_NAME_COLUMNS
