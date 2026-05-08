import { Badge } from '@/components/ui/badge'
import { Kbd, KbdGroup } from '@/components/ui/kbd'
import { KeyboardMetaKeyIcon } from '@/components/ui/keyboard-keys'
import { SettingsPanelDescription, SettingsPanelTitle, SettingsPanelHeader, SettingsPanelContent } from '@/components/ui/settings-dialog'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import _ from '@/lib/translate'
import { ArrowRightLeftIcon, HistoryIcon, LandmarkIcon, ReceiptIcon, SaveIcon, SettingsIcon, ZapIcon } from 'lucide-react'

const Shortcuts = [
    {
        shortcut: <KbdGroup><Kbd><KeyboardMetaKeyIcon /></Kbd><Kbd>B</Kbd></KbdGroup>,
        action: {
            icon: <LandmarkIcon />,
            label: _("Bank Entry"),
            description: _("Record a bank journal entry for expenses, income or split transactions")
        }
    },
    {
        shortcut: <KbdGroup><Kbd><KeyboardMetaKeyIcon /></Kbd><Kbd>P</Kbd></KbdGroup>,
        action: {
            icon: <ReceiptIcon />,
            label: _("Record Payment"),
            description: _("Record a payment against a customer or supplier")
        }
    },
    {
        shortcut: <KbdGroup><Kbd><KeyboardMetaKeyIcon /></Kbd><Kbd>I</Kbd></KbdGroup>,
        action: {
            icon: <ArrowRightLeftIcon />,
            label: _("Transfer"),
            description: _("Record a transfer between two bank accounts")
        }
    },
    {
        shortcut: <KbdGroup><Kbd><KeyboardMetaKeyIcon /></Kbd><Kbd>R</Kbd></KbdGroup>,
        action: {
            icon: <ZapIcon />,
            label: _("Accept Matching Rule"),
            description: _("Accept the rule for the selected transaction")
        }
    },
    {
        shortcut: <KbdGroup><Kbd><KeyboardMetaKeyIcon /></Kbd><Kbd>S</Kbd></KbdGroup>,
        action: {
            icon: <SaveIcon />,
            label: _("Save"),
            description: _("Save the currently opened form")
        }
    },
    {
        shortcut: <KbdGroup><Kbd><KeyboardMetaKeyIcon /></Kbd><Kbd>Z</Kbd></KbdGroup>,
        action: {
            icon: <HistoryIcon />,
            label: _("Reconciliation History"),
            description: _("View all reconciliation actions taken in this session")
        }
    },
    {
        shortcut: <KbdGroup><Kbd><KeyboardMetaKeyIcon /></Kbd><Kbd>⇧</Kbd><Kbd>G</Kbd></KbdGroup>,
        action: {
            icon: <SettingsIcon />,
            label: _("Settings"),
            description: _("Open the settings dialog")
        }
    }
]

const KeyboardShortcuts = () => {
    return (
        <>
            <SettingsPanelHeader>
                <SettingsPanelTitle>{_("Keyboard Shortcuts")}</SettingsPanelTitle>
                <SettingsPanelDescription>{_("Get around the system quickly with keyboard shortcuts")}</SettingsPanelDescription>
            </SettingsPanelHeader>
            <SettingsPanelContent>
                <div className='flex flex-col gap-3'>
                    <p className='text-p-sm text-ink-gray-6'>
                        {_("Transaction actions work when one or more unreconciled transactions are selected.")}
                        <br />
                        {_("To select more than one transaction at a time, press and hold the shift key.")}
                    </p>
                    <Table containerClassName='dark:border-outline-gray-2'>
                        <TableHeader>
                            <TableRow>
                                <TableHead>{_("Shortcut")}</TableHead>
                                <TableHead>{_("Action")}</TableHead>
                                <TableHead>{_("Description")}</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {Shortcuts.map((shortcut) => (
                                <TableRow className='hover:bg-surface-gray-2'>
                                    <TableCell>
                                        {shortcut.shortcut}
                                    </TableCell>
                                    <TableCell>
                                        <Badge size='lg' variant='outline'>
                                            {shortcut.action.icon}
                                            {shortcut.action.label}
                                        </Badge>
                                    </TableCell>
                                    <TableCell>
                                        <p className='text-p-sm text-ink-gray-6 text-wrap'>{shortcut.action.description}</p>
                                    </TableCell>
                                </TableRow>
                            ))}
                        </TableBody>
                    </Table>
                </div>
            </SettingsPanelContent>
        </>
    )
}

export default KeyboardShortcuts