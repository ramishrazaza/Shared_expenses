import React, { useEffect, useState } from 'react';
import Navbar from '../components/Navbar';
import { auditAPI } from '../services/api';
import { History, FileText, CheckCircle, User, AlertCircle } from 'lucide-react';

export default function AuditLog() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    auditAPI.list()
      .then(data => {
        setLogs(data);
      })
      .catch(err => {
        console.error(err);
        setError('Failed to fetch audit log trail.');
      })
      .finally(() => {
        setLoading(false);
      });
  }, []);

  return (
    <div className="min-h-screen bg-[#090d16] text-gray-200">
      <Navbar />

      <main className="max-w-4xl mx-auto px-6 pb-20">
        <div className="mb-10">
          <h1 className="text-4xl font-extrabold text-white tracking-tight flex items-center gap-3">
            <History className="w-8 h-8 text-indigo-400" />
            <span>Audit <span className="text-gradient">Trail</span></span>
          </h1>
          <p className="text-gray-400 mt-1.5 text-sm">
            Verifiable chronological log of memberships, manual adjustments, and CSV data corrections.
          </p>
        </div>

        {error && (
          <div className="mb-6 p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-300">
            {error}
          </div>
        )}

        {loading ? (
          <div className="flex flex-col items-center justify-center py-20 gap-4">
            <div className="w-10 h-10 border-4 border-indigo-500/20 border-t-indigo-500 rounded-full animate-spin"></div>
            <span className="text-gray-400">Loading audit log timeline...</span>
          </div>
        ) : logs.length === 0 ? (
          <div className="glass-panel p-10 rounded-2xl text-center text-gray-500">
            No audit records found yet. Try resolving an anomaly or adding expenses.
          </div>
        ) : (
          <div className="relative border-l border-white/10 pl-6 ml-4 space-y-8">
            {logs.map((log) => {
              const isAnomaly = log.action === 'resolve_anomaly';
              const isCommit = log.action === 'commit_batch';
              const isMember = log.action.startsWith('member_');
              return (
                <div key={log.id} className="relative">
                  {/* Timeline dot */}
                  <div className="absolute left-[-31px] top-1.5 w-[11px] h-[11px] rounded-full bg-indigo-500 border border-slate-950"></div>
                  
                  <div className="glass-panel p-5 rounded-2xl space-y-3">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <span className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded-md ${
                          isCommit
                            ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                            : isAnomaly
                            ? 'bg-indigo-500/10 text-indigo-400 border border-indigo-500/20'
                            : isMember
                            ? 'bg-purple-500/10 text-purple-400 border border-purple-500/20'
                            : 'bg-gray-500/10 text-gray-400 border border-gray-500/20'
                        }`}>
                          {log.action.replace('_', ' ')}
                        </span>
                        <span className="text-xs text-gray-500">•</span>
                        <span className="text-xs text-gray-500">{log.table_name}</span>
                      </div>
                      
                      <span className="text-xs text-gray-500">
                        {new Date(log.timestamp).toLocaleString()}
                      </span>
                    </div>

                    <div className="flex items-center gap-2 text-sm text-white font-medium">
                      <User className="w-4 h-4 text-indigo-400" />
                      <span>Action by: {log.user?.username || 'System Agent'}</span>
                    </div>

                    {/* Diff changes */}
                    {log.old_value && (
                      <div className="p-3 rounded-lg bg-red-950/10 border border-red-900/10 text-xs text-rose-300 font-mono">
                        <span className="block font-bold text-[9px] uppercase tracking-wider text-rose-400 mb-1">Before:</span>
                        <pre className="whitespace-pre-wrap">{JSON.stringify(log.old_value, null, 2)}</pre>
                      </div>
                    )}
                    {log.new_value && (
                      <div className="p-3 rounded-lg bg-emerald-950/10 border border-emerald-900/10 text-xs text-emerald-300 font-mono">
                        <span className="block font-bold text-[9px] uppercase tracking-wider text-emerald-400 mb-1">After/Created:</span>
                        <pre className="whitespace-pre-wrap">{JSON.stringify(log.new_value, null, 2)}</pre>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </main>
    </div>
  );
}
