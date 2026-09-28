import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./features/auth/AuthContext";
import { AppLayout } from "./layouts/AppLayout";
import LoginPage from "./pages/LoginPage";
import HomePage from "./pages/HomePage";
import MyCustomersPage from "./pages/MyCustomersPage";
import CustomerDetailPage from "./pages/CustomerDetailPage";
import FollowupsPage from "./pages/FollowupsPage";
import OrdersPage from "./pages/OrdersPage";
import ProductsPage from "./pages/ProductsPage";
import EmployeesPage from "./pages/EmployeesPage";
import AssignmentPage from "./pages/AssignmentPage";

const Splash = ({ text }: { text: string }) => <div className="min-h-full flex items-center justify-center text-gray-500" role="status">{text}</div>;

export default function App() {
  const { state, error, retry, user } = useAuth();
  if (state === "booting") return <Splash text="جارٍ فتح Nexly…" />;
  if (state === "error") return (
    <div className="min-h-full flex flex-col items-center justify-center gap-3 p-6 text-center">
      <p className="text-red-600">{error ?? "تعذر الاتصال بالخادم"}</p>
      <button className="btn btn-primary" onClick={retry}>إعادة المحاولة</button>
    </div>);
  if (state === "unauthenticated") return <Routes><Route path="*" element={<LoginPage />} /></Routes>;
  const manager = user?.role === "SYSTEM_MANAGER";
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route index element={<HomePage />} />
        <Route path="my-customers" element={<MyCustomersPage />} />
        <Route path="customers/:id" element={<CustomerDetailPage />} />
        <Route path="followups" element={<FollowupsPage />} />
        <Route path="orders" element={<OrdersPage />} />
        <Route path="products" element={<ProductsPage />} />
        {manager && <Route path="employees" element={<EmployeesPage />} />}
        {manager && <Route path="assignment" element={<AssignmentPage />} />}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
