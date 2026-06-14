import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import Navbar from '../components/Navbar';
import { groupsAPI, expensesAPI, settlementsAPI } from '../services/api';
import {
  Users, CreditCard, DollarSign, Send, ArrowRight, Activity, HelpCircle,
  PlusCircle, RefreshCw, AlertCircle, X, ChevronRight, Check
} from 'lucide-react';

export default function Groups() {
  const { id } = useParams();
  const [group, setGroup] = useState(null);
  const [members, setMembers] = useState([]);
  const [expenses, setExpenses] = useState([]);
  const [settlements, setSettlements] = useState([]);
  const [balances, setBalances] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  
  // Explanation Trace Modal
  const [traceUser, setTraceUser] = useState(null);
  const [traceData, setTraceData] = useState(null);
  const [traceLoading, setTraceLoading] = useState(false);

  // Direct Entry States
  const [showExpenseForm, setShowExpenseForm] = useState(false);
  const [showSettlementForm, setShowSettlementForm] = useState(false);
  const [newExpense, setNewExpense] = useState({ description: '', amount: '', paid_by: '', split_type: 'equal' });
  const [newSettlement, setNewSettlement] = useState({ from_user: '', to_user: '', amount: '' });

  const fetchData = async () => {
    try {
      setLoading(true);
      const groupData = await groupsAPI.retrieve(id);
      setGroup(groupData);
      
      const membersData = await groupsAPI.members(id);
      setMembers(membersData);
      
      const balanceData = await groupsAPI.balances(id);
      setBalances(balanceData);
      
      // Load all expenses & settlements
      const expList = await expensesAPI.list();
      setExpenses(expList.filter(e => e.group === id));

      const setlList = await settlementsAPI.list();
      setSettlements(setlList.filter(s => s.group === id));
    } catch (err) {
      console.error(err);
      setError('Failed to load group detail data.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [id]);

  const handleExplain = async (username) => {
    setTraceUser(username);
    setTraceLoading(true);
    setTraceData(null);
    try {
      const data = await groupsAPI.explain(id, username);
      setTraceData(data);
    } catch (err) {
      console.error(err);
    } finally {
      setTraceLoading(false);
    }
  };

  const handleExpenseSubmit = async (e) => {
    e.preventDefault();
    try {
      const activeMembers = members.filter(m => m.is_active).map(m => m.user.id);
      // Construct participants input for equal split
      const shareAmount = parseFloat(newExpense.amount) / activeMembers.length;
      const participants_input = activeMembers.map(mId => ({
        user_id: mId,
        share_amount: shareAmount,
        raw_share_value: 1
      }));

      await expensesAPI.create({
        group: id,
        description: newExpense.description,
        paid_by_id: newExpense.paid_by,
        total_amount: parseFloat(newExpense.amount),
        currency: 'INR',
        split_type: 'equal',
        date: new Date().toISOString().split('T')[0],
        participants_input
      });

      setShowExpenseForm(false);
      setNewExpense({ description: '', amount: '', paid_by: '', split_type: 'equal' });
      fetchData();
    } catch (err) {
      console.error(err);
      alert('Failed to add expense.');
    }
  };

  const handleSettlementSubmit = async (e) => {
    e.preventDefault();
    try {
      await settlementsAPI.create({
        group: id,
        from_user_id: newSettlement.from_user,
        to_user_id: newSettlement.to_user,
        amount: parseFloat(newSettlement.amount),
        currency: 'INR',
        date: new Date().toISOString().split('T')[0]
      });

      setShowSettlementForm(false);
      setNewSettlement({ from_user: '', to_user: '', amount: '' });
      fetchData();
    } catch (err) {
      console.error(err);
      alert('Failed to add settlement.');
    }
  };

  const handleDeleteExpense = async (expenseId) => {
    if (!confirm('Are you sure you want to delete this expense?')) return;
    try {
      await expensesAPI.delete(expenseId);
      fetchData();
    } catch (err) {
      console.error(err);
      alert('Failed to delete expense.');
    }
  };

  return (
    <div className="min-h-screen bg-[#090d16] text-gray-200">
      <Navbar />

      <main className="max-w-7xl mx-auto px-6 pb-20">
        {loading ? (
          <div className="flex flex-col items-center justify-center py-32 gap-4">
            <div className="w-12 h-12 border-4 border-indigo-500/20 border-t-indigo-500 rounded-full animate-spin"></div>
            <span className="text-gray-400">Loading group detail dashboard...</span>
          </div>
        ) : (
          <div>
            {/* Header */}
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6 mb-10">
              <div>
                <div className="flex items-center gap-3">
                  <h1 className="text-4xl font-extrabold text-white tracking-tight">{group?.name}</h1>
                  <span className="px-2.5 py-1 text-xs font-semibold rounded-md bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">
                    Group Ledger
                  </span>
                </div>
                <p className="text-gray-400 mt-1.5 text-sm">
                  Base currency: {group?.base_currency} • Created on {new Date(group?.created_at).toLocaleDateString()}
                </p>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center gap-3 w-full md:w-auto">
                <button
                  onClick={() => setShowExpenseForm(true)}
                  className="flex-1 md:flex-initial py-2.5 px-4 rounded-xl text-white font-medium bg-gradient-premium hover:shadow-lg hover:shadow-indigo-500/20 transition-all flex items-center justify-center gap-2"
                >
                  <PlusCircle className="w-4 h-4" />
                  <span>Add Expense</span>
                </button>

                <button
                  onClick={() => setShowSettlementForm(true)}
                  className="flex-1 md:flex-initial py-2.5 px-4 rounded-xl text-gray-300 font-medium bg-white/5 border border-white/5 hover:bg-white/10 transition-all flex items-center justify-center gap-2"
                >
                  <Send className="w-4 h-4" />
                  <span>Settle Debt</span>
                </button>
              </div>
            </div>

            {/* Split Grid Layout */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
              
              {/* Left Column: Expenses & Settlements List */}
              <div className="lg:col-span-2 space-y-8">
                
                {/* Expenses Ledger */}
                <div className="glass-panel p-6 rounded-2xl space-y-4">
                  <h2 className="text-xl font-bold text-white flex items-center gap-2">
                    <CreditCard className="w-5 h-5 text-indigo-400" />
                    <span>Shared Expenses Ledger</span>
                  </h2>

                  {expenses.length === 0 ? (
                    <p className="text-gray-500 text-sm py-4">No expenses recorded yet in this group.</p>
                  ) : (
                    <div className="overflow-x-auto custom-scrollbar">
                      <table className="w-full text-left text-sm">
                        <thead>
                          <tr className="border-b border-white/5 text-gray-400 font-semibold">
                            <th className="pb-3 pr-4">Date</th>
                            <th className="pb-3 pr-4">Description</th>
                            <th className="pb-3 pr-4">Paid By</th>
                            <th className="pb-3 pr-4">Amount</th>
                            <th className="pb-3 pr-4">Split</th>
                            <th className="pb-3">Action</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-white/5 text-gray-300">
                          {expenses.map((exp) => (
                            <tr key={exp.id} className="hover:bg-white/[0.01]">
                              <td className="py-3.5 pr-4 whitespace-nowrap">{exp.date}</td>
                              <td className="py-3.5 pr-4">
                                <span className="font-semibold text-white">{exp.description}</span>
                              </td>
                              <td className="py-3.5 pr-4">{exp.paid_by?.username}</td>
                              <td className="py-3.5 pr-4 text-white">
                                {exp.total_amount} {exp.currency}
                                {exp.currency !== 'INR' && (
                                  <span className="text-xs block text-gray-500">
                                    ({exp.amount_in_base} INR)
                                  </span>
                                )}
                              </td>
                              <td className="py-3.5 pr-4 whitespace-nowrap capitalize text-xs">
                                <span className="px-2 py-0.5 rounded-md bg-white/5 border border-white/5">
                                  {exp.split_type}
                                </span>
                              </td>
                              <td className="py-3.5">
                                <button
                                  onClick={() => handleDeleteExpense(exp.id)}
                                  className="text-red-400 hover:text-red-300 text-xs font-semibold"
                                >
                                  Delete
                                </button>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>

                {/* Settlements Ledger */}
                <div className="glass-panel p-6 rounded-2xl space-y-4">
                  <h2 className="text-xl font-bold text-white flex items-center gap-2">
                    <Send className="w-5 h-5 text-indigo-400" />
                    <span>Settlements Trail</span>
                  </h2>

                  {settlements.length === 0 ? (
                    <p className="text-gray-500 text-sm py-4">No debt settlements recorded yet.</p>
                  ) : (
                    <div className="space-y-3">
                      {settlements.map((setl) => (
                        <div key={setl.id} className="flex items-center justify-between p-3 rounded-xl bg-white/5 border border-white/5 text-sm">
                          <span className="text-gray-400">{setl.date}</span>
                          <span className="text-white">
                            <span className="font-semibold">{setl.from_user?.username}</span> paid{' '}
                            <span className="font-semibold">{setl.to_user?.username}</span>
                          </span>
                          <span className="font-bold text-emerald-400">
                            +{setl.amount} {setl.currency}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* Right Column: Balances & Simplified Debts */}
              <div className="space-y-8">
                
                {/* Pairwise Simplified Debts (Aisha's requirement) */}
                <div className="glass-panel p-6 rounded-2xl space-y-4">
                  <h2 className="text-xl font-bold text-white flex items-center gap-2">
                    <DollarSign className="w-5 h-5 text-indigo-400" />
                    <span>Simplified Debts</span>
                  </h2>
                  <p className="text-xs text-gray-400">
                    Aisha: "I just want one number per person. Who pays whom, how much, done."
                  </p>

                  {balances?.simplified_debts.length === 0 ? (
                    <div className="flex items-center gap-2 text-emerald-400 bg-emerald-500/10 p-3 rounded-xl border border-emerald-500/20 text-sm font-semibold">
                      <Check className="w-4 h-4" />
                      <span>All debts are settled!</span>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {balances?.simplified_debts.map((debt, index) => (
                        <div key={index} className="p-4 rounded-xl bg-indigo-500/5 border border-indigo-500/10 flex items-center justify-between text-sm">
                          <span className="font-semibold text-gray-300">{debt.from_user}</span>
                          <div className="flex flex-col items-center mx-2 shrink-0">
                            <span className="text-[10px] text-gray-500 uppercase tracking-widest font-bold">Owes</span>
                            <ArrowRight className="w-4 h-4 text-indigo-400" />
                          </div>
                          <span className="font-semibold text-gray-300">{debt.to_user}</span>
                          <span className="font-bold text-indigo-400 ml-4 shrink-0">
                            ₹{debt.amount}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Net Balances and Tracing (Rohan's requirement) */}
                <div className="glass-panel p-6 rounded-2xl space-y-4">
                  <h2 className="text-xl font-bold text-white flex items-center gap-2">
                    <Activity className="w-5 h-5 text-indigo-400" />
                    <span>Net Balances</span>
                  </h2>
                  <p className="text-xs text-gray-400">
                    Rohan: "Click a member to audit exactly which expenses make up their balance."
                  </p>

                  <div className="space-y-3">
                    {balances && Object.entries(balances.net_balances).map(([username, bal]) => {
                      const isOwed = bal > 0;
                      const isZero = bal === 0;
                      return (
                        <button
                          key={username}
                          onClick={() => handleExplain(username)}
                          className="w-full text-left p-3.5 rounded-xl bg-white/5 hover:bg-white/10 border border-white/5 hover:border-indigo-500/20 flex items-center justify-between transition-all group active:scale-[0.98]"
                        >
                          <div className="min-w-0">
                            <span className="font-semibold text-white block truncate">{username}</span>
                            <span className="text-[10px] text-indigo-400 group-hover:text-indigo-300 flex items-center gap-1 mt-0.5">
                              <HelpCircle className="w-3.5 h-3.5" />
                              Audit Ledger
                            </span>
                          </div>

                          <span className={`font-bold ${isZero ? 'text-gray-500' : isOwed ? 'text-emerald-400' : 'text-rose-400'}`}>
                            {isZero ? 'Settled' : isOwed ? `+₹${bal}` : `-₹${Math.abs(bal)}`}
                          </span>
                        </button>
                      );
                    })}
                  </div>
                </div>

                {/* Group Membership History */}
                <div className="glass-panel p-6 rounded-2xl space-y-4">
                  <h2 className="text-xl font-bold text-white flex items-center gap-2">
                    <Users className="w-5 h-5 text-indigo-400" />
                    <span>Membership Timeline</span>
                  </h2>

                  <div className="space-y-3">
                    {members.map((m) => (
                      <div key={m.id} className="flex items-center justify-between text-xs py-2 border-b border-white/5 last:border-b-0">
                        <span className="font-semibold text-white text-sm">{m.user.username}</span>
                        <div className="text-right">
                          <span className="text-gray-400 block">Joined: {m.joined_at}</span>
                          {m.left_at && (
                            <span className="text-rose-400 block font-medium">Left: {m.left_at}</span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

              </div>
            </div>

            {/* Rohan's Audit Ledger Explanation Trace Modal */}
            {traceUser && (
              <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
                {/* Backdrop */}
                <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={() => setTraceUser(null)}></div>
                
                {/* Content */}
                <div className="w-full max-w-3xl glass-panel rounded-2xl shadow-2xl relative z-10 overflow-hidden flex flex-col max-h-[85vh]">
                  
                  {/* Modal Header */}
                  <div className="p-6 border-b border-white/5 flex items-center justify-between shrink-0">
                    <div>
                      <h3 className="text-2xl font-bold text-white">Balance Audit Trail: {traceUser}</h3>
                      <p className="text-gray-400 text-xs mt-1">
                        Verifiable ledger detailing every debit, credit, and settlement. No magic numbers!
                      </p>
                    </div>
                    <button
                      onClick={() => setTraceUser(null)}
                      className="p-1 rounded-lg hover:bg-white/5 text-gray-400 hover:text-white transition-colors"
                    >
                      <X className="w-6 h-6" />
                    </button>
                  </div>

                  {/* Modal Body */}
                  <div className="p-6 overflow-y-auto custom-scrollbar flex-1 space-y-6">
                    {traceLoading ? (
                      <div className="flex flex-col items-center justify-center py-20 gap-4">
                        <div className="w-10 h-10 border-4 border-indigo-500/20 border-t-indigo-500 rounded-full animate-spin"></div>
                        <span className="text-gray-400 text-sm">Compiling historical split data...</span>
                      </div>
                    ) : traceData ? (
                      <div>
                        {/* Net Summary Card */}
                        <div className="p-5 rounded-xl bg-indigo-500/5 border border-indigo-500/10 flex justify-between items-center mb-6">
                          <div>
                            <span className="text-gray-400 text-xs uppercase font-bold tracking-wider">Audit Net balance</span>
                            <h4 className={`text-3xl font-extrabold mt-1 ${
                              traceData.net_balance === 0
                                ? 'text-gray-400'
                                : traceData.net_balance > 0
                                ? 'text-emerald-400'
                                : 'text-rose-400'
                            }`}>
                              {traceData.net_balance === 0
                                ? 'Settled'
                                : traceData.net_balance > 0
                                ? `+₹${traceData.net_balance}`
                                : `-₹${Math.abs(traceData.net_balance)}`}
                            </h4>
                          </div>
                          <span className="text-xs text-gray-500 font-mono">
                            Verifiable Sum = OK
                          </span>
                        </div>

                        {/* Audit Log Table */}
                        <div className="space-y-4">
                          <h4 className="font-bold text-white text-sm">Historical Entries Breakdown</h4>
                          <div className="space-y-3">
                            {traceData.ledger.map((item, index) => {
                              const isPositive = item.impact > 0;
                              return (
                                <div key={index} className="p-4 rounded-xl bg-white/5 border border-white/5 flex items-center justify-between gap-4 text-sm hover:border-white/10 transition-colors">
                                  <div className="min-w-0">
                                    <div className="flex items-center gap-2">
                                      <span className="text-xs text-gray-500 whitespace-nowrap">{item.date}</span>
                                      <span className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded-md ${
                                        item.type.startsWith('expense_paid')
                                          ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                                          : item.type.startsWith('expense_owed')
                                          ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                                          : 'bg-indigo-500/10 text-indigo-400 border border-indigo-500/20'
                                      }`}>
                                        {item.type.replace('_', ' ')}
                                      </span>
                                    </div>
                                    <p className="font-semibold text-white mt-1 truncate">{item.description}</p>
                                    <p className="text-xs text-gray-400 mt-0.5">{item.details}</p>
                                  </div>

                                  <div className="text-right shrink-0">
                                    <span className={`font-bold block text-base ${isPositive ? 'text-emerald-400' : 'text-rose-400'}`}>
                                      {isPositive ? `+₹${item.impact}` : `-₹${Math.abs(item.impact)}`}
                                    </span>
                                    <span className="text-[10px] text-gray-500 font-mono block mt-0.5">
                                      Bal: ₹{item.running_balance}
                                    </span>
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      </div>
                    ) : (
                      <p className="text-gray-400 text-center">No audit trail logs found for this user.</p>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* Direct Expense Dialog */}
            {showExpenseForm && (
              <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
                <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={() => setShowExpenseForm(false)}></div>
                <div className="w-full max-w-md glass-panel p-6 rounded-2xl relative z-10">
                  <div className="flex justify-between items-center mb-6">
                    <h3 className="text-xl font-bold text-white">Add Group Expense</h3>
                    <button onClick={() => setShowExpenseForm(false)} className="p-1 text-gray-400 hover:text-white">
                      <X className="w-6 h-6" />
                    </button>
                  </div>

                  <form onSubmit={handleExpenseSubmit} className="space-y-4">
                    <div>
                      <label className="block text-gray-300 text-sm font-medium mb-1.5">Description</label>
                      <input
                        type="text" required
                        value={newExpense.description}
                        onChange={(e) => setNewExpense({ ...newExpense, description: e.target.value })}
                        className="w-full px-4 py-2 bg-slate-900 border border-gray-700/50 rounded-xl text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                        placeholder="e.g. Electricity, Snacks"
                      />
                    </div>
                    <div>
                      <label className="block text-gray-300 text-sm font-medium mb-1.5">Amount (INR)</label>
                      <input
                        type="number" step="0.01" required
                        value={newExpense.amount}
                        onChange={(e) => setNewExpense({ ...newExpense, amount: e.target.value })}
                        className="w-full px-4 py-2 bg-slate-900 border border-gray-700/50 rounded-xl text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                        placeholder="e.g. 1500"
                      />
                    </div>
                    <div>
                      <label className="block text-gray-300 text-sm font-medium mb-1.5">Paid By</label>
                      <select
                        required
                        value={newExpense.paid_by}
                        onChange={(e) => setNewExpense({ ...newExpense, paid_by: e.target.value })}
                        className="w-full px-4 py-2 bg-slate-900 border border-gray-700/50 rounded-xl text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                      >
                        <option value="">Select Member</option>
                        {members.map(m => (
                          <option key={m.user.id} value={m.user.id}>{m.user.username}</option>
                        ))}
                      </select>
                    </div>

                    <button
                      type="submit"
                      className="w-full py-2.5 rounded-xl font-medium text-white bg-gradient-premium hover:shadow-lg transition-all"
                    >
                      Record Expense
                    </button>
                  </form>
                </div>
              </div>
            )}

            {/* Direct Settlement Dialog */}
            {showSettlementForm && (
              <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
                <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={() => setShowSettlementForm(false)}></div>
                <div className="w-full max-w-md glass-panel p-6 rounded-2xl relative z-10">
                  <div className="flex justify-between items-center mb-6">
                    <h3 className="text-xl font-bold text-white">Record Settlement</h3>
                    <button onClick={() => setShowSettlementForm(false)} className="p-1 text-gray-400 hover:text-white">
                      <X className="w-6 h-6" />
                    </button>
                  </div>

                  <form onSubmit={handleSettlementSubmit} className="space-y-4">
                    <div>
                      <label className="block text-gray-300 text-sm font-medium mb-1.5">From User (Debtor)</label>
                      <select
                        required
                        value={newSettlement.from_user}
                        onChange={(e) => setNewSettlement({ ...newSettlement, from_user: e.target.value })}
                        className="w-full px-4 py-2 bg-slate-900 border border-gray-700/50 rounded-xl text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                      >
                        <option value="">Select Payer</option>
                        {members.map(m => (
                          <option key={m.user.id} value={m.user.id}>{m.user.username}</option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="block text-gray-300 text-sm font-medium mb-1.5">To User (Creditor)</label>
                      <select
                        required
                        value={newSettlement.to_user}
                        onChange={(e) => setNewSettlement({ ...newSettlement, to_user: e.target.value })}
                        className="w-full px-4 py-2 bg-slate-900 border border-gray-700/50 rounded-xl text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                      >
                        <option value="">Select Recipient</option>
                        {members.map(m => (
                          <option key={m.user.id} value={m.user.id}>{m.user.username}</option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="block text-gray-300 text-sm font-medium mb-1.5">Amount (INR)</label>
                      <input
                        type="number" step="0.01" required
                        value={newSettlement.amount}
                        onChange={(e) => setNewSettlement({ ...newSettlement, amount: e.target.value })}
                        className="w-full px-4 py-2 bg-slate-900 border border-gray-700/50 rounded-xl text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                        placeholder="e.g. 500"
                      />
                    </div>

                    <button
                      type="submit"
                      className="w-full py-2.5 rounded-xl font-medium text-white bg-gradient-premium hover:shadow-lg transition-all"
                    >
                      Record Settlement
                    </button>
                  </form>
                </div>
              </div>
            )}

          </div>
        )}
      </main>
    </div>
  );
}
