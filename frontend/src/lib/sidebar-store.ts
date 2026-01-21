import { create } from "zustand";
import { persist } from "zustand/middleware";

interface SidebarStore {
  sidebarOpen: boolean;
  hasHydrated: boolean;
  setSidebarOpen: (open: boolean) => void;
  toggleSidebar: () => void;
  setHasHydrated: (state: boolean) => void;
}

export const useSidebarStore = create<SidebarStore>()(
  persist(
    (set) => ({
      sidebarOpen: true,
      hasHydrated: false,
      setSidebarOpen: (open) => set({ sidebarOpen: open }),
      toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
      setHasHydrated: (state) => set({ hasHydrated: state }),
    }),
    {
      name: "sidebar-storage",
      onRehydrateStorage: () => (state) => {
        state?.setHasHydrated(true);
      },
    }
  )
);
