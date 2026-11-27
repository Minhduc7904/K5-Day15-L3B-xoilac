from dataclasses import dataclass
from functools import lru_cache
from html import escape
from pathlib import Path
from string import Template

TEMPLATES = Path(__file__).resolve().parents[1] / "templates" / "email"


@dataclass(frozen=True)
class EmailContent:
    subject: str
    text: str
    html: str
    logo: bytes


@lru_cache
def _template(name: str) -> Template:
    return Template((TEMPLATES / name).read_text(encoding="utf-8"))


@lru_cache
def _logo() -> bytes:
    return (TEMPLATES / "examind-mark.png").read_bytes()


def verification_email(code: str, minutes: int, *, google: bool) -> EmailContent:
    subject = "Xác minh email đăng nhập Google" if google else "Xác minh email đăng ký"
    action = "xác minh địa chỉ email của bạn" if google else "hoàn tất đăng ký tài khoản Examind"
    content = _template("otp.html").substitute(
        subject=escape(subject), action=escape(action), code=escape(code), minutes=minutes
    )
    return EmailContent(
        subject=f"[Examind] {subject}",
        text=(
            f"Nhập mã {code} để {action}.\n"
            f"Mã có hiệu lực trong {minutes} phút. Hãy giữ mã cho riêng bạn.\n"
            "Nếu bạn không yêu cầu mã này, hãy bỏ qua email."
        ),
        html=_template("base.html").substitute(subject=escape(subject), content=content),
        logo=_logo(),
    )
