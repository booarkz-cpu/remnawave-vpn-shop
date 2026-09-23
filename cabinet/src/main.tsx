import React, {useEffect, useState} from "react";
import {createRoot} from "react-dom/client";
import "./style.css";
import {DomLocalizer, LangProvider, detectLang, t, useLang} from "./i18n";

const API = import.meta.env.VITE_API_URL || "";

type MenuKind = "overview" | "plans" | "trial" | "connection" | "support" | "servers" | "custom";
type MenuItem = {slug: string; title: string; kind: MenuKind; body?: string};

const FALLBACK_MENU: MenuItem[] = [
  {slug: "overview", title: "Обзор", kind: "overview"},
  {slug: "plans", title: "Тарифы", kind: "plans"},
  {slug: "trial", title: "Пробный период", kind: "trial"},
  {slug: "connection", title: "Подключение", kind: "connection"},
  {slug: "servers", title: "Серверы", kind: "servers"},
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

function defaultPick(row: any) {
  const picked: Record<string, number> = {};
  for (const kind of ["devices", "traffic_gb", "days"]) {
    const opt = (row.options || []).find((o: any) => o.kind === kind && o.enabled !== false);
    if (opt) picked[kind] = opt.id;
  }
  return picked;
}

function constructorTotal(row: any, selected: Record<string, number>) {
  let sum = Number(row.base_price || 0);
  for (const kind of ["devices", "traffic_gb", "days"]) {
    const opt = (row.options || []).find((o: any) => o.id === selected[kind] && o.kind === kind);
    if (opt) sum += Number(opt.price || 0);
  }
  return Math.round(sum * 100) / 100;
}

function serverLabel(status?: string) {
  if (status === "online") return "Онлайн";
  if (status === "offline") return "Офлайн";
  if (status === "disabled") return "Отключён";
  return "Неизвестно";
}

function ServerList({servers}: {servers: any}) {
  const nodes = servers?.nodes || [];
  return (
    <div className="plan-list">
      <p className="section-sub">
        {servers?.ok
          ? `Онлайн ${servers.online ?? 0} из ${servers.total ?? 0}`
          : servers?.error || "Remnawave недоступен"}
      </p>
      {nodes.map((node: any, index: number) => (
        <article className="plan-item" key={`${node.name}-${index}`}>
          <div>
            <h3>{node.name}</h3>
            <p className="section-sub" style={{margin: 0}}>
              {node.country || "—"} · {serverLabel(node.status)}
              {typeof node.users_online === "number" ? ` · ${node.users_online}` : ""}
            </p>
          </div>
        </article>
      ))}
      {!nodes.length && <p className="section-sub">Нет узлов</p>}
    </div>
  );
}

function withServers(list: MenuItem[]) {
  if (list.some((item) => item.kind === "servers")) return list;
  const next = list.slice();
  const at = next.findIndex((item) => item.kind === "support");
  const item: MenuItem = {slug: "servers", title: "Серверы", kind: "servers"};
  if (at >= 0) next.splice(at, 0, item);
  else next.push(item);
  return next;
}

function AppsNotice({apps, lang}: {apps: any[]; lang: string}) {
  if (!apps.length) return null;
  return (
    <section className="form-card stack apps-note">
      <h2 className="section-title">Приложения</h2>
      <p className="section-sub">Для Android и iOS есть отдельные приложения магазина.</p>
      <div className="plan-list">
        {apps.map((row) => {
          const title = lang === "en" ? row.title_en || row.title_ru : row.title_ru || row.title_en;
          const text = lang === "en" ? row.text_en || row.text_ru : row.text_ru || row.text_en;
          const fileHref = typeof row.download_url === "string" && /^\/api\/public\/apps\/(android-user|ios-user)\/download$/.test(row.download_url) ? API + row.download_url : "";
          const storeHref = typeof row.url === "string" && row.url.startsWith("https://") ? row.url : "";
          return (
            <article className="plan-item" key={row.id || title}>
              <div>
                <h3>{title}</h3>
                <p className="section-sub">{text}</p>
              </div>
              {fileHref && <a className="btn-primary" href={fileHref}>Скачать</a>}
              {typeof row.sha256 === "string" && /^[a-f0-9]{64}$/.test(row.sha256) && (
                <p className="section-sub">Контрольная сумма {row.sha256}</p>
              )}
              {storeHref && (
                <a className="btn-primary" href={storeHref} target="_blank" rel="noopener noreferrer">
                  Скачать по ссылке
                </a>
              )}
            </article>
          );
        })}
      </div>
    </section>
  );
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
  const [constructors, setConstructors] = useState<any[]>([]);
  const [pick, setPick] = useState<Record<number, Record<string, number>>>({});
  const [servers, setServers] = useState<any>();
  const [provider, setProvider] = useState("");
  const [promo, setPromo] = useState("");
  const [connection, setConnection] = useState<any>();
  const [platform, setPlatform] = useState<string>("android");
  const [ticket, setTicket] = useState({subject: "", message: ""});
  const [copied, setCopied] = useState(false);
  const [shopApps, setShopApps] = useState<any[]>([]);
  const [clientLogo, setClientLogo] = useState("");

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
    try {
      const apps = await req("/api/public/apps");
      const logo = typeof apps?.logo_url === "string" && apps.logo_url.startsWith("/media/") && !apps.logo_url.includes("..") ? apps.logo_url : "";
      setClientLogo(logo);
      setShopApps(Array.isArray(apps?.apps) ? apps.apps.filter((row: any) => row && row.audience === "user" && row.enabled !== false) : []);
    } catch {
      setClientLogo("");
      setShopApps([]);
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
        const menuWithServers = withServers(normalized);
        setMenu(menuWithServers);
        setTab((prev) => (menuWithServers.some((m) => m.slug === prev) ? prev : menuWithServers[0].slug));
        return;
      }
    } catch {}
    setMenu(FALLBACK_MENU);
  }

  async function loadConstructors() {
    try {
      const rows = await req("/api/tariff-constructors");
      const list = Array.isArray(rows) ? rows : [];
      setConstructors(list);
      setPick((prev) => {
        const next = {...prev};
        for (const row of list) if (!next[row.id]) next[row.id] = defaultPick(row);
        return next;
      });
    } catch {
      setConstructors([]);
    }
  }

  async function loadServers(authed: boolean) {
    try {
      setServers(await req(authed ? "/api/me/servers" : "/api/public/servers"));
    } catch {
      setServers({ok: false, nodes: [], error: "Remnawave недоступен"});
    }
  }

  async function loadSession() {
    const [dashboard, planList] = await Promise.all([req("/api/me/dashboard"), req("/api/plans")]);
    setDash(dashboard);
    setPlans(Array.isArray(planList) ? planList : []);
    setAuthed(true);
    await Promise.all([loadConstructors(), loadServers(true)]);
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
    const params = new URLSearchParams(location.search);
    const code = params.get("code");
    const sandboxPayment = params.get("sandbox_payment");
    (async () => {
      await loadPublic();
      await loadMenu();
      await loadConstructors();
      await loadServers(false);
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
        if (sandboxPayment) {
          try {
            await req("/api/payments/sandbox/complete", {
              method: "POST",
              body: JSON.stringify({payment_id: sandboxPayment}),
            });
            flash(t("Платёж создан"));
            await loadSession();
          } catch (e: any) {
            flash(e.message || t("Ошибка"), true);
          }
          const url = new URL(location.href);
          url.searchParams.delete("sandbox_payment");
          history.replaceState({}, "", url.pathname + url.search + url.hash);
        }
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

  async function buySelection(body: Record<string, unknown>, wallet: boolean) {
    setBusy(true);
    flash("");
    try {
      if (wallet) {
        await req("/api/me/wallet/spend", {
          method: "POST",
          headers: {"Idempotency-Key": crypto.randomUUID()},
          body: JSON.stringify(body),
        });
        flash(t("Оплачено с баланса"));
        await loadSession();
      } else {
        const r = await req("/api/payments/create", {
          method: "POST",
          headers: {"Idempotency-Key": crypto.randomUUID()},
          body: JSON.stringify({...body, provider: provider || undefined}),
        });
        if (r.url) location.href = r.url;
        else {
          flash(t("Платёж создан"));
          await loadSession();
        }
      }
    } catch (err: any) {
      flash(err.message || t("Ошибка"), true);
    } finally {
      setBusy(false);
    }
  }

  function buy(plan: any) {
    return buySelection({plan_id: plan.id, promo_code: promo || undefined}, false);
  }

  function buyWallet(plan: any) {
    return buySelection({plan_id: plan.id, promo_code: promo || undefined}, true);
  }

  function buyConstructor(row: any, wallet: boolean) {
    const selected = pick[row.id] || defaultPick(row);
    return buySelection({
      constructor_id: row.id,
      device_option_id: selected.devices,
      traffic_option_id: selected.traffic_gb,
      days_option_id: selected.days,
      promo_code: promo || undefined,
    }, wallet);
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
            {clientLogo ? <img className="brand-logo" src={API + clientLogo} alt="" /> : <span className="orb" aria-hidden />}
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
        <AppsNotice apps={shopApps} lang={lang} />

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
                  <h3 className="section-title" style={{marginTop: 22, fontSize: "1.1rem"}}>Серверы</h3>
                  <ServerList servers={servers} />
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
                  {constructors.map((row) => {
                    const selected = pick[row.id] || defaultPick(row);
                    const total = constructorTotal(row, selected);
                    return (
                      <article className="form-card stack" key={row.id} style={{marginTop: 14}}>
                        <h3>{row.name}</h3>
                        <p className="section-sub">{row.description || "Соберите тариф: устройства, трафик и срок"}</p>
                        {(["devices", "traffic_gb", "days"] as const).map((kind) => (
                          <label className="field" key={kind}>
                            {kind === "devices" ? "Устройства" : kind === "traffic_gb" ? "Трафик" : "Срок"}
                            <select
                              value={selected[kind] || ""}
                              onChange={(e) =>
                                setPick((prev) => ({
                                  ...prev,
                                  [row.id]: {...(prev[row.id] || defaultPick(row)), [kind]: Number(e.target.value)},
                                }))
                              }
                            >
                              {(row.options || [])
                                .filter((o: any) => o.kind === kind)
                                .map((o: any) => (
                                  <option key={o.id} value={o.id}>
                                    {o.label} · {o.value === 0 && kind === "traffic_gb" ? "Безлимит" : o.value}
                                    {Number(o.price) ? ` · +${o.price}` : ""}
                                  </option>
                                ))}
                            </select>
                          </label>
                        ))}
                        <p className="price">
                          {total} {currency}
                        </p>
                        <div className="btn-row">
                          <button type="button" className="btn-primary" disabled={busy || !provider} onClick={() => buyConstructor(row, false)}>
                            Оплатить
                          </button>
                          <button type="button" className="btn-ghost" disabled={busy} onClick={() => buyConstructor(row, true)}>
                            С баланса
                          </button>
                        </div>
                      </article>
                    );
                  })}
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
                          <a className="btn-primary" href={API + "/api/me/subscription-file"}>Скачать подписку</a>
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

              {activeItem?.kind === "servers" && (
                <>
                  <h2 className="section-title">Серверы</h2>
                  <p className="section-sub">Статус узлов без адресов и служебных данных</p>
                  <ServerList servers={servers} />
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
