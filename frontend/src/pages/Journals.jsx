import React, { useState, useEffect } from 'react';
import { Plus, FileText } from 'lucide-react';
import { journals, accounts } from '../services/api';

function Journals() {
  const [journalList, setJournalList] = useState([]);
  const [accountList, setAccountList] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({
    date: new Date().toISOString().split('T')[0],
    description: '',
    currency: 'ZMW',
    total_amount: 0,
    lines: [
      { account_id: '', side: 'debit', amount: 0, narration: '' },
      { account_id: '', side: 'credit', amount: 0, narration: '' },
    ],
  });

  const loadData = () => {
    Promise.all([
      journals.getAll(),
      accounts.getAll()
    ]).then(([journalsRes, accountsRes]) => {
      setJournalList(journalsRes.data);
      setAccountList(accountsRes.data);
      setLoading(false);
    }).catch(() => setLoading(false));
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await journals.create(formData);
      setShowForm(false);
      setFormData({
        date: new Date().toISOString().split('T')[0],
        description: '',
        currency: 'ZMW',
        total_amount: 0,
        lines: [
          { account_id: '', side: 'debit', amount: 0, narration: '' },
          { account_id: '', side: 'credit', amount: 0, narration: '' },
        ],
      });
      loadData();
    } catch (error) {
      alert('Failed to create journal entry');
    }
  };

  const updateLine = (index, field, value) => {
    const newLines = [...formData.lines];
    newLines[index] = { ...newLines[index], [field]: value };
    const total = newLines.reduce((sum, line) => sum + (parseFloat(line.amount) || 0), 0) / 2;
    setFormData({ ...formData, lines: newLines, total_amount: total });
  };

  if (loading) {
    return <div className="text-erik-primary">Loading...</div>;
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Journal Entries</h1>
          <p className="text-gray-400">Record financial transactions</p>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="btn-primary flex items-center"
        >
          <Plus size={20} className="mr-2" />
          New Entry
        </button>
      </div>

      {showForm && (
        <div className="card mb-6">
          <h3 className="text-xl font-semibold text-white mb-4">New Journal Entry</h3>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Date
                </label>
                <input
                  type="date"
                  required
                  className="input-field"
                  value={formData.date}
                  onChange={(e) => setFormData({ ...formData, date: e.target.value })}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Currency
                </label>
                <input
                  type="text"
                  required
                  className="input-field"
                  value={formData.currency}
                  onChange={(e) => setFormData({ ...formData, currency: e.target.value })}
                />
              </div>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Description
              </label>
              <textarea
                required
                className="input-field"
                rows="2"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              />
            </div>

            <div className="space-y-3">
              <h4 className="text-white font-medium">Journal Lines</h4>
              {formData.lines.map((line, index) => (
                <div key={index} className="grid grid-cols-4 gap-3 p-3 bg-erik-dark/30 rounded-lg">
                  <div>
                    <select
                      className="input-field text-sm"
                      value={line.account_id}
                      onChange={(e) => updateLine(index, 'account_id', e.target.value)}
                      required
                    >
                      <option value="">Select Account</option>
                      {accountList.map(acc => (
                        <option key={acc.id} value={acc.id}>
                          {acc.code} - {acc.name}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <select
                      className="input-field text-sm"
                      value={line.side}
                      onChange={(e) => updateLine(index, 'side', e.target.value)}
                    >
                      <option value="debit">Debit</option>
                      <option value="credit">Credit</option>
                    </select>
                  </div>
                  <div>
                    <input
                      type="number"
                      step="0.01"
                      className="input-field text-sm"
                      placeholder="Amount"
                      value={line.amount}
                      onChange={(e) => updateLine(index, 'amount', parseFloat(e.target.value))}
                      required
                    />
                  </div>
                  <div>
                    <input
                      type="text"
                      className="input-field text-sm"
                      placeholder="Narration"
                      value={line.narration}
                      onChange={(e) => updateLine(index, 'narration', e.target.value)}
                    />
                  </div>
                </div>
              ))}
              <div className="text-right text-white">
                Total: <span className="font-bold text-erik-primary">
                  {formData.currency} {formData.total_amount.toFixed(2)}
                </span>
              </div>
            </div>

            <div className="flex space-x-4">
              <button type="submit" className="btn-primary">
                Create Entry
              </button>
              <button
                type="button"
                onClick={() => setShowForm(false)}
                className="btn-secondary"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="card">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-erik-primary/20">
                <th className="text-left py-3 px-4 text-gray-400 font-medium">Journal #</th>
                <th className="text-left py-3 px-4 text-gray-400 font-medium">Date</th>
                <th className="text-left py-3 px-4 text-gray-400 font-medium">Description</th>
                <th className="text-right py-3 px-4 text-gray-400 font-medium">Amount</th>
                <th className="text-left py-3 px-4 text-gray-400 font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              {journalList.length === 0 ? (
                <tr>
                  <td colSpan="5" className="text-center py-8 text-gray-400">
                    No journal entries yet
                  </td>
                </tr>
              ) : (
                journalList.map((journal) => (
                  <tr key={journal.id} className="border-b border-erik-primary/10 hover:bg-erik-dark/30">
                    <td className="py-3 px-4 text-white font-mono">{journal.journal_number}</td>
                    <td className="py-3 px-4 text-white">{journal.date}</td>
                    <td className="py-3 px-4 text-gray-300">{journal.description}</td>
                    <td className="py-3 px-4 text-right text-white font-mono">
                      {journal.total_amount.toFixed(2)}
                    </td>
                    <td className="py-3 px-4">
                      <span className={`text-xs px-2 py-1 rounded ${
                        journal.status === 'posted'
                          ? 'bg-green-500/20 text-green-400'
                          : 'bg-yellow-500/20 text-yellow-400'
                      }`}>
                        {journal.status}
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

export default Journals;
