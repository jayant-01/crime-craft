import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import LoginPage from "./pages/LoginPage";
import CasesPage from "./pages/CasesPage";
import CaseDetailPage from "./pages/CaseDetailPage";
import ChatPage from "./pages/ChatPage";
import DashboardPage from "./pages/DashboardPage";
import NetworkPage from "./pages/NetworkPage";
import RecidivismPage from "./pages/RecidivismPage";
import ProtectedRoute from "./components/ProtectedRoute";
import { useAuth } from "./auth/AuthContext";

export default function App() {
  const { loading } = useAuth();
  if (loading) return <div className="p-8 text-muted">Loading…</div>;

  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Navigate to="/cases" replace />} />
        <Route path="/cases" element={<CasesPage />} />
        <Route path="/cases/:id" element={<CaseDetailPage />} />
        <Route path="/chat" element={<ChatPage />} />
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute roles={["officer", "senior_officer", "admin"]}>
              <DashboardPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/network"
          element={
            <ProtectedRoute roles={["officer", "senior_officer", "admin"]}>
              <NetworkPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/recidivism"
          element={
            <ProtectedRoute roles={["senior_officer", "admin"]}>
              <RecidivismPage />
            </ProtectedRoute>
          }
        />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
