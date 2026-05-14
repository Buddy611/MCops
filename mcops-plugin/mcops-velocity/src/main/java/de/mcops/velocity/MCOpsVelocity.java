package de.mcops.velocity;

import com.google.inject.Inject;
import com.velocitypowered.api.command.CommandSource;
import com.velocitypowered.api.command.SimpleCommand;
import com.velocitypowered.api.event.Subscribe;
import com.velocitypowered.api.event.connection.PostLoginEvent;
import com.velocitypowered.api.event.connection.DisconnectEvent;
import com.velocitypowered.api.event.proxy.ProxyInitializeEvent;
import com.velocitypowered.api.plugin.Plugin;
import com.velocitypowered.api.plugin.annotation.DataDirectory;
import com.velocitypowered.api.proxy.ProxyServer;
import net.kyori.adventure.text.Component;
import org.slf4j.Logger;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;

@Plugin(id = "mcopsplugin", name = "MCOpsPlugin", version = "1.0.0", authors = {"MCOps"})
public class MCOpsVelocity implements SimpleCommand {
    private final ProxyServer server;
    private final Logger logger;
    private final Path dataDirectory;
    private HttpClient httpClient;
    private String panelUrl = "http://127.0.0.1:8000";
    private String apiKey = "changeme";
    private String serverName = "velocity";

    @Inject
    public MCOpsVelocity(ProxyServer server, Logger logger, @DataDirectory Path dataDirectory) {
        this.server = server;
        this.logger = logger;
        this.dataDirectory = dataDirectory;
    }

    @Subscribe
    public void onProxyInitialization(ProxyInitializeEvent event) {
        try {
            if (!Files.exists(dataDirectory)) Files.createDirectories(dataDirectory);
            Path configFile = dataDirectory.resolve("config.yml");
            if (!Files.exists(configFile)) {
                Files.writeString(configFile, "panel-url: 'http://127.0.0.1:8000'\napi-key: 'changeme'\nserver-name: 'velocity'\nenabled: true\n");
            } else {
                for (String line : Files.readAllLines(configFile)) {
                    if (line.startsWith("panel-url:")) panelUrl = line.split(":", 2)[1].replace("'", "").trim();
                    if (line.startsWith("api-key:")) apiKey = line.split(":", 2)[1].replace("'", "").trim();
                    if (line.startsWith("server-name:")) serverName = line.split(":", 2)[1].replace("'", "").trim();
                }
            }
        } catch (Exception e) {
            logger.error("Failed to load config", e);
        }

        if (panelUrl.endsWith("/")) panelUrl = panelUrl.substring(0, panelUrl.length() - 1);
        httpClient = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(5)).build();
        
        server.getCommandManager().register("mcops", this);
        logger.info("MCOps Velocity enabled.");
    }

    @Subscribe
    public void onPostLogin(PostLoginEvent event) {
        sendEvent(event.getPlayer().getUsername(), "join");
    }

    @Subscribe
    public void onDisconnect(DisconnectEvent event) {
        sendEvent(event.getPlayer().getUsername(), "quit");
    }

    private void sendEvent(String playerName, String eventType) {
        String json = String.format("{\"api_key\":\"%s\",\"player\":\"%s\",\"event\":\"%s\",\"server\":\"%s\"}",
                apiKey, playerName, eventType, serverName);
        HttpRequest req = HttpRequest.newBuilder().uri(URI.create(panelUrl + "/api/stats/event"))
                .header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(json)).build();
        httpClient.sendAsync(req, HttpResponse.BodyHandlers.discarding());
    }

    @Override
    public void execute(Invocation invocation) {
        CommandSource source = invocation.source();
        String[] args = invocation.arguments();
        if (!source.hasPermission("mcops.admin")) {
            source.sendMessage(Component.text("§cNo permission."));
            return;
        }

        if (args.length == 0) return;
        String sub = args[0].toLowerCase();

        if (sub.equals("stats")) {
            sendApiRequest(source, "/api/stats?api_key=" + apiKey, "GET", "");
        } else if ((sub.equals("start") || sub.equals("stop") || sub.equals("restart")) && args.length > 1) {
            String target = args[1];
            String json = String.format("{\"api_key\":\"%s\",\"action\":\"%s\"}", apiKey, sub);
            sendApiRequest(source, "/api/server/" + target + "/action", "POST", json);
        } else if (sub.equals("create") && args.length >= 5) {
            String name = args[1], software = args[2], version = args[3], ram = args[4];
            String json = String.format("{\"api_key\":\"%s\",\"server_name\":\"%s\",\"software\":\"%s\",\"version\":\"%s\",\"ram_gb\":%s,\"port\":\"auto\"}",
                    apiKey, name, software, version, ram);
            sendApiRequest(source, "/api/server/create", "POST", json);
        }
    }

    private void sendApiRequest(CommandSource sender, String path, String method, String body) {
        HttpRequest.Builder builder = HttpRequest.newBuilder().uri(URI.create(panelUrl + path));
        if (method.equals("POST")) builder.POST(HttpRequest.BodyPublishers.ofString(body)).header("Content-Type", "application/json");
        else builder.GET();

        httpClient.sendAsync(builder.build(), HttpResponse.BodyHandlers.ofString()).thenAccept(res -> {
            sender.sendMessage(Component.text("§a[MCOps] " + res.statusCode() + ": " + res.body()));
        }).exceptionally(ex -> {
            sender.sendMessage(Component.text("§c[MCOps] Error: " + ex.getMessage()));
            return null;
        });
    }
}
