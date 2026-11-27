import {
  Ban,
  ChartColumn,
  CircleHelp,
  FileText,
  MessageSquareText,
  Search,
  ShieldCheck,
  Shuffle,
  SlidersHorizontal,
  Target,
} from 'lucide-react';
import Image from 'next/image';
import type { ReactNode } from 'react';
import { Container, Section, SectionHeader } from '@/components/layout/container';
import { MascotAnimation } from '@/components/mascot/mascot-animation';
import { Float, Reveal, Stagger, StaggerItem } from '@/components/motion/reveal';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/feedback';
import { Accordion } from '@/components/ui/interactive';
import { cn } from '@/lib/cn';
import { chapters, difficulties, faqs } from './content';

/* ---------- Dải chương chạy ngang ---------- */

function ChapterRow({ items, reverse }: { items: typeof chapters; reverse?: boolean }) {
  const chip = (c: (typeof chapters)[number], key: string) => (
    <li
      key={key}
      className="flex shrink-0 items-center gap-2 rounded-full border border-border bg-background px-4 py-2 text-label text-foreground shadow-soft"
    >
      <span className="rounded-full bg-primary-subtle px-2 py-0.5 text-caption font-semibold text-primary">
        Lớp {c.grade}
      </span>
      {c.name}
    </li>
  );
  return (
    <div className="group flex overflow-hidden [mask-image:linear-gradient(to_right,transparent,black_8%,black_92%,transparent)]">
      <ul
        className={cn(
          'flex w-max animate-marquee gap-3 pr-3 group-hover:[animation-play-state:paused]',
          reverse && '[animation-direction:reverse]',
        )}
      >
        {items.map((c) => chip(c, c.name))}
      </ul>
      <ul
        aria-hidden="true"
        className={cn(
          'flex w-max animate-marquee gap-3 pr-3 group-hover:[animation-play-state:paused]',
          reverse && '[animation-direction:reverse]',
        )}
      >
        {items.map((c) => chip(c, `${c.name}-copy`))}
      </ul>
    </div>
  );
}

export function ChapterMarquee() {
  const half = Math.ceil(chapters.length / 2);
  return (
    <section aria-label="Các chương có thể ôn" className="border-y border-border bg-surface py-8">
      <p className="mb-5 text-center text-label font-semibold text-muted-foreground">
        Ôn theo các chương của chương trình Toán 10, 11, 12
      </p>
      <div className="grid gap-3">
        <ChapterRow items={chapters.slice(0, half)} />
        <ChapterRow items={chapters.slice(half)} reverse />
      </div>
    </section>
  );
}

/* ---------- Vấn đề ---------- */

const problems = [
  {
    icon: ChartColumn,
    title: 'Điểm tổng không nói bạn yếu ở đâu',
    body: 'Được 6 điểm, nhưng 4 điểm mất nằm ở chương nào? Nhìn đáp án thôi rất khó tự nhóm lại.',
  },
  {
    icon: Search,
    title: 'Tìm bài tương tự mất thời gian',
    body: 'Lục sách, lướt mạng để tìm đúng dạng mình hay sai, rồi lại không chắc bài đó đúng mức độ.',
  },
  {
    icon: Shuffle,
    title: 'Ôn lan man, dễ lệch trọng tâm',
    body: 'Làm thêm cả đề mới trong khi chỉ vài chương thật sự cần luyện, thời gian ôn trôi đi mất.',
  },
];

