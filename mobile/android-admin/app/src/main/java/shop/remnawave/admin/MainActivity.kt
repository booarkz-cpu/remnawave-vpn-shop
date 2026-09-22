package shop.remnawave.admin

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
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
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import org.json.JSONArray
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URI
import java.net.URL
import kotlin.concurrent.thread

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent { MaterialTheme(colorScheme = shopColors()) { AdminApp() } }
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
    fun get(path: String): Any = call("GET", path, null)
    fun post(path: String, body: JSONObject): Any = call("POST", path, body)

    private fun call(method: String, path: String, body: JSONObject?): Any {
        val connection = (URL(base + path).openConnection() as HttpURLConnection).apply {
            requestMethod = method
            instanceFollowRedirects = false
            connectTimeout = 15000
            readTimeout = 15000
            setRequestProperty("Accept", "application/json")
            setRequestProperty("Accept-Language", lang)
            setRequestProperty("User-Agent", "RemnawaveShop-Android-Admin/2.8.0")
            setRequestProperty("X-Shop-Client", "android-admin")
            if (token.isNotBlank()) setRequestProperty("Authorization", "Bearer $token")
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
private fun AdminApp() {
    val context = LocalContext.current
    val activity = context as ComponentActivity
    val prefs = remember { context.getSharedPreferences("shop_admin", 0) }
    var lang by remember { mutableStateOf(prefs.getString("lang", "ru") ?: "ru") }
    var base by remember { mutableStateOf(prefs.getString("base", "") ?: "") }
    var token by remember { mutableStateOf(prefs.getString("token", "") ?: "") }
    var email by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }
    var otp by remember { mutableStateOf("") }
    var tab by remember { mutableStateOf("overview") }
    var notice by remember { mutableStateOf("") }
    var busy by remember { mutableStateOf(false) }
    var overview by remember { mutableStateOf(JSONObject()) }
    var plans by remember { mutableStateOf(JSONArray()) }
    var payments by remember { mutableStateOf(JSONArray()) }
    var monitoring by remember { mutableStateOf(JSONObject()) }
    var platform by remember { mutableStateOf(JSONObject()) }
    var tickets by remember { mutableStateOf(JSONArray()) }
    var reply by remember { mutableStateOf("") }
    var logo by remember { mutableStateOf<ImageBitmap?>(null) }
    val strings = remember(lang) { loadStrings(context, lang) }
    fun t(key: String) = strings.optString(key, key)
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
            val nextOverview = api.get("/api/admin/overview") as JSONObject
            val nextPlans = api.get("/api/admin/plans") as JSONArray
            val nextPayments = api.get("/api/admin/payments") as JSONArray
            val nextMonitoring = api.get("/api/admin/remnawave/monitoring") as JSONObject
            val nextPlatform = api.get("/api/admin/platform/summary") as JSONObject
            val nextTickets = api.get("/api/admin/support/tickets") as JSONArray
            val nextLogo = try {
                val catalog = api.get("/api/admin/apps") as JSONObject
                loadLogoBitmap(base, catalog.optString("logo_url"))?.asImageBitmap()
            } catch (_: Exception) { null }
            activity.runOnUiThread {
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
    LaunchedEffect(token, lang) {
        if (token.isNotBlank()) refresh()
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
                OutlinedTextField(otp, { otp = it }, label = { Text(t("otp")) }, modifier = Modifier.fillMaxWidth())
                Button(onClick = {
                    val normalized = try { normalizeBase(base) } catch (_: Exception) { notice = t("https_required"); return@Button }
                    if (!email.contains("@") || !email.contains(".")) { notice = t("email_invalid"); return@Button }
                    if (password.length < 8) { notice = t("password_short"); return@Button }
                    work {
                        val body = JSONObject().put("email", email.trim()).put("password", password)
                        if (otp.isNotBlank()) body.put("otp", otp.trim())
                        val response = ShopApi(normalized, "", lang).post("/api/admin/auth/login", body) as JSONObject
                        val issued = response.optString("access_token")
                        if (issued.isBlank()) throw IllegalStateException("HTTP")
                        activity.runOnUiThread {
                            base = normalized
                            token = issued
                            prefs.edit().putString("base", normalized).putString("token", issued).putString("lang", lang).apply()
                            notice = "${t("role")}: ${response.optString("role")}"
                        }
                    }
                }, enabled = !busy) { Text(t("sign_in")) }
            } else {
                Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    listOf("overview", "plans", "payments", "monitoring", "platform", "support").forEach { key ->
                        FilterChip(selected = tab == key, onClick = { tab = key }, label = { Text(t(key)) })
                    }
                }
                TextButton(onClick = { refresh() }, enabled = !busy) { Text(t("refresh")) }
                TextButton(onClick = {
                    prefs.edit().remove("token").apply()
                    token = ""
                }) { Text(t("sign_out")) }
                when (tab) {
                    "overview" -> Text("${t("role")} ${overview.optString("role")} · ${t("plans")} ${overview.optInt("plans")} · ${t("payments")} ${overview.optInt("payments")}")
                    "plans" -> {
                        if (plans.length() == 0) Text(t("no_data"))
                        for (index in 0 until plans.length()) {
                            val plan = plans.getJSONObject(index)
                            Text("${plan.optString("name")} · ${plan.opt("price")} · ${if (plan.optBoolean("enabled")) t("enabled") else t("disabled")}")
                        }
                    }
                    "payments" -> {
                        if (payments.length() == 0) Text(t("no_data"))
                        for (index in 0 until payments.length()) {
                            val payment = payments.getJSONObject(index)
                            Text("#${payment.optInt("id")} · ${payment.opt("amount")} ${payment.optString("currency")} · ${payment.optString("status")}")
                        }
                    }
                    "monitoring" -> {
                        if (monitoring.optString("error").isNotBlank()) Text(t("panel_down"))
                        val nodes = monitoring.optJSONArray("nodes") ?: JSONArray()
                        if (nodes.length() == 0) Text(t("no_data"))
                        for (index in 0 until nodes.length()) {
                            val node = publicNode(nodes.getJSONObject(index))
                            Text("${node.optString("name")} · ${node.optString("country")} · ${node.optString("status")} · ${node.optInt("users_online")}")
                        }
                    }
                    "platform" -> {
                        Text(t("violations"))
                        val violations = platform.optJSONArray("violations") ?: JSONArray()
                        if (violations.length() == 0) Text(t("no_data"))
                        for (index in 0 until violations.length()) {
                            val row = violations.getJSONObject(index)
                            Text("#${row.optInt("id")} · ${t("score")} ${row.optInt("score")} · ${row.optString("recommendation")}")
                            Row {
                                TextButton(onClick = {
                                    work {
                                        ShopApi(base, token, lang).post("/api/admin/platform/violations/${row.optInt("id")}/review", JSONObject().put("action", "restrict"))
                                        activity.runOnUiThread { notice = t("restricted") }
                                    }
                                }) { Text(t("restrict")) }
                                TextButton(onClick = {
                                    work {
                                        ShopApi(base, token, lang).post("/api/admin/platform/violations/${row.optInt("id")}/review", JSONObject().put("action", "clear"))
                                        activity.runOnUiThread { notice = t("cleared") }
                                    }
                                }) { Text(t("clear")) }
                            }
                        }
                        Text(t("agents"))
                        val agents = platform.optJSONArray("agents") ?: JSONArray()
                        for (index in 0 until agents.length()) {
                            val agent = agents.getJSONObject(index)
                            Text("${agent.optString("name")} · CPU ${agent.optString("cpu")}")
                        }
                        Text(t("countries"))
                        val countries = platform.optJSONArray("countries") ?: JSONArray()
                        for (index in 0 until countries.length()) {
                            val country = countries.getJSONObject(index)
                            Text("${country.optString("country")}: ${country.optInt("count")}")
                        }
                    }
                    "support" -> {
                        OutlinedTextField(reply, { reply = it }, label = { Text(t("reply")) }, modifier = Modifier.fillMaxWidth())
                        if (tickets.length() == 0) Text(t("no_data"))
                        for (index in 0 until tickets.length()) {
                            val ticket = tickets.getJSONObject(index)
                            Text("#${ticket.optInt("id")} · ${ticket.optString("subject")} · ${ticket.optString("status")}")
                            Text(ticket.optString("message"))
                            Button(onClick = {
                                if (reply.isBlank()) return@Button
                                work {
                                    ShopApi(base, token, lang).post("/api/admin/support/tickets/${ticket.optInt("id")}/reply", JSONObject().put("reply", reply.trim()))
                                    activity.runOnUiThread { notice = t("reply_sent"); reply = "" }
                                }
                            }) { Text(t("send")) }
                        }
                    }
                }
            }
        }
    }
}

private fun loadStrings(context: android.content.Context, lang: String): JSONObject {
    val text = context.assets.open("l10n.json").bufferedReader().use { it.readText() }
    return JSONObject(text).getJSONObject(lang)
}
