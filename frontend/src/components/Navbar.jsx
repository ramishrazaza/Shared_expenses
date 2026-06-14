import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { authAPI } from '../services/api';
import { LogOut, Home, Upload, Shield, History, User } from 'lucide-react';

export default function Navbar() {
  const location = useLocation();
  const username = authAPI.getCurrentUser();

  const handleLogout = () => {
    authAPI.logout();
  };

  const navItems = [
    { path: '/', name: 'Dashboard', icon: Home },
    { path: '/import', name: 'Import CSV', icon: Upload },
    { path: '/audit-logs', name: 'Audit Trail', icon: History },
  ];

  return (
    <nav className="glass-panel sticky top-0 z-50 border-b border-white/5 py-4 px-6 mb-8">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        {/* Brand */}
        <Link to="/" className="flex items-center gap-2">
          <Shield className="w-6 h-6 text-indigo-400" />
          <span className="font-bold text-xl text-white tracking-tight">
            Share<span className="text-gradient">Ledger</span>
          </span>
        </Link>

        {/* Links */}
        <div className="hidden md:flex items-center gap-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path;
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all ${
                  isActive
                    ? 'bg-indigo-500/10 text-indigo-300 border border-indigo-500/20 shadow-inner'
                    : 'text-gray-400 hover:text-white hover:bg-white/5 border border-transparent'
                }`}
              >
                <Icon className="w-4 h-4" />
                <span>{item.name}</span>
              </Link>
            );
          })}
        </div>

        {/* User profile & logout */}
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/5 border border-white/5 text-gray-300 text-sm">
            <User className="w-4 h-4 text-indigo-400" />
            <span className="font-medium">{username || 'User'}</span>
          </div>

          <button
            onClick={handleLogout}
            className="p-2.5 rounded-xl bg-red-500/10 text-red-400 hover:bg-red-500/20 hover:text-red-300 border border-red-500/20 transition-all active:scale-95"
            title="Log Out"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </nav>
  );
}
