import React, { useState } from 'react';
import { Shield, Lock, AlertTriangle, CheckCircle2, Database, FileDown, Key, Eye } from 'lucide-react';

export default function SecuritySettings() {
  const [showBackupReminder, setShowBackupReminder] = useState(true);

  const securityChecklist = [
    { id: 1, text: 'Enable MFA for all admin accounts', checked: false },
    { id: 2, text: 'Use strong, unique passwords (12+ characters)', checked: false },
    { id: 3, text: 'Review user roles and permissions monthly', checked: false },
    { id: 4, text: 'Export backups weekly to offline storage', checked: false },
    { id: 5, text: 'Enable session timeout (Settings > Security)', checked: false },
    { id: 6, text: 'Restrict IP access to trusted locations', checked: false },
    { id: 7, text: 'Monitor login attempts and audit logs', checked: false },
    { id: 8, text: 'Train staff on phishing awareness', checked: false },
    { id: 9, text: 'Keep integration API keys secure', checked: false },
    { id: 10, text: 'Schedule quarterly security audits', checked: false }
  ];

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-white">Security & Data Protection</h1>
        <Shield className="w-8 h-8 text-emerald-400" />
      </div>

      {/* AI Assistant Disclaimer */}
      <div className="card border-2 border-yellow-500/30 bg-yellow-500/5">
        <div className="flex items-start space-x-3">
          <AlertTriangle className="w-6 h-6 text-yellow-400 flex-shrink-0 mt-1" />
          <div className="flex-1">
            <h3 className="text-lg font-semibold text-yellow-400 mb-2">⚠️ AI ASSISTANT DISCLAIMER</h3>
            <div className="text-gray-300 space-y-2 text-sm">
              <p>ERIK's AI Assistant provides suggestions based on your data and industry best practices. However:</p>
              <ul className="list-disc list-inside space-y-1 ml-2">
                <li>Always verify AI-generated reports and recommendations</li>
                <li>Critical financial decisions should be reviewed by qualified professionals</li>
                <li>AI suggestions are not legal, tax, or professional advice</li>
                <li>You remain responsible for all business decisions</li>
              </ul>
              <p className="mt-3 font-medium text-yellow-400">
                🔒 The AI does not access or store your data outside ERIK's secure environment.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Data Security Best Practices */}
      <div className="card border-2 border-emerald-500/30">
        <div className="flex items-start space-x-3">
          <Lock className="w-6 h-6 text-emerald-400 flex-shrink-0 mt-1" />
          <div className="flex-1">
            <h3 className="text-lg font-semibold text-emerald-400 mb-3">🔒 DATA SECURITY BEST PRACTICES</h3>
            <div className="text-gray-300 space-y-2 text-sm">
              <p>ERIK implements enterprise-grade security, but you should also:</p>
              <ul className="list-disc list-inside space-y-1 ml-2 mt-2">
                <li>Regularly export and back up your data (Settings → Export Database)</li>
                <li>Store backups offline and in multiple secure locations</li>
                <li>Enable multi-factor authentication (MFA) for all users</li>
                <li>Review user access permissions quarterly</li>
                <li>Monitor audit logs for unusual activity</li>
                <li>Keep software and devices updated</li>
              </ul>
              <p className="mt-3 font-medium text-emerald-400">
                ⚠️ Remember: You are ultimately responsible for your data security.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Cybersecurity Checklist */}
      <div className="card">
        <div className="flex items-center space-x-3 mb-4">
          <CheckCircle2 className="w-6 h-6 text-emerald-400" />
          <h3 className="text-lg font-semibold text-white">🛡️ CYBERSECURITY CHECKLIST</h3>
        </div>
        
        <div className="space-y-2">
          {securityChecklist.map((item) => (
            <label key={item.id} className="flex items-center space-x-3 p-3 rounded-lg hover:bg-white/5 cursor-pointer transition-colors">
              <input 
                type="checkbox" 
                className="w-5 h-5 rounded border-gray-600 bg-gray-700 text-emerald-500 focus:ring-emerald-500 focus:ring-offset-0"
              />
              <span className="text-gray-300 text-sm">{item.text}</span>
            </label>
          ))}
        </div>

        <div className="mt-4 p-4 bg-blue-500/10 border border-blue-500/30 rounded-lg">
          <p className="text-sm text-blue-300">
            💡 <strong>Tip:</strong> Complete this checklist monthly to maintain strong security posture. 
            Consider scheduling a recurring reminder in your calendar.
          </p>
        </div>
      </div>

      {/* Data Backup Section */}
      <div className="card border-2 border-purple-500/30 bg-purple-500/5">
        <div className="flex items-start space-x-3">
          <Database className="w-6 h-6 text-purple-400 flex-shrink-0 mt-1" />
          <div className="flex-1">
            <h3 className="text-lg font-semibold text-purple-400 mb-3">💾 DATA BACKUP & RECOVERY</h3>
            <div className="text-gray-300 space-y-3 text-sm">
              <p>Regular backups are your last line of defense against data loss:</p>
              
              <div className="grid md:grid-cols-2 gap-3 mt-3">
                <div className="p-3 bg-white/5 rounded-lg">
                  <h4 className="font-semibold text-purple-300 mb-2">Backup Frequency</h4>
                  <ul className="text-xs space-y-1">
                    <li>✓ Critical data: Daily</li>
                    <li>✓ Financial records: Weekly</li>
                    <li>✓ Full system: Monthly</li>
                  </ul>
                </div>
                
                <div className="p-3 bg-white/5 rounded-lg">
                  <h4 className="font-semibold text-purple-300 mb-2">Storage Locations</h4>
                  <ul className="text-xs space-y-1">
                    <li>✓ Cloud storage (encrypted)</li>
                    <li>✓ External hard drive</li>
                    <li>✓ Offsite secure location</li>
                  </ul>
                </div>
              </div>

              <button className="mt-4 flex items-center space-x-2 px-4 py-2 bg-purple-500 hover:bg-purple-600 text-white rounded-lg transition-colors">
                <FileDown className="w-4 h-4" />
                <span>Export Database Backup</span>
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Security Features */}
      <div className="grid md:grid-cols-3 gap-4">
        <div className="card text-center">
          <Key className="w-8 h-8 text-emerald-400 mx-auto mb-3" />
          <h3 className="font-semibold text-white mb-2">Multi-Factor Auth</h3>
          <p className="text-sm text-gray-400 mb-3">Add an extra layer of security to your account</p>
          <button className="btn-secondary w-full text-sm">Enable MFA</button>
        </div>

        <div className="card text-center">
          <Eye className="w-8 h-8 text-emerald-400 mx-auto mb-3" />
          <h3 className="font-semibold text-white mb-2">Audit Logs</h3>
          <p className="text-sm text-gray-400 mb-3">Monitor all user activities and system changes</p>
          <button className="btn-secondary w-full text-sm">View Logs</button>
        </div>

        <div className="card text-center">
          <Shield className="w-8 h-8 text-emerald-400 mx-auto mb-3" />
          <h3 className="font-semibold text-white mb-2">IP Restrictions</h3>
          <p className="text-sm text-gray-400 mb-3">Limit access to trusted IP addresses</p>
          <button className="btn-secondary w-full text-sm">Configure</button>
        </div>
      </div>

      {/* Compliance Note */}
      <div className="card bg-gradient-to-r from-emerald-500/10 to-teal-500/10 border-2 border-emerald-500/30">
        <div className="text-center">
          <Shield className="w-12 h-12 text-emerald-400 mx-auto mb-3" />
          <h3 className="text-xl font-bold text-white mb-2">Enterprise-Grade Security</h3>
          <p className="text-gray-300 text-sm max-w-2xl mx-auto">
            ERIK ERP is built with security at its core. We comply with international standards including 
            SOC 2, GDPR, and Zambian Data Protection Act (2021). Your data is encrypted at rest and in transit.
          </p>
        </div>
      </div>
    </div>
  );
}
