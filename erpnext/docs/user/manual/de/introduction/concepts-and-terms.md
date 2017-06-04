# Konzepte und Begriffe
<span class="text-muted contributed-by">Beigetragen von CWT Connector & Wire Technology GmbH</span>

Machen Sie sich mit der Terminologie, die verwendet wird, und mit einigen Grundbegriffen von ERPNext vertraut, bevor Sie mit der Einführung beginnen.

* * *

### Grundbegriffe

#### Firma
Bezeichnung für die Firmendatensätze, die unter ERPNext verwendet werden. In ein und derselben Installation können Sie mehrere Firmendatensätze anlegen, die alle unterschiedliche juristische Personen darstellen. Die Buchführung wird für jede Firma unterschiedlich sein, aber sie teilen sich die Datensätze zu Kunden, Lieferanten und Artikeln.

> Rechnungswesen > Einstellungen > Firma

#### Kunde
Bezeichnung eines Kunden. Ein Kunde kann eine Einzelperson oder eine Organisation sein. Sie können für jeden Kunden mehrere verschiedene Kontakte und Adressen erstellen.

> Vertrieb > Dokumente > Kunde

#### Lieferant
Bezeichnung eines Lieferanten von Waren oder Dienstleistungen. Ihr Telekommunikationsanbieter ist ein Lieferant, genauso wie Ihr Lieferant für Rohmaterial. Auch in diesem Fall kann der Lieferant eine Einzelperson oder eine Organisation sein und mehrere verschiedene Kontakte und Adressen haben.

> Einkauf > Dokumente > Lieferant

#### Artikel
Ein Produkt, ein Unterprodukt oder eine Dienstleistung, welche(s) entweder eingekauft, verkauft oder hergestellt wird, und eindeutig identifizierbar ist.

> Lagerbestand > Dokumente > Artikel

#### Konto
Ein Konto ist der Oberbegriff, unter dem Finanztransaktionen und Unternehmensvorgänge ausgeführt werden. Beispiel: "Reisekosten" ist ein Konto, Der Kunde "Zoe", der Lieferant "Mae" sind Konten. ERPNext erstellt automatisch Konten für Kunden und Lieferanten.

> Rechnungswesen > Dokumente > Kontenplan

#### Adresse
Eine Adresse bezeichnet Einzelheiten zum Sitz eines Kunden oder Lieferanten. Dies können unterschiedliche Orte sein, wie z. B. Hauptbüro, Fertigung, Lager, Ladengeschäft etc.

> Vertrieb > Dokumente > Adresse

#### Kontakt
Ein individueller Kontakt gehört zu einem Kunden oder Lieferanten oder ist gar unabhängig. Ein Kontakt beinhaltet einen Namen und Kontaktdetails wie die E-Mail-Adresse und die Telefonnummer.

> Vertrieb > Dokumente > Kontakt

#### Kommunikation
Eine Auflistung der gesamten Kommunikation mit einem Kontakt oder Lead. Alle E-Mails, die vom System versendet werden, werden dieser Liste hinzugefügt.

> Support > Dokumente > Kommunikation

#### Preisliste
Eine Preisliste ist ein Ort an dem verschiedene Preismodelle gespeichert werden können. Es handelt sich um eine Bezeichnung, die sie für einen Satz von Artikelpreisen, die als definierte Liste abgespeichert werden, vergeben.

> Vertrieb > Einstellungen > Preisliste

> Einkauf > Einstellungen > Preisliste

* * *

### Buchführung

#### Geschäftsjahr
Bezeichnet ein Geschäfts- oder Buchungsjahr. Sie können mehrere verschiedene Geschäftsjahre zur selben Zeit laufen lassen. Jedes Geschäftsjahr hat ein Startdatum und ein Enddatum und Transaktionen können nur zu dieser Periode erfasst werden. Wenn Sie ein Geschäftsjahr schliessen, werden die Schlußstände der Konten als Eröffnungsbuchungen ins nächste Jahr übertragen.

