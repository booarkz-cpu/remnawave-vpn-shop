package shop.remnawave.user

import android.content.ActivityNotFoundException
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import androidx.activity.compose.setContent
import androidx.biometric.BiometricManager
import androidx.biometric.BiometricPrompt
import androidx.fragment.app.FragmentActivity
import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import org.json.JSONArray
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URI
import java.net.URL
import java.util.UUID
import java.util.concurrent.Executors
import javax.crypto.Mac
import javax.crypto.spec.SecretKeySpec
import kotlin.concurrent.thread

private const val mobileClientKey = "b7e1c4a09f6d42e8a1c35b77d0e94f12"

class MainActivity : FragmentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent { MaterialTheme(colorScheme = shopColors()) { UserApp() } }
    }
}

private fun shopColors() = darkColorScheme(
    primary = Color(0xFF00E5C0),
    onPrimary = Color(0xFF06221C),
    background = Color(0xFF0B0F14),
    onBackground = Color(0xFFF4F7FB),
    surface = Color(0xFF141A22),
    onSurface = Color(0xFFF4F7FB),
)

private val localHttpHosts = setOf("localhost", "127.0.0.1", "10.0.2.2")

fun shopProof(client: String, method: String, path: String, nowSeconds: Long): Pair<String, String> {
    val stamp = nowSeconds.toString()
    val message = "$client\n$stamp\n${method.uppercase()}\n$path"
    val mac = Mac.getInstance("HmacSHA256")
    mac.init(SecretKeySpec(mobileClientKey.toByteArray(Charsets.UTF_8), "HmacSHA256"))
    val hex = mac.doFinal(message.toByteArray(Charsets.UTF_8)).joinToString("") { "%02x".format(it) }
    return stamp to hex
}

fun subscriptionApps(url: String): List<Pair<String, String>> {
    if (!url.startsWith("https://") || url.any { it.isWhitespace() }) return emptyList()
    val encoded = Uri.encode(url)
    return listOf("Happ" to "happ://add/$encoded", "v2rayNG" to "v2rayng://install-sub?url=$encoded", "Streisand" to "streisand://import/$encoded")
}

fun promptUnlock(activity: FragmentActivity, title: String, onResult: (Boolean) -> Unit) {
    val authenticators = BiometricManager.Authenticators.BIOMETRIC_WEAK or BiometricManager.Authenticators.DEVICE_CREDENTIAL
    try {
        if (BiometricManager.from(activity).canAuthenticate(authenticators) != BiometricManager.BIOMETRIC_SUCCESS) {
            onResult(true)
            return
        }
        val prompt = BiometricPrompt(activity, Executors.newSingleThreadExecutor(), object : BiometricPrompt.AuthenticationCallback() {
            override fun onAuthenticationSucceeded(result: BiometricPrompt.AuthenticationResult) { activity.runOnUiThread { onResult(true) } }
            override fun onAuthenticationError(errorCode: Int, errString: CharSequence) { activity.runOnUiThread { onResult(false) } }
        })
        prompt.authenticate(BiometricPrompt.PromptInfo.Builder().setTitle(title).setAllowedAuthenticators(authenticators).build())
    } catch (_: Exception) {
        onResult(true)
    }
}

fun externalUrlAllowed(raw: String): Boolean {
    if (raw.isBlank() || raw.any { it.isWhitespace() }) return false
    val uri = try { URI(raw) } catch (_: Exception) { return false }
    val host = uri.host?.lowercase() ?: return false
    if (uri.userInfo != null) return false
    if (uri.scheme == "https") return true
    return uri.scheme == "http" && host in localHttpHosts
}

fun normalizeBase(raw: String): String {
    val value = raw.trim().trimEnd('/')
    val uri = try { URI(value) } catch (_: Exception) { throw IllegalArgumentException("https") }
    val host = uri.host?.lowercase() ?: throw IllegalArgumentException("https")
    if (uri.userInfo != null || value.any { it.isWhitespace() }) throw IllegalArgumentException("https")
    if (uri.scheme == "https") return value
    if (uri.scheme == "http" && host in localHttpHosts) return value
    throw IllegalArgumentException("https")
}

fun safeMediaPath(path: String): String? {
    if (!path.startsWith("/media/") || ".." in path || "\\" in path || "://" in path || "?" in path || "#" in path) return null
    val name = path.removePrefix("/media/")
    if (name.isBlank() || "/" in name) return null
    return path
}

