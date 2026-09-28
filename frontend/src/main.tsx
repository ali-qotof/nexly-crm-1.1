import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import App from "./App";
import { AuthProvider } from "./features/auth/AuthContext";
import { ToastProvider } from "./components/Toast";
import "./styles/index.css";

const client = new QueryClient({ defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false, staleTime: 15_000 } } });

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={client}>
      <ToastProvider><BrowserRouter><AuthProvider><App /></AuthProvider></BrowserRouter></ToastProvider>
    </QueryClientProvider>
  </React.StrictMode>,
);