> Rechnungswesen > Einstellungen > Geschäftsjahr

#### Kostenstelle
Eine Kostenstelle entspricht einem Konto. Im Unterschied dazu gibt ihr Aufbau die Geschäftstätigkeit Ihres Unternehmens noch etwas besser wieder als ein Konto. Beispiel: Sie können in Ihrem Kontenplan Ihre Aufwände nach Typ aufteilen (z. B. Reisen, Marketing). Im Kostenstellenplan können Sie Aufwände nach Produktlinien oder Geschäftseinheiten (z. B. Onlinevertrieb, Einzelhandel, etc.) unterscheiden.

> Rechnungswesen > Einstellungen > Kostenstellenplan 

#### Journalbuchung (Buchungssatz)
Ein Dokument, welches Buchungen des Hauptbuchs beinhaltet und bei dem die Summe von Soll und Haben dieser Buchungen gleich groß ist. Sie können in ERPNext über Journalbuchungen Zahlungen, Rücksendungen, etc. verbuchen.

> Rechnungswesen > Dokumente > Journalbuchung

#### Ausgangsrechnung
Eine Rechnung über die Lieferung von Artikeln (Waren oder Dienstleistungen) an den Kunden.

> Rechnungswesen > Dokumente > Ausgangsrechnung

#### Eingangsrechnung
Eine Rechnung von einem Lieferanten über die Lieferung bestellter Artikel (Waren oder Dienstleistungen)

> Rechnungswesen > Dokumente > Eingangsrechnung

#### Währung
ERPNext erlaubt es Ihnen, Transaktionen in verschiedenen Währungen zu buchen. Es gibt aber nur eine Währung für Ihre Bilanz. Wenn Sie Ihre Rechnungen mit Zahlungen in unterschiedlichen Währungen eingeben, wird der Betrag gemäß dem angegebenen Umrechnungsfaktor in die Standardwährung umgerechnet.

> Einstellungen > Rechnungswesen > Währung

* * *

### Vertrieb

#### Kundengruppe
Eine Einteilung von Kunden, normalerweise basierend auf einem Marktsegment.

> Vertrieb > Einstellungen > Kundengruppe

#### Lead
Eine Person, die in der Zukunft ein Geschäftspartner werden könnte. Aus einem Lead können Opportunities entstehen (und daraus Verkäufe).

> CRM > Dokumente > Lead

#### Opportunity
Ein potenzieller Verkauf

> CRM > Dokumente > Opportunity

#### Kundenauftrag
Eine Mitteilung eines Kunden, mit der er die Lieferbedingungen und den Preis eines Artikels (Produkt oder Dienstleistung) akzeptiert. Auf der Basis eines Kundenauftrages werden Lieferungen, Fertigungsaufträge und Ausgangsrechnungen erstellt.

> Vertrieb > Dokumente > Kundenauftrag

#### Region
Ein geographisches Gebiet für eine Vertriebstätigkeit. Für Regionen können Sie Ziele vereinbaren und jeder Verkauf ist einer Region zugeordnet.

> Vertrieb > Einstellungen > Region

#### Vertriebspartner
Eine Drittpartei, ein Händler, ein Partnerunternehmen oder ein Handelsvertreter, welche die Produkte des Unternehmens vertreiben, normalerweise auf Provisionsbasis.

> Vertrieb > Einstellungen > Vertriebspartner

#### Vertriebsmitarbeiter
Eine Person, die mit einem Kunden Gespräche führt und Geschäfte abschliesst. Sie können für Vertriebsmitarbeiter Ziele definieren und die Vertriebsmitarbeiter bei Transaktionen mit angeben.

> Vertrieb > Einstellungen > Vertriebsmitarbeiter

* * *

### Einkauf

#### Lieferantenauftrag
Ein Vertrag, der mit einem Lieferanten geschlossen wird, um bestimmte Artikel zu vereinbarten Kosten in der richtigen Menge zum richtigen Zeitpunkt und zu den vereinbarten Bedingungen zu liefern.