fun loadLogoBitmap(base: String, path: String): android.graphics.Bitmap? {
    val safe = safeMediaPath(path) ?: return null
    val connection = (URL(base + safe).openConnection() as HttpURLConnection).apply {
        instanceFollowRedirects = false
        connectTimeout = 15000
        readTimeout = 15000
        setRequestProperty("Accept", "image/png,image/jpeg,image/webp")
    }
    if (connection.responseCode !in 200..299) return null
    val bytes = connection.inputStream.use { it.readBytes() }
    if (bytes.size > 2 * 1024 * 1024) return null
    return android.graphics.BitmapFactory.decodeByteArray(bytes, 0, bytes.size)
}

fun publicNode(row: JSONObject): JSONObject {
    val status = row.optString("status", "unknown")
    val safeStatus = if (status in setOf("online", "offline", "disabled", "unknown")) status else "unknown"
    var name = row.optString("name", "node").ifBlank { "node" }
    if ("://" in name || name.count { it == '.' } >= 3 && name.any { it.isDigit() }) name = "node"
    return JSONObject().put("name", name).put("country", row.optString("country")).put("status", safeStatus).put("users_online", row.optInt("users_online", 0))
}

class ShopApi(private val base: String, private val token: String, private val lang: String) {
    fun get(path: String): Any = call("GET", path, null, null)
    fun post(path: String, body: JSONObject, idempotency: String? = null): Any = call("POST", path, body, idempotency)

    private fun call(method: String, path: String, body: JSONObject?, idempotency: String?): Any {
        val connection = (URL(base + path).openConnection() as HttpURLConnection).apply {
            requestMethod = method
            instanceFollowRedirects = false
            connectTimeout = 15000
            readTimeout = 15000
            setRequestProperty("Accept", "application/json")
            setRequestProperty("Accept-Language", lang)
            setRequestProperty("User-Agent", "RemnawaveShop-Android-User/2.10.0")
            // Historical compatibility marker: RemnawaveShop-Android-User/2.9.0
            setRequestProperty("X-Shop-Client", "android-user")
            val proof = shopProof("android-user", method, path, System.currentTimeMillis() / 1000)
            setRequestProperty("X-Shop-Time", proof.first)
            setRequestProperty("X-Shop-Proof", proof.second)
            if (token.isNotBlank()) setRequestProperty("Authorization", "Bearer $token")
            if (idempotency != null) setRequestProperty("Idempotency-Key", idempotency)
            if (body != null) {
                doOutput = true
                setRequestProperty("Content-Type", "application/json")
                outputStream.use { it.write(body.toString().toByteArray()) }
            }
        }
        val code = connection.responseCode
        val text = (if (code in 200..299) connection.inputStream else connection.errorStream)?.bufferedReader()?.use { it.readText() }.orEmpty()
        if (code !in 200..299) throw IllegalStateException(detailOf(text, code))
        val trimmed = text.trim()
        return if (trimmed.startsWith("[")) JSONArray(trimmed) else JSONObject(if (trimmed.isBlank()) "{}" else trimmed)
    }
}

private fun detailOf(payload: String, status: Int): String {
    return try {
        val detail = JSONObject(payload).opt("detail")
        when (detail) {
            is String -> if (detail.isBlank()) "HTTP $status" else detail.take(300)
            is JSONArray -> detail.optJSONObject(0)?.optString("msg")?.take(300) ?: "HTTP $status"
            else -> "HTTP $status"
        }
    } catch (_: Exception) {
        "HTTP $status"
    }
}

