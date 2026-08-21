package computer.heather.advancedbackups.network;

import net.minecraft.network.protocol.common.custom.CustomPacketPayload;
import net.minecraft.server.level.ServerPlayer;
import net.neoforged.neoforge.client.network.event.RegisterClientPayloadHandlersEvent;
import net.neoforged.neoforge.network.PacketDistributor;
import net.neoforged.neoforge.network.event.RegisterPayloadHandlersEvent;
import net.neoforged.neoforge.network.registration.PayloadRegistrar;

public class NetworkHandler {

    public static void onRegisterPayloadHandler(RegisterPayloadHandlersEvent event) {
        final PayloadRegistrar registrar = event.registrar("1").optional();
        registrar.playToClient(PacketBackupStatus.TYPE, PacketBackupStatus.CODEC);
        registrar.playToServer(PacketToastSubscribe.TYPE, PacketToastSubscribe.CODEC, PacketToastSubscribe::handle);
    }

    public static void onRegisterClientPayloadHandler(RegisterClientPayloadHandlersEvent event) {
        event.register(PacketBackupStatus.TYPE, PacketBackupStatus::handle);
    }

    public static <MSG extends CustomPacketPayload> void sendToClient(ServerPlayer player, MSG message) {
        PacketDistributor.sendToPlayer(player, message);
    }
}
