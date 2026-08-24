package computer.heather.advancedbackups.client;

import com.mojang.brigadier.CommandDispatcher;
import com.mojang.brigadier.arguments.StringArgumentType;

import computer.heather.advancedbackups.core.CoreCommandSystem;
import net.fabricmc.fabric.api.client.command.v2.ClientCommands;
import net.fabricmc.fabric.api.client.command.v2.FabricClientCommandSource;
import net.minecraft.client.Minecraft;
import net.minecraft.network.chat.Component;
import net.minecraft.network.protocol.game.ServerboundChatCommandPacket;

public class AdvancedBackupsClientCommand {
    public static void register(CommandDispatcher<FabricClientCommandSource> dispatcher) {
        dispatcher.register(ClientCommands.literal("backup").requires((runner) -> {
            return true;
        }).then(ClientCommands.literal("start").executes((runner) -> {
            Minecraft.getInstance().player.connection.send(new ServerboundChatCommandPacket("backup start"));
            return 1;
        }))

        .then(ClientCommands.literal("reload-config").executes((runner) -> {
            Minecraft.getInstance().player.connection.send(new ServerboundChatCommandPacket("backup reload-config"));
            return 1;
        }))

        .then(ClientCommands.literal("reset-chain").executes((runner) -> {
            Minecraft.getInstance().player.connection.send(new ServerboundChatCommandPacket("backup reset-chain"));
            return 1;
        }))

        .then(ClientCommands.literal("snapshot").executes((runner) -> {
            Minecraft.getInstance().player.connection.send(new ServerboundChatCommandPacket("backup snapshot"));
            return 1;
        })

        .then(ClientCommands.argument("name", StringArgumentType.greedyString()).executes((runner) -> {
            String snapshotName = StringArgumentType.getString(runner, "name");
            Minecraft.getInstance().player.connection.send(new ServerboundChatCommandPacket("backup snapshot " + snapshotName));
            return 1;
        })))

        .then(ClientCommands.literal("cancel").executes((runner) -> {
            Minecraft.getInstance().player.connection.send(new ServerboundChatCommandPacket("backup cancel"));
            return 1;
        }))

        .then(ClientCommands.literal("reload-client-config").executes((runner) -> {
            CoreCommandSystem.reloadClientConfig((response) -> {
                runner.getSource().sendFeedback(Component.literal(response));
            });
            return 1;
        }))

        );
    }
}
