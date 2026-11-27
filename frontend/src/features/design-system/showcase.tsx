'use client';

import { BookOpen, Mail, Plus, Sparkles, Trash2 } from 'lucide-react';
import { useState, type ReactNode } from 'react';
import { Container } from '@/components/layout/container';
import { Navbar } from '@/components/layout/navbar';
import { MascotAnimation } from '@/components/mascot/mascot-animation';
import { Button, IconButton } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Checkbox, Switch } from '@/components/ui/checkbox';
import { Alert, Badge, Skeleton } from '@/components/ui/feedback';
import { FormField } from '@/components/ui/form-field';
import { Input, Textarea } from '@/components/ui/input';
import { Accordion, Progress, Tabs } from '@/components/ui/interactive';
import { PasswordInput } from '@/components/ui/password-input';
import { Spinner } from '@/components/ui/spinner';
import { useToast } from '@/components/ui/toast';

const colorTokens = [
  'background', 'surface', 'surface-muted', 'foreground', 'muted-foreground', 'border', 'input',
  'primary', 'primary-hover', 'primary-subtle', 'accent', 'accent-strong', 'accent-subtle', 'ring',
  'success', 'success-subtle', 'warning', 'warning-subtle', 'danger', 'danger-subtle', 'info', 'info-subtle',
];

const typeScale = [
  ['text-display', 'Ôn đúng phần mình còn yếu'],
  ['text-h1', 'Ứng dụng đạo hàm để khảo sát hàm số'],
  ['text-h2', 'Nguyên hàm và tích phân'],
  ['text-h3', 'Phương pháp toạ độ trong không gian'],
  ['text-body-lg', 'Tính ∫₀¹ (2x + 1) dx và so sánh với log₂ 8 = 3.'],
  ['text-body', 'Học sinh xem trước cấu trúc đề, chỉnh bằng lời rồi mới xác nhận.'],
  ['text-label', 'Nhãn ô nhập · Nút bấm'],
  ['text-caption', 'Chữ phụ, gợi ý dưới ô nhập'],
] as const;

function Block({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="grid gap-5 border-t border-border py-10">
      <h2 className="text-h2 text-foreground">{title}</h2>
      {children}
    </section>
  );
}

