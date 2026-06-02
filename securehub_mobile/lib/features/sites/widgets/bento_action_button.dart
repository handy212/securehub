import 'package:flutter/material.dart';
import '../../../core/theme/app_theme.dart';

class BentoActionButton extends StatefulWidget {
  const BentoActionButton({
    super.key,
    required this.icon,
    required this.label,
    required this.isPrimary,
    required this.onTap,
    this.isActive = false,
    this.isFullWidth = false,
    this.compact = false,
  });

  final IconData icon;
  final String label;
  final bool isPrimary;
  final bool isActive;
  final bool isFullWidth;
  final bool compact;
  final VoidCallback? onTap;

  @override
  State<BentoActionButton> createState() => _BentoActionButtonState();
}

class _BentoActionButtonState extends State<BentoActionButton> {
  bool _isPressed = false;

  @override
  Widget build(BuildContext context) {
    final bool useBrandColor = widget.isActive;
    final bool isDisarm = widget.label.toLowerCase().contains('disarm');

    final Color activeBg = isDisarm ? AppTheme.secondary : AppTheme.primary;
    const Color activeFg = Colors.white;
    final buttonHeight = widget.isFullWidth
        ? (widget.compact ? 54.0 : 64.0)
        : (widget.compact ? 96.0 : 120.0);
    final buttonPadding = widget.compact ? 16.0 : 20.0;
    final iconSize = widget.isFullWidth
        ? (widget.compact ? 20.0 : 22.0)
        : (widget.compact ? 24.0 : 28.0);
    final labelSize = widget.compact ? 13.0 : 15.0;

    return GestureDetector(
      onTapDown: (_) => setState(() => _isPressed = true),
      onTapUp: (_) => setState(() => _isPressed = false),
      onTapCancel: () => setState(() => _isPressed = false),
      onTap: widget.onTap,
      child: AnimatedScale(
        scale: _isPressed ? 0.96 : 1.0,
        duration: const Duration(milliseconds: 100),
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 300),
          height: buttonHeight,
          padding: EdgeInsets.all(buttonPadding),
          decoration: BoxDecoration(
            gradient: useBrandColor
                ? LinearGradient(
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                    colors: [activeBg, activeBg.withValues(alpha: 0.8)],
                  )
                : (widget.isPrimary
                    ? const LinearGradient(
                        begin: Alignment.topLeft,
                        end: Alignment.bottomRight,
                        colors: [AppTheme.primary, AppTheme.primaryContainer],
                      )
                    : null),
            color: (useBrandColor || widget.isPrimary)
                ? null
                : AppTheme.surfaceContainerLowest,
            borderRadius: BorderRadius.circular(20),
            boxShadow: _isPressed ? [] : AppTheme.cardShadow,
            border: Border.all(
              color: useBrandColor
                  ? activeBg.withValues(alpha: 0.2)
                  : (widget.isPrimary
                      ? Colors.transparent
                      : AppTheme.outlineVariant.withValues(alpha: 0.1)),
              width: 1,
            ),
          ),
          child: widget.isFullWidth
              ? Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(
                      widget.icon,
                      color: (useBrandColor || widget.isPrimary)
                          ? activeFg
                          : AppTheme.secondary,
                      size: iconSize,
                    ),
                    SizedBox(width: widget.compact ? 8 : 12),
                    Text(
                      widget.label,
                      style: TextStyle(
                        fontFamily: AppTheme.fontFamily,
                        fontWeight: FontWeight.w700,
                        fontSize: labelSize,
                        color: (useBrandColor || widget.isPrimary)
                            ? activeFg
                            : AppTheme.onSurface,
                      ),
                    ),
                  ],
                )
              : Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Icon(
                      widget.icon,
                      color: (useBrandColor || widget.isPrimary)
                          ? activeFg
                          : AppTheme.secondary,
                      size: iconSize,
                    ),
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          widget.label,
                          style: TextStyle(
                            fontFamily: AppTheme.fontFamily,
                            fontWeight: FontWeight.w700,
                            fontSize: labelSize,
                            color: (useBrandColor || widget.isPrimary)
                                ? activeFg
                                : AppTheme.onSurface,
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
        ),
      ),
    );
  }
}
