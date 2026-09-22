import React, {useEffect, useState} from "react";
import {createRoot} from "react-dom/client";
import "./style.css";
import {DomLocalizer, LangProvider, detectLang, t, useLang} from "./i18n";

const API = import.meta.env.VITE_API_URL || "";

type MenuKind = "overview" | "plans" | "trial" | "connection" | "support" | "custom";
type MenuItem = {slug: string; title: string; kind: MenuKind; body?: string};

const FALLBACK_MENU: MenuItem[] = [
  {slug: "overview", title: "Обзор", kind: "overview"},
  {slug: "plans", title: "Тарифы", kind: "plans"},
  {slug: "trial", title: "Пробный период", kind: "trial"},
  {slug: "connection", title: "Подключение", kind: "connection"},
  {slug: "support", title: "Поддержка", kind: "support"},
];

const PLATFORM_ORDER = ["android", "ios", "tv", "windows", "macos", "linux"] as const;
const PLATFORM_LABELS: Record<string, string> = {
  android: "Android",
  ios: "iOS",
  tv: "TV",
  windows: "Windows",
  macos: "macOS",
  linux: "Linux",
};

const PLATFORM_GUIDES: Record<string, string> = {
  android: "Установите совместимый VPN-клиент, импортируйте ссылку подписки и подключитесь.",
  ios: "Установите совместимый VPN-клиент из App Store, импортируйте ссылку подписки и подключитесь.",
  tv: "Откройте VPN-клиент на ТВ, добавьте подписку по ссылке или QR и активируйте профиль.",
  windows: "Установите клиент для Windows, импортируйте ссылку подписки и включите соединение.",
  macos: "Установите клиент для macOS, импортируйте ссылку подписки и подключитесь.",
  linux: "Установите клиент для Linux, импортируйте ссылку подписки через конфиг или URI.",
};

function csrf(): string {
  return decodeURIComponent(document.cookie.split("; ").find((x) => x.startsWith("rw_csrf="))?.split("=")[1] || "");
}

async function req(path: string, opts: RequestInit = {}) {
  const method = (opts.method || "GET").toString().toUpperCase();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...((opts.headers as Record<string, string>) || {}),
  };
  if (method !== "GET") headers["X-CSRF-Token"] = csrf();
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), 12000);
  try {
    const r = await fetch(API + path, {...opts, headers, credentials: "include", signal: ctrl.signal});
    let d: any = {};
    try {
      d = await r.json();
    } catch {}
    if (!r.ok) throw Error(d.detail || d.message || `HTTP ${r.status}`);
    return d;
  } finally {
    clearTimeout(timer);
  }
}

function pickProvider(providers: string[] | undefined): string {
  const list = Array.isArray(providers) ? providers.map(String) : [];
  const sandbox = list.find((p) => p.toLowerCase().includes("sandbox"));
  return sandbox || list[0] || "";
}

function formatDate(value?: string | null) {
  if (!value) return "—";
  try {
    return new Date(value).toLocaleDateString();
  } catch {
    return String(value);
  }
}

function isHtml(body?: string) {
  return Boolean(body && /<\/?[a-z][\s\S]*>/i.test(body));
}

