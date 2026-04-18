import { SettingsPanelTitle, SettingsPanelHeader, SettingsPanelDescription, SettingsPanelContent } from '@/components/ui/settings-dialog'
import _ from '@/lib/translate'

const MatchingRules = () => {
    return (
        <>
            <SettingsPanelHeader>
                <SettingsPanelTitle>{_("Transaction Matching Rules")}</SettingsPanelTitle>
                <SettingsPanelDescription>{_("Set up rules to automatically classify transactions. Drag and drop rules to reorder their priority.")}</SettingsPanelDescription>
            </SettingsPanelHeader>
            <SettingsPanelContent>

            </SettingsPanelContent>
        </>
    )
}

export default MatchingRules