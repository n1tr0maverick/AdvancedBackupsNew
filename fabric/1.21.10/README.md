# Fabric - 1.21.10

This is the port for Fabric 1.21.10 (released October 6, 2025).

## Build Information
- **Version**: 3.8-1.21.10
- **Fabric Loader**: 0.16.9+
- **Fabric API**: 0.137.0+1.21.10
- **Java**: 21+

## Known Issues
Toast notifications use a solid background instead of the vanilla advancement toast sprite, because `DrawContext.drawGuiTexture` changed in 1.21.10. Text, the item icon, and the progress bar still render. The 26.2 port restores the sprite background.

See `BUILD_NOTES.md` for technical details and development information.

For full documentation, see the main repository README.
