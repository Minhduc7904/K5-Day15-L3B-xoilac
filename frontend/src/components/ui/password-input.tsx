'use client';

import { Eye, EyeOff } from 'lucide-react';
import { useState } from 'react';
import { IconButton } from './button';
import { Input, type InputProps } from './input';

type PasswordInputProps = Omit<InputProps, 'type' | 'rightSlot'>;

export function PasswordInput({ autoComplete = 'current-password', ...props }: PasswordInputProps) {
  const [visible, setVisible] = useState(false);

  return (
    <Input
      {...props}
      type={visible ? 'text' : 'password'}
      autoComplete={autoComplete}
      rightSlot={
        <IconButton
          size="sm"
          label={visible ? 'Ẩn mật khẩu' : 'Hiện mật khẩu'}
          aria-pressed={visible}
          onClick={() => setVisible((v) => !v)}
          disabled={props.disabled}
        >
          {visible ? <EyeOff aria-hidden="true" /> : <Eye aria-hidden="true" />}
        </IconButton>
      }
    />
  );
}