export function DesignSystemShowcase() {
  const toast = useToast();
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(40);
  const emailError = email && !email.includes('@') ? 'Email chưa đúng định dạng.' : undefined;

  return (
    <>
      <Navbar actions={<Button size="sm">Hành động</Button>} />
      <main id="noi-dung">
        <Container className="pb-24">
          <header className="grid gap-3 py-12">
            <Badge tone="accent" icon={<Sparkles aria-hidden="true" />}>
              Chỉ hiện ở dev / mock
            </Badge>
            <h1 className="text-h1 text-foreground">Design system Examind</h1>
            <p className="max-w-2xl text-body-lg text-muted-foreground">
              Token màu, thang chữ và component dùng chung. Tài liệu: docs/architecture/frontend-design-system.md.
            </p>
          </header>

          <Block title="Màu">
            <ul className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
              {colorTokens.map((token) => (
                <li key={token} className="overflow-hidden rounded-2xl border border-border">
                  <div className="h-16" style={{ background: `var(--color-${token})` }} />
                  <p className="px-3 py-2 text-caption font-medium text-foreground">{token}</p>
                </li>
              ))}
            </ul>
          </Block>

          <Block title="Chữ">
            <div className="grid gap-4">
              {typeScale.map(([cls, sample]) => (
                <div key={cls} className="grid gap-1 sm:grid-cols-[9rem_1fr] sm:items-baseline">
                  <code className="text-caption text-muted-foreground">{cls}</code>
                  <p className={`${cls} text-foreground`}>{sample}</p>
                </div>
              ))}
            </div>
          </Block>

          <Block title="Nút">
            <div className="flex flex-wrap gap-3">
              <Button>Primary</Button>
              <Button variant="secondary">Secondary</Button>
              <Button variant="outline">Outline</Button>
              <Button variant="ghost">Ghost</Button>
              <Button variant="accent">Accent</Button>
              <Button variant="danger" leftIcon={<Trash2 aria-hidden="true" />}>
                Xoá
              </Button>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <Button size="sm">Nhỏ</Button>
              <Button size="md">Vừa</Button>
              <Button size="lg">Lớn</Button>
              <Button loading={loading} onClick={() => { setLoading(true); window.setTimeout(() => setLoading(false), 1800); }}>
                {loading ? 'Đang gửi' : 'Bấm để tải'}
              </Button>
              <Button disabled>Vô hiệu</Button>
              <Button href="/" variant="outline">
                Dạng link
              </Button>
              <IconButton label="Thêm">
                <Plus aria-hidden="true" />
              </IconButton>
              <IconButton label="Mở tài liệu" variant="outline">
                <BookOpen aria-hidden="true" />
              </IconButton>
            </div>
            <div className="rounded-2xl bg-primary p-5">
              <Button variant="inverse">Inverse trên nền tối</Button>
            </div>
          </Block>

          <Block title="Biểu mẫu">
            <div className="grid max-w-md gap-5">
              <FormField label="Email" required hint="Dùng email bạn đăng ký." error={emailError}>
                {(field) => (
                  <Input
                    {...field}
                    type="email"
                    autoComplete="email"
                    placeholder="ban@vidu.vn"
                    leftIcon={<Mail />}
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                  />
                )}
              </FormField>
              <FormField label="Mật khẩu" required>
                {(field) => <PasswordInput {...field} placeholder="Ít nhất 8 ký tự" />}
              </FormField>
              <FormField label="Ô lỗi" error="Thông tin chưa hợp lệ.">
                {(field) => <Input {...field} defaultValue="sai định dạng" />}
              </FormField>
              <FormField label="Ghi chú">
                {(field) => <Textarea {...field} placeholder="Mình muốn ôn thêm phần tích phân…" />}
              </FormField>
              <FormField label="Ô vô hiệu">{(field) => <Input {...field} disabled defaultValue="Không sửa được" />}</FormField>
              <Checkbox label="Ghi nhớ đăng nhập" description="Trên thiết bị này trong 30 ngày." />
              <Checkbox label="Ô lỗi" invalid />
              <Switch label="Nhắc ôn hằng ngày" description="Ví dụ công tắc." defaultChecked />
            </div>
          </Block>

          <Block title="Phản hồi">
            <div className="grid gap-3 lg:grid-cols-2">
              <Alert tone="info" title="Thông tin">Phiên của bạn sẽ hết hạn sau 10 phút.</Alert>
              <Alert tone="success" title="Thành công">Đã tạo đề nháp 10 câu.</Alert>
              <Alert tone="warning" title="Cảnh báo">Ngân hàng chỉ có 6/10 câu cho chương này.</Alert>
              <Alert tone="danger" title="Lỗi" onDismiss={() => undefined}>
                Sai email hoặc mật khẩu.
              </Alert>
            </div>
            <div className="flex flex-wrap gap-3">
              {(['info', 'success', 'warning', 'danger'] as const).map((tone) => (
                <Button key={tone} variant="outline" size="sm" onClick={() => toast({ tone, title: `Toast ${tone}`, description: 'Tự ẩn sau vài giây.' })}>
                  Toast {tone}
                </Button>
              ))}
            </div>
            <div className="flex flex-wrap items-center gap-6">
              <Spinner size="sm" />
              <Spinner />
              <Spinner size="lg" label="Đang tải" className="text-primary" />
              <MascotAnimation motion="thinking" size={64} />
            </div>
            <div className="grid max-w-md gap-3">
              <Progress value={progress} label="Tiến độ ôn" showValue />
              <div className="flex gap-2">
                <Button size="sm" variant="secondary" onClick={() => setProgress((p) => Math.max(0, p - 20))}>−20</Button>
                <Button size="sm" variant="secondary" onClick={() => setProgress((p) => Math.min(100, p + 20))}>+20</Button>
              </div>
            </div>
            <div className="grid max-w-md gap-3">
              <Skeleton className="h-6 w-2/3" />
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-5/6" />
            </div>
          </Block>

          <Block title="Hiển thị">
            <div className="flex flex-wrap gap-2">
              {(['neutral', 'primary', 'accent', 'info', 'success', 'warning', 'danger'] as const).map((tone) => (
                <Badge key={tone} tone={tone} dot>
                  {tone}
                </Badge>
              ))}
            </div>
            <div className="grid gap-5 md:grid-cols-3">
              <Card>
                <CardHeader>
                  <CardTitle>Card mặc định</CardTitle>
                  <CardDescription>Viền mảnh, bóng nhẹ.</CardDescription>
                </CardHeader>
                <CardContent>Nội dung thẻ.</CardContent>
                <CardFooter>
                  <Button size="sm">Mở</Button>
                </CardFooter>
              </Card>
              <Card variant="muted" interactive>
                <CardHeader>
                  <CardTitle>Muted + interactive</CardTitle>
                  <CardDescription>Rê chuột để thấy nổi lên.</CardDescription>
                </CardHeader>
                <CardContent />
              </Card>
              <Card variant="elevated">
                <CardHeader>
                  <CardTitle>Elevated</CardTitle>
                  <CardDescription>Không viền, bóng sâu.</CardDescription>
                </CardHeader>
                <CardContent />
              </Card>
            </div>
            <Tabs
              label="Ví dụ tab"
              items={[
                { id: 'a', label: 'Cấu trúc', content: <p className="text-body text-muted-foreground">Chương, số câu, độ khó.</p> },
                { id: 'b', label: 'Đề nháp', content: <p className="text-body text-muted-foreground">10 câu đã duyệt.</p> },
                { id: 'c', label: 'Lịch sử', content: <p className="text-body text-muted-foreground">Các lần ôn trước.</p> },
              ]}
            />
            <Accordion
              items={[
                { id: '1', title: 'Accordion mục 1', content: 'Nội dung mở bằng hoạt ảnh chiều cao.' },
                { id: '2', title: 'Accordion mục 2', content: 'Dùng phím Tab và Enter để mở.' },
              ]}
            />
          </Block>
        </Container>
      </main>
    </>
  );
}
