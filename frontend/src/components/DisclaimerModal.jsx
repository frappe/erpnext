import React from 'react';
import { AlertTriangle, X, Shield } from 'lucide-react';

export default function DisclaimerModal({ isOpen, onClose, onAccept, type = 'general' }) {
  if (!isOpen) return null;

  const disclaimers = {
    general: {
      title: 'Important Security Information',
      icon: Shield,
      content: (
        <div className="space-y-4 text-gray-300">
          <p className="font-semibold text-white">Welcome to ERIK ERP!</p>
          <p>Before you begin, please review these important security guidelines:</p>
          <ul className="list-disc list-inside space-y-2 ml-2">
            <li>You are responsible for maintaining the security of your account</li>
            <li>Regular data backups are essential - export your data weekly</li>
            <li>Use strong, unique passwords and enable MFA when available</li>
            <li>Review user permissions regularly</li>
            <li>AI-generated suggestions should always be verified by qualified professionals</li>
          </ul>
          <p className="text-sm text-emerald-400 mt-4">
            ✓ ERIK ERP is compliant with SOC 2, GDPR, and Zambian Data Protection Act (2021)
          </p>
        </div>
      )
    },
    ai: {
      title: 'AI Assistant Disclaimer',
      icon: AlertTriangle,
      content: (
        <div className="space-y-4 text-gray-300">
          <p className="font-semibold text-yellow-400">⚠️ Please Read Carefully</p>
          <p>ERIK's AI Assistant provides suggestions based on your data and industry best practices:</p>
          <ul className="list-disc list-inside space-y-2 ml-2">
            <li><strong>Always verify</strong> AI-generated reports and recommendations</li>
            <li><strong>Critical financial decisions</strong> should be reviewed by qualified professionals</li>
            <li><strong>AI suggestions are NOT</strong> legal, tax, or professional advice</li>
            <li><strong>You remain responsible</strong> for all business decisions</li>
          </ul>
          <div className="mt-4 p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-lg">
            <p className="text-sm text-emerald-400">
              🔒 <strong>Privacy:</strong> The AI does not access or store your data outside ERIK's secure environment. 
              All processing happens within our encrypted infrastructure.
            </p>
          </div>
        </div>
      )
    },
    backup: {
      title: 'Data Backup Reminder',
      icon: AlertTriangle,
      content: (
        <div className="space-y-4 text-gray-300">
          <p className="font-semibold text-yellow-400">⚠️ Protect Your Data</p>
          <p>We noticed you haven't exported a backup recently. Remember:</p>
          <ul className="list-disc list-inside space-y-2 ml-2">
            <li>Export backups weekly to offline storage</li>
            <li>Store backups in multiple secure locations</li>
            <li>Test backup restoration regularly</li>
            <li>Keep backups encrypted and password-protected</li>
          </ul>
          <div className="mt-4 p-3 bg-red-500/10 border border-red-500/30 rounded-lg">
            <p className="text-sm text-red-300">
              <strong>Important:</strong> While ERIK maintains redundant systems, YOU are ultimately 
              responsible for your data. Regular backups are your safety net against accidental deletion, 
              ransomware, or system failures.
            </p>
          </div>
        </div>
      )
    }
  };

  const current = disclaimers[type] || disclaimers.general;
  const Icon = current.icon;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
      <div className="bg-gradient-to-br from-slate-800 to-slate-900 rounded-xl shadow-2xl max-w-2xl w-full border border-white/10">
        <div className="p-6">
          <div className="flex items-start justify-between mb-6">
            <div className="flex items-center space-x-3">
              <div className={`p-2 rounded-lg ${type === 'ai' ? 'bg-yellow-500/20' : type === 'backup' ? 'bg-red-500/20' : 'bg-emerald-500/20'}`}>
                <Icon className={`w-6 h-6 ${type === 'ai' ? 'text-yellow-400' : type === 'backup' ? 'text-red-400' : 'text-emerald-400'}`} />
              </div>
              <h2 className="text-2xl font-bold text-white">{current.title}</h2>
            </div>
            <button
              onClick={onClose}
              className="p-2 rounded-lg hover:bg-white/10 transition-colors"
            >
              <X className="w-5 h-5 text-gray-400" />
            </button>
          </div>

          <div className="mb-6">
            {current.content}
          </div>

          <div className="flex items-center justify-end space-x-3">
            <button
              onClick={onClose}
              className="px-6 py-2 rounded-lg bg-white/10 hover:bg-white/20 text-white transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={() => {
                onAccept();
                onClose();
              }}
              className="px-6 py-2 rounded-lg bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-600 hover:to-teal-600 text-white font-semibold transition-colors"
            >
              I Understand
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
