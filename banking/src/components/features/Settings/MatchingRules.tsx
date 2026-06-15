import { Button } from '@/components/ui/button'
import { SettingsPanelTitle, SettingsPanelHeader, SettingsPanelDescription, SettingsPanelContent } from '@/components/ui/settings-dialog'
import _ from '@/lib/translate'
import { PlusIcon } from 'lucide-react'
import { useState } from 'react'
import RuleList, { RunRulesButton } from './Rules/RuleList'
import CreateNewRule from '../BankReconciliation/Rules/CreateNewRule'
import EditRule from '../BankReconciliation/Rules/EditRule'

const MatchingRules = () => {

    const [selectedRule, setSelectedRule] = useState<string | null>(null)
    const [isNewRule, setIsNewRule] = useState(false)


    if (isNewRule) {
        return <CreateNewRule onCreate={() => setIsNewRule(false)} />
    }

    if (selectedRule) {
        return <EditRule onClose={() => setSelectedRule(null)} ruleID={selectedRule} />
    }

    return (
        <>
            <SettingsPanelHeader
                actions={
                    <div className='flex gap-2 items-center'>
                        <RunRulesButton />
                        <Button type='button' onClick={() => setIsNewRule(true)}><PlusIcon /> {_("Add Rule")}</Button>
                    </div>
                }
            >
                <SettingsPanelTitle>{_("Transaction Matching Rules")}</SettingsPanelTitle>

                <SettingsPanelDescription>
                    {_("Set up rules to automatically classify transactions. Drag and drop rules to reorder their priority.")}
                </SettingsPanelDescription>
            </SettingsPanelHeader>
            <SettingsPanelContent>
                <RuleList setSelectedRule={setSelectedRule} />
            </SettingsPanelContent>
        </>
    )
}
export default MatchingRules
