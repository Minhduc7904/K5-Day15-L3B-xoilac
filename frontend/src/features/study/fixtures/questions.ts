import type { Question } from '../types';

/**
 * Câu hỏi mẫu do nhóm tự soạn cho chế độ mock (không chép từ ngân hàng của trung tâm).
 * Định dạng giống bảng `questions`/`statements` ở production: LaTeX trong `$…$`, `$$…$$`,
 * ảnh `![media:ID](media:ID)`, xuống dòng bằng `\n`.
 */
const r = String.raw;

const sc = (id: string, chapter: string, difficulty: Question['difficulty'], content: string, options: string[], correct: number, solution: string): Question => ({
  id,
  type: 'SINGLE_CHOICE',
  difficulty,
  chapter,
  content,
  statements: options.map((text, i) => ({ label: 'ABCD'[i], content: text, correct: i === correct })),
  solution,
});

const tf = (id: string, chapter: string, difficulty: Question['difficulty'], content: string, items: Array<[string, boolean]>, solution: string): Question => ({
  id,
  type: 'TRUE_FALSE',
  difficulty,
  chapter,
  content,
  statements: items.map(([text, correct], i) => ({ label: 'abcd'[i], content: text, correct })),
  solution,
});

const sa = (id: string, chapter: string, difficulty: Question['difficulty'], content: string, answer: string, solution: string): Question => ({
  id,
  type: 'SHORT_ANSWER',
  difficulty,
  chapter,
  content,
  statements: [],
  answer,
  solution,
});

