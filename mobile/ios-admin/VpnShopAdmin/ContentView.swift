import SwiftUI
import UIKit

struct AdminRootView: View {
    @AppStorage("shop_admin_lang") private var lang = "ru"
    @AppStorage("shop_admin_base") private var base = ""
    @AppStorage("shop_admin_token") private var token = ""
    @State private var email = ""
    @State private var password = ""
    @State private var otp = ""
    @State private var tab = "overview"
    @State private var notice = ""
    @State private var busy = false
    @State private var overview: [String: Any] = [:]
    @State private var plans: [[String: Any]] = []
    @State private var payments: [[String: Any]] = []
    @State private var monitoring: [String: Any] = [:]
    @State private var platform: [String: Any] = [:]
    @State private var tickets: [[String: Any]] = []
    @State private var reply = ""
    @State private var logo: UIImage?

    private func t(_ key: String) -> String { loadStrings(lang)[key] ?? key }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 12) {
                HStack {
                    if let logo { Image(uiImage: logo).resizable().frame(width: 48, height: 48) }
                    Text(t("app_name")).font(.title2).foregroundStyle(Color(red: 0, green: 0.90, blue: 0.75))
                    Spacer()
                    Button(lang == "ru" ? "EN" : "RU") { lang = lang == "ru" ? "en" : "ru" }
                }
                Text(t("tagline")).foregroundStyle(.secondary)
                if !notice.isEmpty { Text(notice).foregroundStyle(.orange) }
                if token.isEmpty { auth } else { home }
            }.padding()
        }
        .background(Color(red: 0.04, green: 0.06, blue: 0.08))
        .preferredColorScheme(.dark)
        .onAppear {
            if !token.isEmpty { refresh() }
            else { loadPublicLogo() }
        }
        .onChange(of: token) { value in if !value.isEmpty { refresh() } }
        .onChange(of: lang) { _ in if !token.isEmpty { refresh() } }
    }

    private var auth: some View {
        VStack(alignment: .leading, spacing: 8) {
            TextField(t("server"), text: $base).textFieldStyle(.roundedBorder)
            TextField(t("email"), text: $email).textFieldStyle(.roundedBorder)
            SecureField(t("password"), text: $password).textFieldStyle(.roundedBorder)
            TextField(t("otp"), text: $otp).textFieldStyle(.roundedBorder)
            Button(t("sign_in")) { signIn() }.disabled(busy)
        }
    }

    private var home: some View {
        VStack(alignment: .leading, spacing: 10) {
            ScrollView(.horizontal, showsIndicators: false) {
                HStack {
                    ForEach(["overview", "plans", "payments", "monitoring", "platform", "support"], id: \.self) { key in
                        Button(t(key)) { tab = key }.buttonStyle(.bordered)
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
            Text("\(t("role")) \(overview["role"] as? String ?? "") · \(t("plans")) \(jsonInt(overview["plans"]) ?? 0) · \(t("payments")) \(jsonInt(overview["payments"]) ?? 0)")
        case "plans":
            if plans.isEmpty { Text(t("no_data")) }
            ForEach(Array(plans.enumerated()), id: \.offset) { _, plan in
                Text("\(plan["name"] as? String ?? "") · \(plan["price"] ?? "") · \(jsonBool(plan["enabled"]) ? t("enabled") : t("disabled"))")
            }
        case "payments":
            if payments.isEmpty { Text(t("no_data")) }
            ForEach(Array(payments.enumerated()), id: \.offset) { _, payment in
                Text("#\(payment["id"] ?? "") · \(payment["amount"] ?? "") \(payment["currency"] as? String ?? "") · \(payment["status"] as? String ?? "")")
            }
        case "monitoring":
            if (monitoring["error"] as? String)?.isEmpty == false { Text(t("panel_down")) }
            let nodes = monitoring["nodes"] as? [[String: Any]] ?? []
            if nodes.isEmpty { Text(t("no_data")) }
            ForEach(Array(nodes.enumerated()), id: \.offset) { _, row in
                let node = publicNode(row)
                Text("\(node["name"] as? String ?? "") · \(node["country"] as? String ?? "") · \(node["status"] as? String ?? "") · \(node["users_online"] as? Int ?? 0)")
            }
        case "platform":
            Text(t("violations"))
            let violations = platform["violations"] as? [[String: Any]] ?? []
            if violations.isEmpty { Text(t("no_data")) }
            ForEach(Array(violations.enumerated()), id: \.offset) { _, row in
                Text("#\(row["id"] ?? "") · \(t("score")) \(row["score"] ?? "") · \(row["recommendation"] as? String ?? "")")
                HStack {
                    Button(t("restrict")) { review(row, "restrict") }
                    Button(t("clear")) { review(row, "clear") }
                }
            }
            Text(t("agents"))
            let agents = platform["agents"] as? [[String: Any]] ?? []
            ForEach(Array(agents.enumerated()), id: \.offset) { _, agent in
                Text("\(agent["name"] as? String ?? "") · CPU \(agent["cpu"] ?? "")")
            }
            Text(t("countries"))
            let countries = platform["countries"] as? [[String: Any]] ?? []
            ForEach(Array(countries.enumerated()), id: \.offset) { _, country in
                Text("\(country["country"] as? String ?? ""): \(country["count"] ?? 0)")
            }
        default:
            TextField(t("reply"), text: $reply).textFieldStyle(.roundedBorder)
            if tickets.isEmpty { Text(t("no_data")) }
            ForEach(Array(tickets.enumerated()), id: \.offset) { _, ticket in
                Text("#\(ticket["id"] ?? "") · \(ticket["subject"] as? String ?? "") · \(ticket["status"] as? String ?? "")")
                Text(ticket["message"] as? String ?? "")
                Button(t("send")) { send(ticket) }.disabled(busy)
            }
        }
    }

    private func signIn() {
        guard let normalized = try? normalizeBase(base) else { notice = t("https_required"); return }
        guard email.contains("@"), email.contains(".") else { notice = t("email_invalid"); return }
        guard password.count >= 8 else { notice = t("password_short"); return }
        work {
            var body: [String: Any] = ["email": email, "password": password]
            if !otp.trimmingCharacters(in: .whitespaces).isEmpty { body["otp"] = otp }
            let response = try ShopClient(base: normalized, token: "", lang: lang).call("POST", "/api/admin/auth/login", body: body) as? [String: Any]
            let issued = response?["access_token"] as? String ?? ""
            if issued.isEmpty { throw URLError(.userAuthenticationRequired) }
            DispatchQueue.main.async {
                base = normalized
                token = issued
                notice = "\(t("role")): \(response?["role"] as? String ?? "")"
            }
        }
    }

    private func logoImage(_ api: ShopClient, _ path: String) -> UIImage? {
        guard let catalog = try? api.call("GET", path) as? [String: Any],
              let media = catalog["logo_url"] as? String,
              let data = try? api.bytes(media) else { return nil }
        return UIImage(data: data)
    }

    private func loadPublicLogo() {
        guard let normalized = try? normalizeBase(base) else { return }
        work {
            let image = logoImage(ShopClient(base: normalized, token: "", lang: lang), "/api/public/apps")
            DispatchQueue.main.async { logo = image }
        }
    }

    private func refresh() {
        work {
            let api = ShopClient(base: base, token: token, lang: lang)
            let nextOverview = try api.call("GET", "/api/admin/overview") as? [String: Any] ?? [:]
            let nextPlans = try api.call("GET", "/api/admin/plans") as? [[String: Any]] ?? []
            let nextPayments = try api.call("GET", "/api/admin/payments") as? [[String: Any]] ?? []
            let nextMonitoring = try api.call("GET", "/api/admin/remnawave/monitoring") as? [String: Any] ?? [:]
            let nextPlatform = try api.call("GET", "/api/admin/platform/summary") as? [String: Any] ?? [:]
            let nextTickets = try api.call("GET", "/api/admin/support/tickets") as? [[String: Any]] ?? []
            let nextLogo = logoImage(api, "/api/admin/apps")
            DispatchQueue.main.async {
                overview = nextOverview
                plans = nextPlans
                payments = nextPayments
                monitoring = nextMonitoring
                platform = nextPlatform
                tickets = nextTickets
                logo = nextLogo
            }
        }
    }

    private func review(_ row: [String: Any], _ action: String) {
        guard let id = jsonInt(row["id"]) else { return }
        work {
            _ = try ShopClient(base: base, token: token, lang: lang).call("POST", "/api/admin/platform/violations/\(id)/review", body: ["action": action])
            DispatchQueue.main.async { notice = t(action == "restrict" ? "restricted" : "cleared") }
        }
    }

    private func send(_ ticket: [String: Any]) {
        guard let id = jsonInt(ticket["id"]) else { return }
        let text = reply.trimmingCharacters(in: .whitespaces)
        if text.isEmpty { return }
        work {
            _ = try ShopClient(base: base, token: token, lang: lang).call("POST", "/api/admin/support/tickets/\(id)/reply", body: ["reply": text])
            DispatchQueue.main.async { notice = t("reply_sent"); reply = "" }
        }
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
