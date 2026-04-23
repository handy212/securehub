import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import 'dart:math' as math;

import '../../core/biometric/biometric_lock_service.dart';
import '../../core/theme/app_theme.dart';

class LockScreen extends ConsumerStatefulWidget {
  const LockScreen({super.key});

  @override
  ConsumerState<LockScreen> createState() => _LockScreenState();
}

class _LockScreenState extends ConsumerState<LockScreen> with SingleTickerProviderStateMixin {
  bool _authenticating = false;
  bool _failed = false;
  late AnimationController _shakeController;

  @override
  void initState() {
    super.initState();
    _shakeController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 400),
    );
    // Auto-trigger biometric prompt on display.
    WidgetsBinding.instance.addPostFrameCallback((_) => _authenticate());
  }

  @override
  void dispose() {
    _shakeController.dispose();
    super.dispose();
  }

  Future<void> _authenticate() async {
    if (_authenticating) return;
    setState(() {
      _authenticating = true;
      _failed = false;
    });
    
    HapticFeedback.selectionClick();
    final success =
        await ref.read(biometricLockServiceProvider).authenticate();
    
    if (!mounted) return;
    
    setState(() {
      _authenticating = false;
      _failed = !success;
    });

    if (!success) {
      HapticFeedback.heavyImpact();
      _shakeController.forward(from: 0);
    } else {
      HapticFeedback.mediumImpact();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.surface,
      body: Stack(
        children: [
          // Dot-grid background
          Positioned.fill(
            child: Opacity(
              opacity: 0.3,
              child: CustomPaint(painter: _DotGridPainter()),
            ),
          ),
          
          SafeArea(
            child: Center(
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 40),
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    // Identity
                    AnimatedScale(
                      scale: _authenticating ? 0.95 : 1.0,
                      duration: const Duration(milliseconds: 500),
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Container(
                            width: 32,
                            height: 32,
                            padding: const EdgeInsets.all(6),
                            decoration: const BoxDecoration(
                              color: AppTheme.surfaceContainerLowest,
                              shape: BoxShape.circle,
                            ),
                            child: Image.asset(
                              'assets/images/Logo-WhiteBG.png',
                              fit: BoxFit.contain,
                            ),
                          ),
                          const SizedBox(width: 8),
                          Text(
                            'SECURE HUB',
                            style: GoogleFonts.inter(
                              color: AppTheme.primary,
                              fontSize: 16,
                              fontWeight: FontWeight.w900,
                              letterSpacing: 1.0,
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 80),
                    
                    // Biometric Visual
                    AnimatedBuilder(
                      animation: _shakeController,
                      builder: (context, child) {
                        final sineValue = math.sin(_shakeController.value * 3 * math.pi);
                        return Transform.translate(
                          offset: Offset(sineValue * 10, 0),
                          child: child,
                        );
                      },
                      child: GestureDetector(
                        onTap: _authenticate,
                        child: Container(
                          width: 140,
                          height: 140,
                          decoration: BoxDecoration(
                            color: AppTheme.surfaceContainerLowest,
                            shape: BoxShape.circle,
                            boxShadow: AppTheme.cardShadow,
                            border: Border.all(
                              color: _failed 
                                  ? AppTheme.error.withValues(alpha: 0.3) 
                                  : AppTheme.outlineVariant.withValues(alpha: 0.1),
                              width: 2,
                            ),
                          ),
                          child: Stack(
                            alignment: Alignment.center,
                            children: [
                              Icon(
                                Icons.fingerprint_rounded,
                                size: 70,
                                color: _failed ? AppTheme.error : AppTheme.primary,
                              ),
                              if (_authenticating)
                                const SizedBox(
                                  width: 100,
                                  height: 100,
                                  child: CircularProgressIndicator(
                                    strokeWidth: 2,
                                    color: AppTheme.secondary,
                                  ),
                                ),
                            ],
                          ),
                        ),
                      ),
                    ),
                    
                    const SizedBox(height: 48),
                    
                    AnimatedSwitcher(
                      duration: const Duration(milliseconds: 300),
                      child: Text(
                        _failed ? 'IDENTITY NOT VERIFIED' : 'SECURE LOCK ACTIVE',
                        key: ValueKey(_failed),
                        style: GoogleFonts.inter(
                          color: _failed ? AppTheme.error : AppTheme.primary,
                          fontSize: 12,
                          fontWeight: FontWeight.w900,
                          letterSpacing: 1.5,
                        ),
                      ),
                    ),
                    
                    const SizedBox(height: 12),
                    
                    Opacity(
                      opacity: 0.7,
                      child: Text(
                        _failed 
                          ? 'Tap the icon to retry identity verification' 
                          : 'Biometric required to access your security telemetry',
                        textAlign: TextAlign.center,
                        style: GoogleFonts.inter(
                          color: AppTheme.onSurfaceVariant,
                          fontSize: 13,
                          fontWeight: FontWeight.w500,
                          height: 1.5,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// Dot-grid background painter
class _DotGridPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = AppTheme.outlineVariant
      ..strokeWidth = 1;
    const spacing = 40.0;
    for (double x = 0; x < size.width; x += spacing) {
      for (double y = 0; y < size.height; y += spacing) {
        canvas.drawCircle(Offset(x, y), 1, paint);
      }
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
