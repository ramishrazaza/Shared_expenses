import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Groups from './pages/Groups';
import ImportCSV from './pages/ImportCSV';
import ImportReport from './pages/ImportReport';
import AuditLog from './pages/AuditLog';

// Route guard to protect pages
const PrivateRoute = ({ children }) => {
  const token = localStorage.getItem('access_token');
  return token ? children : <Navigate to="/login" replace />;
};

export default function App() {
  return (
    <Router>
      <Routes>
        {/* Public Routes */}
        <Route path="/login" element={<Login />} />

        {/* Protected Routes */}
        <Route
          path="/"
          element={
            <PrivateRoute>
              <Dashboard />
            </PrivateRoute>
          }
        />
        <Route
          path="/groups/:id"
          element={
            <PrivateRoute>
              <Groups />
            </PrivateRoute>
          }
        />
        <Route
          path="/import"
          element={
            <PrivateRoute>
              <ImportCSV />
            </PrivateRoute>
          }
        />
        <Route
          path="/import/batch/:batchId"
          element={
            <PrivateRoute>
              <ImportReport />
            </PrivateRoute>
          }
        />
        <Route
          path="/audit-logs"
          element={
            <PrivateRoute>
              <AuditLog />
            </PrivateRoute>
          }
        />

        {/* Fallback */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Router>
  );
}
