import 'package:flutter/material.dart';

class SiteStatusHero extends StatefulWidget {
  const SiteStatusHero({
    super.key,
    required this.isArmed,
    required this.hasAlarm,
    required this.isSuspended,
    required this.tone,
    this.compact = false,
  });

  final bool isArmed;
  final bool hasAlarm;
  final bool isSuspended;
  final Color tone;
  final bool compact;

  @override
  State<SiteStatusHero> createState() => _SiteStatusHeroState();
}

class _SiteStatusHeroState extends SiteStatusHeroState {
  @override
  Widget build(BuildContext context) {
    final Color glowColor = widget.tone;
    final outerSize = widget.compact ? 138.0 : 180.0;
    final ringSize = widget.compact ? 114.0 : 150.0;
    final coreSize = widget.compact ? 88.0 : 120.0;
    final logoPadding = widget.compact ? 16.0 : 22.0;
    final badgeSize = widget.compact ? 20.0 : 24.0;
    final badgeInset = widget.compact ? 8.0 : 12.0;
    final badgeIconSize = widget.compact ? 10.0 : 12.0;

    final IconData statusIcon = widget.isSuspended
        ? Icons.lock_clock_rounded
        : (widget.hasAlarm
            ? Icons.priority_high_rounded
            : (widget.isArmed ? Icons.shield_rounded : Icons.shield_outlined));

    return Stack(
      alignment: Alignment.center,
      children: [
        AnimatedBuilder(
          animation: animation,
          builder: (context, child) {
            return Container(
              width: outerSize,
              height: outerSize,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                boxShadow: [
                  BoxShadow(
                    color: glowColor.withValues(alpha: 0.15 * animation.value),
                    blurRadius: (widget.compact ? 28 : 40) +
                        ((widget.compact ? 12 : 20) * animation.value),
                    spreadRadius: (widget.compact ? 6 : 10) +
                        ((widget.compact ? 6 : 10) * animation.value),
                  ),
                ],
              ),
            );
          },
        ),
        Container(
          width: ringSize,
          height: ringSize,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            border: Border.all(
              color: glowColor.withValues(alpha: 0.1),
              width: 1,
            ),
          ),
        ),
        Container(
          width: coreSize,
          height: coreSize,
          decoration: BoxDecoration(
            color: Colors.white,
            shape: BoxShape.circle,
            boxShadow: [
              BoxShadow(
                color: Colors.black.withValues(alpha: 0.05),
                blurRadius: 20,
                offset: const Offset(0, 10),
              ),
            ],
          ),
          child: ClipOval(
            child: Stack(
              children: [
                Center(
                  child: Padding(
                    padding: EdgeInsets.all(logoPadding),
                    child: Image.asset(
                      'assets/images/Logo-WhiteBG.png',
                      fit: BoxFit.contain,
                    ),
                  ),
                ),
                Positioned(
                  bottom: badgeInset,
                  right: badgeInset,
                  child: Container(
                    width: badgeSize,
                    height: badgeSize,
                    decoration: BoxDecoration(
                      color: glowColor,
                      shape: BoxShape.circle,
                      border: Border.all(
                        color: Colors.white,
                        width: widget.compact ? 2 : 3,
                      ),
                      boxShadow: [
                        BoxShadow(
                          color: glowColor.withValues(alpha: 0.4),
                          blurRadius: 8,
                        ),
                      ],
                    ),
                    child: Icon(
                      statusIcon,
                      color: Colors.white,
                      size: badgeIconSize,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }
}

abstract class SiteStatusHeroState extends State<SiteStatusHero>
    with SingleTickerProviderStateMixin {
  late AnimationController controller;
  late Animation<double> animation;

  @override
  void initState() {
    super.initState();
    controller = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 2),
    )..repeat(reverse: true);
    animation = Tween<double>(
      begin: 0.0,
      end: 1.0,
    ).animate(CurvedAnimation(parent: controller, curve: Curves.easeInOut));
  }

  @override
  void dispose() {
    controller.dispose();
    super.dispose();
  }
}
