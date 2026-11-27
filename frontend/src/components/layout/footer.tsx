import { Container } from './container';
import { Logo } from './logo';
import type { NavLink } from './navbar';

interface FooterProps {
  links?: NavLink[];
}

export function Footer({ links = [] }: FooterProps) {
  return (
    <footer className="border-t border-border bg-surface">
      <Container className="grid gap-10 py-12 md:grid-cols-[1.4fr_1fr] md:items-start">
        <div className="grid max-w-sm gap-4">
          <Logo />
          <p className="text-body text-muted-foreground">
            Trợ lý ôn Toán THPT: đề xuất đề ôn theo chương bạn còn yếu, ghép từ các câu hỏi đã được duyệt.
          </p>
        </div>
        {links.length > 0 && (
          <nav aria-label="Liên kết chân trang">
            <p className="text-label font-semibold text-foreground">Khám phá</p>
            <ul className="mt-3 grid grid-cols-2 gap-x-6 gap-y-2">
              {links.map((link) => (
                <li key={link.href}>
                  <a
                    href={link.href}
                    className="rounded text-body text-muted-foreground transition-colors hover:text-primary focus-visible:outline-2 focus-visible:outline-ring"
                  >
                    {link.label}
                  </a>
                </li>
              ))}
            </ul>
          </nav>
        )}
      </Container>
      <div className="border-t border-border">
        <Container className="flex flex-col gap-2 py-5 text-caption text-muted-foreground sm:flex-row sm:justify-between">
          <p>© {new Date().getFullYear()} Examind. Dự án hackathon AI20K.</p>
          <p>Đề do Examind tạo là đề luyện tập, không phải đề hay điểm chính thức.</p>
        </Container>
      </div>
    </footer>
  );
}
