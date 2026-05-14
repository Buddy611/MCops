package de.mcops.fabric;

import com.google.gson.Gson;
import com.google.gson.JsonObject;
import com.mojang.brigadier.CommandDispatcher;
import com.mojang.brigadier.arguments.StringArgumentType;
import net.fabricmc.api.ModInitializer;
import net.fabricmc.fabric.api.command.v2.CommandRegistrationCallback;
import net.fabricmc.fabric.api.networking.v1.ServerPlayConnectionEvents;
import net.fabricmc.loader.api.FabricLoader;
import net.minecraft.server.command.CommandManager;
import net.minecraft.server.command.ServerCommandSource;
import net.minecraft.text.Text;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;

public class MCOpsFabric implements ModInitializer {
    private HttpClient httpClient;
    private String panelUrl = "http://127.0.0.1:8000";
    private String apiKey = "changeme";
    private String serverName = "fabric";

    @Override
    public void onInitialize() {
        try {
            Path configDir = FabricLoader.getInstance().getConfigDir();
            Path configFile = configDir.resolve("mcops.json");
            Gson gson = new Gson();
            if (!Files.exists(configFile)) {
                JsonObject obj = new JsonObject();
                obj.addProperty("panel-url", panelUrl);
                obj.addProperty("api-key", apiKey);
                obj.addProperty("server-name", serverName);
                obj.addProperty("enabled", true);
                Files.writeString(configFile, gson.toJson(obj));
            } else {
                JsonObject obj = gson.fromJson(Files.readString(configFile), JsonObject.class);
                if (obj.has("panel-url")) panelUrl = obj.get("panel-url").getAsString();
                if (obj.has("api-key")) apiKey = obj.get("api-key").getAsString();
                if (obj.has("server-name")) serverName = obj.get("server-name").getAsString();
            }
        } catch (Exception e) {
            e.printStackTrace();
        }

        if (panelUrl.endsWith("/")) panelUrl = panelUrl.substring(0, panelUrl.length() - 1);
        httpClient = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(5)).build();

        ServerPlayConnectionEvents.JOIN.register((handler, sender, server) -> {
            sendEvent(handler.getPlayer().getName().getString(), "join");
        });

        ServerPlayConnectionEvents.DISCONNECT.register((handler, server) -> {
            sendEvent(handler.getPlayer().getName().getString(), "quit");
        });

        CommandRegistrationCallback.EVENT.register((dispatcher, registryAccess, environment) -> registerCommands(dispatcher));
        System.out.println("MCOps Fabric enabled.");
    }

    private void sendEvent(String playerName, String eventType) {
        String json = String.format("{\"api_key\":\"%s\",\"player\":\"%s\",\"event\":\"%s\",\"server\":\"%s\"}",
                apiKey, playerName, eventType, serverName);
        HttpRequest req = HttpRequest.newBuilder().uri(URI.create(panelUrl + "/api/stats/event"))
                .header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(json)).build();
        httpClient.sendAsync(req, HttpResponse.BodyHandlers.discarding());
    }

    private void registerCommands(CommandDispatcher<ServerCommandSource> dispatcher) {
        dispatcher.register(CommandManager.literal("mcops")
                .requires(source -> source.hasPermissionLevel(4))
                .then(CommandManager.literal("stats").executes(context -> {
                    sendApiRequest(context.getSource(), "/api/stats?api_key=" + apiKey, "GET", "");
                    return 1;
                }))
                .then(CommandManager.literal("start").then(CommandManager.argument("target", StringArgumentType.string()).executes(context -> {
                    String target = StringArgumentType.getString(context, "target");
                    sendApiRequest(context.getSource(), "/api/server/" + target + "/action", "POST", String.format("{\"api_key\":\"%s\",\"action\":\"start\"}", apiKey));
                    return 1;
                })))
                .then(CommandManager.literal("stop").then(CommandManager.argument("target", StringArgumentType.string()).executes(context -> {
                    String target = StringArgumentType.getString(context, "target");
                    sendApiRequest(context.getSource(), "/api/server/" + target + "/action", "POST", String.format("{\"api_key\":\"%s\",\"action\":\"stop\"}", apiKey));
                    return 1;
                })))
        );
    }

    private void sendApiRequest(ServerCommandSource sender, String path, String method, String body) {
        HttpRequest.Builder builder = HttpRequest.newBuilder().uri(URI.create(panelUrl + path));
        if (method.equals("POST")) builder.POST(HttpRequest.BodyPublishers.ofString(body)).header("Content-Type", "application/json");
        else builder.GET();

        httpClient.sendAsync(builder.build(), HttpResponse.BodyHandlers.ofString()).thenAccept(res -> {
            sender.sendMessage(Text.of("§a[MCOps] " + res.statusCode() + ": " + res.body()));
        }).exceptionally(ex -> {
            sender.sendMessage(Text.of("§c[MCOps] Error: " + ex.getMessage()));
            return null;
        });
    }
}
