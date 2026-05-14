package de.mcops.bukkit;

import org.bukkit.command.Command;
import org.bukkit.command.CommandExecutor;
import org.bukkit.command.CommandSender;
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

public class MCOpsBukkit extends JavaPlugin implements Listener, CommandExecutor {
    private HttpClient httpClient;
    private String panelUrl;
    private String apiKey;
    private String serverName;
    private boolean enabled;

    @Override
    public void onEnable() {
        saveDefaultConfig();
        FileConfiguration cfg = getConfig();
        panelUrl = cfg.getString("panel-url", "http://localhost:8000");
        apiKey = cfg.getString("api-key", "");
        serverName = cfg.getString("server-name", getServer().getName());
        enabled = cfg.getBoolean("enabled", true);

        if (panelUrl.endsWith("/")) panelUrl = panelUrl.substring(0, panelUrl.length() - 1);

        httpClient = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(5)).build();
        getServer().getPluginManager().registerEvents(this, this);
        getCommand("mcops").setExecutor(this);
        getLogger().info("MCOps Bukkit enabled.");
    }

    @EventHandler(priority = EventPriority.MONITOR)
    public void onJoin(PlayerJoinEvent e) { sendEvent(e.getPlayer().getName(), "join"); }

    @EventHandler(priority = EventPriority.MONITOR)
    public void onQuit(PlayerQuitEvent e) { sendEvent(e.getPlayer().getName(), "quit"); }

    private void sendEvent(String playerName, String eventType) {
        if (!enabled) return;
        String json = String.format("{\"api_key\":\"%s\",\"player\":\"%s\",\"event\":\"%s\",\"server\":\"%s\"}",
                apiKey, playerName, eventType, serverName);
        
        HttpRequest req = HttpRequest.newBuilder().uri(URI.create(panelUrl + "/api/stats/event"))
                .header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(json)).build();
        httpClient.sendAsync(req, HttpResponse.BodyHandlers.discarding());
    }

    @Override
    public boolean onCommand(CommandSender sender, Command cmd, String label, String[] args) {
        if (args.length == 0) return false;
        String sub = args[0].toLowerCase();
        if (sub.equals("stats")) {
            sendApiRequest(sender, "/api/stats?api_key=" + apiKey, "GET", "");
            return true;
        } else if ((sub.equals("start") || sub.equals("stop") || sub.equals("restart")) && args.length > 1) {
            String target = args[1];
            String json = String.format("{\"api_key\":\"%s\",\"action\":\"%s\"}", apiKey, sub);
            sendApiRequest(sender, "/api/server/" + target + "/action", "POST", json);
            return true;
        } else if (sub.equals("create") && args.length >= 5) {
            String name = args[1], software = args[2], version = args[3], ram = args[4];
            String json = String.format("{\"api_key\":\"%s\",\"server_name\":\"%s\",\"software\":\"%s\",\"version\":\"%s\",\"ram_gb\":%s,\"port\":\"auto\"}",
                    apiKey, name, software, version, ram);
            sendApiRequest(sender, "/api/server/create", "POST", json);
            return true;
        }
        return false;
    }

    private void sendApiRequest(CommandSender sender, String path, String method, String body) {
        HttpRequest.Builder builder = HttpRequest.newBuilder().uri(URI.create(panelUrl + path));
        if (method.equals("POST")) builder.POST(HttpRequest.BodyPublishers.ofString(body)).header("Content-Type", "application/json");
        else builder.GET();

        httpClient.sendAsync(builder.build(), HttpResponse.BodyHandlers.ofString()).thenAccept(res -> {
            sender.sendMessage("§a[MCOps] " + res.statusCode() + ": " + res.body());
        }).exceptionally(ex -> {
            sender.sendMessage("§c[MCOps] Error: " + ex.getMessage());
            return null;
        });
    }
}