export function Problems() {
  return (
    <Section id="van-de" aria-labelledby="van-de-title">
      <Container>
        <Reveal>
          <SectionHeader
            titleId="van-de-title"
            eyebrow="Vấn đề"
            title="Chữa đề xong rồi… ôn gì tiếp?"
            description="Sau mỗi bài kiểm tra, câu hỏi khó nhất thường không nằm trong đề mà là: tiếp theo mình nên luyện phần nào."
          />
        </Reveal>
        <Stagger className="mt-14 grid gap-5 md:grid-cols-3">
          {problems.map(({ icon: Icon, title, body }, i) => (
            <StaggerItem key={title}>
              <Card interactive className="group h-full p-7">
                <span
                  className={cn(
                    'flex size-12 items-center justify-center rounded-2xl transition-transform duration-300 group-hover:-rotate-6 group-hover:scale-110',
                    ['bg-primary-subtle text-primary', 'bg-accent-subtle text-accent-strong', 'bg-warning-subtle text-warning'][i],
                  )}
                >
                  <Icon className="size-6" aria-hidden="true" />
                </span>
                <h3 className="mt-5 text-h3 text-foreground">{title}</h3>
                <p className="mt-2 text-body text-muted-foreground">{body}</p>
              </Card>
            </StaggerItem>
          ))}
        </Stagger>
      </Container>
    </Section>
  );
}

/* ---------- Cách hoạt động ---------- */

const steps = [
  {
    icon: MessageSquareText,
    mascot: 'working',
    alt: 'Linh vật đang gõ yêu cầu',
    title: 'Nhắn yêu cầu ôn',
    body: 'Viết như nhắn tin cho bạn: muốn ôn phần hay sai, ôn cho bài kiểm tra hay thi học kỳ.',
  },
  {
    icon: SlidersHorizontal,
    mascot: 'studying',
    alt: 'Linh vật đang xem cấu trúc đề',
    title: 'Xem và chỉnh cấu trúc đề',
    body: 'Examind đề xuất chương, số câu, độ khó kèm lý do. Muốn đổi gì, bạn chỉ cần nói.',
  },
  {
    icon: FileText,
    mascot: 'success',
    alt: 'Linh vật vui mừng cầm đề nháp',
    title: 'Nhận đề nháp',
    body: 'Đề ghép từ câu đã duyệt trong ngân hàng, không kèm đáp án, để bạn in ra hoặc làm bên ngoài.',
  },
];

export function HowItWorks() {
  return (
    <Section id="cach-hoat-dong" tone="surface" aria-labelledby="cach-hoat-dong-title" className="overflow-hidden">
      <div className="bg-grid pointer-events-none absolute inset-0 opacity-60" aria-hidden="true" />
      <Container className="relative">
        <Reveal>
          <SectionHeader
            titleId="cach-hoat-dong-title"
            eyebrow="Cách hoạt động"
            title="Ba bước, bạn luôn là người quyết"
            description="Examind không tự ra đề rồi bắt bạn làm. Bạn xem trước, chỉnh lại, rồi mới nhận đề."
          />
        </Reveal>

        <Stagger className="relative mt-16 grid gap-6 lg:grid-cols-3" stagger={0.15}>
          <div
            className="absolute top-24 right-[16%] left-[16%] hidden border-t-2 border-dashed border-primary/25 lg:block"
            aria-hidden="true"
          />
          {steps.map(({ icon: Icon, mascot, alt, title, body }, i) => (
            <StaggerItem key={title}>
              <Card interactive className="relative h-full overflow-hidden p-7 text-center">
                <span className="absolute top-5 left-5 text-h2 font-bold text-primary/15 tabular-nums">0{i + 1}</span>
                <Float distance={6} duration={4 + i * 0.6} delay={i * 0.4} className="mx-auto w-32">
                  <Image
                    src={`/brand/mascot/static/${mascot}.webp`}
                    alt={alt}
                    width={384}
                    height={384}
                    sizes="128px"
                    className="h-auto w-full"
                  />
                </Float>
                <span className="mx-auto mt-4 flex size-11 items-center justify-center rounded-full bg-primary text-primary-foreground shadow-soft">
                  <Icon className="size-5" aria-hidden="true" />
                </span>
                <h3 className="mt-4 text-h3 text-foreground">{title}</h3>
                <p className="mt-2 text-body text-muted-foreground">{body}</p>
              </Card>
            </StaggerItem>
          ))}
        </Stagger>
      </Container>
    </Section>
  );
}

/* ---------- Điểm nổi bật ---------- */

