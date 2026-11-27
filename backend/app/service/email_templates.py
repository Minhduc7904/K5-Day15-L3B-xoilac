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


@lru_cache
def _template(name: str) -> Template:
    return Template((TEMPLATES / name).read_text(encoding="utf-8"))


LOGO_PATH = "/brand/examind-mark-email.png"


_PURPOSES = {
    "registration": ("Xác minh email đăng ký", "hoàn tất đăng ký tài khoản Examind"),
    "google_email": ("Xác minh email đăng nhập Google", "xác minh địa chỉ email của bạn"),
    "password_reset": ("Đặt lại mật khẩu", "đặt lại mật khẩu tài khoản Examind"),
}


def verification_email(
    code: str, minutes: int, *, google: bool = False, purpose: str | None = None, site_url: str = ""
) -> EmailContent:
    """`purpose` là registration, google_email hoặc password_reset. `google` giữ cho lời gọi cũ.

    Logo lấy từ `site_url` (frontend công khai) thay vì đính kèm: Gmail hiện ảnh đính kèm như tệp và hay vỡ ảnh.
    """
    subject, action = _PURPOSES[purpose or ("google_email" if google else "registration")]
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
        html=_template("base.html").substitute(
            subject=escape(subject), content=content, logo_url=escape(site_url.rstrip("/") + LOGO_PATH, quote=True)
        ),
    )
