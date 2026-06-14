import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Navbar from '../components/Navbar';
import { groupsAPI, importsAPI } from '../services/api';
import { Upload, FileText, AlertCircle, FileCheck, ArrowRight } from 'lucide-react';

export default function ImportCSV() {
  const [groups, setGroups] = useState([]);
  const [selectedGroup, setSelectedGroup] = useState('');
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    groupsAPI.list()
      .then(data => {
        setGroups(data);
        if (data.length > 0) {
          setSelectedGroup(data[0].id);
        }
      })
      .catch(err => {
        console.error(err);
        setError('Failed to fetch groups list.');
      });
  }, []);

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      setFile(e.target.files[0]);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!file || !selectedGroup) {
      setError('Please select both a group and a CSV file.');
      return;
    }

    setError('');
    setLoading(true);

    try {
      const batch = await importsAPI.upload(selectedGroup, file);
      // Redirect to the interactive Import Report page
      navigate(`/import/batch/${batch.id}`);
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.error || 'Failed to upload and parse CSV. Please make sure the format is valid.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#090d16] text-gray-200">
      <Navbar />

      <main className="max-w-3xl mx-auto px-6 pb-20">
        <div className="mb-10 text-center">
          <h1 className="text-4xl font-extrabold text-white tracking-tight mb-2">
            Import <span className="text-gradient">Transactions</span>
          </h1>
          <p className="text-gray-400">
            Upload your spreadsheet export. We will scan for errors, duplicate entries, currency issues, and membership date overlaps.
          </p>
        </div>

        {error && (
          <div className="mb-6 p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-300 flex items-start gap-3">
            <AlertCircle className="w-5 h-5 shrink-0 text-red-400" />
            <span>{error}</span>
          </div>
        )}

        <div className="glass-panel p-8 rounded-2xl shadow-xl">
          <form onSubmit={handleSubmit} className="space-y-6">
            
            {/* Select Group */}
            <div>
              <label className="block text-gray-300 text-sm font-medium mb-2" htmlFor="group-select">
                Target Expense Group
              </label>
              <select
                id="group-select"
                required
                value={selectedGroup}
                onChange={(e) => setSelectedGroup(e.target.value)}
                className="w-full px-4 py-3 bg-slate-900 border border-gray-700/50 rounded-xl text-white focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
              >
                <option value="">Select a Group</option>
                {groups.map((g) => (
                  <option key={g.id} value={g.id}>
                    {g.name} ({g.base_currency})
                  </option>
                ))}
              </select>
            </div>

            {/* Drag and Drop Area */}
            <div>
              <label className="block text-gray-300 text-sm font-medium mb-2">
                Select CSV Spreadsheet File
              </label>
              <div className="border-2 border-dashed border-gray-700/50 rounded-2xl p-8 text-center hover:border-indigo-500/50 transition-colors bg-slate-900/30 relative">
                <input
                  type="file"
                  accept=".csv"
                  required
                  onChange={handleFileChange}
                  className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                />
                
                <div className="flex flex-col items-center gap-3">
                  <div className="p-4 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                    <Upload className="w-8 h-8" />
                  </div>
                  {file ? (
                    <div>
                      <p className="font-semibold text-white text-sm">{file.name}</p>
                      <p className="text-gray-500 text-xs mt-1">{(file.size / 1024).toFixed(2)} KB</p>
                    </div>
                  ) : (
                    <div>
                      <p className="font-semibold text-white text-sm">Click to upload or drag & drop</p>
                      <p className="text-gray-500 text-xs mt-1">Accepts CSV spreadsheets containing expenses data (max 5MB)</p>
                    </div>
                  )}
                </div>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading || !file}
              className="w-full py-3 px-4 rounded-xl font-medium text-white bg-gradient-premium hover:shadow-lg hover:shadow-indigo-500/20 active:scale-[0.98] transition-all flex items-center justify-center gap-2 disabled:opacity-50 disabled:pointer-events-none"
            >
              {loading ? (
                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
              ) : (
                <>
                  <FileCheck className="w-5 h-5" />
                  <span>Dry-Run Scan CSV</span>
                </>
              )}
            </button>
          </form>
        </div>
      </main>
    </div>
  );
}
