import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import Navbar from '../components/Navbar';
import { groupsAPI, importsAPI } from '../services/api';
import { ArrowRight, Users, TrendingUp, AlertTriangle, CheckCircle, RefreshCw, FileText } from 'lucide-react';

export default function Dashboard() {
  const [groups, setGroups] = useState([]);
  const [batches, setBatches] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchDashboardData = async () => {
    try {
      const groupsData = await groupsAPI.list();
      setGroups(groupsData);
      
      const batchesData = await importsAPI.list();
      setBatches(batchesData.slice(0, 5)); // show top 5 recent batches
    } catch (err) {
      console.error(err);
      setError('Failed to fetch dashboard data.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

  return (
    <div className="min-h-screen bg-[#090d16] text-gray-200">
      <Navbar />
      
      <main className="max-w-7xl mx-auto px-6 pb-12">
        {/* Welcome Section */}
        <div className="mb-10">
          <h1 className="text-4xl font-extrabold tracking-tight text-white mb-2">
            Workspace <span className="text-gradient">Dashboard</span>
          </h1>
          <p className="text-gray-400">
            Monitor shared flatmate expenses, dynamic memberships, and review import anomaly logs.
          </p>
        </div>

        {error && (
          <div className="mb-8 p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-300">
            {error}
          </div>
        )}

        {loading ? (
          <div className="flex flex-col items-center justify-center py-20 gap-4">
            <div className="w-10 h-10 border-4 border-indigo-500/20 border-t-indigo-500 rounded-full animate-spin"></div>
            <span className="text-gray-400 text-sm">Loading workspace dashboard...</span>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            
            {/* Groups Section */}
            <div className="lg:col-span-2 space-y-6">
              <div className="flex items-center justify-between">
                <h2 className="text-2xl font-bold text-white flex items-center gap-2">
                  <Users className="w-6 h-6 text-indigo-400" />
                  <span>Expense Groups</span>
                </h2>
              </div>

              {groups.length === 0 ? (
                <div className="glass-panel p-10 rounded-2xl text-center space-y-4">
                  <p className="text-gray-400">No active groups found in the workspace.</p>
                  <p className="text-sm text-gray-500">Run the seed command in the backend to initialize flatmates data.</p>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {groups.map((group) => (
                    <div key={group.id} className="glass-panel p-6 rounded-2xl hover:border-indigo-500/30 transition-all flex flex-col justify-between group">
                      <div>
                        <div className="flex justify-between items-start mb-4">
                          <h3 className="font-bold text-xl text-white group-hover:text-indigo-400 transition-colors">
                            {group.name}
                          </h3>
                          <span className="px-2.5 py-1 text-xs font-semibold rounded-md bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">
                            {group.base_currency}
                          </span>
                        </div>
                        <p className="text-sm text-gray-400 mb-6">
                          Dynamic group for tracking shared household utility and travel bills.
                        </p>
                      </div>

                      <Link
                        to={`/groups/${group.id}`}
                        className="w-full py-2.5 px-4 rounded-xl bg-white/5 hover:bg-indigo-600 hover:text-white text-indigo-300 font-semibold text-sm transition-all flex items-center justify-center gap-2"
                      >
                        <span>View Balances & Expenses</span>
                        <ArrowRight className="w-4 h-4" />
                      </Link>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Imports & Logs Panel */}
            <div className="space-y-6">
              <h2 className="text-2xl font-bold text-white flex items-center gap-2">
                <TrendingUp className="w-6 h-6 text-indigo-400" />
                <span>Recent CSV Imports</span>
              </h2>

              <div className="glass-panel rounded-2xl p-6 space-y-4">
                {batches.length === 0 ? (
                  <div className="text-center py-6 text-gray-400 text-sm">
                    No files imported yet. Head to the <Link to="/import" className="text-indigo-400 underline hover:text-indigo-300">Import CSV</Link> page to upload spreadsheet records.
                  </div>
                ) : (
                  <div className="divide-y divide-white/5">
                    {batches.map((batch) => (
                      <div key={batch.id} className="py-4 first:pt-0 last:pb-0 flex items-center justify-between gap-4">
                        <div className="min-w-0">
                          <p className="font-medium text-white truncate text-sm" title={batch.file_name}>
                            {batch.file_name}
                          </p>
                          <div className="flex items-center gap-2 mt-1">
                            <span className="text-xs text-gray-500">
                              {new Date(batch.created_at).toLocaleDateString()}
                            </span>
                            <span className="text-xs text-gray-500">•</span>
                            <span className="text-xs text-indigo-400 flex items-center gap-1">
                              <FileText className="w-3.5 h-3.5" />
                              {batch.anomalies_count} issues found
                            </span>
                          </div>
                        </div>
                        
                        <div>
                          {batch.status === 'completed' ? (
                            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-semibold rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                              <CheckCircle className="w-3 h-3" />
                              <span>Imported</span>
                            </span>
                          ) : (
                            <Link
                              to={`/import/batch/${batch.id}`}
                              className="inline-flex items-center gap-1.5 px-3 py-1 text-xs font-semibold rounded-full bg-amber-500/10 text-amber-400 hover:bg-amber-500/20 border border-amber-500/20 transition-all"
                            >
                              <AlertTriangle className="w-3 h-3 animate-pulse" />
                              <span>Review</span>
                            </Link>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

          </div>
        )}
      </main>
    </div>
  );
}
