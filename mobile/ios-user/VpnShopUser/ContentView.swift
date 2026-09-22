import SwiftUI
import UIKit

struct UserRootView: View {
    @AppStorage("shop_lang") private var lang = "ru"
    @AppStorage("shop_base") private var base = ""
    @AppStorage("shop_token") private var token = ""
    @State private var email = ""
    @State private var password = ""
    @State private var tab = "overview"
    @State private var notice = ""
    @State private var busy = false
    @State private var dashboard: [String: Any] = [:]
    @State private var plans: [[String: Any]] = []
    @State private var builders: [[String: Any]] = []
    @State private var servers: [String: Any] = [:]
    @State private var connection: [String: Any] = [:]
    @State private var config: [String: Any] = [:]
    @State private var promo = ""
    @State private var subject = ""
    @State private var message = ""

    private var strings: [String: String] { loadStrings(lang) }
    private func t(_ key: String) -> String { strings[key] ?? key }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 12) {
                HStack {
                    Text(t("app_name")).font(.title2).foregroundStyle(Color(red: 0, green: 0.90, blue: 0.75))
                    Spacer()
                    Button(lang == "ru" ? "EN" : "RU") { lang = lang == "ru" ? "en" : "ru" }
                }
                Text(t("tagline")).foregroundStyle(.secondary)
                if !notice.isEmpty { Text(notice).foregroundStyle(.orange) }
                if token.isEmpty { auth } else { home }
            }
            .padding()
        }
        .background(Color(red: 0.04, green: 0.06, blue: 0.08))
        .preferredColorScheme(.dark)
        .onAppear { if !token.isEmpty { refresh() } }
        .onChange(of: token) { value in if !value.isEmpty { refresh() } }
        .onChange(of: lang) { _ in if !token.isEmpty { refresh() } }
    }

    private var auth: some View {
        VStack(alignment: .leading, spacing: 8) {
            field(t("server"), text: $base)
            field(t("email"), text: $email)
            SecureField(t("password"), text: $password).textFieldStyle(.roundedBorder)
            Button(t("sign_in")) { authenticate("/api/auth/login") }.disabled(busy)
            Button(t("sign_up")) { authenticate("/api/auth/register") }.disabled(busy)
        }
    }

    private var home: some View {
        VStack(alignment: .leading, spacing: 10) {
            ScrollView(.horizontal, showsIndicators: false) {
                HStack {
                    ForEach(["overview", "plans", "builder", "servers", "connection", "support"], id: \.self) { key in
                        Button(t(key)) { tab = key }.buttonStyle(.bordered).tint(tab == key ? Color(red: 0, green: 0.90, blue: 0.75) : .gray)
                    }
                }
            }
            Button(t("refresh")) { refresh() }.disabled(busy)
            Button(t("sign_out")) { token = "" }
            section
        }
    }

    @ViewBuilder private var section: some View {
        switch tab {
        case "overview":
            let user = dashboard["user"] as? [String: Any] ?? [:]
            Text("\(t("wallet")): \(user["wallet_balance"] as? String ?? "0")")
            Text("\(t("referral")): \(user["referral_code"] as? String ?? "")")
            if dashboard["subscription"] == nil || dashboard["subscription"] is NSNull {
                Text(t("no_subscription"))
            } else {
                Text(t("active"))
            }
        case "plans":
            field(t("promo"), text: $promo)
            ForEach(Array(plans.enumerated()), id: \.offset) { _, plan in
                Text("\(jsonText(plan["name"])) · \(jsonText(plan["price"]))")
                Button(t("pay")) { buy(plan, wallet: false) }
                Button(t("pay_wallet")) { buy(plan, wallet: true) }
            }
        case "builder":
            ForEach(Array(builders.enumerated()), id: \.offset) { _, row in
                Text(row["name"] as? String ?? "")
                Button(t("pay")) { buyConstructor(row) }
            }
        case "servers":
            if (servers["error"] as? String)?.isEmpty == false { Text(t("panel_down")) }
            let nodes = servers["nodes"] as? [[String: Any]] ?? []
            if nodes.isEmpty { Text(t("nodes_empty")) }
            ForEach(Array(nodes.enumerated()), id: \.offset) { _, row in
                let node = publicNode(row)
                Text("\(node["name"] as? String ?? "") · \(node["country"] as? String ?? "") · \(t(node["status"] as? String ?? "unknown")) · \(node["users_online"] as? Int ?? 0)")
            }
        case "connection":
            let url = connection["subscription_url"] as? String ?? ""
            Text(url.isEmpty ? t("no_subscription") : url)
            if !url.isEmpty {
                Button(t("copy")) {
                    UIPasteboard.general.string = url
                    notice = t("copied")
                }
            }
            Text(t("guides"))
            let platforms = connection["platforms"] as? [String: Any] ?? [:]
            ForEach(["android", "ios", "tv", "windows", "macos", "linux"], id: \.self) { key in
                Text("\(key): \(jsonText(platforms[key]))")
            }
            Button(t("trial")) { startTrial() }
        default:
            field(t("subject"), text: $subject)
            field(t("message"), text: $message)
            Button(t("send")) { sendTicket() }.disabled(busy)
        }
    }

    private func field(_ title: String, text: Binding<String>) -> some View {
        TextField(title, text: text).textFieldStyle(.roundedBorder)
    }

    private func authenticate(_ path: String) {
        guard let normalized = try? normalizeBase(base) else { notice = t("https_required"); return }
        guard email.contains("@"), email.contains(".") else { notice = t("email_invalid"); return }
        guard password.count >= 8 else { notice = t("password_short"); return }
        work {
            let response = try ShopClient(base: normalized, token: "", lang: lang).call("POST", path, body: ["email": email, "password": password]) as? [String: Any]
            let issued = response?["access_token"] as? String ?? ""
            if issued.isEmpty { throw URLError(.userAuthenticationRequired) }
            DispatchQueue.main.async { base = normalized; token = issued }
        }
    }

    private func refresh() {
        work {
            let api = ShopClient(base: base, token: token, lang: lang)
            let nextDashboard = try api.call("GET", "/api/me/dashboard") as? [String: Any] ?? [:]
            let nextPlans = try api.call("GET", "/api/plans") as? [[String: Any]] ?? []
            let nextBuilders = try api.call("GET", "/api/tariff-constructors") as? [[String: Any]] ?? []
            let nextServers = try api.call("GET", "/api/me/servers") as? [String: Any] ?? [:]
            let nextConnection = try api.call("GET", "/api/me/connection-info") as? [String: Any] ?? [:]
            let nextConfig = try api.call("GET", "/api/public/config") as? [String: Any] ?? [:]
            DispatchQueue.main.async {
                dashboard = nextDashboard
                plans = nextPlans
                builders = nextBuilders
                servers = nextServers
                connection = nextConnection
                config = nextConfig
            }
        }
    }

    private func buy(_ plan: [String: Any], wallet: Bool) {
        guard let id = jsonInt(plan["id"]) else { return }
        work {
            var body: [String: Any] = ["plan_id": id]
            if !promo.trimmingCharacters(in: .whitespaces).isEmpty { body["promo_code"] = promo }
            let api = ShopClient(base: base, token: token, lang: lang)
            if wallet {
                _ = try api.call("POST", "/api/me/wallet/spend", body: body, idempotency: UUID().uuidString)
                DispatchQueue.main.async { notice = t("paid_wallet") }
            } else {
                body["provider"] = providerName()
                let response = try api.call("POST", "/api/payments/create", body: body, idempotency: UUID().uuidString) as? [String: Any]
                DispatchQueue.main.async {
                    notice = t("payment_created")
                    openPayment(response?["url"] as? String ?? "")
                }
            }
        }
    }

    private func buyConstructor(_ row: [String: Any]) {
        guard let id = jsonInt(row["id"]) else { return }
        let options = row["options"] as? [[String: Any]] ?? []
        var picked: [String: Int] = [:]
        for kind in ["devices", "traffic_gb", "days"] {
            if let option = options.first(where: { ($0["kind"] as? String) == kind }), let optionId = jsonInt(option["id"]) {
                picked[kind] = optionId
            }
        }
        work {
            let body: [String: Any] = [
                "constructor_id": id,
                "provider": providerName(),
                "device_option_id": picked["devices"] ?? 0,
                "traffic_option_id": picked["traffic_gb"] ?? 0,
                "days_option_id": picked["days"] ?? 0,
            ]
            let response = try ShopClient(base: base, token: token, lang: lang).call("POST", "/api/payments/create", body: body, idempotency: UUID().uuidString) as? [String: Any]
            DispatchQueue.main.async {
                notice = t("payment_created")
                openPayment(response?["url"] as? String ?? "")
            }
        }
    }

    private func startTrial() {
        guard let plan = plans.first, let id = jsonInt(plan["id"]) else { return }
        let days = jsonInt(config["trial_days"]) ?? 3
        work {
            _ = try ShopClient(base: base, token: token, lang: lang).call("POST", "/api/me/trial", body: ["plan_id": id, "days": days])
            DispatchQueue.main.async { notice = t("trial_started") }
        }
    }

    private func sendTicket() {
        let title = subject.trimmingCharacters(in: .whitespaces)
        let text = message.trimmingCharacters(in: .whitespaces)
        if title.isEmpty || text.isEmpty { return }
        work {
            _ = try ShopClient(base: base, token: token, lang: lang).call("POST", "/api/me/support/tickets", body: ["subject": title, "message": text])
            DispatchQueue.main.async { notice = t("ticket_sent"); subject = ""; message = "" }
        }
    }

    private func providerName() -> String {
        let providers = config["payment_providers"] as? [String] ?? []
        return providers.first { $0.lowercased() == "sandbox" } ?? providers.first ?? ""
    }

    private func openPayment(_ url: String) {
        guard let target = URL(string: url) else { return }
        let host = target.host?.lowercased() ?? ""
        let allowed = target.scheme == "https" || (target.scheme == "http" && localHttpHosts.contains(host))
        if allowed { UIApplication.shared.open(target) }
    }

    private func work(_ block: @escaping () throws -> Void) {
        busy = true
        notice = ""
        DispatchQueue.global(qos: .userInitiated).async {
            do {
                try block()
                DispatchQueue.main.async { busy = false }
            } catch {
                DispatchQueue.main.async { busy = false; notice = error.localizedDescription }
            }
        }
    }
}
