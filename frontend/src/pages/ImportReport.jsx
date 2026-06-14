import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import Navbar from '../components/Navbar';
import { importsAPI, groupsAPI } from '../services/api';
import {
  AlertTriangle, FileText, CheckCircle2, ShieldAlert,
  ArrowRight, Check, X, Edit3, Trash2, ArrowLeftRight
} from 'lucide-react';

export default function ImportReport() {
  const { batchId } = useParams();
  const navigate = useNavigate();
  const [batch, setBatch] = useState(null);
  const [anomalies, setAnomalies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  
  // List of group members for resolution dropdowns
  const [members, setMembers] = useState([]);

  // Editor states
  const [editingAnomalyId, setEditingAnomalyId] = useState(null);
  const [editorData, setEditorData] = useState({});
  const [committing, setCommitting] = useState(false);
  const [commitResult, setCommitResult] = useState(null);

  const fetchReportData = async () => {
    try {
      setLoading(true);
      const batches = await importsAPI.list();
      const currentBatch = batches.find(b => b.id === batchId);
      setBatch(currentBatch);
      
      const anomaliesData = await importsAPI.anomalies(batchId);
      setAnomalies(anomaliesData);

      // Load flatmate members list to help with resolutions
      if (currentBatch) {
        // Find group ID. For simplicity, we seed one group.
        const groups = await groupsAPI.list();
        if (groups.length > 0) {
          const membersData = await groupsAPI.members(groups[0].id);
          setMembers(membersData);
        }
      }
    } catch (err) {
      console.error(err);
      setError('Failed to fetch import anomaly report details.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReportData();
  }, [batchId]);

  const handleIgnore = async (anomalyId) => {
    try {
      await importsAPI.resolve(batchId, anomalyId, 'ignored');
      fetchReportData(); // reload
    } catch (err) {
      console.error(err);
      alert('Failed to ignore anomaly.');
    }
  };

  const startResolve = (anomaly) => {
    setEditingAnomalyId(anomaly.id);
    // Populate editor with raw row data or existing overrides
    const raw = anomaly.raw_row_data;
    setEditorData({
      date: anomaly.resolved_data?.date || raw.date || '',
      description: anomaly.resolved_data?.description || raw.description || '',
      paid_by: anomaly.resolved_data?.paid_by || raw.paid_by || '',
      amount: anomaly.resolved_data?.amount || raw.amount || '',
      currency: anomaly.resolved_data?.currency || raw.currency || 'INR',
      split_type: anomaly.resolved_data?.split_type || raw.split_type || 'equal',
      split_with: anomaly.resolved_data?.split_with || raw.split_with || '',
      split_details: anomaly.resolved_data?.split_details || raw.split_details || '',
      exchange_rate: anomaly.resolved_data?.exchange_rate || (raw.currency?.strip?.()?.upper?.() === 'USD' ? '83.0' : '1.0')
    });
  };

  const handleSaveResolution = async (anomalyId) => {
    try {
      await importsAPI.resolve(batchId, anomalyId, 'resolved', editorData);
      setEditingAnomalyId(null);
      fetchReportData(); // reload
    } catch (err) {
      console.error(err);
      alert('Failed to save anomaly resolution.');
    }
  };

  const handleCommit = async () => {
    if (anomalies.some(an => an.status === 'detected' && an.severity === 'critical')) {
      alert('You must resolve or ignore all Critical severity anomalies before final database commit!');
      return;
    }

    if (!confirm('Are you ready to commit the cleaned CSV transactions to the main database? Meera: "Clean up the duplicates — but I want to approve anything the app deletes or changes."')) return;

    setCommitting(true);
    setError('');
    try {
      const stats = await importsAPI.commit(batchId);
      setCommitResult(stats);
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.error || 'Failed to commit batch. Verification failed.');
    } finally {
      setCommitting(false);
    }
  };

  const getSeverityBadgeClass = (severity) => {
    switch (severity) {
      case 'critical':
        return 'bg-red-500/20 text-red-400 border-red-500/30';
      case 'high':
        return 'bg-amber-500/20 text-amber-400 border-amber-500/30';
      case 'medium':
        return 'bg-indigo-500/20 text-indigo-400 border-indigo-500/30';
      default:
        return 'bg-gray-500/20 text-gray-400 border-gray-500/30';
    }
  };

  return (
    <div className="min-h-screen bg-[#090d16] text-gray-200">
      <Navbar />

      <main className="max-w-7xl mx-auto px-6 pb-20">
        
        {/* Header */}
        <div className="mb-8 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
          <div>
            <h1 className="text-3xl font-extrabold text-white tracking-tight flex items-center gap-3">
              <FileText className="w-8 h-8 text-indigo-400" />
              <span>Import report: <span className="text-gradient">{batch?.file_name}</span></span>
            </h1>
            <p className="text-gray-400 text-sm mt-1">
              Verify detected anomalies and apply manual overrides before saving transactions.
            </p>
          </div>

          {!commitResult && (
            <button
              onClick={handleCommit}
              disabled={committing}
              className="py-3 px-6 rounded-xl font-bold text-white bg-gradient-premium hover:shadow-lg hover:shadow-indigo-500/20 active:scale-[0.98] transition-all disabled:opacity-50"
            >
              {committing ? 'Saving...' : 'Commit Data to DB'}
            </button>
          )}
        </div>

        {error && (
          <div className="mb-6 p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-300">
            {error}
          </div>
        )}

        {/* Commitment Success screen */}
        {commitResult && (
          <div className="glass-panel p-10 rounded-2xl text-center space-y-6 max-w-2xl mx-auto">
            <div className="inline-flex p-4 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 mb-2">
              <CheckCircle2 className="w-16 h-16" />
            </div>
            <h2 className="text-3xl font-bold text-white">Database Commit Successful!</h2>
            <p className="text-gray-400 text-sm">
              All resolved CSV rows have been correctly parsed, split, and saved in your expense database.
            </p>

            {/* Stats */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 py-4">
              <div className="p-4 rounded-xl bg-white/5 border border-white/5">
                <span className="block text-2xl font-extrabold text-white">{commitResult.expenses_created}</span>
                <span className="text-[10px] text-gray-500 uppercase font-semibold">Expenses Created</span>
              </div>
              <div className="p-4 rounded-xl bg-white/5 border border-white/5">
                <span className="block text-2xl font-extrabold text-white">{commitResult.settlements_created}</span>
                <span className="text-[10px] text-gray-500 uppercase font-semibold">Settlements Saved</span>
              </div>
              <div className="p-4 rounded-xl bg-white/5 border border-white/5">
                <span className="block text-2xl font-extrabold text-white">{commitResult.anomalies_resolved}</span>
                <span className="text-[10px] text-gray-500 uppercase font-semibold">Issues Resolved</span>
              </div>
              <div className="p-4 rounded-xl bg-white/5 border border-white/5">
                <span className="block text-2xl font-extrabold text-white">{commitResult.skipped_rows}</span>
                <span className="text-[10px] text-gray-500 uppercase font-semibold">Rows Skipped</span>
              </div>
            </div>

            <button
              onClick={() => navigate('/')}
              className="py-3 px-6 rounded-xl font-bold text-white bg-indigo-600 hover:bg-indigo-500 transition-colors inline-flex items-center gap-2"
            >
              <span>Back to Dashboard</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* Audit Review Table */}
        {!commitResult && loading ? (
          <div className="flex flex-col items-center justify-center py-20 gap-4">
            <div className="w-10 h-10 border-4 border-indigo-500/20 border-t-indigo-500 rounded-full animate-spin"></div>
            <span className="text-gray-400">Scanning spreadsheet for conflicts...</span>
          </div>
        ) : !commitResult && (
          <div className="space-y-6">
            
            {/* Stats summary */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="glass-panel p-5 rounded-2xl flex items-center gap-4">
                <div className="p-3 rounded-xl bg-indigo-500/10 text-indigo-400">
                  <AlertTriangle className="w-6 h-6" />
                </div>
                <div>
                  <span className="text-xs text-gray-400 block font-semibold uppercase tracking-wider">Total Scanned Issues</span>
                  <span className="text-2xl font-extrabold text-white">{anomalies.length} detected</span>
                </div>
              </div>
              
              <div className="glass-panel p-5 rounded-2xl flex items-center gap-4">
                <div className="p-3 rounded-xl bg-emerald-500/10 text-emerald-400">
                  <CheckCircle2 className="w-6 h-6" />
                </div>
                <div>
                  <span className="text-xs text-gray-400 block font-semibold uppercase tracking-wider">Resolved Conflicts</span>
                  <span className="text-2xl font-extrabold text-white">
                    {anomalies.filter(an => an.status === 'resolved').length} approved
                  </span>
                </div>
              </div>

              <div className="glass-panel p-5 rounded-2xl flex items-center gap-4">
                <div className="p-3 rounded-xl bg-rose-500/10 text-rose-400">
                  <Trash2 className="w-6 h-6" />
                </div>
                <div>
                  <span className="text-xs text-gray-400 block font-semibold uppercase tracking-wider">Rows to Ignore (Deleted)</span>
                  <span className="text-2xl font-extrabold text-white">
                    {anomalies.filter(an => an.status === 'ignored').length} skipped
                  </span>
                </div>
              </div>
            </div>

            {/* Anomalies List */}
            <div className="glass-panel rounded-2xl p-6 space-y-6">
              <h3 className="text-xl font-bold text-white">Anomaly Logs ({anomalies.filter(a => a.status === 'detected').length} Unresolved)</h3>

              {anomalies.length === 0 ? (
                <div className="p-8 text-center text-gray-500 text-sm">
                  No anomalies detected! This spreadsheet is ready for direct DB commit.
                </div>
              ) : (
                <div className="space-y-6">
                  {anomalies.map((an) => {
                    const isEditing = editingAnomalyId === an.id;
                    return (
                      <div
                        key={an.id}
                        className={`p-6 rounded-2xl border transition-all ${
                          an.status === 'ignored'
                            ? 'bg-rose-950/10 border-rose-900/20 opacity-50'
                            : an.status === 'resolved'
                            ? 'bg-emerald-950/10 border-emerald-900/20'
                            : 'bg-white/5 border-white/5 hover:border-white/10'
                        }`}
                      >
                        {/* Header of anomaly block */}
                        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-4">
                          <div className="flex items-center gap-3">
                            <span className="px-3 py-1 rounded-lg bg-white/5 border border-white/5 text-xs text-gray-400 font-mono">
                              Row {an.row_number}
                            </span>
                            <span className={`px-2.5 py-0.5 text-xs font-semibold rounded-md border capitalize ${getSeverityBadgeClass(an.severity)}`}>
                              {an.severity}
                            </span>
                            <span className="text-sm font-semibold text-white capitalize">{an.anomaly_type.replace(/_/g, ' ')}</span>
                          </div>
                          
                          {/* Actions */}
                          {an.status === 'detected' && !isEditing && (
                            <div className="flex items-center gap-2 w-full sm:w-auto">
                              <button
                                onClick={() => startResolve(an)}
                                className="flex-1 sm:flex-initial py-1.5 px-3 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-xs flex items-center justify-center gap-1.5 transition-colors"
                              >
                                <Edit3 className="w-3.5 h-3.5" />
                                <span>Resolve</span>
                              </button>
                              <button
                                onClick={() => handleIgnore(an.id)}
                                className="flex-1 sm:flex-initial py-1.5 px-3 rounded-lg bg-white/5 hover:bg-rose-500/10 border border-white/5 hover:border-rose-500/20 text-gray-400 hover:text-rose-400 font-medium text-xs flex items-center justify-center gap-1.5 transition-all"
                              >
                                <Trash2 className="w-3.5 h-3.5" />
                                <span>Ignore Row</span>
                              </button>
                            </div>
                          )}

                          {an.status !== 'detected' && !isEditing && (
                            <div className="flex items-center gap-3">
                              <span className={`text-xs font-semibold uppercase ${an.status === 'ignored' ? 'text-rose-400' : 'text-emerald-400'}`}>
                                {an.status === 'ignored' ? 'Row Ignored (Deleted)' : 'Issue Resolved'}
                              </span>
                              <button
                                onClick={() => startResolve(an)}
                                className="text-xs text-gray-500 hover:text-white underline"
                              >
                                Edit Choice
                              </button>
                            </div>
                          )}
                        </div>

                        {/* Description */}
                        <p className="text-sm text-gray-300 mb-4">{an.description}</p>

                        {/* Raw Row Values block */}
                        {!isEditing && (
                          <div className="p-4 rounded-xl bg-slate-950/40 border border-white/5 grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs font-mono text-gray-400">
                            <div>
                              <span className="block text-[10px] text-gray-600 uppercase font-bold">Date</span>
                              <span className="text-white">{an.resolved_data?.date || an.raw_row_data.date || 'N/A'}</span>
                            </div>
                            <div>
                              <span className="block text-[10px] text-gray-600 uppercase font-bold">Description</span>
                              <span className="text-white truncate block" title={an.resolved_data?.description || an.raw_row_data.description}>
                                {an.resolved_data?.description || an.raw_row_data.description || 'N/A'}
                              </span>
                            </div>
                            <div>
                              <span className="block text-[10px] text-gray-600 uppercase font-bold">Paid By</span>
                              <span className="text-white">{an.resolved_data?.paid_by || an.raw_row_data.paid_by || 'N/A'}</span>
                            </div>
                            <div>
                              <span className="block text-[10px] text-gray-600 uppercase font-bold">Amount</span>
                              <span className="text-white font-bold">
                                {an.resolved_data?.amount || an.raw_row_data.amount || 'N/A'} {an.resolved_data?.currency || an.raw_row_data.currency || 'INR'}
                              </span>
                            </div>
                          </div>
                        )}

                        {/* Inline Editor */}
                        {isEditing && (
                          <div className="p-5 rounded-xl bg-slate-900 border border-indigo-500/20 space-y-4">
                            <h4 className="font-bold text-white text-sm">Resolution Editor</h4>
                            
                            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
                              <div>
                                <label className="block text-[10px] text-gray-400 uppercase font-bold mb-1">Date</label>
                                <input
                                  type="text"
                                  value={editorData.date}
                                  onChange={(e) => setEditorData({ ...editorData, date: e.target.value })}
                                  className="w-full px-2.5 py-1.5 bg-slate-950 border border-gray-700/50 rounded-lg text-white text-xs"
                                />
                              </div>

                              <div>
                                <label className="block text-[10px] text-gray-400 uppercase font-bold mb-1">Description</label>
                                <input
                                  type="text"
                                  value={editorData.description}
                                  onChange={(e) => setEditorData({ ...editorData, description: e.target.value })}
                                  className="w-full px-2.5 py-1.5 bg-slate-950 border border-gray-700/50 rounded-lg text-white text-xs"
                                />
                              </div>

                              <div>
                                <label className="block text-[10px] text-gray-400 uppercase font-bold mb-1">Paid By (Payer)</label>
                                <select
                                  value={editorData.paid_by}
                                  onChange={(e) => setEditorData({ ...editorData, paid_by: e.target.value })}
                                  className="w-full px-2.5 py-1.5 bg-slate-950 border border-gray-700/50 rounded-lg text-white text-xs"
                                >
                                  <option value="">Select</option>
                                  {members.map(m => (
                                    <option key={m.user.id} value={m.user.username}>{m.user.username}</option>
                                  ))}
                                  {/* Also allow unknown raw value if not resolving */}
                                  {!members.some(m => m.user.username === editorData.paid_by) && editorData.paid_by && (
                                    <option value={editorData.paid_by}>{editorData.paid_by} (Raw)</option>
                                  )}
                                </select>
                              </div>

                              <div>
                                <label className="block text-[10px] text-gray-400 uppercase font-bold mb-1">Amount</label>
                                <input
                                  type="text"
                                  value={editorData.amount}
                                  onChange={(e) => setEditorData({ ...editorData, amount: e.target.value })}
                                  className="w-full px-2.5 py-1.5 bg-slate-950 border border-gray-700/50 rounded-lg text-white text-xs"
                                />
                              </div>

                              <div>
                                <label className="block text-[10px] text-gray-400 uppercase font-bold mb-1">Currency</label>
                                <input
                                  type="text"
                                  value={editorData.currency}
                                  onChange={(e) => setEditorData({ ...editorData, currency: e.target.value })}
                                  className="w-full px-2.5 py-1.5 bg-slate-950 border border-gray-700/50 rounded-lg text-white text-xs"
                                />
                              </div>

                              {editorData.currency?.toUpperCase() === 'USD' && (
                                <div>
                                  <label className="block text-[10px] text-gray-400 uppercase font-bold mb-1">Exchange Rate (USD to INR)</label>
                                  <input
                                    type="text"
                                    value={editorData.exchange_rate}
                                    onChange={(e) => setEditorData({ ...editorData, exchange_rate: e.target.value })}
                                    className="w-full px-2.5 py-1.5 bg-slate-950 border border-gray-700/50 rounded-lg text-white text-xs"
                                  />
                                </div>
                              )}

                              <div>
                                <label className="block text-[10px] text-gray-400 uppercase font-bold mb-1">Split Type</label>
                                <select
                                  value={editorData.split_type}
                                  onChange={(e) => setEditorData({ ...editorData, split_type: e.target.value })}
                                  className="w-full px-2.5 py-1.5 bg-slate-950 border border-gray-700/50 rounded-lg text-white text-xs"
                                >
                                  <option value="equal">Equal</option>
                                  <option value="unequal">Unequal</option>
                                  <option value="percentage">Percentage</option>
                                  <option value="share">Share</option>
                                  <option value="">None (Settlement)</option>
                                </select>
                              </div>

                              <div className="sm:col-span-2">
                                <label className="block text-[10px] text-gray-400 uppercase font-bold mb-1">Split With (Separated by ;)</label>
                                <input
                                  type="text"
                                  value={editorData.split_with}
                                  onChange={(e) => setEditorData({ ...editorData, split_with: e.target.value })}
                                  className="w-full px-2.5 py-1.5 bg-slate-950 border border-gray-700/50 rounded-lg text-white text-xs"
                                />
                              </div>

                              <div className="sm:col-span-2">
                                <label className="block text-[10px] text-gray-400 uppercase font-bold mb-1">Split Details (e.g. percentages or shares)</label>
                                <input
                                  type="text"
                                  value={editorData.split_details}
                                  onChange={(e) => setEditorData({ ...editorData, split_details: e.target.value })}
                                  className="w-full px-2.5 py-1.5 bg-slate-950 border border-gray-700/50 rounded-lg text-white text-xs"
                                />
                              </div>
                            </div>

                            <div className="flex items-center gap-2 justify-end pt-3">
                              <button
                                onClick={() => handleSaveResolution(an.id)}
                                className="py-1.5 px-3 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-medium text-xs flex items-center gap-1"
                              >
                                <Check className="w-3.5 h-3.5" />
                                <span>Save changes</span>
                              </button>
                              <button
                                onClick={() => setEditingAnomalyId(null)}
                                className="py-1.5 px-3 rounded-lg bg-white/5 hover:bg-white/10 text-gray-400 hover:text-white text-xs"
                              >
                                Cancel
                              </button>
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