> Einkauf > Dokumente > Lieferantenauftrag

#### Materialanfrage
Eine von einem Systembenutzer oder automatisch von ERPNext (basierend auf einem Mindestbestand oder einer geplanten Menge im Fertigungsplan) generierte Anfrage, um eine Menge an Artikeln zu beschaffen.

> Einkauf > Dokumente > Materialanfrage

* * *

### Lager(bestand)

#### Lager
Ein logisches Lager zu dem Lagerbuchungen erstellt werden.

> Lagerbestand > Dokumente > Lager

#### Lagerbuchung
Materialübertrag von einem Lager, in ein Lager oder zwischen mehreren Lagern.

> Lagerbestand > Dokumente > Lagerbuchung

#### Lieferschein
Eine Liste von Artikeln mit Mengenangaben für die Auslieferung an den Kunden. Ein Lieferschein reduziert die Lagermenge eines Artikels auf dem Lager, von dem er versendet wird. Ein Lieferschein wird normalerweise zu einem Kundenauftrag erstellt.

> Lagerbestand > Dokumente > Lieferschein

#### Kaufbeleg
Eine Notiz, die angibt, dass eine bestimmte Menge von Artikeln von einem Lieferanten erhalten wurde, meistens in Verbindung mit einem Lieferantenauftrag.

> Lagerbestand > Dokumente > Kaufbeleg

#### Seriennummer
Eine einmalig vergebene Nummer, die einem bestimmten einzelnen Artikel zugeordnet wird.

> Lagerbestand > Dokumente > Seriennummer

#### Charge(nnummer)
Eine Nummer, die einer Menge von einzelnen Artikeln, die beispielsweise als zusammenhängende Gruppe eingekauft oder produziert werden, zugeordnet wird.

> Lagerbestand > Dokumente > Charge

#### Lagerbuch
Eine Tabelle, in der alle Materialbewegungen von einem Lager in ein anderes erfasst werden. Das ist die Tabelle, die aktualisiert wird, wenn eine Lagerbuchung, ein Lieferschein, ein Kaufbeleg oder eine Ausgangsrechnung (POS) erstellt werden.

#### Lagerabgleich
Lageraktualisierung mehrerer verschiedener Artikel über eine Tabellendatei (CSV).

> Lagerbestand > Werkzeuge > Bestandsabgleich

#### Qualitätsprüfung
Ein Erfassungsbogen, auf dem bestimmte (qualitative) Parameter eines Artikels zur Zeit des Erhalts vom Lieferanten oder zum Zeitpunkt der Lieferung an den Kunden festgehalten werden.

> Lagerbestand > Werkzeuge > Qualitätsprüfung

#### Artikelgruppe
Eine Einteilung von Artikeln.

> Lagerbestand > Einstellungen > Artikelgruppenstruktur

* * *

### Personalwesen

#### Mitarbeiter
Datensatz einer Person, die in der Vergangenheit oder Gegenwart im Unternehmen gearbeitet hat oder arbeitet.

> Personalwesen > Dokumente > Mitarbeiter

#### Urlaubsantrag
Ein Datensatz eines genehmigten oder abgelehnten Urlaubsantrages.

> Personalwesen > Dokumente > Urlaubsantrag

#### Urlaubstyp
Eine Urlaubsart (z. B. Erkrankung, Mutterschaft, usw.)

> Personalwesen > Einstellungen > Urlaubstyp

#### Gehaltsabrechnung erstellen
Ein Werkzeug, welches Ihnen dabei hilft, mehrere verschiedene Gehaltsabrechnungen für Mitarbeiter zu erstellen.

> Rechnungswesen > Werkzeuge > Gehaltsabrechung bearbeiten

#### Gehaltsabrechnung
Ein Datensatz über das monatliche Gehalt, das an einen Mitarbeiter ausgezahlt wird.

