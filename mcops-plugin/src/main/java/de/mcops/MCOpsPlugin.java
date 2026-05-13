package de.mcops;

import org.bukkit.configuration.file.FileConfiguration;
import org.bukkit.event.EventHandler;
import org.bukkit.event.EventPriority;
import org.bukkit.event.Listener;
import org.bukkit.event.player.PlayerJoinEvent;
import org.bukkit.event.player.PlayerQuitEvent;
import org.bukkit.plugin.java.JavaPlugin;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.concurrent.CompletableFuture;
import java.util.logging.Level;

public class MCOpsPlugin extends JavaPlugin implements Listener {

    private HttpClient httpClient;
    private String panelUrl;
    private String serverName;
    private boolean enabled_reporting;

    @Override
    public void onEnable() {
        saveDefaultConfig();
        reloadPluginConfig();

        httpClient = HttpClient.newBuilder()
                .connectTimeout(Duration.ofSeconds(5))
                .version(HttpClient.Version.HTTP_1_1)
                .build();

        getServer().getPluginManager().registerEvents(this, this);
        getLogger().info("MCOps Plugin enabled. Reporting to: " + panelUrl);
    }

    @Override
    public void onDisable() {
        getLogger().info("MCOps Plugin disabled.");
    }

    private void reloadPluginConfig() {
        FileConfiguration cfg = getConfig();
        panelUrl         = cfg.getString("panel-url",  "http://localhost:8000");
        serverName       = cfg.getString("server-name", getServer().getName());
        enabled_reporting= cfg.getBoolean("enabled", true);
        // trim trailing slash
        if (panelUrl.endsWith("/")) panelUrl = panelUrl.substring(0, panelUrl.length() - 1);
    }

    // ── Event Handlers ─────────────────────────────────────────

    @EventHandler(priority = EventPriority.MONITOR)
    public void onJoin(PlayerJoinEvent e) {
        sendEvent(e.getPlayer().getName(), "join");
    }

    @EventHandler(priority = EventPriority.MONITOR)
    public void onQuit(PlayerQuitEvent e) {
        sendEvent(e.getPlayer().getName(), "quit");
    }

    // ── HTTP Reporting ──────────────────────────────────────────

    private void sendEvent(String playerName, String eventType) {
        if (!enabled_reporting) return;

        // Sanitize inputs (prevent JSON injection)
        String safePlayer = playerName.replaceAll("[^a-zA-Z0-9_]", "");
        String safeServer = serverName.replaceAll("[^a-zA-Z0-9_\\-]", "");

        String json = String.format(
                "{\"player\":\"%s\",\"event\":\"%s\",\"server\":\"%s\"}",
                safePlayer, eventType, safeServer
        );

        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(panelUrl + "/api/stats/event"))
                .header("Content-Type", "application/json")
                .timeout(Duration.ofSeconds(5))
                .POST(HttpRequest.BodyPublishers.ofString(json, StandardCharsets.UTF_8))
                .build();

        CompletableFuture<HttpResponse<Void>> future =
                httpClient.sendAsync(request, HttpResponse.BodyHandlers.discarding());

        future.exceptionally(ex -> {
            getLogger().log(Level.WARNING,
                    "[MCOps] Failed to report " + eventType + " for " + safePlayer + ": " + ex.getMessage());
            return null;
        });
    }
}