const exampleChapters = [
  { name: 'Ứng dụng đạo hàm', wrong: 7, total: 12 },
  { name: 'Nguyên hàm và tích phân', wrong: 4, total: 10 },
  { name: 'Toạ độ trong không gian', wrong: 2, total: 9 },
];

function FeatureCard({
  icon,
  title,
  body,
  className,
  children,
}: {
  icon: ReactNode;
  title: string;
  body: string;
  className?: string;
  children?: ReactNode;
}) {
  return (
    <Card interactive className={cn('group flex h-full flex-col gap-4 p-7', className)}>
      <span className="flex size-11 items-center justify-center rounded-2xl bg-primary-subtle text-primary transition-colors duration-300 group-hover:bg-primary group-hover:text-primary-foreground">
        {icon}
      </span>
      <div className="grid gap-2">
        <h3 className="text-h3 text-foreground">{title}</h3>
        <p className="text-body text-muted-foreground">{body}</p>
      </div>
      {children}
    </Card>
  );
}

export function Features() {
  return (
    <Section id="diem-noi-bat" aria-labelledby="diem-noi-bat-title">
      <Container>
        <Reveal>
          <SectionHeader
            titleId="diem-noi-bat-title"
            eyebrow="Điểm nổi bật"
            title="Một trợ lý ôn tập biết nói “mình chưa chắc”"
            description="Examind được thiết kế để bạn tin được: có căn cứ, có bước duyệt, và không đoán khi thiếu dữ liệu."
          />
        </Reveal>

        <Stagger className="mt-14 grid gap-5 lg:grid-cols-3">
          <StaggerItem className="lg:col-span-2">
            <FeatureCard
              icon={<Target className="size-5" aria-hidden="true" />}
              title="Có căn cứ bằng số liệu"
              body="Examind nêu số câu sai trên tổng số câu của từng chương, để bạn biết vì sao nên ôn phần đó."
            >
              <div className="mt-auto grid gap-3 rounded-2xl border border-border bg-surface p-5">
                <div className="flex items-center justify-between">
                  <span className="text-label font-semibold text-foreground">Tỉ lệ sai theo chương</span>
                  <Badge tone="neutral">Ví dụ</Badge>
                </div>
                {exampleChapters.map((c, i) => (
                  <div key={c.name} className="grid gap-1.5">
                    <div className="flex justify-between text-caption">
                      <span className="text-foreground">{c.name}</span>
                      <span className="font-semibold text-muted-foreground tabular-nums">
                        {c.wrong}/{c.total} câu sai
                      </span>
                    </div>
                    <div className="h-2.5 overflow-hidden rounded-full bg-surface-muted">
                      <Reveal y={0} delay={0.2 + i * 0.12} className="h-full">
                        <div
                          className={cn('h-full rounded-full', i === 0 ? 'bg-danger' : i === 1 ? 'bg-warning' : 'bg-success')}
                          style={{ width: `${(c.wrong / c.total) * 100}%` }}
                        />
                      </Reveal>
                    </div>
                  </div>
                ))}
              </div>
            </FeatureCard>
          </StaggerItem>

          <StaggerItem>
            <FeatureCard
              icon={<SlidersHorizontal className="size-5" aria-hidden="true" />}
              title="Bạn là người quyết"
              body="Mọi đề đều qua bước xem trước. Bạn đổi chương, số câu hay độ khó bằng lời, Examind cập nhật lại và hỏi xác nhận."
            />
          </StaggerItem>

          <StaggerItem>
            <FeatureCard
              icon={<ShieldCheck className="size-5" aria-hidden="true" />}
              title="Chỉ dùng câu đã duyệt"
              body="Câu hỏi đến từ ngân hàng đã được kiểm duyệt. Examind kiểm từng mã câu trước khi đưa vào đề."
            />
          </StaggerItem>

          <StaggerItem>
            <FeatureCard
              icon={<CircleHelp className="size-5" aria-hidden="true" />}
              title="Nói thẳng khi thiếu dữ liệu"
              body="Chưa có lịch sử làm bài hay ngân hàng thiếu câu? Examind nói rõ và hỏi lại bạn, không đoán bừa."
            />
          </StaggerItem>

          <StaggerItem>
            <FeatureCard
              icon={<ChartColumn className="size-5" aria-hidden="true" />}
              title="Bốn mức độ khó"
              body="Cân số câu theo từng mức để đề vừa sức."
            >
              <ul className="mt-auto grid grid-cols-2 gap-2">
                {difficulties.map((d) => (
                  <li key={d.code} className="rounded-xl bg-surface px-3 py-2">
                    <span className="block text-label font-bold text-primary">{d.code}</span>
                    <span className="block text-caption text-muted-foreground">{d.name}</span>
                  </li>
                ))}
              </ul>
            </FeatureCard>
          </StaggerItem>
        </Stagger>
      </Container>
    </Section>
  );
}

