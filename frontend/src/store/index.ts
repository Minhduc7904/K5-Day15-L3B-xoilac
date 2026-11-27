import { configureStore } from '@reduxjs/toolkit';
import { useDispatch, useSelector } from 'react-redux';
import { authSlice } from '@/features/auth/auth-slice';
import { realtimeSlice } from '@/features/realtime/realtime-slice';

export function makeStore() {
  return configureStore({
    reducer: {
      auth: authSlice.reducer,
      realtime: realtimeSlice.reducer,
    },
  });
}

export type AppStore = ReturnType<typeof makeStore>;
export type RootState = ReturnType<AppStore['getState']>;
export type AppDispatch = AppStore['dispatch'];
export const useAppDispatch = useDispatch.withTypes<AppDispatch>();
export const useAppSelector = useSelector.withTypes<RootState>();
