package computer.heather.advancedbackups.client;

import computer.heather.advancedbackups.core.ABCore;
import computer.heather.advancedbackups.core.config.ClientConfigManager;
import computer.heather.advancedbackups.network.PacketBackupStatus;
import computer.heather.advancedbackups.network.PacketToastSubscribe;
import net.minecraft.client.Minecraft;
import net.minecraft.network.protocol.common.custom.CustomPacketPayload;
import net.neoforged.fml.event.lifecycle.FMLClientSetupEvent;
import net.neoforged.neoforge.client.event.ClientPlayerNetworkEvent;
import net.neoforged.neoforge.client.event.RegisterClientCommandsEvent;
import net.neoforged.neoforge.client.network.ClientPacketDistributor;
import net.neoforged.neoforge.common.NeoForge;
import net.neoforged.neoforge.network.handling.IPayloadContext;

public class ClientWrapper {

    public static void handle(PacketBackupStatus packet, IPayloadContext context) {
        BackupToast.starting = packet.starting();
        BackupToast.started = packet.started();
        BackupToast.failed = packet.failed();
        BackupToast.finished = packet.finished();
        BackupToast.cancelled = packet.cancelled();

        BackupToast.progress = packet.progress();
        BackupToast.max = packet.max();

        if (!BackupToast.exists) {
            BackupToast.exists = true;
            Minecraft.getInstance().getToastManager().addToast(new BackupToast());
        }
    }

    public static void init(FMLClientSetupEvent e) {
        NeoForge.EVENT_BUS.addListener(ClientWrapper::registerClientCommands);
        NeoForge.EVENT_BUS.addListener(ClientWrapper::onServerConnected);
        ClientConfigManager.loadOrCreateConfig();
    }

    public static void registerClientCommands(RegisterClientCommandsEvent event) {
        AdvancedBackupsClientCommand.register(event.getDispatcher());
    }

    public static void onServerConnected(ClientPlayerNetworkEvent.LoggingIn event) {
        sendToServer(new PacketToastSubscribe(ClientConfigManager.showProgress.get()));
    }

    public static <MSG extends CustomPacketPayload> void sendToServer(MSG message) {
        try {
            ClientPacketDistributor.sendToServer(message);
        } catch (UnsupportedOperationException e) {
            ABCore.warningLogger.accept("Refusing to send packet " + message + " to server as the server cannot receive it.");
        }
    }
}
