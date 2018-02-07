# Lager
<span class="text-muted contributed-by">Beigetragen von CWT Connector & Wire Technology GmbH</span>

Ein Lager ist ein geschäftlich genutztes Gebäude zum Lagern von Waren. Lager werden von Herstellern, Importeuren, Exporteuren, Großhändlern, Transporteuren, vom Zoll, usw. genutzt. Es handelt sich normalerweise um große, flache Gebäude in Industriegebieten von Städten und Ortschaften. Meistens verfügen sie über Ladestationen um Waren auf LKWs zu verladen und sie aus LKWs zu entladen.

Um zum Bereich "Lager" zu gelangen, klicken Sie auf "Lagerbestand" und gehen Sie unter "Dokumente" auf "Lager". Sie können auch über das Modul "Einstellungen" gehen und auf "Lagerbestand" und "Lager-Einstellungen" klicken.

> Lagerbestand > Einstellungen > Lager > Neu

<img class="screenshot" alt="Lager" src="{{docs_base_url}}/assets/img/stock/warehouse.png">

In ERPNext muss jedes Lager einer festen Firma zugeordnet sein, um einen unternehmensbezogenen Lagerbestand zu erhalten. Die Lager werden mit den ihnen zugeordneten Firmenkürzeln abgespeichert. Dies erleichtert es auf einen Blick herauszufinden, welches Lager zu welcher Firma gehört.

Sie können für diese Lager Benutzereinschränkungen mit einstellen. Wenn Sie nicht möchten, dass ein bestimmter Benutzer mit einem bestimmten Lager arbeiten kann, können Sie diesen Benutzer vom Zugriff auf das Lager ausschliessen.

### Lager verschmelzen

Bei der täglichen Arbeit kommt es vor, dass fälschlicherweise doppelte Einträge erstellt werden, was zu doppelten Lagern führt. Doppelte Datensätze können zu einem einzigen Lagerort verschmolzen werden. Wählen Sie hierzu aus der Kopfmenüleiste des Systems das Menü "Datei" aus. Wählen Sie "Umbenennen" und geben Sie das richtige Lager ein, drücken Sie danach die Schaltfläche "Verschmelzen". Das System ersetzt in allen Transaktionen alle falschen Lagereinträge durch das richtige Lager. Weiterhin wird die verfügbare Menge (tatsächliche Menge, reservierte Menge, bestellte Menge, usw.) aller Artikel im doppelt vorhandenen Lager auf das richtige Lager übertragen. Löschen Sie nach dem Abschluß der Verschmelzung das doppelte Lager.

> Hinweis: ERPNext berechnet den Lagerbestand für jede mögliche Kombination aus Artikel und Lager. Aus diesem Grund können Sie sich für jeden beliebigen Artikel den Lagerbestand in einem bestimmten Lager zu einem bestimmten Datum anzeigen lassen.

{next}