function App() {
  const {lang, setLang} = useLang();
  const [booting, setBooting] = useState(true);
  const [authed, setAuthed] = useState(false);
  const [authMode, setAuthMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");
  const [msgError, setMsgError] = useState(false);

  const [cfg, setCfg] = useState<any>({});
  const [menu, setMenu] = useState<MenuItem[]>(FALLBACK_MENU);
  const [tab, setTab] = useState("overview");
  const [dash, setDash] = useState<any>();
  const [plans, setPlans] = useState<any[]>([]);
  const [provider, setProvider] = useState("");
  const [promo, setPromo] = useState("");
  const [connection, setConnection] = useState<any>();
  const [platform, setPlatform] = useState<string>("android");
  const [ticket, setTicket] = useState({subject: "", message: ""});
  const [copied, setCopied] = useState(false);

  function flash(text: string, error = false) {
    setMsg(text);
    setMsgError(error);
  }

  async function loadPublic() {
    try {
      const conf = await req("/api/public/config");
      setCfg(conf);
      setProvider(pickProvider(conf.payment_providers));
      if (!localStorage.getItem("rw_lang")) setLang(detectLang(conf.default_language));
      document.title = conf.app_name ? `${conf.app_name} · ${t("Личный кабинет")}` : t("Личный кабинет");
    } catch {
      setCfg({});
    }
  }

  async function loadMenu() {
    try {
      const items = await req("/api/public/cabinet-menu");
      const list: MenuItem[] = Array.isArray(items) ? items : items?.items || [];
      const normalized = list
        .filter((x) => x && x.slug && x.title)
        .map((x) => ({
          slug: String(x.slug),
          title: String(x.title),
          kind: (x.kind || "custom") as MenuKind,
          body: x.body || "",
        }));
      if (normalized.length) {
        setMenu(normalized);
        setTab((prev) => (normalized.some((m) => m.slug === prev) ? prev : normalized[0].slug));
        return;
      }
    } catch {}
    setMenu(FALLBACK_MENU);
  }

  async function loadSession() {
    const [dashboard, planList] = await Promise.all([req("/api/me/dashboard"), req("/api/plans")]);
    setDash(dashboard);
    setPlans(Array.isArray(planList) ? planList : []);
    setAuthed(true);
    try {
      const info = await req("/api/me/connection-info");
      setConnection(info);
      const keys = Object.keys(info?.platforms || {});
      if (keys.length) setPlatform(keys.includes("android") ? "android" : keys[0]);
    } catch {
      setConnection(null);
    }
  }

  useEffect(() => {
    const tg = (window as any).Telegram?.WebApp;
    tg?.ready?.();
    const code = new URLSearchParams(location.search).get("code");
    (async () => {
      await loadPublic();
      await loadMenu();
      try {
        if (tg?.initData) {
          await req("/api/auth/telegram", {method: "POST", body: JSON.stringify({initData: tg.initData})});
        } else if (code) {
          await req("/api/auth/exchange", {method: "POST", body: JSON.stringify({code})});
          const url = new URL(location.href);
          url.searchParams.delete("code");
          history.replaceState({}, "", url.pathname + url.search + url.hash);
        }
        await loadSession();
      } catch (e: any) {
        setAuthed(false);
        if (code) flash(e.message || t("Ошибка"), true);
      } finally {
        setBooting(false);
      }
    })();
  }, []);

  async function submitAuth(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    flash("");
    try {
      const path = authMode === "login" ? "/api/auth/login" : "/api/auth/register";
      await req(path, {method: "POST", body: JSON.stringify({email: email.trim(), password})});
      await loadSession();
      flash(authMode === "login" ? t("Добро пожаловать") : t("Создать аккаунт"));
    } catch (err: any) {
      flash(err.message || t("Ошибка"), true);
    } finally {
      setBusy(false);
    }
  }

  async function authTelegram() {
    setBusy(true);
    flash("");
    try {
      const initData = (window as any).Telegram?.WebApp?.initData;
      if (!initData) throw Error("Telegram WebApp initData недоступен");
      await req("/api/auth/telegram", {method: "POST", body: JSON.stringify({initData})});
      await loadSession();
    } catch (err: any) {
      flash(err.message || t("Ошибка"), true);
    } finally {
      setBusy(false);
    }
  }

  function oauthRedirect(path: string) {
    location.href = API + path;
  }

  async function buy(plan: any) {
    setBusy(true);
    flash("");
    try {
      const r = await req("/api/payments/create", {
        method: "POST",
        headers: {"Idempotency-Key": crypto.randomUUID()},
        body: JSON.stringify({plan_id: plan.id, provider: provider || undefined, promo_code: promo || undefined}),
      });
      if (r.url) location.href = r.url;
      else {
        flash(t("Платёж создан"));
        await loadSession();
      }
    } catch (err: any) {
      flash(err.message || t("Ошибка"), true);
    } finally {
      setBusy(false);
    }
  }

  async function buyWallet(plan: any) {
    setBusy(true);
    flash("");
    try {
      await req("/api/me/wallet/spend", {
        method: "POST",
        headers: {"Idempotency-Key": crypto.randomUUID()},
        body: JSON.stringify({plan_id: plan.id, promo_code: promo || undefined}),
      });
      flash(t("Оплачено с баланса"));
      await loadSession();
    } catch (err: any) {
      flash(err.message || t("Ошибка"), true);
    } finally {
      setBusy(false);
    }
  }

  async function claimTrial(planId: number) {
    setBusy(true);
    flash("");
    try {
      const days = Number(cfg.trial_days || 3);
      await req("/api/me/trial", {method: "POST", body: JSON.stringify({plan_id: planId, days})});
      flash(t("Пробный период активирован"));
      await loadSession();
    } catch (err: any) {
      flash(err.message || t("Ошибка"), true);
    } finally {
      setBusy(false);
    }
  }

  async function copyLink(url: string) {
    try {
      await navigator.clipboard?.writeText(url);
      setCopied(true);
      flash(t("Скопировано"));
      setTimeout(() => setCopied(false), 1600);
    } catch {
      flash(t("Ошибка"), true);
    }
  }

  async function sendTicket(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    flash("");
    try {
      await req("/api/me/support/tickets", {method: "POST", body: JSON.stringify(ticket)});
      setTicket({subject: "", message: ""});
      flash(t("Тикет создан"));
    } catch (err: any) {
      flash(err.message || t("Ошибка"), true);
    } finally {
      setBusy(false);
    }
  }

  async function logout() {
    try {
      await req("/api/auth/logout", {method: "POST", body: "{}"});
    } catch {}
    setAuthed(false);
    setDash(undefined);
    setConnection(undefined);
  }

  const brand = cfg.app_name || cfg.bot_name || "Магазин VPN";
  const currency = cfg.currency || "₽";
  const sub = dash?.subscription;
  const subUrl = connection?.subscription_url || sub?.subscription_url || "";
  const activeItem = menu.find((m) => m.slug === tab) || menu[0];
  const platforms = connection?.platforms || {};
  const platformKeys = PLATFORM_ORDER.filter((k) => k in platforms).concat(
    Object.keys(platforms).filter((k) => !(PLATFORM_ORDER as readonly string[]).includes(k)),
  );
  const apiGuide = platforms[platform] ? String(platforms[platform]) : "";
  const guideText = PLATFORM_GUIDES[platform] || apiGuide;

  if (booting) {
    return (
      <DomLocalizer>
        <div className="loading">Загрузка…</div>
      </DomLocalizer>
    );
  }

  return (
    <DomLocalizer>
      <div className="app-shell">
        <div className="topbar">
          <div className="brand-mark">
            <span className="orb" aria-hidden />
            <span>{brand}</span>
          </div>
          <div className="btn-row">
            <button type="button" className="btn-ghost" onClick={() => setLang(lang === "ru" ? "en" : "ru")}>
              {lang === "ru" ? "EN" : "RU"}
            </button>
            {authed && (
              <button type="button" className="btn-ghost" onClick={logout}>
                Выйти
              </button>
            )}
          </div>
        </div>

        <header className="hero">
          <h1>{brand}</h1>
          <p>{authed ? "Управляйте подпиской, тарифами и подключением" : "Безопасный доступ к сети"}</p>
        </header>

        {!authed ? (
          <section className="auth-layout">
            <div className="form-card">
              <div className="auth-switch">
                <button type="button" className={`tab ${authMode === "login" ? "active" : ""}`} onClick={() => setAuthMode("login")}>
                  Вход
                </button>
                <button type="button" className={`tab ${authMode === "register" ? "active" : ""}`} onClick={() => setAuthMode("register")}>
                  Регистрация
                </button>
              </div>
              <form className="stack" onSubmit={submitAuth}>
                <label className="field">
                  Электронная почта
                  <input
                    type="email"
                    autoComplete="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="Электронная почта"
                  />
                </label>
                <label className="field">
                  Пароль
                  <input
                    type="password"
                    autoComplete={authMode === "login" ? "current-password" : "new-password"}
                    required
                    minLength={8}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Пароль"
                  />
                </label>
                <button className="btn-primary" type="submit" disabled={busy}>
                  {authMode === "login" ? "Войти" : "Создать аккаунт"}
                </button>
              </form>
              <button
                type="button"
                className="btn-soft"
                style={{marginTop: 12, width: "100%"}}
                onClick={() => setAuthMode(authMode === "login" ? "register" : "login")}
              >
                {authMode === "login" ? "Нет аккаунта? Зарегистрироваться" : "Уже есть аккаунт? Войти"}
              </button>
            </div>

            <div className="form-card stack">
              <div className="divider">или</div>
              <button type="button" className="btn-oauth" disabled={busy} onClick={authTelegram}>
                Войти через Telegram
              </button>
              <button type="button" className="btn-oauth" disabled={busy} onClick={() => oauthRedirect("/api/auth/yandex")}>
                Войти через Яндекс
              </button>
              <button type="button" className="btn-oauth" disabled={busy} onClick={() => oauthRedirect("/api/auth/vk")}>
                Войти через VK
              </button>
            </div>
          </section>
        ) : (
          <>
            <nav className="tabs" aria-label="Разделы кабинета">
              {menu.map((item) => (
                <button
                  key={item.slug}
                  type="button"
                  className={`tab ${tab === item.slug ? "active" : ""}`}
                  onClick={() => setTab(item.slug)}
                >
                  {item.title}
                </button>
              ))}
            </nav>

            <section className="panel">
              {activeItem?.kind === "overview" && (
                <>
                  <h2 className="section-title">Обзор</h2>
                  <p className="section-sub">Подписка и балансы вашего аккаунта</p>
                  <div className="metrics">
                    <div className="metric">
                      <span className="label">Подписка</span>
                      <span className={`value ${sub?.expires_at ? "ok" : "warn"}`}>
                        {sub?.expires_at ? "Активна" : "Неактивна"}
                      </span>
                    </div>
                    <div className="metric">
                      <span className="label">Истекает</span>
                      <span className="value">{sub?.expires_at ? formatDate(sub.expires_at) : "Нет активной подписки"}</span>
                    </div>
                    <div className="metric">
                      <span className="label">Кошелёк</span>
                      <span className="value">{dash?.user?.wallet_balance || "0.00"} {currency}</span>
                    </div>
                  </div>
                  <div className="metrics">
                    <div className="metric">
                      <span className="label">Реферальный баланс</span>
                      <span className="value">{dash?.user?.referral_balance || "0.00"} {currency}</span>
                    </div>
                    <div className="metric">
                      <span className="label">Статус</span>
                      <span className="value">{sub?.expires_at ? `Активна до ${formatDate(sub.expires_at)}` : "Нет активной подписки"}</span>
                    </div>
                    <div className="metric">
                      <span className="label">Код</span>
                      <span className="value">{dash?.user?.referral_code || "—"}</span>
                    </div>
                  </div>
                </>
              )}

              {activeItem?.kind === "plans" && (
                <>
                  <h2 className="section-title">Тарифы</h2>
                  <p className="section-sub">Выберите тариф и способ оплаты</p>
                  <div className="form-card stack" style={{marginBottom: 14}}>
                    <label className="field">
                      Промокод
                      <input value={promo} onChange={(e) => setPromo(e.target.value.toUpperCase())} placeholder="Промокод" />
                    </label>
                    {(cfg.payment_providers || []).length > 0 && (
                      <label className="field">
                        Провайдер оплаты
                        <select value={provider} onChange={(e) => setProvider(e.target.value)}>
                          {(cfg.payment_providers || []).map((p: string) => (
                            <option key={p} value={p}>
                              {p}
                            </option>
                          ))}
                        </select>
                      </label>
                    )}
                  </div>
                  <div className="plan-list">
                    {plans.map((p) => (
                      <article className="plan-item" key={p.id}>
                        <div>
                          <h3>{p.name}</h3>
                          <p className="price">
                            {p.final_price ?? p.price} {currency} · {p.duration_days} дней
                          </p>
                        </div>
                        <div className="btn-row">
                          <button type="button" className="btn-primary" disabled={busy || !provider} onClick={() => buy(p)}>
                            Оплатить
                          </button>
                          <button type="button" className="btn-ghost" disabled={busy} onClick={() => buyWallet(p)}>
                            С баланса
                          </button>
                        </div>
                      </article>
                    ))}
                    {!plans.length && <p className="section-sub">Выберите тариф</p>}
                  </div>
                </>
              )}

              {activeItem?.kind === "trial" && (
                <>
                  <h2 className="section-title">Пробный период</h2>
                  <p className="section-sub">
                    Пробный период · {cfg.trial_days || 3} дней
                  </p>
                  <div className="plan-list">
                    {plans.map((p) => (
                      <article className="plan-item" key={p.id}>
                        <div>
                          <h3>{p.name}</h3>
                          <p className="section-sub" style={{margin: 0}}>
                            {cfg.trial_days || 3} дней бесплатно
                          </p>
                        </div>
                        <button type="button" className="btn-primary" disabled={busy} onClick={() => claimTrial(p.id)}>
                          Активировать пробный период
                        </button>
                      </article>
                    ))}
                    {!plans.length && <p className="section-sub">Выберите тариф для пробного периода</p>}
                  </div>
                </>
              )}

              {activeItem?.kind === "connection" && (
                <>
                  <h2 className="section-title">Подключение</h2>
                  <p className="section-sub">Ссылка подписки и инструкции по устройствам</p>
                  {subUrl ? (
                    <div className="form-card stack">
                      <label className="field">
                        Ссылка подписки
                        <div className="link-box">
                          <input readOnly value={subUrl} />
                          <button type="button" className="btn-primary" onClick={() => copyLink(subUrl)}>
                            {copied ? "Скопировано" : "Копировать ссылку"}
                          </button>
                        </div>
                      </label>
                    </div>
                  ) : (
                    <p className="section-sub">Ссылка подписки пока недоступна</p>
                  )}
                  <h3 className="section-title" style={{marginTop: 22, fontSize: "1.1rem"}}>
                    Инструкции по устройствам
                  </h3>
                  <div className="platform-grid">
                    {(platformKeys.length ? platformKeys : PLATFORM_ORDER).map((key) => (
                      <button
                        key={key}
                        type="button"
                        className={`platform-chip ${platform === key ? "active" : ""}`}
                        onClick={() => setPlatform(key)}
                      >
                        {PLATFORM_LABELS[key] || key}
                      </button>
                    ))}
                  </div>
                  <div className="platform-guide">{guideText || apiGuide}</div>
                </>
              )}

              {activeItem?.kind === "support" && (
                <>
                  <h2 className="section-title">Поддержка</h2>
                  <p className="section-sub">Создайте обращение в службу поддержки</p>
                  <form className="form-card stack" onSubmit={sendTicket}>
                    <label className="field">
                      Тема
                      <input
                        required
                        value={ticket.subject}
                        onChange={(e) => setTicket({...ticket, subject: e.target.value})}
                        placeholder="Тема"
                      />
                    </label>
                    <label className="field">
                      Сообщение
                      <textarea
                        required
                        value={ticket.message}
                        onChange={(e) => setTicket({...ticket, message: e.target.value})}
                        placeholder="Сообщение"
                      />
                    </label>
                    <button className="btn-primary" type="submit" disabled={busy}>
                      Создать тикет
                    </button>
                  </form>
                </>
              )}

              {activeItem?.kind === "custom" && (
                <>
                  <h2 className="section-title">{activeItem.title || "Пользовательский раздел"}</h2>
                  {isHtml(activeItem.body) ? (
                    <div className="custom-body" dangerouslySetInnerHTML={{__html: activeItem.body || ""}} />
                  ) : (
                    <p className="custom-body" style={{whiteSpace: "pre-wrap"}}>
                      {activeItem.body || ""}
                    </p>
                  )}
                </>
              )}
            </section>
          </>
        )}

        {msg && <div className={`toast ${msgError ? "error" : ""}`}>{msg}</div>}
      </div>
    </DomLocalizer>
  );
}

createRoot(document.getElementById("root")!).render(
  <LangProvider>
    <App />
  </LangProvider>,
);