export const questions: Question[] = [
  sc(
    'q01', '12C1', 'NB',
    r`Cho hàm số $y=\frac{a x+b}{c x+d}$ có đồ thị như hình bên. Tiệm cận đứng của đồ thị hàm số là
![media:9001](media:9001)`,
    [r`$x=1$.`, r`$x=2$.`, r`$y=1$.`, r`$y=2$.`],
    0,
    r`Từ đồ thị, khi $x \to 1$ thì $|y| \to +\infty$ nên đường thẳng $x=1$ là tiệm cận đứng.
Đường $y=2$ là tiệm cận **ngang**, dễ nhầm với tiệm cận đứng.`,
  ),
  sc(
    'q02', '12C1', 'TH',
    r`Hàm số $y=x^{3}-3 x^{2}+2$ nghịch biến trên khoảng nào dưới đây?`,
    [r`$(0 ; 2)$.`, r`$(-\infty ; 0)$.`, r`$(2 ;+\infty)$.`, r`$(-1 ; 1)$.`],
    0,
    r`Ta có $y^{\prime}=3 x^{2}-6 x=3 x(x-2)$.
$$y^{\prime}<0 \Leftrightarrow 0<x<2$$
Vậy hàm số nghịch biến trên $(0 ; 2)$.`,
  ),
  sc(
    'q03', '12C1', 'VD',
    r`Giá trị lớn nhất của hàm số $f(x)=x+\frac{4}{x}$ trên đoạn $[1 ; 4]$ bằng`,
    [r`$4$.`, r`$5$.`, r`$6$.`, r`$\frac{17}{4}$.`],
    1,
    r`$$f^{\prime}(x)=1-\frac{4}{x^{2}}=0 \Leftrightarrow x=2 \in[1 ; 4]$$
Ta có $f(1)=5, f(2)=4, f(4)=5$.
Vậy $\max _{[1 ; 4]} f(x)=5$.`,
  ),
  sc(
    'q04', '12C4', 'NB',
    r`Họ nguyên hàm của hàm số $f(x)=x^{2}$ là`,
    [r`$\frac{x^{3}}{3}+C$.`, r`$2 x+C$.`, r`$x^{3}+C$.`, r`$\frac{x^{2}}{2}+C$.`],
    0,
    r`Áp dụng $\int x^{n} \mathrm{~d} x=\frac{x^{n+1}}{n+1}+C$ với $n=2$, ta được $\int x^{2} \mathrm{~d} x=\frac{x^{3}}{3}+C$.`,
  ),
  sc(
    'q05', '12C4', 'TH',
    r`Tích phân $\int_{0}^{1}(2 x+1) \mathrm{d} x$ bằng`,
    [r`$1$.`, r`$2$.`, r`$3$.`, r`$\frac{3}{2}$.`],
    1,
    r`$$\int_{0}^{1}(2 x+1) \mathrm{d} x=\left.\left(x^{2}+x\right)\right|_{0} ^{1}=2-0=2$$`,
  ),
  sc(
    'q06', '12C4', 'VD',
    r`Diện tích $S$ của hình phẳng giới hạn bởi hai đồ thị $y=x^{2}$ và $y=x$ bằng`,
    [r`$\frac{1}{6}$.`, r`$\frac{1}{3}$.`, r`$\frac{1}{2}$.`, r`$\frac{5}{6}$.`],
    0,
    r`Phương trình hoành độ giao điểm: $x^{2}=x \Leftrightarrow x=0$ hoặc $x=1$. Trên $[0 ; 1]$ ta có $x \geq x^{2}$.
![media:9003](media:9003)
$$S=\int_{0}^{1}\left(x-x^{2}\right) \mathrm{d} x=\left.\left(\frac{x^{2}}{2}-\frac{x^{3}}{3}\right)\right|_{0} ^{1}=\frac{1}{6}$$`,
  ),
  sc(
    'q07', '11C6', 'NB',
    r`Giá trị của $\log _{2} 8$ bằng`,
    [r`$4$.`, r`$3$.`, r`$\frac{1}{3}$.`, r`$16$.`],
    1,
    r`Vì $2^{3}=8$ nên $\log _{2} 8=3$.`,
  ),
  sc(
    'q08', '11C6', 'TH',
    r`Nghiệm của phương trình $2^{x+1}=8$ là`,
    [r`$x=3$.`, r`$x=1$.`, r`$x=2$.`, r`$x=4$.`],
    2,
    r`$2^{x+1}=2^{3} \Leftrightarrow x+1=3 \Leftrightarrow x=2$.`,
  ),
  sc(
    'q09', '11C7', 'TH',
    r`Cho hình chóp $S . A B C D$ có đáy $A B C D$ là hình vuông và $S A \perp(A B C D)$ (hình bên). Đường thẳng $B C$ vuông góc với mặt phẳng nào sau đây?
![media:9002](media:9002)`,
    [r`$(S A B)$.`, r`$(S A C)$.`, r`$(S C D)$.`, r`$(S B D)$.`],
    0,
    r`Ta có $B C \perp A B$ (vì $A B C D$ là hình vuông) và $B C \perp S A$ (vì $S A \perp(A B C D)$).
Mà $A B, S A$ cắt nhau và cùng nằm trong $(S A B)$ nên $B C \perp(S A B)$.`,
  ),
  sc(
    'q10', '12C5', 'NB',
    r`Trong không gian $O x y z$, mặt phẳng $(P): 2 x-y+3 z-1=0$ có một vectơ pháp tuyến là`,
    [r`$\vec{n}=(2 ;-1 ; 3)$.`, r`$\vec{n}=(2 ; 1 ; 3)$.`, r`$\vec{n}=(-1 ; 3 ;-1)$.`, r`$\vec{n}=(2 ;-1 ;-1)$.`],
    0,
    r`Mặt phẳng $a x+b y+c z+d=0$ có vectơ pháp tuyến $\vec{n}=(a ; b ; c)$, nên $\vec{n}=(2 ;-1 ; 3)$.`,
  ),
  sc(
    'q11', '12C3', 'TH',
    r`Một mẫu số liệu ghép nhóm có nhóm đầu tiên là $[10 ; 15)$ và nhóm cuối cùng là $[35 ; 40)$. Khoảng biến thiên của mẫu số liệu đó là`,
    [r`$25$.`, r`$30$.`, r`$35$.`, r`$5$.`],
    1,
    r`Khoảng biến thiên bằng đầu mút phải của nhóm cuối trừ đầu mút trái của nhóm đầu: $R=40-10=30$.`,
  ),
  sc(
    'q12', '11C9', 'TH',
    r`Đạo hàm của hàm số $y=\sin 2 x$ là`,
    [r`$y^{\prime}=\cos 2 x$.`, r`$y^{\prime}=-2 \cos 2 x$.`, r`$y^{\prime}=2 \cos 2 x$.`, r`$y^{\prime}=2 \sin x$.`],
    2,
    r`Áp dụng $(\sin u)^{\prime}=u^{\prime} \cos u$ với $u=2 x$: $y^{\prime}=2 \cos 2 x$.`,
  ),
  tf(
    't01', '12C1', 'TH',
    r`Cho hàm số $f(x)=x^{3}-3 x+1$.`,
    [
      [r`Đạo hàm của hàm số là $f^{\prime}(x)=3 x^{2}-3$.`, true],
      [r`Hàm số đồng biến trên khoảng $(-1 ; 1)$.`, false],
      [r`Giá trị cực tiểu của hàm số bằng $-1$.`, true],
      [r`Giá trị lớn nhất của $f(x)$ trên đoạn $[0 ; 2]$ bằng $3$.`, true],
    ],
    r`a) ĐÚNG. $f^{\prime}(x)=3 x^{2}-3$.
b) SAI. $f^{\prime}(x)<0 \Leftrightarrow-1<x<1$ nên hàm số **nghịch biến** trên $(-1 ; 1)$.
c) ĐÚNG. Hàm số đạt cực tiểu tại $x=1$, $f(1)=1-3+1=-1$.
d) ĐÚNG. $f(0)=1, f(1)=-1, f(2)=3$ nên $\max _{[0 ; 2]} f(x)=3$.`,
  ),
  tf(
    't02', '12C4', 'VD',
    r`Cho $F(x)$ là một nguyên hàm của $f(x)=2 x+\cos x$ thỏa mãn $F(0)=1$.`,
    [
      [r`$F(x)=x^{2}+\sin x+C$ với $C$ là hằng số.`, true],
      [r`$C=0$.`, false],
      [r`$F\left(\frac{\pi}{2}\right)=\frac{\pi^{2}}{4}+2$.`, true],
      [r`$\int_{0}^{\pi} f(x) \mathrm{d} x=\pi^{2}$.`, true],
    ],
    r`a) ĐÚNG. $\int(2 x+\cos x) \mathrm{d} x=x^{2}+\sin x+C$.
b) SAI. $F(0)=C=1$.
c) ĐÚNG. $F\left(\frac{\pi}{2}\right)=\frac{\pi^{2}}{4}+1+1=\frac{\pi^{2}}{4}+2$.
d) ĐÚNG.
$$\int_{0}^{\pi} f(x) \mathrm{d} x=F(\pi)-F(0)=\left(\pi^{2}+0+1\right)-1=\pi^{2}$$`,
  ),
  tf(
    't03', '12C5', 'TH',
    r`Trong không gian $O x y z$, cho hai điểm $A(1 ; 2 ;-1)$ và $B(3 ; 0 ; 1)$.`,
    [
      [r`$\overrightarrow{A B}=(2 ;-2 ; 2)$.`, true],
      [r`$A B=2 \sqrt{3}$.`, true],
      [r`Trung điểm của đoạn $A B$ là $I(2 ; 1 ; 0)$.`, true],
      [r`Mặt cầu đường kính $A B$ có bán kính bằng $2 \sqrt{3}$.`, false],
    ],
    r`a) ĐÚNG. $\overrightarrow{A B}=(3-1 ; 0-2 ; 1+1)=(2 ;-2 ; 2)$.
b) ĐÚNG. $A B=\sqrt{4+4+4}=2 \sqrt{3}$.
c) ĐÚNG. $I\left(\frac{1+3}{2} ; \frac{2+0}{2} ; \frac{-1+1}{2}\right)=(2 ; 1 ; 0)$.
d) SAI. Bán kính bằng $\frac{A B}{2}=\sqrt{3}$.`,
  ),
  sa(
    's01', '12C4', 'TH',
    r`Tính tích phân $I=\int_{1}^{2} \frac{2}{x} \mathrm{~d} x$ (kết quả làm tròn đến hàng phần trăm).`,
    '1,39',
    r`$$I=\left.2 \ln |x|\right|_{1} ^{2}=2 \ln 2 \approx 1,39$$`,
  ),
  sa(
    's02', '12C1', 'VD',
    r`Người ta làm một chiếc hộp không nắp có đáy là hình vuông cạnh $x$ (dm) và thể tích bằng $32 \mathrm{dm}^{3}$. Hỏi $x$ bằng bao nhiêu để tốn ít vật liệu nhất?`,
    '4',
    r`Chiều cao $h=\frac{32}{x^{2}}$. Diện tích vật liệu:
$$S(x)=x^{2}+4 x h=x^{2}+\frac{128}{x}, \quad x>0$$
$S^{\prime}(x)=2 x-\frac{128}{x^{2}}=0 \Leftrightarrow x^{3}=64 \Leftrightarrow x=4$.
Lập bảng biến thiên, $S(x)$ nhỏ nhất khi $x=4$.`,
  ),
  sa(
    's03', '11C6', 'TH',
    r`Bất phương trình $\log _{3}(x-1)<2$ có bao nhiêu nghiệm nguyên?`,
    '8',
    r`Điều kiện $x>1$. Ta có $\log _{3}(x-1)<2 \Leftrightarrow 0<x-1<9 \Leftrightarrow 1<x<10$.
Các nghiệm nguyên là $2,3, \ldots, 9$: có $8$ nghiệm.`,
  ),
  sa(
    's04', '10C9', 'TH',
    r`Một hộp có $5$ viên bi đỏ và $3$ viên bi xanh. Lấy ngẫu nhiên đồng thời $2$ viên. Tính xác suất để cả hai viên đều màu đỏ (làm tròn đến hàng phần trăm).`,
    '0,36',
    r`$$P=\frac{C_{5}^{2}}{C_{8}^{2}}=\frac{10}{28}=\frac{5}{14} \approx 0,36$$`,
  ),
];

/** Ảnh minh hoạ tự vẽ cho mock, thay cho bảng `media` + MinIO ở production. */
export const mockMedia: Record<string, { src: string; alt: string; width: number; height: number }> = {
  '9001': { src: '/mock/media/do-thi-ham-phan-thuc.svg', alt: 'Đồ thị hàm phân thức có tiệm cận đứng x = 1 và tiệm cận ngang y = 2', width: 340, height: 300 },
  '9002': { src: '/mock/media/hinh-chop-sabcd.svg', alt: 'Hình chóp S.ABCD, đáy là hình vuông, SA vuông góc với đáy', width: 340, height: 290 },
  '9003': { src: '/mock/media/dien-tich-hinh-phang.svg', alt: 'Hình phẳng giới hạn bởi y = x và y = x² trên đoạn từ 0 đến 1 được tô màu', width: 300, height: 280 },
};
