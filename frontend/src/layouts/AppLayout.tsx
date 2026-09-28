import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../features/auth/AuthContext";

const employeeNav = [
  { to: "/", label: "اليوم", end: true }, { to: "/my-customers", label: "عملائي" },
  { to: "/followups", label: "متابعات" }, { to: "/products", label: "المنتجات" }, { to: "/orders", label: "أوردرات" },
];
const managerNav = [
  { to: "/", label: "الرئيسية", end: true }, { to: "/assignment", label: "التوزيع" },
  { to: "/employees", label: "الموظفات" }, { to: "/orders", label: "أوردرات" }, { to: "/products", label: "المنتجات" },
];

/** موبايل أولًا: شريط تنقل سفلي. ديسكتوب: يتحول لشريط علوي. لا Sidebar ضخمة (القاعدة 41). */
export function AppLayout() {
  const { user, logout } = useAuth();
  const nav = user?.role === "SYSTEM_MANAGER" ? managerNav : employeeNav;
  return (
    <div className="min-h-full flex flex-col md:flex-col-reverse">
      <header className="sticky top-0 z-30 bg-white border-b px-4 min-h-[56px] flex items-center justify-between pt-[env(safe-area-inset-top)]">
        <strong className="text-brand-700 text-lg">Nexly</strong>
        <div className="flex items-center gap-3 text-sm">
          <span className="text-gray-600">{user?.full_name}</span>
          <button className="btn btn-ghost !min-h-[40px] !px-3" onClick={() => void logout()}>خروج</button>
        </div>
      </header>
      <main className="flex-1 w-full max-w-3xl mx-auto p-4 pb-28 md:pb-6"><Outlet /></main>
      <nav className="fixed bottom-0 inset-x-0 z-30 bg-white border-t flex pb-[env(safe-area-inset-bottom)] md:static md:justify-center md:border-t-0 md:border-b" aria-label="التنقل">
        {nav.map((n) => (
          <NavLink key={n.to} to={n.to} end={n.end}
            className={({ isActive }) => `flex-1 md:flex-none md:px-6 text-center py-3 text-sm font-semibold ${isActive ? "text-brand-700 border-t-2 md:border-t-0 md:border-b-2 border-brand-600" : "text-gray-500"}`}>
            {n.label}
          </NavLink>
        ))}
      </nav>
    </div>
  );
}
