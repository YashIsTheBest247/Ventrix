import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App.jsx";
import ConfirmProvider from "./components/ConfirmProvider.jsx";
import AccessGate from "./components/AccessGate.jsx";
import "./index.css";

// Apply saved theme before first paint to avoid a flash.
const savedTheme = localStorage.getItem("ventrix_theme");
if (savedTheme) document.documentElement.dataset.theme = savedTheme;

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <BrowserRouter>
      <AccessGate>
        <ConfirmProvider>
          <App />
        </ConfirmProvider>
      </AccessGate>
    </BrowserRouter>
  </React.StrictMode>
);
