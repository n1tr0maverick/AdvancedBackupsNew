package computer.heather.advancedbackups.network;

import computer.heather.advancedbackups.AdvancedBackups;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraft.network.codec.StreamCodec;
import net.minecraft.network.protocol.common.custom.CustomPacketPayload;
import net.minecraft.resources.Identifier;
import net.minecraft.world.entity.player.Player;
import net.neoforged.neoforge.network.handling.IPayloadContext;

public record PacketToastSubscribe(boolean enable) implements CustomPacketPayload {

    public static final Type<PacketToastSubscribe> TYPE = new CustomPacketPayload.Type<>(Identifier.fromNamespaceAndPath("advancedbackups", "toast_subscribe"));

    public static final StreamCodec<FriendlyByteBuf, PacketToastSubscribe> CODEC = StreamCodec.of(
        (buf, packet) -> buf.writeBoolean(packet.enable),
        buf -> new PacketToastSubscribe(buf.readBoolean())
    );

    public static void handle(PacketToastSubscribe message, IPayloadContext context) {
        Player player = context.player();

        if (message.enable() && !AdvancedBackups.players.contains(player.getStringUUID())) {
            AdvancedBackups.players.add(player.getStringUUID());
        } else if (!message.enable()) {
            AdvancedBackups.players.remove(player.getStringUUID());
        }
    }

    @Override
    public Type<? extends CustomPacketPayload> type() {
        return TYPE;
    }
}
