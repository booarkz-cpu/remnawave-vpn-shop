import React, {createContext, useContext, useEffect, useLayoutEffect, useRef, useState} from "react";

export type Lang = "ru" | "en";

export const EN: Record<string, string> = {
  "Личный кабинет": "Account",
  "Магазин VPN": "VPN shop",
  "Вход": "Sign in",
  "Регистрация": "Sign up",
  "Электронная почта": "Email",
  "Пароль": "Password",
  "Войти": "Sign in",
  "Создать аккаунт": "Create account",
  "Уже есть аккаунт? Войти": "Already have an account? Sign in",
  "Нет аккаунта? Зарегистрироваться": "No account? Sign up",
  "Войти через Telegram": "Sign in with Telegram",
  "Войти через Яндекс": "Sign in with Yandex",
  "Войти через VK": "Sign in with VK",
  "Обзор": "Overview",
  "Тарифы": "Plans",
  "Пробный период": "Trial",
  "Подключение": "Connection",
  "Поддержка": "Support",
  "Серверы": "Servers",
  "Конструктор тарифов": "Plan builder",
  "Устройства": "Devices",
  "Трафик": "Traffic",
  "Срок": "Duration",
  "Безлимит": "Unlimited",
  "Онлайн": "Online",
  "Офлайн": "Offline",
  "Отключён": "Disabled",
  "Неизвестно": "Unknown",
  "Нет узлов": "No nodes",
  "Remnawave недоступен": "Remnawave is unavailable",
  "Статус узлов без адресов и служебных данных": "Node status without addresses or internal data",
  "Соберите тариф: устройства, трафик и срок": "Build a plan: devices, traffic and duration",
  "Подписка": "Subscription",
  "Статус": "Status",
  "Активна": "Active",
  "Неактивна": "Inactive",
  "Нет активной подписки": "No active subscription",
  "Истекает": "Expires",
  "Кошелёк": "Wallet",
  "Реферальный баланс": "Referral balance",
  "Баланс кошелька": "Wallet balance",
  "Промокод": "Promo code",
  "Оплатить": "Pay",
  "С баланса": "Pay from balance",
  "Платёж создан": "Payment created",
  "Оплачено с баланса": "Paid from balance",
  "Активировать пробный период": "Activate trial",
  "Пробный период активирован": "Trial activated",
  "дней": "days",
  "Ссылка подписки": "Subscription link",
  "Копировать ссылку": "Copy link",
  "Скопировано": "Copied",
  "Инструкции по устройствам": "Device guides",
  "Тема": "Subject",
  "Сообщение": "Message",
  "Создать тикет": "Create ticket",
  "Тикет создан": "Ticket created",
  "Выйти": "Sign out",
  "Язык": "Language",
  "Загрузка…": "Loading…",
  "Выберите тариф": "Choose a plan",
  "Провайдер оплаты": "Payment provider",
  "Сохранить": "Save",
  "Отмена": "Cancel",
  "Ошибка": "Error",
  "Разделы кабинета": "Account sections",
  "Telegram WebApp initData недоступен": "Telegram WebApp initData is unavailable",
  "Добро пожаловать": "Welcome",
  "Управляйте подпиской, тарифами и подключением": "Manage your subscription, plans and connection",
  "Безопасный доступ к сети": "Secure network access",
  "Пользовательский раздел": "Custom section",
  "Ссылка подписки пока недоступна": "Subscription link is not available yet",
  "Выберите тариф для пробного периода": "Select a plan for the trial",
  "дней бесплатно": "free days",
  "Подписка и балансы вашего аккаунта": "Your subscription and balances",
  "Выберите тариф и способ оплаты": "Choose a plan and payment method",
  "Создайте обращение в службу поддержки": "Create a support request",
  "Ссылка подписки и инструкции по устройствам": "Subscription link and device guides",
  "или": "or",
  "Код": "Code",
  "Установите совместимый VPN-клиент, импортируйте ссылку подписки и подключитесь.": "Install a compatible VPN client, import the subscription URL, then connect.",
  "Установите совместимый VPN-клиент из App Store, импортируйте ссылку подписки и подключитесь.": "Install a compatible VPN client from the App Store, import the subscription URL, then connect.",
  "Откройте VPN-клиент на ТВ, добавьте подписку по ссылке или QR и активируйте профиль.": "Open the VPN client on your TV, add the subscription via link or QR, then activate the profile.",
  "Установите клиент для Windows, импортируйте ссылку подписки и включите соединение.": "Install a Windows VPN client, import the subscription URL, then enable the connection.",
  "Установите клиент для macOS, импортируйте ссылку подписки и подключитесь.": "Install a macOS VPN client, import the subscription URL, then connect.",
  "Установите клиент для Linux, импортируйте ссылку подписки через конфиг или URI.": "Install a Linux VPN client and import the subscription URL via config or URI.",
  "Use your compatible VPN client and import the subscription URL.": "Use your compatible VPN client and import the subscription URL.",
  "Приложения": "Apps",
  "Для Android и iOS есть отдельные приложения магазина.": "Separate shop apps are available for Android and iOS.",
  "Открыть": "Open",
  "Скачать": "Download",
  "Скачать по ссылке": "Download from link",
  "Скачать подписку": "Download subscription",
  "Контрольная сумма": "Checksum",
};

let activeLang: Lang = "ru";

export function translate(lang: Lang, value: string): string {
  if (!value || lang !== "en") return value;
  if (EN[value]) return EN[value];
  const active = value.match(/^Активна до (.+)$/);
  if (active) return `Active until ${active[1]}`;
  const days = value.match(/^(.*) · (.*) дней$/);
  if (days) return `${days[1]} · ${days[2]} days`;
  const status = value.match(/^Статус: (.+)$/);
  if (status) return `Status: ${status[1]}`;
  const balance = value.match(/^Баланс: (.+)$/);
  if (balance) return `Balance: ${balance[1]}`;
  const wallet = value.match(/^Баланс кошелька: (.+)$/);
  if (wallet) return `Wallet balance: ${wallet[1]}`;
  const expires = value.match(/^Истекает: (.+)$/);
  if (expires) return `Expires: ${expires[1]}`;
  const trial = value.match(/^Пробный период · (.+) дней$/);
  if (trial) return `Trial · ${trial[1]} days`;
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