> Rechnungswesen > Dokumente > Gehaltsabrechnung

#### Gehaltsstruktur
Eine Vorlage, in der alle Komponenten des Gehalts (Verdienstes) eines Mitarbeiters, sowie Steuern und andere soziale Abgaben enthalten sind.

> Rechnungswesen > Einstellungen > Gehaltsstruktur

#### Beurteilung
Ein Datensatz über die Leistungsfähigkeit eines Mitarbeiters zu einem bestimmten Zeitraum basierend auf bestimmten Parametern.

> Rechnungswesen > Dokumente > Bewertung

#### Bewertungsvorlage
Eine Vorlage, die alle unterschiedlichen Parameter der Leistungsfähigkeit eines Mitarbeiters und deren Gewichtung für eine bestimmte Rolle erfasst.

> Rechnungswesen > Einstellungen > Bewertungsvorlage

#### Anwesenheit
Ein Datensatz der die Anwesenheit oder Abwesenheit eines Mitarbeiters an einem bestimmten Tag widerspiegelt.

> Rechnungswesen > Dokumente > Anwesenheit

* * *

### Fertigung

#### Stücklisten
Eine Liste aller Arbeitsgänge und Artikel und deren Mengen, die benötigt wird, um einen neuen Artikel zu fertigen. Eine Stückliste wird verwendet um Einkäufe zu planen und die Produktkalkulation durchzuführen.

> Fertigung > Dokumente > Stückliste

#### Arbeitsplatz
Ein Ort, an dem ein Arbeitsgang der Stückliste durchgeführt wird. Der Arbeitsplatz wird auch verwendet um die direkten Kosten eines Produktes zu kalkulieren.

> Fertigung > Dokumente > Arbeitsplatz

#### Fertigungsauftrag
Ein Dokument, welches die Fertigung (Herstellung) eines bestimmten Produktes in einer bestimmten Menge anstösst.

> Fertigung > Dokumente > Fertigungsauftrag

#### Werkzeug zur Fertigungsplanung
Ein Werkzeug zur automatisierten Erstellung von Fertigungsaufträgen und Materialanfragen basierend auf offenen Kundenaufträgen in einem vorgegebenen Zeitraum.

> Fertigung > Werkzeuge > Werkzeug zur Fertigungsplanung

* * *

### Webseite

#### Blogeintrag
Ein kleiner Text der im Abschnitt "Blog" der Webseite erscheint, erstellt über das Webseitenmodul von ERPNext. "Blog" ist eine Kurzform von "web log".

> Webseite > Dokumente > Blogeintrag

#### Webseite
Eine Webseite mit einer eindeutigen URL (Webadresse), erstellt über ERPNext.

> Webseite > Dokumente > Webseite

* * *

### Einstellungen / Anpassung

#### Benutzerdefiniertes Feld
Ein vom Benutzer definiertes Feld auf einem Formular/in einer Tabelle.

> Einstellungen > Anpassen > Benutzerdefiniertes Feld

#### Allgemeine Einstellungen
In diesem Abschnitt stellen Sie grundlegende Voreinstellungen für verschiedene Parameter des Systems ein.

> Einstellungen > Einstellungen > Allgemeine Einstellungen

#### Druckkopf
Eine Kopfzeile, die bei einer Transaktion für den Druck eingestellt werden kann. Beispiel: Sie wollen ein Angebot mit der Überschrift "Angebot" oder "Proforma Rechnung" ausdrucken.

> Einstellungen > Druck > Druckkopf

#### Allgemeine Geschäftsbedingungen
Hier befindet sich der Text Ihrer Vertragsbedingungen.

> Einstellungen > Druck > Allgemeine Geschäftsbedingungen

#### Standardmaßeinheit
Hier wird festgelegt, in welcher Einheit ein Artikel gemessen wird. Z. B. kg, Stück, Paar, Pakete usw.

> Lagerbestand > Einstellungen > Maßeinheit


{next}
