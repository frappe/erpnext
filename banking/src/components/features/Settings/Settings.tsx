import { Button } from '@/components/ui/button'
import { Dialog, DialogTrigger } from '@/components/ui/dialog'
import {
    SettingsDialog,
    SettingsPanel,
    SettingsPanels,
    SettingsTabGroup,
    SettingsTabItem,
    SettingsTabs,
} from '@/components/ui/settings-dialog'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import _ from '@/lib/translate'
import { LandmarkIcon, ListIcon, SettingsIcon, SlidersVerticalIcon, ZapIcon } from 'lucide-react'
import { useState } from 'react'
import { Preferences } from './Preferences'
import MatchingRules from './MatchingRules'

const Settings = () => {

    const [isOpen, setIsOpen] = useState(false)

    return (
        <Dialog open={isOpen} onOpenChange={setIsOpen}>
            <Tooltip>
                <TooltipTrigger asChild>
                    <DialogTrigger asChild>
                        <Button variant={'outline'} isIconButton size='md'>
                            <SettingsIcon />
                        </Button>
                    </DialogTrigger>
                </TooltipTrigger>
                <TooltipContent>
                    {_("Settings")}
                </TooltipContent>
            </Tooltip>
            <SettingsDialog defaultValue="preferences" onClose={() => setIsOpen(false)}>
                <SettingsTabs>
                    <SettingsTabGroup header={_("Configuration")}>
                        <SettingsTabItem
                            icon={<SlidersVerticalIcon />}
                            label={_("Preferences")}
                            value="preferences"
                        />
                        <SettingsTabItem
                            icon={<ZapIcon />}
                            label={_("Matching Rules")}
                            value="rules"
                        />
                    </SettingsTabGroup>

                    <SettingsTabGroup header={_("Setup")}>
                        <SettingsTabItem
                            icon={<LandmarkIcon />}
                            label={_("Bank Accounts")}
                            value="bank-accounts"
                        />
                        <SettingsTabItem
                            icon={<ListIcon />}
                            label={_("Masters")}
                            value="masters"
                        />
                    </SettingsTabGroup>
                </SettingsTabs>

                <SettingsPanels>
                    <SettingsPanel value="preferences">
                        <Preferences />
                    </SettingsPanel>
                    <SettingsPanel value="rules">
                        <MatchingRules />
                    </SettingsPanel>
                    <SettingsPanel value="bank-accounts" />
                    <SettingsPanel value="masters" />
                </SettingsPanels>
            </SettingsDialog>
        </Dialog>
    )
}

export default Settings
