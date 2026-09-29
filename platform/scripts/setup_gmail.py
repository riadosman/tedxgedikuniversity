"""Local-only Gmail setup. Credentials never enter command arguments or logs."""

import queue
import re
import smtplib
import ssl
import threading
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import ttk

from dotenv import set_key

ROOT = Path(__file__).resolve().parents[2]


def configure(address, password):
    address = address.strip()
    password = password.replace(" ", "").strip()
    if not re.fullmatch(r"[^\s@]+@(?:gmail|googlemail)\.com", address, re.I):
        raise ValueError("Gmail adresinizi kontrol edin.")
    if not re.fullmatch(r"[a-zA-Z]{16}", password):
        raise ValueError("Google'ın oluşturduğu 16 harfli uygulama şifresini girin.")
    with smtplib.SMTP("smtp.gmail.com", 587, timeout=15) as smtp:
        smtp.ehlo()
        smtp.starttls(context=ssl.create_default_context())
        smtp.ehlo()
        smtp.login(address, password)
    # Authenticate only: do not send messages or drain an existing mail queue here.
    for key, value in {
        "EMAIL_BACKEND": "django.core.mail.backends.smtp.EmailBackend",
        "EMAIL_HOST": "smtp.gmail.com",
        "EMAIL_PORT": "587",
        "EMAIL_USE_TLS": "true",
        "EMAIL_HOST_USER": address,
        "EMAIL_HOST_PASSWORD": password,
        "DEFAULT_FROM_EMAIL": address,
    }.items():
        set_key(str(ROOT / ".env"), key, value)
    (ROOT / ".local").mkdir(exist_ok=True)
    (ROOT / ".local/gmail-configured.txt").write_text("SMTP authentication verified.\n", encoding="utf-8")


def main():
    window = tk.Tk()
    window.title("TEDxGedik · Gmail bağlantısı")
    window.geometry("560x430")
    window.resizable(False, False)
    frame = ttk.Frame(window, padding=28)
    frame.pack(fill="both", expand=True)
    ttk.Label(frame, text="Doğrulama e-postalarını Gmail ile gönder", font=("Segoe UI", 15, "bold")).pack(
        anchor="w"
    )
    ttk.Label(
        frame,
        text="Bilgiler yalnızca bu bilgisayardaki .env dosyasına kaydedilir.\nNormal Gmail şifrenizi kullanmayın.",
        padding=(0, 12),
    ).pack(anchor="w")
    ttk.Button(
        frame,
        text="Google uygulama şifresi oluştur",
        command=lambda: webbrowser.open("https://myaccount.google.com/apppasswords"),
    ).pack(anchor="w", pady=(0, 16))
    ttk.Label(frame, text="Gmail adresi").pack(anchor="w")
    address = ttk.Entry(frame, width=65)
    address.pack(fill="x", pady=(5, 14))
    ttk.Label(frame, text="16 harfli uygulama şifresi").pack(anchor="w")
    password = ttk.Entry(frame, show="•", width=65)
    password.pack(fill="x", pady=(5, 16))
    status = tk.StringVar(value="Bağlantı kontrol edilir; bu işlem e-posta göndermez.")
    results = queue.Queue()

    def submit():
        button.state(["disabled"])
        status.set("Google bağlantısı kontrol ediliyor…")
        email_value, password_value = address.get(), password.get()

        def run():
            try:
                configure(email_value, password_value)
                results.put((True, "Gmail bağlandı. Bu pencereyi kapatıp sohbete 'Gmail hazır' yazın."))
            except ValueError as error:
                results.put((False, str(error)))
            except smtplib.SMTPAuthenticationError:
                results.put((False, "Google girişi kabul etmedi. Adresi ve uygulama şifresini kontrol edin."))
            except Exception:
                results.put((False, "Bağlantı kurulamadı. İnternetinizi kontrol edip yeniden deneyin."))

        threading.Thread(target=run, daemon=True).start()

    def poll():
        try:
            success, message = results.get_nowait()
            status.set(message)
            if success:
                password.delete(0, "end")
            else:
                button.state(["!disabled"])
        except queue.Empty:
            pass
        window.after(200, poll)

    button = ttk.Button(frame, text="Bağlan ve kaydet", command=submit)
    button.pack(anchor="w")
    ttk.Label(frame, textvariable=status, wraplength=495, padding=(0, 14)).pack(anchor="w")
    address.focus_set()
    poll()
    window.mainloop()


if __name__ == "__main__":
    main()
