import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "sonner";
import { AuthProvider, useAuth } from "@/context/AuthContext";
import Landing from "@/pages/Landing";
import AuthPage from "@/pages/AuthPage";
import Panel from "@/pages/Panel";
import AuditDetail from "@/pages/AuditDetail";

const Protected = ({ children }) => {
  const { user } = useAuth();
  if (user === null)
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#F8FAFC]">
        <div className="w-8 h-8 border-2 border-[#0284C7] border-t-transparent rounded-full animate-spin" data-testid="auth-loading-spinner" />
      </div>
    );
  if (user === false) return <Navigate to="/acceso" replace />;
  return children;
};

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/acceso" element={<AuthPage />} />
          <Route
            path="/panel"
            element={
              <Protected>
                <Panel />
              </Protected>
            }
          />
          <Route
            path="/panel/auditoria/:id"
            element={
              <Protected>
                <AuditDetail />
              </Protected>
            }
          />
        </Routes>
      </BrowserRouter>
      <Toaster position="top-right" richColors />
    </AuthProvider>
  );
}

export default App;
