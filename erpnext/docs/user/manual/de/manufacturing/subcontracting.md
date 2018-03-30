# Fremdvergabe
<span class="text-muted contributed-by">Beigetragen von CWT Connector & Wire Technology GmbH</span>

Fremdvergabe ist eine Art Arbeitsvertrag bei dem bestimmte Arbeiten an andere Unternehmen ausgelagert werden. Das ermöglicht es mehr als eine Phase eines Projektes zum selben Zeitpunkt abzuarbeiten, was oftmals zu einer schnelleren Fertigstellung führt. Fremdvergabe von Arbeiten wird in vielen Industriebranchen praktiziert. So vergeben z. B. Hersteller, die eine Vielzahl von Produkten aus anspruchsvollen Bestandteilen erstellen, Unteraufträge zur Herstellung von Komponenten und verarbeiten diese dann in Ihren Fabrikationsanlagen.

Wenn Sie bei Ihrer Tätigkeit bestimmte Prozesse an eine Drittpartei, bei der Sie Rohmateriel einkaufen, unterbeauftragen. können Sie das über die Option "Fremdvergabe" in ERPNext nachverfolgen.

### Fremdvergabe einstellen

1. Erstellen Sie getrennte Artikel für unbearbeitete und bearbeitet Produkte. Beispiel: Wenn Sie Ihrem Lieferanten unlackierte Artikel X übergeben und Ihnen der Lieferant lackierte Produkte X zurückliefert, dann erstellen Sie zwei Artikel: "X unlackiert" und "X".
2. Erstellen Sie ein Lager für den Lieferanten, damit Sie die übergebenen Artikel nachverfolgen können (möglicherweise geben Sie ja Artikel im Wert einer Monatslieferung außer Haus).
3. Stellen Sie für den bearbeiteten Artikel  und der Artikelvorlage den Punkt "Ist Fremdvergabe" auf JA ein.

<img class="screenshot" alt="Fremdvergabe" src="{{docs_base_url}}/assets/img/manufacturing/subcontract.png">


**Schritt 1:** Erstellen Sie für den bearbeiteten Artikel eine Stückliste, die den unbearbeiteten Artikel als Unterartikel enthält. Beispiel: Wenn Sie einen Stift herstellen, wird der bearbeitete Stift mit der Stückliste benannt, wbei der Tintentank, der Knopf und andere Artikel, die in die Fertigung eingehen als Unterartikel verwaltet werden.

**Schritt 2:** Erstellen Sie für den bearbeiteten Artikel eine Kundenbestellung. Wenn Sie abspeichern, werden unter "Rohmaterial geliefert" alle unbearbeiteten Artikel aufgrund Ihrer Stückliste aktualisert.

**Schritt 3:** Erstellen Sie eine Lagerbuchung um die Rohmaterialartikel an Ihren Lieferanten zu liefern.

**Schritt 4:** Sie erhalten Ihre Artikel vom Lieferanten über den Kaufbeleg zurück. Stellen Sie sicher, dass Sie den Punkt "Verbrauchte Menge" in der Tabelle Rohmaterial ankreuzen, damit der korrekte Lagerbestand auf Seiten des Lieferanten verwaltet wird.

> Anmerkung 1: Stellen Sie sicher, dass der Preis des verarbeiteten Artikels der Preis der Bearbeitung ist (ohne den Preis des Rohmaterials).

> Anmerkung 2: ERPNext fügt zur Bewertung automatisch den Wert des Rohmaterials hinzu, wenn die fertigen Erzeugnisse in Ihrem Lager ankommen.

{next}
