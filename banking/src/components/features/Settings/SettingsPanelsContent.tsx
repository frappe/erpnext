import { SettingsPanel } from '@/components/ui/settings-dialog'
import { Preferences } from './Preferences'
import MatchingRules from './MatchingRules'
import KeyboardShortcuts from './KeyboardShortcuts'

const SettingsPanelsContent = () => {
	return (
		<>
			<SettingsPanel value="preferences">
				<Preferences />
			</SettingsPanel>
			<SettingsPanel value="rules">
				<MatchingRules />
			</SettingsPanel>
			<SettingsPanel value="bank-accounts" />
			<SettingsPanel value="masters" />
			<SettingsPanel value="keyboard-shortcuts">
				<KeyboardShortcuts />
			</SettingsPanel>
		</>
	)
}

export default SettingsPanelsContent
