import { createSlice, type PayloadAction } from '@reduxjs/toolkit';
import type { RealtimeStatus } from './types';

export interface RealtimeState {
  status: RealtimeStatus;
}

const initialState: RealtimeState = { status: 'idle' };

export const realtimeSlice = createSlice({
  name: 'realtime',
  initialState,
  reducers: {
    realtimeStatusChanged(state, action: PayloadAction<RealtimeStatus>) {
      state.status = action.payload;
    },
  },
});

export const { realtimeStatusChanged } = realtimeSlice.actions;
