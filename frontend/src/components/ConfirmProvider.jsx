import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";

const ConfirmContext = createContext(() => Promise.resolve(false));

export function useConfirm() {
  return useContext(ConfirmContext);
}

const DEFAULTS = {
  title: "Are you sure?",
  message: "",
  confirmLabel: "Confirm",
  cancelLabel: "Cancel",
  danger: false,
};

export default function ConfirmProvider({ children }) {
  const [state, setState] = useState(null); // { ...options }
  const resolver = useRef(null);
  const confirmBtn = useRef(null);

  const confirm = useCallback((options = {}) => {
    return new Promise((resolve) => {
      resolver.current = resolve;
      setState({ ...DEFAULTS, ...options });
    });
  }, []);

  const close = useCallback(
    (result) => {
      setState(null);
      if (resolver.current) {
        resolver.current(result);
        resolver.current = null;
      }
    },
    []
  );

  // Keyboard: Esc cancels, Enter confirms. Focus the confirm button on open.
  useEffect(() => {
    if (!state) return;
    confirmBtn.current?.focus();
    const onKey = (e) => {
      if (e.key === "Escape") close(false);
      if (e.key === "Enter") close(true);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [state, close]);

  return (
    <ConfirmContext.Provider value={confirm}>
      {children}
      {state && (
        <div className="modal-backdrop" onClick={() => close(false)}>
          <div
            className="modal"
            role="alertdialog"
            aria-modal="true"
            aria-label={state.title}
            onClick={(e) => e.stopPropagation()}
          >
            <h3>{state.title}</h3>
            {state.message && <p>{state.message}</p>}
            <div className="modal-actions">
              <button className="btn" onClick={() => close(false)}>
                {state.cancelLabel}
              </button>
              <button
                ref={confirmBtn}
                className={`btn ${state.danger ? "danger-solid" : "primary"}`}
                onClick={() => close(true)}
              >
                {state.confirmLabel}
              </button>
            </div>
          </div>
        </div>
      )}
    </ConfirmContext.Provider>
  );
}