@Composable
private fun UserApp() {
    val context = LocalContext.current
    val activity = context as FragmentActivity
    val prefs = remember { context.getSharedPreferences("shop_user", 0) }
    var lang by remember { mutableStateOf(prefs.getString("lang", "ru") ?: "ru") }
    var base by remember { mutableStateOf(prefs.getString("base", "") ?: "") }
    var token by remember { mutableStateOf(prefs.getString("token", "") ?: "") }
    var email by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }
    var tab by remember { mutableStateOf("overview") }
    var notice by remember { mutableStateOf("") }
    var busy by remember { mutableStateOf(false) }
    var dashboard by remember { mutableStateOf(JSONObject()) }
    var plans by remember { mutableStateOf(JSONArray()) }
    var builders by remember { mutableStateOf(JSONArray()) }
    var servers by remember { mutableStateOf(JSONObject()) }
    var connection by remember { mutableStateOf(JSONObject()) }
    var config by remember { mutableStateOf(JSONObject()) }
    var logo by remember { mutableStateOf<ImageBitmap?>(null) }
    var promo by remember { mutableStateOf("") }
    var devices by remember { mutableStateOf(JSONArray()) }
    var traffic by remember { mutableStateOf(JSONObject()) }
    var giftCode by remember { mutableStateOf("") }
    var topupAmount by remember { mutableStateOf("100") }
    var qr by remember { mutableStateOf<ImageBitmap?>(null) }
    var unlocked by remember { mutableStateOf(token.isBlank()) }
    var subject by remember { mutableStateOf("") }
    var message by remember { mutableStateOf("") }
    val strings = remember(lang) { loadStrings(context, lang) }
    fun t(key: String) = strings.optString(key, key)
    fun saveSession(nextBase: String, nextToken: String) {
        base = nextBase
        token = nextToken
        unlocked = true
        prefs.edit().putString("base", nextBase).putString("token", nextToken).putString("lang", lang).apply()
    }
    fun work(block: () -> Unit) {
        busy = true
        notice = ""
        thread {
            val error = try { block(); null } catch (exc: Exception) { exc.message ?: "HTTP" }
            activity.runOnUiThread {
                busy = false
                if (error != null) notice = error
            }
        }
    }
    fun refresh() {
        val api = ShopApi(base, token, lang)
        work {
            val nextDashboard = api.get("/api/me/dashboard") as JSONObject
            val nextPlans = api.get("/api/plans") as JSONArray
            val nextBuilders = api.get("/api/tariff-constructors") as JSONArray
            val nextServers = api.get("/api/me/servers") as JSONObject
            val nextConnection = api.get("/api/me/connection-info") as JSONObject
            val nextConfig = api.get("/api/public/config") as JSONObject
            val nextTraffic = api.get("/api/me/traffic") as JSONObject
            val nextDevices = api.get("/api/me/devices") as JSONArray
            val nextQr = loadAuthedPng(base, "/api/me/connection-qr", token, lang)
            val nextLogo = try {
                val catalog = api.get("/api/public/apps") as JSONObject
                loadLogoBitmap(base, catalog.optString("logo_url"))?.asImageBitmap()
            } catch (_: Exception) { null }
            activity.runOnUiThread {
                dashboard = nextDashboard
                plans = nextPlans
                builders = nextBuilders
                servers = nextServers
                connection = nextConnection
                config = nextConfig
                traffic = nextTraffic
                devices = nextDevices
                qr = nextQr
                logo = nextLogo
            }
        }
    }
    LaunchedEffect(token) {
        if (token.isNotBlank() && !unlocked) promptUnlock(activity, t("unlock")) { unlocked = it }
    }
    LaunchedEffect(token, lang, unlocked) {
        if (token.isNotBlank() && unlocked) refresh()
    }
    LaunchedEffect(base) {
        val normalized = try { normalizeBase(base) } catch (_: Exception) { return@LaunchedEffect }
        if (token.isNotBlank()) return@LaunchedEffect
        thread {
            try {
                val catalog = ShopApi(normalized, "", lang).get("/api/public/apps") as JSONObject
                val nextLogo = loadLogoBitmap(normalized, catalog.optString("logo_url"))?.asImageBitmap()
                activity.runOnUiThread { logo = nextLogo }
            } catch (_: Exception) {
            }
        }
    }
    Scaffold { padding ->
        Column(Modifier.fillMaxSize().padding(padding).padding(16.dp).verticalScroll(rememberScrollState()), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                if (logo != null) Image(logo!!, contentDescription = t("app_name"), modifier = Modifier.size(48.dp))
                Text(t("app_name"), style = MaterialTheme.typography.headlineSmall, color = Color(0xFF00E5C0))
                TextButton(onClick = {
                    lang = if (lang == "ru") "en" else "ru"
                    prefs.edit().putString("lang", lang).apply()
                }) { Text(if (lang == "ru") "EN" else "RU") }
            }
            Text(t("tagline"), color = Color(0xFF9AA6B2))
            if (notice.isNotBlank()) Text(notice, color = Color(0xFFFFB020))
            if (token.isBlank()) {
                OutlinedTextField(base, { base = it }, label = { Text(t("server")) }, modifier = Modifier.fillMaxWidth())
                OutlinedTextField(email, { email = it }, label = { Text(t("email")) }, modifier = Modifier.fillMaxWidth())
                OutlinedTextField(password, { password = it }, label = { Text(t("password")) }, visualTransformation = PasswordVisualTransformation(), modifier = Modifier.fillMaxWidth())
                Button(onClick = {
                    val normalized = try { normalizeBase(base) } catch (_: Exception) { notice = t("https_required"); return@Button }
                    if (!email.contains("@") || !email.contains(".")) { notice = t("email_invalid"); return@Button }
                    if (password.length < 8) { notice = t("password_short"); return@Button }
                    work {
                        val api = ShopApi(normalized, "", lang)
                        val body = JSONObject().put("email", email.trim()).put("password", password)
                        val response = api.post("/api/auth/login", body) as JSONObject
                        val issued = response.optString("access_token")
                        if (issued.isBlank()) throw IllegalStateException("HTTP")
                        activity.runOnUiThread { saveSession(normalized, issued) }
                    }
                }, enabled = !busy) { Text(t("sign_in")) }
                TextButton(onClick = {
                    val normalized = try { normalizeBase(base) } catch (_: Exception) { notice = t("https_required"); return@TextButton }
                    if (!email.contains("@") || !email.contains(".")) { notice = t("email_invalid"); return@TextButton }
                    if (password.length < 8) { notice = t("password_short"); return@TextButton }
                    work {
                        val api = ShopApi(normalized, "", lang)
                        val body = JSONObject().put("email", email.trim()).put("password", password)
                        val response = api.post("/api/auth/register", body) as JSONObject
                        val issued = response.optString("access_token")
                        if (issued.isBlank()) throw IllegalStateException("HTTP")
                        activity.runOnUiThread { saveSession(normalized, issued) }
                    }
                }, enabled = !busy) { Text(t("sign_up")) }
            } else if (!unlocked) {
                Button(onClick = { promptUnlock(activity, t("unlock")) { unlocked = it } }) { Text(t("unlock")) }
                TextButton(onClick = { prefs.edit().remove("token").apply(); token = ""; unlocked = true }) { Text(t("sign_out")) }
            } else {
                Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    listOf("overview", "plans", "builder", "servers", "connection", "devices", "support").forEach { key ->
                        FilterChip(selected = tab == key, onClick = { tab = key }, label = { Text(t(key)) })
                    }
                }
                TextButton(onClick = { refresh() }, enabled = !busy) { Text(t("refresh")) }
                TextButton(onClick = {
                    prefs.edit().remove("token").apply()
                    token = ""
                }) { Text(t("sign_out")) }
                when (tab) {
                    "overview" -> {
                        val user = dashboard.optJSONObject("user") ?: JSONObject()
                        val sub = dashboard.optJSONObject("subscription")
                        Text("${t("wallet")}: ${user.optString("wallet_balance", "0")}")
                        Text("${t("referral")}: ${user.optString("referral_code")}")
                        Text(if (sub == null) t("no_subscription") else "${t("subscription")}: ${t("active")} · ${t("expires")} ${sub.optString("expires_at")}")
                        val used = traffic.opt("traffic_used_bytes")
                        val limit = traffic.opt("traffic_limit_bytes")
                        Text("${t("traffic_used")}: ${if (traffic.optBoolean("available")) used else t("usage_unavailable")}")
                        Text("${t("traffic_limit")}: ${if (limit == null || limit == JSONObject.NULL) t("unlimited") else limit}")
                        OutlinedTextField(topupAmount, { topupAmount = it }, label = { Text(t("topup_amount")) }, modifier = Modifier.fillMaxWidth())
                        Button(onClick = {
                            val amount = topupAmount.trim()
                            work {
                                val body = JSONObject().put("amount", amount).put("provider", providerOf(config))
                                val response = ShopApi(base, token, lang).post("/api/me/wallet/topup", body, UUID.randomUUID().toString()) as JSONObject
                                val url = response.optString("url")
                                activity.runOnUiThread {
                                    notice = t("topup_ok")
                                    if (externalUrlAllowed(url)) context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
                                }
                            }
                        }) { Text(t("topup")) }
                        OutlinedTextField(giftCode, { giftCode = it }, label = { Text(t("gift_code")) }, modifier = Modifier.fillMaxWidth())
                        Button(onClick = {
                            if (giftCode.isBlank()) return@Button
                            work {
                                ShopApi(base, token, lang).post("/api/me/gifts/redeem", JSONObject().put("code", giftCode.trim().uppercase()))
                                activity.runOnUiThread { notice = t("gift_ok"); giftCode = "" }
                            }
                        }) { Text(t("redeem")) }
                    }
                    "plans" -> {
                        OutlinedTextField(promo, { promo = it }, label = { Text(t("promo")) }, modifier = Modifier.fillMaxWidth())
                        for (index in 0 until plans.length()) {
                            val plan = plans.getJSONObject(index)
                            Text("${plan.optString("name")} · ${plan.opt("price")} · ${plan.opt("duration_days")} ${t("days")}")
                            Row {
                                Button(onClick = {
                                    work {
                                        val body = JSONObject().put("plan_id", plan.getInt("id")).put("provider", providerOf(config))
                                        if (promo.isNotBlank()) body.put("promo_code", promo.trim())
                                        val response = ShopApi(base, token, lang).post("/api/payments/create", body, UUID.randomUUID().toString()) as JSONObject
                                        val url = response.optString("url")
                                        activity.runOnUiThread {
                                            notice = t("payment_created")
                                            if (externalUrlAllowed(url)) {
                                                context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
                                            }
                                        }
                                    }
                                }) { Text(t("pay")) }
                                TextButton(onClick = {
                                    work {
                                        val body = JSONObject().put("plan_id", plan.getInt("id"))
                                        if (promo.isNotBlank()) body.put("promo_code", promo.trim())
                                        ShopApi(base, token, lang).post("/api/me/wallet/spend", body, UUID.randomUUID().toString())
                                        activity.runOnUiThread { notice = t("paid_wallet") }
                                    }
                                }) { Text(t("pay_wallet")) }
                            }
                        }
                    }
                    "builder" -> {
                        for (index in 0 until builders.length()) {
                            val row = builders.getJSONObject(index)
                            Text(row.optString("name"))
                            val options = row.optJSONArray("options") ?: JSONArray()
                            val picked = pickOptions(options)
                            Text("${t("devices")} / ${t("traffic")} / ${t("days")}: ${picked.keys().asSequence().joinToString()}")
                            Button(onClick = {
                                work {
                                    val body = JSONObject()
                                        .put("constructor_id", row.getInt("id"))
                                        .put("provider", providerOf(config))
                                        .put("device_option_id", picked.optInt("devices"))
                                        .put("traffic_option_id", picked.optInt("traffic_gb"))
                                        .put("days_option_id", picked.optInt("days"))
                                    val response = ShopApi(base, token, lang).post("/api/payments/create", body, UUID.randomUUID().toString()) as JSONObject
                                    val url = response.optString("url")
                                    activity.runOnUiThread {
                                        notice = t("payment_created")
                                        if (externalUrlAllowed(url)) {
                                            context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
                                        }
                                    }
                                }
                            }) { Text(t("pay")) }
                        }
                    }
                    "servers" -> {
                        if (servers.optString("error").isNotBlank()) Text(t("panel_down"))
                        val nodes = servers.optJSONArray("nodes") ?: JSONArray()
                        if (nodes.length() == 0) Text(t("nodes_empty"))
                        for (index in 0 until nodes.length()) {
                            val node = publicNode(nodes.getJSONObject(index))
                            Text("${node.optString("name")} · ${node.optString("country")} · ${t(node.optString("status"))} · ${node.optInt("users_online")}")
                        }
                    }
                    "connection" -> {
                        val url = connection.optString("subscription_url")
                        Text(if (url.isBlank()) t("no_subscription") else url)
                        if (url.isNotBlank()) {
                            if (qr != null) Image(qr!!, contentDescription = t("qr"), modifier = Modifier.size(180.dp))
                            TextButton(onClick = {
                                context.getSystemService(android.content.ClipboardManager::class.java)?.setPrimaryClip(android.content.ClipData.newPlainText("subscription", url))
                                notice = t("copied")
                            }) { Text(t("copy")) }
                            subscriptionApps(url).forEach { (label, link) ->
                                TextButton(onClick = {
                                    try { context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(link))) }
                                    catch (_: ActivityNotFoundException) { notice = label }
                                }) { Text(label) }
                            }
                        }
                        Text(t("guides"))
                        val platforms = connection.optJSONObject("platforms") ?: JSONObject()
                        for (key in listOf("android", "ios", "tv", "windows", "macos", "linux")) Text("$key: ${platforms.optString(key)}")
                        Button(onClick = {
                            val planId = if (plans.length() > 0) plans.getJSONObject(0).optInt("id") else 0
                            if (planId == 0) return@Button
                            work {
                                ShopApi(base, token, lang).post("/api/me/trial", JSONObject().put("plan_id", planId).put("days", config.optInt("trial_days", 3)))
                                activity.runOnUiThread { notice = t("trial_started") }
                            }
                        }) { Text(t("trial")) }
                    }
                    "devices" -> {
                        if (devices.length() == 0) Text(t("no_devices"))
                        for (index in 0 until devices.length()) {
                            val device = devices.getJSONObject(index)
                            Text("${device.optString("name")} · ${device.optString("platform")} · ${device.optString("status")}")
                            if (device.optString("status") == "active") {
                                TextButton(onClick = {
                                    work {
                                        ShopApi(base, token, lang).post("/api/me/devices/${device.optInt("id")}/revoke", JSONObject())
                                        activity.runOnUiThread { notice = t("device_revoked") }
                                    }
                                }) { Text(t("revoke")) }
                            }
                        }
                    }
                    "support" -> {
                        OutlinedTextField(subject, { subject = it }, label = { Text(t("subject")) }, modifier = Modifier.fillMaxWidth())
                        OutlinedTextField(message, { message = it }, label = { Text(t("message")) }, modifier = Modifier.fillMaxWidth())
                        Button(onClick = {
                            if (subject.isBlank() || message.isBlank()) return@Button
                            work {
                                ShopApi(base, token, lang).post("/api/me/support/tickets", JSONObject().put("subject", subject.trim()).put("message", message.trim()))
                                activity.runOnUiThread { notice = t("ticket_sent"); subject = ""; message = "" }
                            }
                        }) { Text(t("send")) }
                    }
                }
            }
        }
    }
}

