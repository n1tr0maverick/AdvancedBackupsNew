package computer.heather.advancedbackups.client;

import java.util.List;

import computer.heather.advancedbackups.AdvancedBackups;
import computer.heather.advancedbackups.interfaces.IClientContactor;
import computer.heather.advancedbackups.network.NetworkHandler;
import computer.heather.advancedbackups.network.PacketBackupStatus;
import net.minecraft.commands.Commands;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerPlayer;

public class ClientContactor implements IClientContactor {

    @Override
    public void backupComplete(boolean all) {
        send(new PacketBackupStatus(false, false, false, true, false, 0, 0), all);
    }

    @Override
    public void backupFailed(boolean all) {
        send(new PacketBackupStatus(false, false, true, false, false, 0, 0), all);
    }

    @Override
    public void backupProgress(int progress, int max, boolean all) {
        send(new PacketBackupStatus(false, true, false, false, false, progress, max), all);
    }

    @Override
    public void backupStarting(boolean all) {
        send(new PacketBackupStatus(true, false, false, false, false, 0, 0), all);
    }

    @Override
    public void backupCancelled(boolean all) {
        send(new PacketBackupStatus(false, false, false, false, true, 0, 0), all);
    }

    private void send(PacketBackupStatus packet, boolean all) {
        MinecraftServer server = AdvancedBackups.server;
        List<ServerPlayer> players = server.getPlayerList().getPlayers();
        for (ServerPlayer player : players) {
            if (!AdvancedBackups.players.contains(player.getStringUUID())) continue;
            if (!server.isDedicatedServer() || Commands.LEVEL_ADMINS.check(player.permissions()) || all) {
                NetworkHandler.sendToClient(player, packet);
            }
        }
    }
}