/* ---------- Cam kết ---------- */

const nots = [
  { title: 'Không tự viết câu hỏi hay đáp án', body: 'Chỉ chọn và ghép câu có sẵn đã được duyệt trong ngân hàng.' },
  { title: 'Không chấm điểm chính thức', body: 'Không ghi điểm, không sửa kết quả, không xếp hạng hay so sánh học sinh.' },
  { title: 'Không đưa đáp án đề đang thi', body: 'Không giúp chép bài với đề đang thi hoặc đề kiểm tra của lớp.' },
];

export function Promises() {
  return (
    <Section tone="inverse" aria-labelledby="cam-ket-title" className="overflow-hidden">
      <div
        className="pointer-events-none absolute -top-32 right-0 size-[480px] rounded-full bg-accent/20 blur-3xl"
        aria-hidden="true"
      />
      <Container className="relative grid items-center gap-12 lg:grid-cols-[0.9fr_1.1fr]">
        <Reveal className="grid gap-8">
          <SectionHeader
            align="left"
            inverse
            titleId="cam-ket-title"
            eyebrow="Cam kết"
            title="Những điều Examind không làm"
            description="Ôn tập chỉ có ích khi trung thực. Đây là giới hạn nhóm đặt ra ngay từ thiết kế."
          />
          <Float distance={8} duration={5} className="hidden w-40 lg:block">
            <Image
              src="/brand/mascot/static/front.webp"
              alt="Linh vật Examind"
              width={384}
              height={384}
              sizes="160px"
              className="h-auto w-full"
            />
          </Float>
        </Reveal>
        <Stagger className="grid gap-4" stagger={0.12}>
          {nots.map((item) => (
            <StaggerItem key={item.title}>
              <div className="flex gap-4 rounded-3xl border border-primary-foreground/10 bg-primary-foreground/5 p-6 transition-colors duration-300 hover:bg-primary-foreground/10">
                <span className="flex size-11 shrink-0 items-center justify-center rounded-2xl bg-accent text-foreground">
                  <Ban className="size-5" aria-hidden="true" />
                </span>
                <div className="grid gap-1">
                  <h3 className="text-h3 text-primary-foreground">{item.title}</h3>
                  <p className="text-body text-primary-foreground/75">{item.body}</p>
                </div>
              </div>
            </StaggerItem>
          ))}
        </Stagger>
      </Container>
    </Section>
  );
}

/* ---------- Hỏi đáp ---------- */

export function Faq() {
  return (
    <Section id="hoi-dap" aria-labelledby="hoi-dap-title">
      <Container className="grid gap-12 lg:grid-cols-[0.8fr_1.2fr]">
        <Reveal className="grid content-start gap-6">
          <SectionHeader
            align="left"
            titleId="hoi-dap-title"
            eyebrow="Hỏi đáp"
            title="Câu hỏi thường gặp"
            description="Chưa thấy câu bạn cần? Hãy hỏi trực tiếp Examind sau khi đăng nhập."
          />
          <div className="hidden lg:block">
            <MascotAnimation motion="thinking" size={140} />
          </div>
        </Reveal>
        <Reveal delay={0.1}>
          <Accordion items={faqs} defaultOpenId={faqs[0].id} />
        </Reveal>
      </Container>
    </Section>
  );
}
