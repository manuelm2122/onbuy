import "@/App.css";
import "@/dark-theme.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "sonner";
import { AuthProvider, useAuth } from "@/context/AuthContext";
import { ThemeProvider, useTheme } from "@/context/ThemeContext";
import Home from "@/pages/Home";
import Landing from "@/pages/Landing";
import LegalService from "@/pages/LegalService";
import Blog from "@/pages/Blog";
import BlogPost from "@/pages/BlogPost";
import AuthPage from "@/pages/AuthPage";
import Panel from "@/pages/Panel";
import AuditDetail from "@/pages/AuditDetail";
import LegalPage from "@/pages/LegalPage";
import ComplaintsPage from "@/pages/ComplaintsPage";

const Protected = ({ children }) => {
  const { user } = useAuth();
  if (user === null)
    return (
      <div className="themeable min-h-screen flex items-center justify-center bg-[#F8FAFC]">
        <div className="w-8 h-8 border-2 border-[#0284C7] border-t-transparent rounded-full animate-spin" data-testid="auth-loading-spinner" />
      </div>
    );
  if (user === false) return <Navigate to="/acceso" replace />;
  return children;
};

const ThemedToaster = () => {
  const { theme } = useTheme();
  return <Toaster position="top-right" richColors theme={theme} />;
};

function App() {
  return (
    <ThemeProvider>
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/auditorias-condominios" element={<Landing />} />
          <Route path="/asesoria-legal" element={<LegalService />} />
          <Route path="/blog" element={<Blog />} />
          <Route path="/blog/:slug" element={<BlogPost />} />
          <Route path="/acceso" element={<AuthPage />} />
          <Route path="/terminos" element={<LegalPage />} />
          <Route path="/privacidad" element={<LegalPage />} />
          <Route path="/uso-ia" element={<LegalPage />} />
          <Route path="/libro-de-reclamaciones" element={<ComplaintsPage />} />
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
      <ThemedToaster />
    </AuthProvider>
    </ThemeProvider>
  );
}

export default App;