private fun loadAuthedPng(base: String, path: String, token: String, lang: String): ImageBitmap? {
    val proof = shopProof("android-user", "GET", path, System.currentTimeMillis() / 1000)
    val connection = (URL(base + path).openConnection() as HttpURLConnection).apply {
        instanceFollowRedirects = false
        connectTimeout = 15000
        readTimeout = 15000
        setRequestProperty("Accept", "image/png")
        setRequestProperty("Accept-Language", lang)
        setRequestProperty("User-Agent", "RemnawaveShop-Android-User/2.10.0")
        setRequestProperty("X-Shop-Client", "android-user")
        setRequestProperty("X-Shop-Time", proof.first)
        setRequestProperty("X-Shop-Proof", proof.second)
        if (token.isNotBlank()) setRequestProperty("Authorization", "Bearer $token")
    }
    if (connection.responseCode !in 200..299) return null
    val bytes = connection.inputStream.use { it.readBytes() }
    if (bytes.size > 2 * 1024 * 1024) return null
    return android.graphics.BitmapFactory.decodeByteArray(bytes, 0, bytes.size)?.asImageBitmap()
}

private fun providerOf(config: JSONObject): String {
    val providers = config.optJSONArray("payment_providers") ?: JSONArray()
    for (index in 0 until providers.length()) {
        val name = providers.optString(index)
        if (name.equals("sandbox", true)) return name
    }
    return if (providers.length() > 0) providers.optString(0) else ""
}

private fun pickOptions(options: JSONArray): JSONObject {
    val picked = JSONObject()
    for (kind in listOf("devices", "traffic_gb", "days")) {
        for (index in 0 until options.length()) {
            val option = options.getJSONObject(index)
            if (option.optString("kind") == kind && option.optBoolean("enabled", true) && !picked.has(kind)) picked.put(kind, option.optInt("id"))
        }
    }
    return picked
}

private fun loadStrings(context: android.content.Context, lang: String): JSONObject {
    val text = context.assets.open("l10n.json").bufferedReader().use { it.readText() }
    return JSONObject(text).getJSONObject(lang)
}
