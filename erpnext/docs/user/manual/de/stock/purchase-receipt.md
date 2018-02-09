# Kaufbeleg
<span class="text-muted contributed-by">Beigetragen von CWT Connector & Wire Technology GmbH</span>

Kaufbelege werden erstellt, wenn Sie Material von einem Lieferanten annehmen, normalerweise aufgrund einer Einkaufsbestellung.

Sie können Kaufbelege auch direkt annehmen (Setzen Sie hierfür "Kaufbeleg notwendig" in den Einkaufs-Einstellungen auf "Nein").

Sie können einen Kaufbeleg direkt erstellen über:

> Lagerbestand > Dokumente > Kaufbeleg > Neu

oder aus einer "übertragenen" Einkaufsbestellung heraus, in dem Sie auf die Schaltfläche "Kaufbeleg erstellen" klicken.

<img class="screenshot" alt="Kaufbeleg" src="{{docs_base_url}}/assets/img/stock/purchase-receipt.png">

### Ausschuss

Im Kaufbeleg wird erwartet, dass Sie eingeben ob das gesamte erhaltene Material eine annehmbare Qualität aufweist (für den Fall, dass eine Wareneingangsprüfung statt findet). Wenn Sie Beanstandungen haben, müssen Sie die Spalte "Menge Ausschuss" in der Tabelle der Artikel aktualisieren.

Wenn Sie aussortieren, müssen Sie ein Ausschusslager angeben, mit dem Sie angeben, wo Sie die aussortierten Artikel lagern.

### Qualitätsprüfung

Wenn für bestimmte Artikel eine Qualitätsprüfungen zwingend erforderlich sind (wenn Sie das z. B. so in den Artikelstammdaten angegeben haben), müssen Sie die Spalte Qualitätsprüfungsnummer (QA Nr) aktualisieren. Das System erlaubt Ihnen ein "Übertragen" des Kaufbelegs nur dann, wenn Sie die Qualitätsprüfungsnummer aktualisieren.

### Umwandlung von Standardmaßeinheiten

Wenn die Standardmaßeinheit der Einkaufsbestellung für einen Artikel nicht gleich derjenigen des Lagers ist, müssen Sie den Standardmaßeinheit-Umrechnungsfaktor angeben.

### Währungsumrechnung

Da sich der eingegangene Artikel auf den Wert des Lagerbestandes auswirkt, ist es wichtig den Wert des Artikels in Ihre Basiswährung umzurechnen, wenn Sie ihn in einer anderen Währung bestellt haben. Sie müssen (sofern zutreffend) einen Währungsumrechnungsfaktor eingeben.

### Steuern und Bewertung

Einige Ihrer Steuern und Gebühren können sich auf den Wert Ihres Artikels auswirken. Zum Beispiel: Eine Steuer wird möglicherweise nicht zum Wert Ihres Artikels hinzugerechnet, weil Sie beim Verkauf des Artikels die Steuer aufrechnen müssen. Aus diesem Grund sollten Sie sicher stellen, dass in der Tabelle "Steuern und Gebühren" alle Steuern für eine angemessene Bewertung korrekt eingetragen sind

### Seriennummern und Chargen

Wenn Ihr Artiel serialisiert ist oder als Charge verwaltet wird, müssen Sie die Seriennummer und die Charge in der Artikeltabelle eingeben. Sie dürfen verschiedene Seriennummern in eine Zeile eingeben (jede in ein gesondertes Feld) und Sie müssen dieselbe Anzahl an Seriennummern eingeben wie es Artikel gibt. Ebenfalls müssen Sie die Chargennummer jeweils in ein gesondertes Feld eingeben.

---

### Was passiert, wenn der Kaufbeleg "übertragen" wurde?

Für jeden Artikel wird eine Buchung im Lagerhauptbuch vorgenommen. Diese fügt dem Lager die akzeptierte Menge des Artikels zu. Wenn Sie Ausschuss haben, wird für jeden Ausschuss eine Buchung im Lagerhauptbuch erstellt. Die "Offene Menge" wird in der Einkaufsbestellung verzeichnet.

---

### Wie erhöht man den Wert eines Artikels nach Verbuchung des Kaufbelegs?

Manchmal weis man bestimmte Aufwendungen, die den Wert eines eingekauften Artikels erhöhen, erst nach einiger Zeit. Ein häufiges Beispiel ist folgendes: Wenn Sie Artikel importieren wissen Sie den Zollbetrag erst dann, wenn Ihnen der Abwicklungs-Agent eine Rechnung schickt. Wenn Sie diese Kosten den gekauften Artikeln hinzufügen wollen, müssem Sie den Einstandskosten-Assistenten benutzen. Warum Einstandskosten? Weil sie die Gebühren beinhalten, die Sie bezahlt haben, wenn die Ware in Ihren Besitz gelangt.

{next}
