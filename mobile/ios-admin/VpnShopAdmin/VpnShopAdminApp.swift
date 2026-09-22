import CryptoKit
import SwiftUI

@main
struct VpnShopAdminApp: App {
    var body: some Scene {
        WindowGroup { AdminRootView() }
    }
}

private let localHttpHosts: Set<String> = ["localhost", "127.0.0.1", "10.0.2.2"]
let mobileClientKey = "b7e1c4a09f6d42e8a1c35b77d0e94f12"

func shopProof(_ client: String, _ method: String, _ path: String, _ now: Int) -> (String, String) {
    let stamp = String(now)
    let message = "\(client)\n\(stamp)\n\(method.uppercased())\n\(path)"
    let key = SymmetricKey(data: Data(mobileClientKey.utf8))
    let code = HMAC<SHA256>.authenticationCode(for: Data(message.utf8), using: key)
    return (stamp, code.map { String(format: "%02x", $0) }.joined())
}

func normalizeBase(_ raw: String) throws -> String {
    let value = raw.trimmingCharacters(in: .whitespacesAndNewlines).trimmingCharacters(in: CharacterSet(charactersIn: "/"))
    guard let url = URL(string: value), let host = url.host?.lowercased(), url.user == nil, !value.contains(where: \.isWhitespace) else {
        throw URLError(.badURL)
    }
    if url.scheme == "https" { return value }
    if url.scheme == "http", localHttpHosts.contains(host) { return value }
    throw URLError(.badURL)
}

func jsonInt(_ value: Any?) -> Int? {
    if value == nil || value is NSNull { return nil }
    if let number = value as? Int { return number }
    if let number = value as? NSNumber { return number.intValue }
    if let text = value as? String { return Int(text) }
    return nil
}

func jsonBool(_ value: Any?) -> Bool {
    if let flag = value as? Bool { return flag }
    if let number = value as? NSNumber { return number.boolValue }
    return false
}

func jsonText(_ value: Any?) -> String {
    if value == nil || value is NSNull { return "" }
    if let text = value as? String { return text }
    if let number = value as? NSNumber { return number.stringValue }
    return ""
}

func safeMediaPath(_ path: String) -> String? {
    guard path.hasPrefix("/media/"), !path.contains(".."), !path.contains("://"), !path.contains("\\"), !path.contains("?"), !path.contains("#") else { return nil }
    let name = String(path.dropFirst("/media/".count))
    if name.isEmpty || name.contains("/") { return nil }
    return path
}

func publicNode(_ row: [String: Any]) -> [String: Any] {
    let status = (row["status"] as? String) ?? "unknown"
    let safe = ["online", "offline", "disabled", "unknown"].contains(status) ? status : "unknown"
    var name = (row["name"] as? String)?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
    if name.isEmpty { name = "node" }
    if name.contains("://") || (name.filter { $0 == "." }.count >= 3 && name.contains(where: \.isNumber)) { name = "node" }
    return ["name": name, "country": row["country"] as? String ?? "", "status": safe, "users_online": jsonInt(row["users_online"]) ?? 0]
}

final class ShopClient: NSObject, URLSessionTaskDelegate {
    let base: String
    let token: String
    let lang: String
    private lazy var session: URLSession = URLSession(configuration: .ephemeral, delegate: self, delegateQueue: nil)

    init(base: String, token: String, lang: String) {
        self.base = base
        self.token = token
        self.lang = lang
    }

    func urlSession(_ session: URLSession, task: URLSessionTask, willPerformHTTPRedirection response: HTTPURLResponse, newRequest request: URLRequest, completionHandler: @escaping (URLRequest?) -> Void) {
        completionHandler(nil)
    }

    func call(_ method: String, _ path: String, body: [String: Any]? = nil) throws -> Any {
        var request = URLRequest(url: URL(string: base + path)!)
        request.httpMethod = method
        request.timeoutInterval = 15
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        request.setValue(lang, forHTTPHeaderField: "Accept-Language")
        request.setValue("RemnawaveShop-iOS-Admin/2.12.0", forHTTPHeaderField: "User-Agent")
        // Historical compatibility marker: RemnawaveShop-iOS-Admin/2.10.0
        // Historical compatibility marker: RemnawaveShop-iOS-Admin/2.9.0
        request.setValue("ios-admin", forHTTPHeaderField: "X-Shop-Client")
        let proof = shopProof("ios-admin", method, path, Int(Date().timeIntervalSince1970))
        request.setValue(proof.0, forHTTPHeaderField: "X-Shop-Time")
        request.setValue(proof.1, forHTTPHeaderField: "X-Shop-Proof")
        if !token.isEmpty { request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization") }
        if let body {
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
            request.httpBody = try JSONSerialization.data(withJSONObject: body)
        }
        let semaphore = DispatchSemaphore(value: 0)
        var payload = Data()
        var status = 0
        var failure: Error?
        session.dataTask(with: request) { data, response, error in
            payload = data ?? Data()
            status = (response as? HTTPURLResponse)?.statusCode ?? 0
            failure = error
            semaphore.signal()
        }.resume()
        semaphore.wait()
        if let failure { throw failure }
        if !(200...299).contains(status) { throw NSError(domain: "shop", code: status, userInfo: [NSLocalizedDescriptionKey: detailOf(payload, status)]) }
        if payload.isEmpty { return [String: Any]() }
        return try JSONSerialization.jsonObject(with: payload)
    }

    func bytes(_ path: String) throws -> Data {
        guard let safe = safeMediaPath(path), let url = URL(string: base + safe) else { throw URLError(.badURL) }
        var request = URLRequest(url: url)
        request.timeoutInterval = 15
        request.setValue("image/png,image/jpeg,image/webp", forHTTPHeaderField: "Accept")
        let semaphore = DispatchSemaphore(value: 0)
        var payload = Data()
        var status = 0
        var failure: Error?
        session.dataTask(with: request) { data, response, error in
            payload = data ?? Data()
            status = (response as? HTTPURLResponse)?.statusCode ?? 0
            failure = error
            semaphore.signal()
        }.resume()
        semaphore.wait()
        if let failure { throw failure }
        if !(200...299).contains(status) || payload.count > 2 * 1024 * 1024 { throw URLError(.badServerResponse) }
        return payload
    }
}

private func detailOf(_ payload: Data, _ status: Int) -> String {
    let json = (try? JSONSerialization.jsonObject(with: payload)) as? [String: Any]
    if let detail = json?["detail"] as? String, !detail.isEmpty { return String(detail.prefix(300)) }
    if let list = json?["detail"] as? [[String: Any]], let msg = list.first?["msg"] as? String { return String(msg.prefix(300)) }
    return "HTTP \(status)"
}

func loadStrings(_ lang: String) -> [String: String] {
    guard let url = Bundle.main.url(forResource: "l10n", withExtension: "json"),
          let data = try? Data(contentsOf: url),
          let root = try? JSONSerialization.jsonObject(with: data) as? [String: [String: String]],
          let table = root[lang] else { return [:] }
    return table
}
