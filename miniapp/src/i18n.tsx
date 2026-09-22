import React, {createContext, useContext, useEffect, useLayoutEffect, useRef, useState} from "react";

export type Lang = "ru" | "en";

export const EN: Record<string, string> = {
  "Магазин VPN": "VPN shop",
  "Личный кабинет": "Account",
  "Быстрые действия": "Quick actions",
  "Состояние сервиса": "Service status",
  "Все основные компоненты работают нормально": "All core components are operating normally",
  "Есть деградация сервиса — подробности ниже": "The service is degraded — details are below",
  "Уведомления": "Notifications",
  "Прочитано": "Mark read",
  "Новых уведомлений нет.": "No new notifications.",
  "Подписка": "Subscription",
  "Автопродление": "Auto-renew",
  "включено": "enabled",
  "выключено": "disabled",
  "Нет активной подписки": "No active subscription",
  "Копировать ссылку": "Copy link",
  "Открыть": "Open",
  "Тарифы": "Plans",
  "Серверы": "Servers",
  "Конструктор тарифов": "Plan builder",
  "Устройства": "Devices",
  "Трафик": "Traffic",
  "Срок": "Duration",
  "Онлайн": "Online",
  "Офлайн": "Offline",
  "Отключён": "Disabled",
  "Неизвестно": "Unknown",
  "Remnawave недоступен": "Remnawave is unavailable",
  "Промокод": "Promo code",
  "Оплатить": "Pay",
  "С баланса": "Pay from balance",
  "В подарок": "Buy as a gift",
  "Кошелёк": "Wallet",
  "Баланс кошелька": "Wallet balance",
  "Пополнить": "Top up",
  "Сумма пополнения": "Top-up amount",
  "Платёж создан": "Payment created",
  "Оплачено с баланса": "Paid from balance",
  "Подарок создан": "Gift created",
  "Управление подпиской": "Subscription management",
  "Статус": "Status",
  "Отмена": "Cancellation",
  "Возобновить": "Resume",
  "Отменить после окончания": "Cancel at period end",
  "🎁 Активировать подарок": "🎁 Redeem a gift",
  "Платежи": "Payments",
  "Реферальная программа": "Referral program",
  "Код": "Code",
  "Баланс": "Balance",
  "Дополнительная информация": "Additional information",
  "Безопасность": "Security",
  "Отозвать все сессии": "Revoke all sessions",
  "Поддержка": "Support",
  "Тема": "Subject",
  "Сообщение": "Message",
  "Создать тикет": "Create ticket",
  "Тикет создан": "Ticket created",
  "Отмена подписки запланирована": "Subscription cancellation scheduled",
  "Подписка возобновлена": "Subscription resumed",
  "Подарочный код": "Gift code",
  "Подарок активирован": "Gift redeemed",
  "Все сессии отозваны": "All sessions revoked",
  "неизвестно": "unknown",
  "Язык": "Language",
  "Сессий": "Sessions",
  "Устройств": "Devices",
  "дней": "days",
};

let activeLang: Lang = "ru";

export function translate(lang: Lang, value: string): string {
  if (!value || lang !== "en") return value;
  if (EN[value]) return EN[value];
  const active = value.match(/^Активна до (.+)$/);
  if (active) return `Active until ${active[1]}`;
  const days = value.match(/^(.*) · (.*) дней$/);
  if (days) return `${days[1]} · ${days[2]} days`;
  const cancel = value.match(/^Отмена: (.+)$/);
  if (cancel) return `Cancellation: ${cancel[1]}`;
  const auto = value.match(/^Автопродление: (.+)$/);
  if (auto) return `Auto-renew: ${translate(lang, auto[1])}`;
  const status = value.match(/^Статус: (.+)$/);
  if (status) return `Status: ${status[1]}`;
  const code = value.match(/^Код: (.+)$/);
  if (code) return `Code: ${code[1]}`;
  const balance = value.match(/^Баланс: (.+)$/);
  if (balance) return `Balance: ${balance[1]}`;
  const wallet = value.match(/^Баланс кошелька: (.+)$/);
  if (wallet) return `Wallet balance: ${wallet[1]}`;
  const online = value.match(/^Онлайн (\d+) из (\d+)$/);
  if (online) return `Online ${online[1]} of ${online[2]}`;
  return value;
}

export function t(value: string): string {
  return translate(activeLang, value);
}

const LangContext = createContext<{lang: Lang; setLang: (lang: Lang) => void}>({lang: "ru", setLang: () => undefined});

export function detectLang(serverDefault?: string): Lang {
  const stored = localStorage.getItem("rw_lang");
  if (stored === "en" || stored === "ru") return stored;
  if (serverDefault === "en" || serverDefault === "ru") return serverDefault;
  return navigator.language?.toLowerCase().startsWith("en") ? "en" : "ru";
}

export function LangProvider({children}: {children: React.ReactNode}) {
  const [lang, setLangState] = useState<Lang>(detectLang());
  useEffect(() => {
    activeLang = lang;
    document.documentElement.lang = lang;
  }, [lang]);
  function setLang(next: Lang) {
    activeLang = next;
    localStorage.setItem("rw_lang", next);
    setLangState(next);
  }
  return <LangContext.Provider value={{lang, setLang}}>{children}</LangContext.Provider>;
}

export function useLang() {
  return useContext(LangContext);
}

function sourceOf(current: string, stored: string | undefined, lang: Lang): string {
  if (stored && (current === stored || current === translate("en", stored) || current === translate("ru", stored))) return stored;
  return current;
}

export function DomLocalizer({children}: {children: React.ReactNode}) {
  const ref = useRef<HTMLDivElement>(null);
  const {lang} = useLang();
  useLayoutEffect(() => {
    const root = ref.current;
    if (!root) return;
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    const nodes: Text[] = [];
    let current: Node | null = walker.nextNode();
    while (current) {
      nodes.push(current as Text);
      current = walker.nextNode();
    }
    for (const node of nodes) {
      const value = node.nodeValue ?? "";
      const extra = node as Text & {__i18nSource?: string};
      const source = sourceOf(value, extra.__i18nSource, lang);
      extra.__i18nSource = source;
      const next = translate(lang, source);
      if (node.nodeValue !== next) node.nodeValue = next;
    }
    root.querySelectorAll<HTMLElement>("[aria-label]").forEach((el) => {
      const label = el.getAttribute("aria-label") || "";
      const stored = el.dataset.i18nAria;
      const source = sourceOf(label, stored, lang);
      el.dataset.i18nAria = source;
      const next = translate(lang, source);
      if (label !== next) el.setAttribute("aria-label", next);
    });
    root.querySelectorAll<HTMLInputElement | HTMLTextAreaElement>("input,textarea").forEach((el) => {
      const source = sourceOf(el.placeholder || "", el.dataset.i18nPlaceholder, lang);
      el.dataset.i18nPlaceholder = source;
      const next = translate(lang, source);
      if (el.placeholder !== next) el.placeholder = next;
    });
  });
  return <div ref={ref} style={{display: "contents"}}>{children}</div>;
}
